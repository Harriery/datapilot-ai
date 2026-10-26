"""Whole task lifecycle invariants, independent of a particular provider answer.

Synthetic schemas and controlled decisions only. These are not live model or
human-learning acceptance results.
"""
from copy import deepcopy
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from backend.app import database
from backend.app.mentor_research_service import GroundedResearchDecision, generate_research_reply
from backend.app.mentor_research_store import load_research_state, save_research_state
from backend.app.mentor_preview_evidence_service import missing_preview_rows
from backend.benchmarks.run_mentor_connected_followup import recorded_cell


@pytest.fixture(autouse=True)
def storage(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DATABASE_PATH', tmp_path / 'workflow.sqlite')
    database.init_db()


def context():
    columns = [f'feature_{i}' for i in range(29)] + ['measurement', 'indicator']
    rows = [dict.fromkeys(columns, None) for _ in range(3)]
    for index, row in enumerate(rows):
        row['indicator'] = bool(index % 2)
    preview = {'cell_id': 'examples', 'section_title': 'measurement',
               'code': "df.loc[df['measurement'].isna()].head(5)", 'last_execution': {
                   'success': True, 'output': 'measurement indicator ...\n0 NaN False',
                   'preview_rows': rows, 'input_row_count': 42, 'input_total_row_count': 42,
                   'input_data_version': 'v1', 'dataset_kind': 'working', 'executed_at': 'receipt-1'}}
    return {'workspace_id': 'workflow', 'task_brief': 'Investigate a quality issue before choosing a treatment.',
            'learner_skills': [{'skill_name': 'null_analysis', 'status': 'new'}],
            'ui_context': {'language': 'tr'}, 'dataset_profile_summary': {'columns': columns},
            'artifacts': {'selected_notebook': {'notebook_id': 'n1', 'dataset_kind': 'working',
                'configured_development_rows': 42, 'current_input_version': 'v1',
                'latest_cell': preview, 'recent_cells': [preview], 'available_columns': columns}}}


def saved():
    return load_research_state('workflow', 'n1')


def provider_for(code):
    calls = []
    def respond(*args, **kwargs):
        payload = json.loads(kwargs['input'])
        calls.append(payload)
        return SimpleNamespace(output_parsed=GroundedResearchDecision(
            next_action={'kind': 'inspect', 'code': code} if len(calls) == 1 else None,
            evidence_ids=[payload['latest_observation_id']]))
    return respond, calls


def runtime():
    return SimpleNamespace(client=None, provider='groq', model='controlled-test')


OPERATIONS = [
    ("df['measurement'].isna().sum()", '17', 'isna'),
    ("df['measurement'].value_counts(dropna=False)", '1.0    7\nNaN    17', 'value_counts'),
    ("df['measurement'].head(3)", '0 NaN\n1 1.0', 'head'),
    ("df['measurement'].tail(3)", '40 NaN\n41 1.0', 'tail'),
    ("df['measurement'].min()", '-2.0', 'min'),
    ("df['measurement'].max()", '11.0', 'max'),
    ("df['measurement'].mean()", '4.0', 'mean'),
    ("df['measurement'].median()", '3.0', 'median'),
    ("df['measurement'].count()", '25', 'count'),
    ("df['measurement'].nunique()", '8', 'nunique'),
]


@pytest.mark.parametrize('code,output,concept', OPERATIONS)
def test_one_active_step_survives_help_reload_and_no_execution_then_closes_on_new_receipt(code, output, concept):
    ctx = context()
    respond, requests = provider_for(code)
    with patch('backend.app.mentor_research_service.get_ai_runtime', return_value=runtime()), \
         patch('backend.app.mentor_research_service.guarded_responses_parse', side_effect=respond) as model:
        first = generate_research_reply(ctx, 'measurement incelemesinde sonraki tek adımı söyle. Kodu verme.', [])
        initial = saved()
        step_id = initial['workflow']['active_step']['id']
        assert initial['workflow']['active_step']['status'] == 'awaiting_execution'
        assert requests[0]['investigation_context']['learner_skills'][0]['skill_name'] == 'null_analysis'
        for question in ['Tamam şimdi ne yapacağız, nereden araştırmaya başlayacağız?',
                         'Yaptım, gördün mü?', 'Anlamadım, beraber ilerleyelim.', 'Kodu gösterme. Nasıl yapacağım?']:
            reply = generate_research_reply(ctx, question, [], allow_provider=False)
            state = saved()
            assert len(state['proposals']) == 1
            assert state['workflow']['active_step']['id'] == step_id
            assert state['workflow']['active_step']['status'] == 'awaiting_execution'
            assert state['last_validation']['validation_kind'] == 'pending_step_support'
            assert concept in reply and '```' not in reply and len(reply) < 1100
        assert model.call_count == 1
        shown = generate_research_reply(ctx, 'Şimdi kodu göster.', [], allow_provider=False)
        assert f'```python\n{code}\n```' in shown

        notebook = ctx['artifacts']['selected_notebook']
        result = {'cell_id': 'answer', 'section_title': 'measurement', 'code': code,
                  'last_execution': {'success': True, 'output': output, 'input_row_count': 42,
                      'input_total_row_count': 42, 'input_data_version': 'v1',
                      'dataset_kind': 'working', 'executed_at': 'receipt-2'}}
        notebook['recent_cells'] = [result, notebook['latest_cell']]
        notebook['latest_cell'] = result
        generate_research_reply(ctx, 'Sonucu açıkla. Yeni görev verme.', [])
        state = saved()
        assert state['workflow']['active_step']['id'] == step_id
        assert state['workflow']['active_step']['status'] == 'observed'
        assert state['workflow']['phase'] == 'reason'
        assert state['proposals'][0]['status'] == 'observed'
        assert len(state['proposals']) == 1


def test_wide_preview_keeps_late_target_boolean_types_and_detects_ambiguity():
    ctx = context()
    from backend.app.mentor_research_service import prepare_research_context, build_research_request
    notebook = ctx['artifacts']['selected_notebook']
    state = prepare_research_context(notebook, 'measurement')
    rows = missing_preview_rows(state['observations'][0])
    assert len(rows) == 3 and len(rows[0]) <= 12
    assert rows[0]['measurement'] is None and rows[0]['indicator'] is False
    payload = build_research_request(ctx, state, 'Ne görüyoruz?', [])
    assert payload['current_observations'][0]['preview_rows'][0]['indicator'] is False
    assert payload['current_observations'][0]['preview_projection']['original_field_count'] == 31
    for row in notebook['latest_cell']['last_execution']['preview_rows']:
        row['second_indicator'] = True
    state = prepare_research_context(notebook, 'measurement')
    preferred = [f'feature_{i}' for i in range(20)]
    projected = missing_preview_rows(state['observations'][0], preferred)
    assert 'indicator' in projected[0] and 'second_indicator' in projected[0]
    assert type(projected[0]['indicator']) is bool


def test_refresh_explanation_applies_only_to_the_same_row_selection():
    from backend.app.mentor_investigation_presenter import task_purpose
    from backend.app.mentor_observation_contract import expression_contract
    current = expression_contract("df['measurement'].isna().sum()")
    old = expression_contract("df.loc[df['indicator'] == True, 'measurement'].isna().sum()")
    state = {'observations': [{'analysis_contract': old, 'version_verified': False}]}
    assert 'Önceki sayımın' not in task_purpose(current, state, 'tr')
    state['observations'][0]['analysis_contract'] = current
    assert 'Önceki sayımın' in task_purpose(current, state, 'tr')


def test_processed_notebook_cannot_start_from_a_source_profile_alone():
    from backend.app.mentor_investigation_service import schema_start_action
    ctx = context()
    notebook = ctx['artifacts']['selected_notebook']
    notebook['dataset_kind'] = 'processed'
    state = {'focus_column': 'measurement', 'available_columns': ['measurement']}
    assert schema_start_action(state, notebook) is None


def test_pending_source_question_is_explained_without_duplicate_planning():
    from backend.app.mentor_investigation_service import register_action
    from backend.app.mentor_research_service import prepare_research_context
    ctx = context()
    notebook = ctx['artifacts']['selected_notebook']
    state = prepare_research_context(notebook, 'measurement')
    register_action(state, {'kind': 'clarify', 'focus_column': 'measurement',
        'code': None, 'instruction': 'Kaynak açıklamasını paylaş.', 'why': '', 'evidence_ids': []}, notebook)
    save_research_state('workflow', 'n1', state)
    with patch('backend.app.mentor_research_service.get_ai_runtime') as provider:
        for message in ('Biraz daha açık anlatır mısın?', 'Nereden devam edeceğiz?'):
            reply = generate_research_reply(ctx, message, [], allow_provider=False)
            assert 'analiz sonucu istemiyorum' in reply and '```' not in reply
            assert len(saved()['proposals']) == 1
            assert saved()['workflow']['active_step']['status'] == 'awaiting_answer'
        generate_research_reply(ctx, 'Kaynak açıklaması elimde yok. Devam edelim.', [], allow_provider=False)
    provider.assert_not_called()
    history = saved()['workflow']['step_history']
    assert any(x['kind'] == 'clarify' and x['status'] == 'answered_unavailable' for x in history)
    assert saved()['workflow']['active_step']['kind'] == 'inspect'


def test_workflow_scenario_cli_reports_its_limits_and_restores_database(tmp_path):
    from backend.benchmarks.run_mentor_workflow_scenarios import main
    original = database.DATABASE_PATH
    with patch('backend.app.mentor_research_service.get_ai_runtime') as runtime_mock:
        assert main(['--output-dir', str(tmp_path / 'reports')]) == 0
    runtime_mock.assert_not_called()
    assert database.DATABASE_PATH == original
    report = json.loads(next((tmp_path / 'reports').glob('*/report.json')).read_text(encoding='utf-8'))
    assert len(report['results']) == 3 and all(x['passed'] for x in report['results'])
    assert report['provider_calls'] == 0
    assert not report['live_model_quality_tested'] and not report['beginner_usability_tested']
    assert not report['learning_benefit_proven'] and not report['full_project_completion_proven']


def test_failed_or_unrelated_execution_does_not_complete_or_reassign_count():
    ctx = context()
    code = "df['measurement'].isna().sum()"
    respond, _ = provider_for(code)
    with patch('backend.app.mentor_research_service.get_ai_runtime', return_value=runtime()), \
         patch('backend.app.mentor_research_service.guarded_responses_parse', side_effect=respond) as model:
        generate_research_reply(ctx, 'measurement için sonraki adım ne?', [])
        notebook = ctx['artifacts']['selected_notebook']
        wrong = deepcopy(notebook['latest_cell'])
        wrong.update(cell_id='wrong', code="df['unknown_column'].isna().sum()")
        wrong['last_execution'].update(success=False, output='KeyError', executed_at='failed-2')
        notebook['latest_cell'] = wrong
        notebook['recent_cells'] = [wrong] + notebook['recent_cells']
        reply = generate_research_reply(ctx, 'Neden olmadı, nasıl ilerleyelim?', [])
        assert 'tamamlanmış sayılmıyor' in reply and 'yeni çıktı istemeyeceğim' in reply
        assert saved()['workflow']['active_step']['status'] == 'awaiting_execution'
        assert len(saved()['proposals']) == 1 and model.call_count == 1


@pytest.mark.parametrize('new_kind', ['working', 'raw'])
def test_scope_change_requires_new_version_before_completion(new_kind):
    ctx = context()
    code = "df['measurement'].isna().sum()"
    respond, _ = provider_for(code)
    with patch('backend.app.mentor_research_service.get_ai_runtime', return_value=runtime()), \
         patch('backend.app.mentor_research_service.guarded_responses_parse', side_effect=respond):
        generate_research_reply(ctx, 'measurement için sonraki adım?', [])
        notebook = ctx['artifacts']['selected_notebook']
        notebook['current_input_version'] = 'v2'
        notebook['dataset_kind'] = new_kind
        reply = generate_research_reply(ctx, 'Nereden devam edeceğim?', [], allow_provider=False)
        assert 'kapsamı değişti' in reply
        assert saved()['workflow']['active_step']['status'] == 'needs_revalidation'
        refreshed = {'cell_id': 'new-count', 'code': code, 'last_execution': {
            'success': True, 'output': '17', 'input_row_count': 42,
            'input_total_row_count': 42, 'input_data_version': 'v2',
            'dataset_kind': new_kind, 'executed_at': 'new-scope-execution'}}
        notebook['recent_cells'] = [refreshed] + notebook['recent_cells']
        notebook['latest_cell'] = refreshed
        generate_research_reply(ctx, 'Sonucu açıkla. Yeni görev verme.', [])
        assert saved()['workflow']['active_step']['status'] == 'observed'
        assert saved()['workflow']['active_step']['dataset_kind'] == new_kind


def test_finding_is_recorded_only_on_explicit_deferral_and_is_idempotent():
    ctx = context()
    notebook = ctx['artifacts']['selected_notebook']
    count = {'cell_id': 'count', 'code': "df['measurement'].isna().sum()", 'section_title': 'measurement',
             'last_execution': {'success': True, 'output': '17', 'input_row_count': 42,
                 'input_total_row_count': 42, 'input_data_version': 'v1', 'dataset_kind': 'working',
                 'executed_at': 'receipt-2'}}
    notebook['recent_cells'] = [count] + notebook['recent_cells']
    notebook['latest_cell'] = count
    from backend.app.mentor_research_service import prepare_research_context
    state = prepare_research_context(notebook, 'measurement')
    state['definition_availability'] = {'focus_column': 'measurement', 'status': 'unavailable'}
    save_research_state('workflow', 'n1', state)
    with patch('backend.app.mentor_research_service.get_ai_runtime') as runtime_mock:
        reply = generate_research_reply(ctx, 'Şimdilik değişiklik yapmadan bulguyu kaydet.', [], allow_provider=False)
        generate_research_reply(ctx, 'Şimdilik değişiklik yapmadan bulguyu kaydet.', [], allow_provider=False)
    runtime_mock.assert_not_called()
    flow = saved()['workflow']
    assert flow['status'] == 'documented_deferred' and len(flow['findings']) == 1
    assert flow['findings'][0]['decision'] == 'deferred'
    assert not flow['findings'][0]['data_changed'] and not flow['findings'][0]['full_source_verified']
    assert 'mentor günlüğüne' in reply and 'bütün projenin tamamlanması' in reply
    from backend.app.mentor_research_service import prepare_research_context
    changed = prepare_research_context(notebook, 'feature_0 sütununa geçelim.', saved())
    assert changed['focus_column'] == 'feature_0'
    assert changed['finding_ledger'][0]['focus_column'] == 'measurement'
    assert not changed['workflow']['findings']


def test_editing_code_without_a_new_execution_receipt_cannot_complete_a_task():
    ctx = context()
    notebook = ctx['artifacts']['selected_notebook']
    old = deepcopy(notebook['latest_cell'])
    old.update(cell_id='answer', code="df['measurement'].nunique()")
    old['last_execution'].update(output='17', executed_at='old-receipt')
    notebook['recent_cells'].append(old)
    code = "df['measurement'].isna().sum()"
    respond, _ = provider_for(code)
    with patch('backend.app.mentor_research_service.get_ai_runtime', return_value=runtime()), \
         patch('backend.app.mentor_research_service.guarded_responses_parse', side_effect=respond) as model:
        generate_research_reply(ctx, 'measurement için sonraki adım?', [])
        edited = deepcopy(old)
        edited['code'] = code
        notebook['latest_cell'] = edited
        notebook['recent_cells'] = [edited, notebook['recent_cells'][0]]
        generate_research_reply(ctx, 'Yaptım, gördün mü?', [], allow_provider=False)
        assert saved()['workflow']['active_step']['status'] == 'awaiting_execution'
        assert len(saved()['proposals']) == 1 and model.call_count == 1


def test_no_completed_notebook_cell_is_required_to_start_from_a_known_schema():
    ctx = context()
    notebook = ctx['artifacts']['selected_notebook']
    notebook['latest_cell'] = None
    notebook['recent_cells'] = []
    with patch('backend.app.mentor_research_service.get_ai_runtime') as runtime_mock:
        reply = generate_research_reply(ctx, 'measurement eksikliğini incelemek istiyorum. Kodu verme.', [], allow_provider=False)
    runtime_mock.assert_not_called()
    state = saved()
    assert state['last_validation']['validation_kind'] == 'schema_start_only'
    assert state['workflow']['active_step']['status'] == 'awaiting_execution'
    assert not state['observations'] and 'isna' in reply and '```' not in reply
