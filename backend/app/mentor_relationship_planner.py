"""Turn exploratory input associations into two checked notebook inspections."""
from backend.app.mentor_local_progress_service import guidance_requested


def plan_relationship_comparison(state, notebook, relationship_map, message):
    if not guidance_requested(message) or relationship_map.get('status') != 'ready':
        return None
    if (relationship_map.get('input_version') != notebook.get('current_input_version')
            or relationship_map.get('dataset_kind') != notebook.get('dataset_kind')):
        return None
    current = set(state.get('current_evidence_ids') or [])
    items = [x for x in state.get('observations', []) if x['id'] in current
             and x.get('success') and x.get('version_verified') and not x.get('stale_scope')
             and x.get('input_data_version') == relationship_map['input_version']
             and x.get('analysis_contract', {}).get('supported')]
    latest_id = (state.get('current_evidence_ids') or [None])[0]
    if not items or not any(x['id'] == latest_id for x in items):
        return None
    order = {identity: rank for rank, identity in enumerate(state.get('current_evidence_ids', []))}
    items.sort(key=lambda x: order[x['id']])
    if any(x.get('status') == 'proposed' for x in state.get('proposals', [])):
        return None
    target = state.get('focus_column')
    candidates = [x for x in relationship_map.get('candidates', [])
                  if x['target_column'] == target and x['helper_column'] in state.get('available_columns', [])]
    if not candidates:
        return None
    # Keep the selected contrast across both sides; do not hop to another
    # hypothesis after seeing just the missing side.
    previous = state.get('relationship_investigation') or {}
    candidate = next((x for x in candidates if previous.get('input_version') == relationship_map['input_version']
                      and previous.get('helper_column') == x['helper_column']), candidates[0])
    helper = candidate['helper_column']
    completed = set()
    side_ids = {}
    for item in items:
        contract = item['analysis_contract']
        if (contract.get('operation') == 'distribution'
                and contract.get('measured_columns') == [helper]
                and contract.get('options', {}).get('dropna') is False
                and contract.get('options', {}).get('normalize') is True
                and contract.get('measurement_transform') == ('missing_indicator' if candidate['kind'] == 'co_missingness' else None)):
            predicate = contract.get('row_predicate')
            for method, expected in [('isna', {'op': 'missing', 'column': target}),
                                     ('notna', {'op': 'present', 'column': target})]:
                if predicate == expected:
                    completed.add(method)
                    side_ids.setdefault(method, item['id'])
    state['relationship_investigation'] = {
        'target_column': target, 'helper_column': helper, 'input_version': relationship_map['input_version'],
        'origin': relationship_map['origin'], 'candidate_kind': candidate['kind'],
        'status': 'comparison_outputs_recorded' if len(completed) == 2 else 'awaiting_notebook_comparison',
        'completed_sides': sorted(completed), 'business_rule_confirmed': False,
    }
    if len(completed) == 2:
        return {'next_action': None, 'evidence_ids': list(dict.fromkeys([latest_id] + list(side_ids.values())))}
    method = 'isna' if 'isna' not in completed else 'notna'
    transform = '.isna()' if candidate['kind'] == 'co_missingness' else ''
    code = f'df.loc[df[{target!r}].{method}(), {helper!r}]{transform}.value_counts(dropna=False, normalize=True)'
    return {'next_action': {'kind': 'inspect', 'code': code}, 'evidence_ids': [latest_id]}
