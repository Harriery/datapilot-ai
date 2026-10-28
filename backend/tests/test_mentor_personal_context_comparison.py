"""Context ablation boundaries; controlled replies do not prove teaching quality."""
from copy import deepcopy
import json
import sqlite3
from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx
import pytest
from openai import BadRequestError

from backend.app import database, personal_data_mentor_service as personal
from backend.benchmarks import run_mentor_teaching_probe as probe
from backend.tests.test_personal_data_mentor_service import project, completion


QUESTIONS = ['Eksikleri saydım; ne yaptım?', 'Saymak ile seçmek farklı mı? Kod verme.',
             'True/False işaretlerini nasıl kullanacağım? Kısa anlat, kod verme.']


def seed(project):
    _, workspace, _, _, _ = project
    for question in QUESTIONS:
        database.insert_message(session_id=workspace.mentor_session_id, role='user', content=question)
        database.insert_message(session_id=workspace.mentor_session_id, role='assistant', content='Önceki gerçek yanıt.')
    return workspace


def dump_db():
    con = sqlite3.connect(database.DATABASE_PATH)
    try:
        return '\n'.join(con.iterdump())
    finally:
        con.close()


def prepare(workspace):
    return probe.prepare_personal_context_comparison(learner_id='context-choice', workspace_title=workspace.title)


@pytest.fixture(autouse=True)
def free_groq(monkeypatch):
    monkeypatch.setenv('AI_MENTOR_PROVIDER', 'groq')
    monkeypatch.setenv('AI_GROQ_MENTOR_MODEL', 'openai/gpt-oss-120b')
    monkeypatch.setenv('AI_FREE_ONLY', 'true')
    monkeypatch.setenv('AI_FREE_PROVIDER_ALLOWLIST', 'groq')


def test_actual_production_context_preparation_is_read_only_and_only_context_differs(project):
    workspace = seed(project)
    before = dump_db()
    csv = (project[4] / 'working.csv').read_bytes()
    with patch.object(probe, 'get_ai_runtime') as provider:
        report = prepare(workspace)
        probe.run_personal_context_comparison(report, live=False)
    provider.assert_not_called()
    assert dump_db() == before
    assert (project[4] / 'working.csv').read_bytes() == csv
    assert report['provider_calls'] == 0 and report['max_provider_calls'] == 6
    assert [p['question'] for p in report['pairs']] == QUESTIONS
    for pair in report['pairs']:
        lean, full = (pair['arms'][name]['messages'] for name in ('lean', 'application_context'))
        assert lean[:1] == full[:1] and lean[2:] == full[2:]
        assert lean[-2]['content'] == pair['question']
        assert lean[-1]['content'] == personal.FINAL_RESPONSE_RULES
        minimal, actual = (json.loads(x[1]['content'])['context'] for x in (lean, full))
        assert minimal['dataset']['scope'] == actual['dataset']['scope']
        assert minimal['notebook']['recent_cells'] == actual['notebook']['recent_cells']
        assert actual['dataset']['schema'] and actual['dataset']['example_rows']
        assert 'schema' not in minimal['dataset']
        assert actual['dataset']['scope']['snapshot_rows'] == 4
    assert not report['project_completion_proven'] and report['human_review_required']


def fake_runtime(side_effect=None):
    response = completion('True işaretli satırlar görünür; diğerleri silinmez.')
    response.usage = None
    client = Mock()
    client.with_options.return_value = client
    client.chat.completions.create.side_effect = side_effect
    client.chat.completions.create.return_value = response
    return SimpleNamespace(provider='groq', model='openai/gpt-oss-120b', client=client)


def test_live_probe_uses_same_settings_normal_ledger_no_tools_and_six_calls(project):
    report = prepare(seed(project))
    runtime = fake_runtime()
    states = []
    before = database.get_ai_usage_counts()['daily_requests']
    with patch.object(probe, 'get_ai_runtime', return_value=runtime):
        result = probe.run_personal_context_comparison(report, live=True, delay=0, checkpoint=states.append)
    assert database.get_ai_usage_counts()['daily_requests'] - before == 6
    assert runtime.client.chat.completions.create.call_count == 6
    runtime.client.with_options.assert_called_once_with(max_retries=0, timeout=90)
    for call in runtime.client.chat.completions.create.call_args_list:
        assert 'tools' not in call.kwargs and 'tool_choice' not in call.kwargs
        assert call.kwargs['reasoning_effort'] == 'medium'
        assert call.kwargs['model'] == report['model']
    assert result['status'] == 'completed_requires_human_review'
    assert states[0]['provider_calls'] == 0 and states[-1]['provider_calls'] == 6
    assert all(p['arms'][a]['status'] == 'received' for p in result['pairs'] for a in p['arms'])
    assert not result['project_completion_proven']


