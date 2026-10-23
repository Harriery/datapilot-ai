"""Bounded local missingness discovery, separate from notebook execution facts.

No model calls, category values, example rows or arbitrary query execution.
Candidates are exploratory associations replicated on a held-out split, never
business rules or causal conclusions. Cache identity follows the input file.
"""
from contextlib import closing
import hashlib
import json

import numpy as np
import pandas as pd

from backend.app import database, workspace_data_service
from backend.app.notebook_scope_service import notebook_input_version


MAX_ROWS = 20000
MAX_COLUMNS = 64
MAX_TARGETS = 12
MAX_FILE_BYTES = 32 * 1024 * 1024
MIN_GROUP = 20
MIN_EFFECT = .25
VERSION = 1


def _difference(missing, group, discovery, validation):
    """Check the SAME selected contrast in discovery and held-out records."""
    rates = []
    for partition in (discovery, validation):
        a, b = partition & group, partition & ~group
        if min(int(a.sum()), int(b.sum())) < MIN_GROUP:
            return None
        rates.append(float(missing[a].mean()) - float(missing[b].mean()))
    if abs(rates[0]) < MIN_EFFECT or abs(rates[1]) < MIN_EFFECT or rates[0] * rates[1] <= 0:
        return None
    return [round(value, 4) for value in rates]


