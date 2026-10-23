"""Invented datasets only: discovery is a hypothesis, not notebook evidence."""
from copy import deepcopy
import json
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from backend.app import database
from backend.app.mentor_relationship_service import build_relationship_map, load_local_relationship_map
from backend.app.mentor_relationship_planner import plan_relationship_comparison
from backend.app.mentor_research_service import generate_research_reply, build_research_request, prepare_research_context
from backend.app.mentor_research_store import load_research_state
from backend.app.models import WorkspaceNotebook, WorkspaceNotebookCell
from backend.app.notebook_scope_service import notebook_input_version
from backend.benchmarks.run_mentor_connected_followup import recorded_cell


@pytest.fixture(autouse=True)
def storage(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DATABASE_PATH', tmp_path / 'relationships.sqlite')
    database.init_db()


def frame(target='measurement', helper='status_code'):
    index = np.arange(1000)
    return pd.DataFrame({**{f'noise_{i}': index for i in range(29)},
        target: np.where(index % 4 == 0, np.nan, index), helper: np.where(index % 4 == 0, 7, 9)})


@pytest.mark.parametrize('target,helper', [('measurement', 'status_code'), ('price', 'region'), ('duration', 'phase')])
def test_discovery_replicates_association_in_different_schemas_without_semantics(target, helper):
    df = frame(target, helper)
    original = df.copy(deep=True)
    report = build_relationship_map(df, input_version='v1')
    candidate = next(x for x in report['candidates'] if x['target_column'] == target and x['helper_column'] == helper)
    assert candidate['strength'] == 1 and candidate['status'] == 'replicated_exploratory_association'
    assert not candidate['causality_established'] and not report['business_rule_confirmed']
    assert not report['full_source_verified'] and report['origin'] == 'persisted_input_not_notebook_df'
    assert df.equals(original)
    assert report['pairs_examined'] <= report['pair_budget']


def test_discovery_excludes_absent_constant_random_and_identifier_patterns():
    index = np.arange(1000)
    # All four combinations occur evenly: grouping reveals no missingness gap.
    df = pd.DataFrame({'target': np.where(index % 2 == 0, np.nan, index),
                       'independent': (index // 2) % 2, 'constant': 'x', 'identifier': index})
    assert build_relationship_map(df, input_version='v1')['candidates'] == []


def test_discovery_selected_pattern_must_repeat_on_the_held_out_split():
    df = frame()
    order = np.random.default_rng(42).permutation(len(df))
    held = order[len(df) // 2:]
    # Reverse the signal only in validation: discovery must not bless it.
    df.loc[held, 'status_code'] = np.where(df.loc[held, 'measurement'].isna(), 9, 7)
    assert not build_relationship_map(df, input_version='v1')['candidates']


def test_rare_groups_and_raw_values_are_not_exported_as_candidates():
    df = pd.DataFrame({'target': [None] * 3 + list(range(997)),
                       'category': ['PRIVATE-IDENTIFIER'] * 3 + ['common'] * 997})
    report = build_relationship_map(df, input_version='v1')
    assert not report['candidates']
    assert 'PRIVATE-IDENTIFIER' not in json.dumps(report) and 'common' not in json.dumps(report)
    assert not report['category_values_stored']


def test_co_missingness_is_detected_and_wide_coverage_is_explicit():
    df = frame()
    df['related'] = df['measurement']
    for i in range(80):
        df[f'other_{i}'] = i
    report = build_relationship_map(df, input_version='v1')
    assert report['columns_examined'] == 64 and report['columns_omitted'] == len(df.columns) - 64
    assert any(x['kind'] == 'co_missingness' and x['helper_column'] == 'related' for x in report['candidates'])


def test_small_and_invalid_schemas_do_not_produce_confident_relationships():
    assert build_relationship_map(frame().head(20), input_version='v1')['status'] == 'insufficient_rows'
    with pytest.raises(ValueError):
        build_relationship_map(pd.DataFrame([[1, 2]], columns=['x', 'x']), input_version='v1')


def context(df):
    cell = recorded_cell('count', "df['measurement'].isna().sum()", 250, 'measurement', 'v1', len(df))
    notebook = {'notebook_id': 'n1', 'dataset_kind': 'working', 'configured_development_rows': len(df),
                'current_input_version': 'v1', 'latest_cell': cell, 'recent_cells': [cell]}
    return {'workspace_id': 'relations', 'ui_context': {'language': 'tr'},
            'dataset_profile_summary': {'columns': list(df.columns)},
            'local_relationship_map': build_relationship_map(df, input_version='v1'),
            'artifacts': {'selected_notebook': notebook}}


@pytest.mark.parametrize('start_preview', [False, True])
@pytest.mark.parametrize('kind', ['categorical', 'co_missingness'])
@pytest.mark.parametrize('contradict_input', [False, True])
def test_actual_mentor_proposes_both_populations_without_repeating_or_using_a_provider(start_preview, kind, contradict_input):
    df = frame()
    helper = 'status_code'
    if kind == 'co_missingness':
        df = df.drop(columns='status_code')
        df['related'] = df['measurement']
        helper = 'related'
    ctx = context(df)
    if contradict_input:
        # A notebook df can differ from its persisted input. The explanation
        # must follow the actual two outputs, not the original candidate.
        independent = (np.arange(len(df)) // 4) % 2
        df[helper] = np.where(independent == 0, np.nan, np.arange(len(df))) if kind == 'co_missingness' else independent
    notebook = ctx['artifacts']['selected_notebook']
    if start_preview:
        preview = recorded_cell('preview', "df.loc[df['measurement'].isna()].head(5)",
            df.loc[df['measurement'].isna()].head(5), 'measurement', 'v1', len(df))
        notebook['latest_cell'] = preview
        notebook['recent_cells'].insert(0, preview)
    with patch('backend.app.mentor_research_service.get_ai_runtime') as provider:
        for method in ('isna', 'notna'):
            reply = generate_research_reply(ctx, 'Sonraki tek adımı söyle. Kodu verme.', [], allow_provider=False)
            state = load_research_state('relations', 'n1')
            assert state['last_validation']['accepted'], reply
            assert state['last_validation']['policy'] == 'relationship_comparison_v1'
            assert 'notebook’taki df için henüz doğrulanmış değil' in reply
            assert '```' not in reply
            code = state['workflow']['active_step']['code']
            assert f'.{method}()' in code and 'normalize=True' in code
            shown = generate_research_reply(ctx, 'Kodu göster.', [], allow_provider=False)
            assert code in shown
            same = generate_research_reply(ctx, 'Anlamadım. Beraber ilerleyelim, kodu gösterme.', [], allow_provider=False)
            assert '```' not in same
            # Execute only the expected fixed safe expression, never eval.
            mask = df['measurement'].isna() if method == 'isna' else df['measurement'].notna()
            series = df.loc[mask, helper]
            if kind == 'co_missingness':
                assert "].isna().value_counts" in code
                series = series.isna()
            result = series.value_counts(dropna=False, normalize=True)
            cell = recorded_cell(method, code, result, 'measurement', 'v1', len(df))
            notebook['recent_cells'].insert(0, cell)
            notebook['latest_cell'] = cell
        final = generate_research_reply(ctx, 'Sonraki tek adım ne?', [], allow_provider=False)
        assert 'Kaydedilen iki dağılımı karşılaştırınca' in final
        if contradict_input:
            assert 'yaklaşık %50.0' in final and 'yaklaşık 0.0 yüzde puan' in final
        else:
            assert 'yaklaşık %100.0' in final and 'yaklaşık %0.0' in final
        assert 'tek başına kanıtlamaz' in final
    provider.assert_not_called()
    state = load_research_state('relations', 'n1')
    assert state['relationship_investigation']['status'] == 'comparison_outputs_recorded'
    assert not state['relationship_investigation']['business_rule_confirmed']
    assert len(state['proposals']) == 2
    assert all(p['status'] == 'observed' for p in state['proposals'])


@pytest.mark.parametrize('code', [
    "df[['measurement','status_code']].isna().value_counts()",
    "df.isna().value_counts()", "df['measurement'].isna(1).value_counts()",
    "df['measurement'].fillna(0).value_counts()", "alias['measurement'].isna().value_counts()",
    "df['measurement'].apply(str).value_counts()",
])
def test_indicator_contract_does_not_accept_arbitrary_transformations(code):
    from backend.app.mentor_observation_contract import expression_contract
    assert expression_contract(code).get('supported') is False


def test_missing_indicator_is_labelled_as_a_measurement_not_a_raw_value():
    from backend.app.mentor_observation_contract import observation_contract, observation_text
    code = "df.loc[df['measurement'].notna(), 'related'].isna().value_counts(normalize=True, dropna=False)"
    contract = observation_contract(code, {'success': True, 'output': 'False    1.0'})
    assert contract['supported'] and contract['measurement_transform'] == 'missing_indicator'
    assert contract['row_predicate'] == {'op': 'present', 'column': 'measurement'}
    text = observation_text(contract, 'tr')
    assert 'True=boş, False=dolu' in text and 'ham değerleri değil' in text


@pytest.mark.parametrize('output', [
    'a    10\nb    20\nName: proportion, dtype: float64',
    'a    0.2\nb    0.3\nName: proportion, dtype: float64',
    'a    0.5\na    0.5\nName: proportion, dtype: float64',
    'a    0.5\n...\nb    0.5\nName: proportion, dtype: float64',
    'Series([], Name: proportion, dtype: float64)',
])
def test_partial_ambiguous_empty_or_non_proportion_output_is_not_interpreted(output):
    from backend.app.mentor_observation_contract import observation_contract
    from backend.app.mentor_relationship_interpretation import proportions
    code = "df.loc[df['measurement'].isna(), 'phase'].value_counts(dropna=False, normalize=True)"
    item = {'analysis_contract': observation_contract(code, {'success': True, 'output': output})}
    assert proportions(item) is None


def test_stale_map_and_explanation_only_cannot_assign_a_comparison():
    ctx = context(frame())
    notebook = ctx['artifacts']['selected_notebook']
    notebook['available_columns'] = ctx['dataset_profile_summary']['columns']
    state = prepare_research_context(notebook, 'measurement')
    report = ctx['local_relationship_map']
    assert plan_relationship_comparison(state, notebook, report, 'Sonucu açıkla. Yeni görev verme.') is None
    stale = deepcopy(report)
    stale['input_version'] = 'old'
    assert plan_relationship_comparison(state, notebook, stale, 'Devam edelim.') is None


def test_relationship_map_is_not_in_the_provider_request():
    ctx = context(frame())
    notebook = ctx['artifacts']['selected_notebook']
    notebook['available_columns'] = ctx['dataset_profile_summary']['columns']
    state = prepare_research_context(notebook, 'measurement')
    ctx['local_relationship_map']['PRIVATE-CANARY'] = 'DO-NOT-SEND'
    payload = build_research_request(ctx, state, 'Sonucu açıkla.', [])
    assert 'DO-NOT-SEND' not in json.dumps(payload)
    assert 'local_relationship_map' not in payload
    from backend.app.mentor_prompt_context_service import compact_mentor_workspace_context
    assert 'DO-NOT-SEND' not in json.dumps(compact_mentor_workspace_context(ctx))


def test_saved_workspace_chat_builds_and_reuses_cache_then_invalidates_it(tmp_path, monkeypatch):
    monkeypatch.setenv('AI_NOTEBOOK_RESEARCH_ENABLED', 'true')
    monkeypatch.setattr('backend.app.workspace_data_service.get_workspace_data_dir', lambda _: tmp_path)
    monkeypatch.setattr('backend.app.notebook_scope_service.get_workspace_data_dir', lambda _: tmp_path)
    from fastapi.testclient import TestClient
    from backend.app.main import app
    client = TestClient(app)
    database.insert_learner_profile(learner_id='local-map', answer_length='concise', learning_style='guided', code_support='medium')
    created = client.post('/workspaces', json={'learner_id': 'local-map', 'title': 'Relationship test'})
    assert created.status_code == 200
    workspace = database.get_workspace(workspace_id=created.json()['workspace_id'], learner_id='local-map')
    df = frame()
    df.to_csv(tmp_path / 'working.csv', index=False)
    workspace.development_sample_size = len(df)
    workspace.dataset_profile = {'columns': list(df.columns), 'null_counts': {'measurement': 250}}
    notebook = WorkspaceNotebook(notebook_id='n1', name='Investigation', dataset_kind='working',
        created_at='2026-10-23', updated_at='2026-10-23', cells=[])
    version = notebook_input_version(workspace.workspace_id, notebook, len(df))
    cell = recorded_cell('count', "df['measurement'].isna().sum()", 250, 'measurement', version, len(df))
    notebook.cells = [WorkspaceNotebookCell(**cell)]
    workspace.notebooks = [notebook]
    database.save_workspace(workspace=workspace)
    with patch('backend.app.mentor_research_service.get_ai_runtime') as provider:
        response = client.post('/chat', json={'learner_id': 'local-map', 'workspace_id': workspace.workspace_id,
            'session_id': workspace.mentor_session_id, 'message': 'measurement için sonraki tek adım ne? Kodu verme.',
            'ui_context': {'selected_notebook_id': 'n1', 'workbench_view': 'notebook', 'language': 'tr'}})
    provider.assert_not_called()
    assert response.status_code == 200, response.text
    state = load_research_state(workspace.workspace_id, 'n1')
    assert state['last_validation']['policy'] == 'relationship_comparison_v1'
    from backend.app.mentor_context_service import build_trusted_notebook_state
    snapshot = build_trusted_notebook_state(workspace=workspace, ui_context={'selected_notebook_id': 'n1'})
    with patch('backend.app.mentor_relationship_service.build_relationship_map') as scan:
        cached = load_local_relationship_map(workspace, snapshot)
    scan.assert_not_called()
    assert cached['input_version'] == version and cached['candidates']
    # An interrupted/corrupt cache must not break chat or become fake evidence.
    with database.get_connection() as connection:
        connection.execute('UPDATE mentor_relationship_cache SET map_json=?', ('{broken',))
    rebuilt = load_local_relationship_map(workspace, snapshot)
    assert rebuilt['candidates'] == cached['candidates']
    # Change persisted input: cache and old notebook evidence are no longer current.
    df['status_code'] = 1
    df.to_csv(tmp_path / 'working.csv', index=False)
    snapshot = build_trusted_notebook_state(workspace=workspace, ui_context={'selected_notebook_id': 'n1'})
    refreshed = load_local_relationship_map(workspace, snapshot)
    assert refreshed['input_version'] != version and not refreshed['candidates']