@pytest.mark.parametrize('failure', ['provider', 'interrupt'])
def test_error_or_interrupt_keeps_first_answer_without_retries_or_raw_error(project, failure):
    report = prepare(seed(project))
    reply = completion('İlk cevap.'); reply.usage = None
    error = BadRequestError('PRIVATE_SECRET', response=httpx.Response(400,
        request=httpx.Request('POST', 'https://provider.invalid')),
        body={'code': 'tool_use_failed', 'message': 'PRIVATE_SECRET'})
    runtime = fake_runtime([reply, error if failure == 'provider' else KeyboardInterrupt()])
    states = []
    with patch.object(probe, 'get_ai_runtime', return_value=runtime):
        result = probe.run_personal_context_comparison(report, live=True, delay=0, checkpoint=states.append)
    assert runtime.client.chat.completions.create.call_count == 2
    assert result['pairs'][0]['arms']['lean']['answer'] == 'İlk cevap.'
    assert result['pairs'][0]['arms']['application_context']['status'] in {'failed', 'interrupted_outcome_unknown'}
    assert result['pairs'][1]['arms']['lean']['status'] == 'pending'
    assert 'PRIVATE_SECRET' not in json.dumps(states)


def test_ambiguous_notebook_requires_selection_before_any_provider_request(project):
    workspace = seed(project)
    other = workspace.notebooks[0].model_copy(deep=True)
    other.notebook_id = 'n2'
    workspace.notebooks.append(other)
    database.save_workspace(workspace=workspace)
    with pytest.raises(ValueError, match='notebook-id'):
        prepare(workspace)


def test_company_or_unconsented_project_is_not_exported(project):
    workspace = seed(project)
    workspace.mentor_setup.notebook_teaching_context = 'question_and_code'
    database.save_workspace(workspace=workspace)
    with pytest.raises(ValueError, match='personal_data'):
        prepare(workspace)


def test_offline_cli_writes_actual_frozen_requests_without_provider_calls(project, tmp_path):
    workspace = seed(project)
    before = dump_db()
    with patch.object(probe, 'get_ai_runtime') as provider:
        result = probe.main(['--offline', '--context-comparison', '--learner-id', 'context-choice',
            '--workspace-title', workspace.title, '--output-dir', str(tmp_path / 'results')])
    assert result == 0 and dump_db() == before
    provider.assert_not_called()
    reports = list((tmp_path / 'results').glob('*/report.json'))
    assert len(reports) == 1
    frozen = json.loads(reports[0].read_text(encoding='utf-8'))
    assert frozen['experiment'] == 'personal_context_ablation_v1'
    assert frozen['source']['workspace_id'] == workspace.workspace_id
    assert frozen['frozen_input_scope']['snapshot_rows'] == 4


def test_snapshot_change_blocks_preparation_before_live_model_calls(project):
    workspace = seed(project)
    original = personal.load_input_snapshot
    counter = 0
    def changed(*args):
        nonlocal counter
        counter += 1
        frame, scope, notebook = original(*args)
        if counter == 2:
            scope['input_version'] = 'changed'
        return frame, scope, notebook
    with patch.object(personal, 'load_input_snapshot', side_effect=changed):
        with pytest.raises(ValueError, match='changed during preparation'):
            prepare(workspace)


def test_resume_preserves_first_answer_and_spends_only_five_more_calls(project):
    report = prepare(seed(project))
    saved = report['pairs'][0]['arms']['lean']
    saved.update(status='received', answer='Previously saved answer', finish_reason='stop')
    report['provider_calls'] = 1
    before = deepcopy(saved)
    runtime = fake_runtime()
    with patch.object(probe, 'get_ai_runtime', return_value=runtime):
        result = probe.run_personal_context_comparison(report, live=True, delay=0)
    assert runtime.client.chat.completions.create.call_count == 5
    assert result['provider_calls'] == 6
    assert result['pairs'][0]['arms']['lean'] == before


@pytest.mark.parametrize('change', ['unknown', 'count', 'settings'])
def test_resume_rejects_ambiguous_accounting_or_changed_settings_before_provider(project, change):
    report = prepare(seed(project))
    if change == 'unknown':
        report['pairs'][0]['arms']['lean']['status'] = 'interrupted_outcome_unknown'
    elif change == 'count':
        report['provider_calls'] = 1
    else:
        report['settings']['max_completion_tokens'] = 100
    with patch.object(probe, 'get_ai_runtime') as provider:
        with pytest.raises(ValueError):
            probe.run_personal_context_comparison(report, live=True, delay=0)
    provider.assert_not_called()