def build_relationship_map(frame, *, input_version, dataset_kind='working', selection='bounded_prefix'):
    if not frame.columns.is_unique or not all(isinstance(c, str) for c in frame.columns):
        raise ValueError('Relationship discovery requires distinct string column names')
    total_rows, total_columns = frame.shape
    # Select target-bearing columns first; explicitly report budget coverage.
    nulls = frame.isna().sum().sort_values(ascending=False, kind='stable')
    targets = [c for c in nulls.index if 0 < nulls[c] < total_rows][:MAX_TARGETS]
    columns = list(dict.fromkeys(targets + list(frame.columns)))[:MAX_COLUMNS]
    df = frame.loc[:, columns].iloc[:MAX_ROWS]
    result = {'schema_version': VERSION, 'status': 'ready', 'input_version': input_version,
        'dataset_kind': dataset_kind, 'origin': 'persisted_input_not_notebook_df',
        'selection': selection, 'rows': len(df), 'columns_examined': len(columns),
        'columns_omitted': total_columns - len(columns), 'rows_omitted_from_frame': total_rows - len(df),
        'target_budget': MAX_TARGETS, 'pair_budget': MAX_TARGETS * (MAX_COLUMNS - 1),
        'pairs_examined': 0, 'candidates': [], 'business_rule_confirmed': False,
        'full_source_verified': False, 'category_values_stored': False}
    if len(df) < MIN_GROUP * 4:
        result['status'] = 'insufficient_rows'
        return result
    order = np.random.default_rng(42).permutation(len(df))
    discovery = np.zeros(len(df), dtype=bool)
    discovery[order[:len(df) // 2]] = True
    validation = ~discovery
    masks = {c: df[c].isna().to_numpy() for c in columns}
    for target in targets:
        missing = masks[target]
        for helper in columns:
            if helper == target:
                continue
            result['pairs_examined'] += 1
            choices = []
            difference = _difference(missing, masks[helper], discovery, validation)
            if difference:
                choices.append(('co_missingness', difference))
            # Categories are encoded locally. No labels or literal values leave
            # this calculation, and numeric 0/1 is never assigned semantics.
            codes, unique = pd.factorize(df[helper], sort=False)
            if 2 <= len(unique) <= 12:
                groups = sorted(set(codes[discovery]))
                rates = [(g, float(missing[discovery & (codes == g)].mean()))
                         for g in groups if int((discovery & (codes == g)).sum()) >= MIN_GROUP]
                if len(rates) >= 2:
                    high = max(rates, key=lambda x: x[1])[0]
                    difference = _difference(missing, codes == high, discovery, validation)
                    if difference:
                        choices.append(('categorical_missingness', difference))
            if choices:
                kind, effects = max(choices, key=lambda x: min(abs(v) for v in x[1]))
                result['candidates'].append({'target_column': target, 'helper_column': helper,
                    'kind': kind, 'discovery_difference': effects[0],
                    'holdout_difference': effects[1], 'strength': min(abs(v) for v in effects),
                    'status': 'replicated_exploratory_association', 'causality_established': False})
    result['candidates'].sort(key=lambda x: (-x['strength'], x['target_column'], x['helper_column']))
    # Keep a bounded set for each target; other targets must not crowd it out.
    result['candidates'] = [item for target in targets for item in
        [x for x in result['candidates'] if x['target_column'] == target][:3]]
    return result


def _prepare(connection):
    connection.execute('''CREATE TABLE IF NOT EXISTS mentor_relationship_cache (
        workspace_id TEXT NOT NULL, cache_key TEXT NOT NULL, map_json TEXT NOT NULL,
        created_at INTEGER NOT NULL DEFAULT (unixepoch()),
        PRIMARY KEY(workspace_id, cache_key))''')


def load_local_relationship_map(workspace, notebook_state):
    """Lazy first-mentor scan of bounded working input, cached across restarts.

    Do not scan the large raw source from chat or imply matching in-memory df.
    Missing files, unsupported scopes or a changed file yield no candidate.
    """
    unavailable = {'status': 'unavailable', 'candidates': []}
    if not notebook_state or notebook_state.get('dataset_kind') != 'working':
        return unavailable
    notebook = next((n for n in workspace.notebooks if n.notebook_id == notebook_state['notebook_id']), None)
    version = notebook_state.get('current_input_version')
    limit = int(workspace.development_sample_size or workspace.development_sample_row_count
                or workspace.development_sample_max_size or 1000)
    if not notebook or not version:
        return unavailable
    key = hashlib.sha256(json.dumps([VERSION, version, limit]).encode()).hexdigest()
    with closing(database.get_connection()) as connection, connection:
        _prepare(connection)
        row = connection.execute('SELECT map_json FROM mentor_relationship_cache WHERE workspace_id=? AND cache_key=?',
                                 (workspace.workspace_id, key)).fetchone()
    if row:
        try:
            cached = json.loads(row[0])
            if isinstance(cached, dict) and cached.get('schema_version') == VERSION:
                return cached
        except (ValueError, TypeError):
            pass  # An unusable cache is rebuilt, never treated as evidence.
    try:
        path = workspace_data_service.get_workspace_data_dir(workspace.workspace_id) / 'working.csv'
        if path.stat().st_size > MAX_FILE_BYTES:
            return {'status': 'file_budget_exceeded', 'candidates': []}
        header = list(pd.read_csv(path, nrows=0).columns)
        # Profile null counts prioritize columns before reading wide CSVs.
        counts = (workspace.dataset_profile or {}).get('null_counts') or {}
        counts = {c: value for c, value in counts.items() if type(value) is int and value > 0} if isinstance(counts, dict) else {}
        targets = sorted([c for c in header if counts.get(c, 0) > 0], key=lambda c: -counts[c])[:MAX_TARGETS]
        selected = list(dict.fromkeys(targets + header))[:MAX_COLUMNS]
        frame = pd.read_csv(path, usecols=selected, nrows=min(limit, MAX_ROWS) + 1)
        truncated = len(frame) > min(limit, MAX_ROWS)
        frame = frame.iloc[:min(limit, MAX_ROWS)]
        if notebook_input_version(workspace.workspace_id, notebook, limit) != version:
            return {'status': 'input_changed', 'candidates': []}
        result = build_relationship_map(frame, input_version=version,
            selection='bounded_prefix' if truncated else 'whole_persisted_working_input')
        result['columns_omitted'] = len(header) - len(selected)
        result['row_limit_reached'] = truncated
    except (OSError, ValueError, pd.errors.ParserError, pd.errors.EmptyDataError):
        return unavailable
    with closing(database.get_connection()) as connection, connection:
        _prepare(connection)
        connection.execute('INSERT OR REPLACE INTO mentor_relationship_cache (workspace_id,cache_key,map_json) VALUES (?,?,?)',
                           (workspace.workspace_id, key, json.dumps(result)))
        connection.execute('DELETE FROM mentor_relationship_cache WHERE workspace_id=? AND cache_key NOT IN '
                           '(SELECT cache_key FROM mentor_relationship_cache WHERE workspace_id=? '
                           'ORDER BY created_at DESC, rowid DESC LIMIT 4)', (workspace.workspace_id, workspace.workspace_id))
    return result
