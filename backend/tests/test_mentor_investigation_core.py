"""Controlled, multi-turn invented-data tests. Not live-model or novice acceptance."""
from copy import deepcopy
import json
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd
import pytest

from backend.app import database
from backend.app.mentor_adaptive_teaching_service import TeachingExplanation, build_teaching_request, conceptual_request
from backend.app.mentor_investigation_service import (
    investigation_view, InvestigationReasoning, validate_reasoning, remember_reasoning,
)
from backend.app.mentor_research_service import (
    generate_research_reply, build_research_request, prepare_research_context, GroundedResearchDecision,
)
from backend.app.mentor_research_store import load_research_state
from backend.benchmarks.run_mentor_teaching_probe import synthetic_context
from backend.benchmarks.run_mentor_connected_followup import recorded_cell


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(database, 'DATABASE_PATH', tmp_path / 'core.sqlite')
    database.init_db()


def setup(case='orders'):
    context = synthetic_context(public=True)
    target, helper = {'orders': ('delivery_days', 'shipment_status'),
        'sensors': ('reading', 'sensor_state'), 'tickets': ('resolution_time', 'ticket_state')}[case]
    # Rename schema AND code/results/map, not just prompt strings.
    frame = pd.DataFrame({target: [None if i % 4 == 0 else i % 8 for i in range(1000)],
                          helper: ['open' if i % 4 == 0 else 'closed' for i in range(1000)]})
    from backend.app.mentor_relationship_service import build_relationship_map
    context['workspace_id'] = 'core-' + case
    context['dataset_profile_summary']['columns'] = [target, helper]
    context['local_relationship_map'] = build_relationship_map(frame, input_version='core-v1')
    cell = recorded_cell('count', f'df[{target!r}].isna().sum()', 250, target, 'core-v1', 1000)
    notebook = context['artifacts']['selected_notebook']
    notebook.update(current_input_version='core-v1', latest_cell=cell, recent_cells=[cell])
    context.update(task_brief='Understand incomplete observations before deciding treatment.',
        mentor_setup={'experience_level': 'beginner', 'approach': 'guided', 'learning_focus': ['python', 'quality']},
        ui_context={'language': 'tr', 'active_workspace_stage': 'prepare',
                    'active_prepare_stage': 'workbench', 'workbench_view': 'notebook'})
    generate_research_reply(context, f'{target} sayımını yaptım. Veri sözlüğüm yok. Sonraki adım?', [], allow_provider=False)
    return context, load_research_state(context['workspace_id'], 'n1'), target, helper


def provider_reply(step, **fields):
    return TeachingExplanation(task_id=step['id'], approach='contrast',
        explanation='Sayım bir toplam verir; koşul ise hangi satırların kalacağını işaretler.',
        first_action='Eksikliği gösteren işaretleri satırları süzen koşul olarak kullan.',
        why='İncelemeyi ilgili satır grubuna sınırlandırmak için.', **fields)


def teach(context, reply, message):
    runtime = SimpleNamespace(provider='groq', model='controlled', client=object())
    with patch('backend.app.mentor_adaptive_teaching_service.get_ai_runtime', return_value=runtime), \
         patch('backend.app.mentor_adaptive_teaching_service.guarded_responses_parse',
               return_value=SimpleNamespace(output_parsed=reply, status='completed')) as call:
        visible = generate_research_reply(context, message, [])
    return visible, load_research_state(context['workspace_id'], 'n1'), json.loads(call.call_args.kwargs['input'])


@pytest.mark.parametrize('case', ['orders', 'sensors', 'tickets'])
def test_concept_partial_attempt_evidence_and_scope_change_share_one_investigation(case):
    context, state, target, helper = setup(case)
    step = deepcopy(state['workflow']['active_step'])
    visible, state, payload = teach(context, provider_reply(step,
        conversation_kind='concept', learner_need='Counting versus row selection.'),
        'Saymakla satır seçmek arasındaki farkı anlamadım; kod verme.')
    core = payload['investigation_context']
    assert core['project_goal'] == context['task_brief']
    assert core['learner_preferences']['approach'] == 'guided'
    assert core['stage'] == 'prepare.workbench.notebook'
    assert core['definition_availability']['status'] == 'unavailable'
    assert core['verified_checks'][0]['contract']['operation'] == 'missing_count'
    assert state['conversation_memory']['understanding_verified'] is False
    assert '```' not in visible

    notebook = context['artifacts']['selected_notebook']
    partial = recorded_cell('condition', f'df[{target!r}].isna()', 'synthetic condition output', target, 'core-v1', 1000)
    notebook.update(latest_cell=partial, recent_cells=[partial, notebook['latest_cell']])
    response = provider_reply(step, conversation_kind='attempt', learner_need='Apply the condition to rows.')
    response.explanation = 'Koşul işaretleri üretmek, satırları seçmekten önce gelir; henüz seçimi tamamladığını varsayamayız.'
    _, state, payload = teach(context, response, 'Bu koşulu yazdım; şimdi nasıl kullanacağım?')
    assert payload['last_attempt_shape']['uses_missing_condition']
    assert not payload['last_attempt_shape']['uses_row_selection']
    assert payload['investigation_context']['learner_need'] == 'Counting versus row selection.'
    assert state['workflow']['active_step']['id'] == step['id']
    assert state['workflow']['active_step']['status'] == 'awaiting_execution'
    # Valid count remains available although the latest attempt is unsupported.
    count_id = payload['investigation_context']['verified_checks'][0]['id']
    response = provider_reply(step, conversation_kind='evidence', evidence_ids=[count_id])
    response.explanation = 'Kayıtlı sayım aşağıda gösteriliyor; satır seçiminin yapıldığını göstermez.'
    visible, state, payload = teach(context, response, 'Önceki sayımın sonucu neyi gösteriyordu?')
    assert '250' in visible and '1,000' in visible
    assert 'result' not in json.dumps(payload['investigation_context']['verified_checks'])
    assert state['workflow']['active_step']['status'] == 'awaiting_execution'
    assert state['last_validation']['conversation_kind'] == 'evidence'

    # New data cannot inherit execution completion or an old hypothesis.
    notebook['current_input_version'] = 'core-v2'
    with patch('backend.app.mentor_adaptive_teaching_service.guarded_responses_parse') as call:
        generate_research_reply(context, 'Veri değişti, aynı sonuç mu?', [])
    call.assert_not_called()
    state = load_research_state(context['workspace_id'], 'n1')
    assert state['workflow']['active_step']['status'] == 'needs_revalidation'
    assert not state['last_validation']['teaching_accepted']


def test_shared_projection_preserves_truth_and_is_detached_from_memory():
    context, state, target, helper = setup()
    before = deepcopy(state)
    core = investigation_view(context, state, include_results=True)
    assert core['verified_checks'][0]['result'] == 250
    assert core['verified_checks'][0]['full_source_verified'] is False
    core['verified_checks'][0]['contract']['measured_columns'].clear()
    assert state == before
    teacher = build_teaching_request(context, state, state['workflow']['active_step'], 'Neden?')
    planner = build_research_request(context, state, 'Neden?', [])
    assert teacher['investigation_context']['research_question'] == planner['investigation_context']['research_question']
    assert teacher['investigation_context']['pending_task'] == planner['investigation_context']['pending_task']
    assert 'result' not in teacher['investigation_context']['verified_checks'][0]


def test_generic_projection_is_allow_listed_even_if_new_context_contains_private_data():
    context, state, _, _ = setup()
    payload = build_teaching_request(context, state, state['workflow']['active_step'], 'private-canary')
    payload['future_metadata'] = 'private-canary'
    payload['investigation_context']['project_goal'] = 'private-canary'
    safe, aliases = conceptual_request(payload, 'private-canary')
    assert 'private-canary' not in json.dumps(safe)
    assert 'investigation_context' not in safe and aliases


def test_scoped_consent_does_not_expand_into_sharing_results_or_project_brief():
    context, state, _, _ = setup()
    context['teaching_data_policy']['data_sensitivity'] = None
    context['mentor_setup']['notebook_teaching_context'] = 'question_and_code'
    context['task_brief'] = 'private-project-canary'
    _, after, payload = teach(context, provider_reply(state['workflow']['active_step']), 'Nasıl?')
    assert 'private-project-canary' not in json.dumps(payload)
    assert 'result' not in json.dumps(payload['investigation_context']['verified_checks'])
    assert after['last_validation']['teaching_context_mode'] == 'user_shared_question_and_code'


@pytest.mark.parametrize('ids', [['unknown'], []])
def test_evidence_conversation_requires_current_verifiable_references(ids):
    context, state, _, _ = setup()
    visible, after, _ = teach(context, provider_reply(state['workflow']['active_step'],
        conversation_kind='evidence', evidence_ids=ids), 'Sonuç ne?')
    assert after['last_validation']['reason'] == 'unavailable_evidence_reference'
    assert 'yeni çıktı istemeyeceğim' in visible
    assert 'value_counts' not in visible and 'çalıştır' not in visible
    assert 'conversation_memory' not in after


def test_research_candidates_are_speculative_scoped_and_require_valid_provenance():
    context, state, _, _ = setup()
    ref = state['current_evidence_ids'][0]
    reasoning = InvestigationReasoning(hypotheses=[{
        'explanation': 'Eksiklik kayıt sürecindeki duruma bağlı olabilir.',
        'prediction': 'Eksik ve dolu gruplarda durum oranları farklı olabilir.',
        'supporting_evidence_ids': [ref], 'contradicting_evidence_ids': []}],
        next_test_reason='Durum ile eksiklik arasında karşılaştırılabilir bir örüntü olup olmadığını sınamak için.')
    assert not validate_reasoning(reasoning, state)
    remember_reasoning(state, context, reasoning)
    assert state['investigation_reasoning']['status'] == 'untested_model_candidates_not_facts'
    assert investigation_view(context, state)['candidate_explanations']
    context['artifacts']['selected_notebook']['current_input_version'] = 'new-version'
    assert not investigation_view(context, state)['candidate_explanations']
    assert investigation_view(context, state)['previous_candidates_out_of_scope']
    reasoning.hypotheses[0].contradicting_evidence_ids = [ref]
    assert validate_reasoning(reasoning, state)
    reasoning.hypotheses[0].contradicting_evidence_ids = ['unknown']
    assert validate_reasoning(reasoning, state)
    assert state['workflow']['active_step']['status'] == 'awaiting_execution'


def test_research_wire_can_express_alternatives_without_publishing_facts_or_mutations():
    wire = GroundedResearchDecision.model_validate({'next_action': None, 'evidence_ids': [],
        'reasoning': {'hypotheses': [], 'next_test_reason': 'Önce karşılaştırmanın kapsamını belirlemek gerekir.'}})
    assert wire.reasoning.next_test_reason
    assert set(wire.model_dump()) == {'next_action', 'evidence_ids', 'reasoning'}


def test_summary_consent_exposes_only_parsed_aggregates_and_can_be_revoked():
    context, state, target, helper = setup()
    context['teaching_data_policy']['data_sensitivity'] = None
    context['mentor_setup']['notebook_teaching_context'] = 'question_code_and_summaries'
    # Malformed/free-form cell text is never eligible as an aggregate summary.
    _, after, payload = teach(context, provider_reply(state['workflow']['active_step']), 'Sayım neyi gösterir?')
    assert payload['aggregate_summaries_shared'] is True
    assert payload['investigation_context']['project_goal'] == context['task_brief']
    assert payload['investigation_context']['verified_checks'][0]['result'] == 250
    assert 'data_version' not in payload['investigation_context']['verified_checks'][0]
    assert after['last_validation']['teaching_context_mode'] == 'user_shared_question_code_and_summaries'
    context['mentor_setup']['notebook_teaching_context'] = 'question_and_code'
    answer = provider_reply(state['workflow']['active_step'])
    answer.explanation = 'Sayımın kendisi satırları ayırmaz; ilgili grubun seçilmesi gerekir.'
    _, _, payload = teach(context, answer, 'Satır seçimi neydi?')
    assert payload['aggregate_summaries_shared'] is False
    assert 'result' not in payload['investigation_context']['verified_checks'][0]


@pytest.mark.parametrize('case', ['orders', 'sensors', 'service'])
def test_frozen_six_turn_probe_preserves_actual_model_candidate_and_displayed_reply(case):
    from backend.benchmarks.run_mentor_teaching_probe import run_dialogue_suite
    calls, saved = [], []
    def model(*args, **kwargs):
        payload = json.loads(kwargs['input'])
        calls.append(payload)
        kind = 'evidence' if 'Yeni çalıştırdığım' in payload['learner_question'] else 'concept'
        refs = [payload['investigation_context']['verified_checks'][0]['id']] if kind == 'evidence' else []
        result = TeachingExplanation(task_id=payload['task_id'], conversation_kind=kind,
            approach='contrast', explanation='Bu ayrı bir konuşma açıklamasıdır: ' + ['sayım ile seçim farklıdır.',
                'işaretleri satır filtresi olarak kullanırız.', 'koşul tek başına satır seçmez.',
                'hata nedeni bu bağlamdan kesin belirlenemiyor.', 'görünen dağılım tek başına neden kanıtlamaz.',
                'kaynak tanımı olmadan kesin iş kuralı çıkaramayız.'][len(calls)-1],
            first_action='Önce ilgili satır grubunu belirleyen koşulu düşün.',
            why='Araştırmanın hedefini korumak için.', evidence_ids=refs)
        return SimpleNamespace(output_parsed=result, status='completed')
    runtime = SimpleNamespace(provider='groq', model='controlled', client=object())
    with patch('backend.app.mentor_adaptive_teaching_service.get_ai_runtime', return_value=runtime), \
         patch('backend.app.mentor_adaptive_teaching_service.guarded_responses_parse', side_effect=model):
        report = run_dialogue_suite(case, delay=0, checkpoint=lambda x: saved.append(deepcopy(x)))
    assert len(calls) == 6 and len(report['turns']) == 6
    assert len(saved[-1]['turns']) == 6
    assert all(turn['provider_candidate'] and turn['displayed_reply'] for turn in report['turns'])
    assert all(turn['provider_calls'] == 1 for turn in report['turns'])
    assert report['turns'][2]['pending_task']['status'] == 'awaiting_execution'
    assert calls[2]['last_attempt_shape']['uses_missing_condition']
    assert calls[3]['last_attempt_shape']['success'] is False
    assert calls[4]['investigation_context']['verified_checks'][0]['proportions'] == {'open': .9, 'closed': .1}
    assert report['turns'][4]['pending_task']['id'] != report['turns'][0]['pending_task']['id']
    assert report['status'] == 'completed_requires_human_review'
    assert not report['ui_tested'] and not report['novice_usability_accepted'] and not report['project_completion_proven']


def test_checked_research_reasoning_reaches_memory_and_visible_rationale_only_after_validation():
    from backend.app.mentor_research_store import save_research_state
    context, state, target, _ = setup()
    state['workflow']['active_step'] = None
    state['proposals'] = []
    save_research_state(context['workspace_id'], 'n1', state)
    raw = GroundedResearchDecision.model_validate({'next_action': {'kind': 'inspect',
        'code': f'df[df[{target!r}].isna()].head()'}, 'evidence_ids': [state['current_evidence_ids'][0]],
        'reasoning': {'hypotheses': [{'explanation': 'Eksiklik işlem durumuna bağlı olabilir.',
            'prediction': 'Durum dağılımı eksik ve dolu gruplarda farklı olabilir.',
            'supporting_evidence_ids': [], 'contradicting_evidence_ids': []}],
            'next_test_reason': 'Eksik grubun örneklerinde karşılaştırılabilecek alanları belirlemek için.'}})
    runtime = SimpleNamespace(provider='groq', model='controlled', client=object())
    with patch('backend.app.mentor_research_service.plan_relationship_comparison', return_value=None), \
         patch('backend.app.mentor_research_service.plan_missing_preview', return_value=None), \
         patch('backend.app.mentor_research_service.plan_preview_continuation', return_value=None), \
         patch('backend.app.mentor_research_service.get_ai_runtime', return_value=runtime), \
         patch('backend.app.mentor_research_service.guarded_responses_parse',
               return_value=SimpleNamespace(output_parsed=raw)) as model:
        visible = generate_research_reply(context, 'Sonraki kontrolü seç; kod verme.', [], max_attempts=1)
    assert model.call_count == 1
    after = load_research_state(context['workspace_id'], 'n1')
    assert after['last_validation']['accepted']
    assert after['investigation_reasoning']['status'] == 'untested_model_candidates_not_facts'
    assert 'Sınanacak olasılık (doğrulanmadı)' in visible
    assert raw.reasoning.next_test_reason in visible
    assert '```' not in visible


def test_history_budget_preserves_current_question_and_execution_contract():
    from backend.app.mentor_adaptive_teaching_service import bound_teaching_context
    context, state, _, _ = setup()
    payload = build_teaching_request(context, state, state['workflow']['active_step'], 'current-question')
    expected = deepcopy(payload['task_contract'])
    source = payload['latest_verified_expression']
    payload['previous_explanations'] = [{'question': 'x'*1200, 'explanation': 'y'*700} for _ in range(6)]
    payload['investigation_context']['candidate_explanations'] = ['z'*1000]*3
    assert bound_teaching_context(payload)
    assert len(json.dumps(payload, ensure_ascii=False)) <= 9000
    assert payload['context_omissions']
    assert payload['learner_question'] == 'current-question'
    assert payload['task_contract'] == expected and payload['latest_verified_expression'] == source


def test_auxiliary_evidence_can_be_explained_without_changing_the_pending_task():
    context, state, target, _ = setup()
    context['dataset_profile_summary']['columns'].append('side_field')
    notebook = context['artifacts']['selected_notebook']
    auxiliary = recorded_cell('side-check', "df['side_field'].isna().sum()", 0, target, 'core-v1', 1000)
    notebook.update(latest_cell=auxiliary, recent_cells=[auxiliary] + notebook['recent_cells'])
    # Bind the new receipt through the real context preparation, not a fake ID.
    prepared = prepare_research_context({**notebook, 'available_columns': context['dataset_profile_summary']['columns']},
                                        'Önceki kontrolü açıkla.', state)
    ref = prepared['current_evidence_ids'][0]
    response = provider_reply(state['workflow']['active_step'], conversation_kind='evidence', evidence_ids=[ref])
    response.explanation = 'side_field sayımı ayrı bir yardımcı kontroldür; hedef eksikliğinin dağılımını ölçmez.'
    visible, after, _ = teach(context, response, 'Yaptığım yardımcı kontrolü açıklar mısın?')
    assert after['last_validation']['teaching_accepted'] and 'side_field' in visible
    assert after['workflow']['active_step']['id'] == state['workflow']['active_step']['id']
    response.explanation = 'side_field kontrolü ayrı bir ölçümdür; araştırmanın hedefi değişmedi.'
    response.first_action = 'side_field üzerinde yeni bir dağılım incele.'
    _, after, _ = teach(context, response, 'Sırada ne var?')
    assert after['last_validation']['reason'] == 'optional_guidance_omitted'
    assert after['last_validation']['guidance_rejection_reason'] == 'unrelated_column'
    assert after['last_validation']['provider_contract_accepted'] is False


def test_probe_cli_loads_local_provider_config_without_overwriting_shell_settings(tmp_path, monkeypatch):
    from backend.benchmarks import run_mentor_teaching_probe as probe
    from backend.app.ai_provider_service import get_ai_runtime_config
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('AI_GROQ_MENTOR_MODEL', 'synthetic-before')
    monkeypatch.delenv('AI_GROQ_MENTOR_MODEL')
    monkeypatch.setenv('AI_MENTOR_PROVIDER', 'groq')
    (tmp_path / '.env').write_text('AI_MENTOR_PROVIDER=openai\nAI_GROQ_MENTOR_MODEL=synthetic-config-choice\n')
    previous_database = database.DATABASE_PATH
    seen = []
    def controlled(*args, **kwargs):
        config = get_ai_runtime_config('mentor')
        seen.append((config.provider, config.model))
        return {'turns': [], 'status': 'completed_requires_human_review'}
    monkeypatch.setattr(probe, 'run_dialogue_suite', controlled)
    assert probe.main(['--live', '--dialogue-suite', '--output-dir', str(tmp_path / 'reports')]) == 0
    assert seen == [('groq', 'synthetic-config-choice')]
    assert database.DATABASE_PATH == previous_database
    assert len(list((tmp_path / 'reports').glob('*/report.json'))) == 1


def test_probe_collects_section_failures_without_counting_scripted_continuation_as_success():
    from backend.benchmarks.run_mentor_teaching_probe import run_dialogue_suite
    calls = []
    def model(*args, **kwargs):
        payload = json.loads(kwargs['input']); calls.append(payload)
        n = len(calls)
        evidence = n == 5
        return SimpleNamespace(status='completed', output_parsed=TeachingExplanation(
            task_id=payload['task_id'], conversation_kind='evidence' if evidence else 'concept',
            evidence_ids=[payload['investigation_context']['verified_checks'][0]['id']] if evidence else [],
            approach='break_down',
            explanation=['Sayım bir toplamdır; seçim ilgili kayıtları ayırır.',
                '`df[unverified_flags]` ile seç.', 'Koşul tek başına satır seçimi değildir.',
                'Hata nedenini bu bağlamla kesinleştiremiyorum.',
                'Kayıtlı dağılım tek başına iş kuralı kanıtlamaz.',
                'Kaynak tanımı olmadan nedeni kesinleştiremeyiz.'][n-1],
            first_action='df.dropna(inplace=True)' if n == 1 else None,
            why='Önce bu işlemi yap.' if n == 1 else None))
    runtime = SimpleNamespace(provider='groq', model='controlled', client=object())
    with patch('backend.app.mentor_adaptive_teaching_service.get_ai_runtime', return_value=runtime), \
         patch('backend.app.mentor_adaptive_teaching_service.guarded_responses_parse', side_effect=model):
        report = run_dialogue_suite('sensors', delay=0)
    assert len(calls) == 6 and len(report['turns']) == 6
    first, second = report['turns'][:2]
    assert first['diagnostics']['teaching_accepted']
    assert first['diagnostics']['provider_contract_accepted'] is False
    assert first['diagnostics']['delivery_mode'] == 'explanation_only'
    assert 'dropna' not in first['displayed_reply']
    assert not second['diagnostics']['teaching_accepted']
    assert not second['continuation_after_blocked_reply']
    assert all(x['continuation_after_blocked_reply'] for x in report['turns'][2:])
    assert not report['protocol_checks_passed']
    assert report['status'] == 'completed_with_protocol_failures'
    assert report['delivery_checks'] == {'all_explanations_delivered': False,
        'guidance_was_omitted': True, 'blocked_reply_occurred': True}
    assert report['scripted_execution_receipts'] and not report['project_completion_proven']
    # The invalid model instruction must not seed the next model request.
    assert 'df.dropna(inplace=True)' not in json.dumps(calls[1])


def test_probe_stops_on_provider_failure_without_repeating_failed_requests():
    from backend.benchmarks.run_mentor_teaching_probe import run_dialogue_suite
    runtime = SimpleNamespace(provider='groq', model='controlled', client=object())
    with patch('backend.app.mentor_adaptive_teaching_service.get_ai_runtime', return_value=runtime), \
         patch('backend.app.mentor_adaptive_teaching_service.guarded_responses_parse',
               side_effect=RuntimeError('synthetic provider failure')) as model:
        report = run_dialogue_suite('service', delay=0)
    assert model.call_count == 1 and len(report['turns']) == 1
    assert not report['protocol_checks_passed']
    assert report['turns'][0]['diagnostics']['reason'] == 'provider_or_schema_error'


def test_paired_offline_prepares_same_source_checkpoints_without_provider_or_sqlite_access():
    from backend.benchmarks.run_mentor_teaching_probe import run_paired_comparison
    with patch('backend.benchmarks.run_mentor_teaching_probe.get_ai_runtime') as model, \
         patch('backend.benchmarks.run_mentor_teaching_probe.guarded_responses_parse') as provider, \
         patch.object(database, 'get_connection', side_effect=AssertionError('Unexpected SQLite access')):
        report = run_paired_comparison(live=False, max_pairs=9)
    model.assert_not_called(); provider.assert_not_called()
    assert report['provider_calls'] == 0 and report['status'] == 'prepared_not_live_tested'
    assert len(report['pairs']) == 9 and report['comparison_winner'] is None
    schemas, scenarios, sources = set(), set(), {}
    for pair in report['pairs']:
        schemas.add(pair['case']); scenarios.add(pair['scenario'])
        current, simple = pair['arms']['current'], pair['arms']['simple']
        assert current['max_output_tokens'] == simple['max_output_tokens']
        assert len(json.dumps(current['input'], ensure_ascii=False)) <= 9000
        assert simple['input'] == pair['source_snapshot']
        assert current['input']['learner_question'] == simple['input']['question']
        assert not simple['input']['scope']['full_source_verified']
        assert 'row_predicate' not in json.dumps(simple['input'])
        assert simple['input']['history'] == []
        if pair['scenario'] == 'count_vs_filter':
            sources[pair['case']] = simple['input']['recorded_cells'][0]['output']
        if pair['scenario'] == 'error':
            assert simple['input']['recorded_cells'][0]['success'] is False
            assert 'SyntaxError' in simple['input']['recorded_cells'][0]['output']
    assert len(schemas) == 3 and len(scenarios) == 3
    assert len(set(sources.values())) == 3  # Patterns differ, not only field names.
    assert not report['novice_usability_accepted'] and not report['project_completion_proven']


def test_paired_live_wiring_uses_same_model_budget_and_keeps_candidates_separate_from_display():
    from backend.benchmarks import run_mentor_teaching_probe as probe
    calls = []
    runtime = SimpleNamespace(provider='groq', model='openai/gpt-oss-120b', client=object())
    def provider(*args, **kwargs):
        calls.append(kwargs)
        if kwargs['text_format'] is probe.ComparisonAnswer:
            parsed = probe.ComparisonAnswer(answer='Bu serbest deney cevabıdır; kod çalıştırılmaz.')
        else:
            payload = json.loads(kwargs['input'])
            parsed = TeachingExplanation(task_id=payload['task_id'], approach='break_down',
                explanation='Sayım ile satır seçimi farklı işlemlerdir.',
                first_action='df.dropna(inplace=True)', why=None)
        return SimpleNamespace(output_parsed=parsed, status='completed',
            usage=SimpleNamespace(input_tokens=100, output_tokens=20, total_tokens=120))
    original_database = database.DATABASE_PATH
    with patch.object(probe, 'get_ai_runtime', return_value=runtime), \
         patch.object(probe, 'get_ai_billing_policy', return_value={'free_only': True, 'allowed_free_providers': ['groq']}), \
         patch.object(probe, 'guarded_responses_parse', side_effect=provider), \
         patch.object(database, 'get_connection', side_effect=AssertionError('Unexpected project DB access')):
        report = probe.run_paired_comparison(live=True, max_pairs=3, delay=0)
    assert database.DATABASE_PATH == original_database
    assert report['provider_calls'] == 6 and len(calls) == 6
    assert report['status'] == 'completed_requires_human_review'
    assert report['comparison_winner'] is None
    assert report['pairs'][0]['call_order'] == ['current', 'simple']
    assert report['pairs'][1]['call_order'] == ['simple', 'current']
    for pair in report['pairs']:
        current, simple = pair['arms']['current'], pair['arms']['simple']
        assert current['input']['learner_question'] == simple['input']['question']
        assert current['max_output_tokens'] == simple['max_output_tokens']
        assert current['reasoning'] == simple['reasoning']
        assert 'dropna' in current['provider_candidate']['first_action']
        assert 'dropna' not in current['displayed_reply']
        assert current['diagnostics']['provider_contract_accepted'] is False
        assert current['usage']['total_tokens'] == simple['usage']['total_tokens'] == 120
        assert all(score is None for score in pair['human_scores'].values())
    assert {(x['provider'],x['model']) for x in calls} == {('groq','openai/gpt-oss-120b')}


@pytest.mark.parametrize('free_only,provider', [(False,'groq'), (True,'openai')])
def test_comparison_refuses_paid_or_unapproved_runtime(free_only, provider):
    from backend.benchmarks import run_mentor_teaching_probe as probe
    with patch.object(probe, 'get_ai_runtime', return_value=SimpleNamespace(provider=provider)), \
         patch.object(probe, 'get_ai_billing_policy', return_value={'free_only': free_only, 'allowed_free_providers':['groq']}), \
         patch.object(probe, 'guarded_responses_parse') as model:
        report = probe.run_paired_comparison(live=True)
    model.assert_not_called()
    assert report['status'] == 'blocked_configuration' and report['provider_calls'] == 0


def test_comparison_saves_partial_pair_on_provider_failure_and_does_not_retry():
    from backend.benchmarks import run_mentor_teaching_probe as probe
    checkpoints = []
    with patch.object(probe, 'get_ai_runtime', return_value=SimpleNamespace(provider='groq', model='controlled', client=object())), \
         patch.object(probe, 'get_ai_billing_policy', return_value={'free_only':True,'allowed_free_providers':['groq']}), \
         patch.object(probe, 'guarded_responses_parse', side_effect=RuntimeError('private-provider-error')) as model:
        report = probe.run_paired_comparison(live=True, delay=0, checkpoint=lambda x: checkpoints.append(deepcopy(x)))
    assert model.call_count == 1 and report['provider_calls'] == 1
    assert report['status'] == 'blocked' and len(report['pairs']) == 1
    assert 'private-provider-error' not in json.dumps(report)
    assert checkpoints[-1]['status'] == 'blocked'


def test_paired_experiment_retains_normal_usage_guards_while_research_state_is_isolated(monkeypatch):
    from backend.benchmarks import run_mentor_teaching_probe as probe
    monkeypatch.setenv('AI_FREE_ONLY', 'true')
    monkeypatch.setenv('AI_FREE_PROVIDER_ALLOWLIST', 'groq')
    monkeypatch.setenv('AI_DAILY_REQUEST_LIMIT', '100')
    monkeypatch.setenv('AI_MONTHLY_REQUEST_LIMIT', '100')
    before = database.get_ai_usage_counts()
    def parse(**kwargs):
        if kwargs['text_format'] is probe.ComparisonAnswer:
            parsed = probe.ComparisonAnswer(answer='Sentetik karşılaştırma cevabı.')
        else:
            request = json.loads(kwargs['input'])
            parsed = TeachingExplanation(task_id=request['task_id'], approach='contrast',
                explanation='Sayım toplam verir; seçim satırları ayırır.', first_action=None, why=None)
        return SimpleNamespace(status='completed', output_parsed=parsed)
    runtime = SimpleNamespace(provider='groq', model='openai/gpt-oss-120b',
                              client=SimpleNamespace(responses=SimpleNamespace(parse=parse)))
    with patch.object(probe, 'get_ai_runtime', return_value=runtime):
        report = probe.run_paired_comparison(live=True, max_pairs=1, delay=0)
    assert report['status'] == 'completed_requires_human_review'
    assert database.get_ai_usage_counts()['daily_requests'] - before['daily_requests'] == 2
    # No real provider was used: this verifies ledger routing through the real guard.
    connection = database.get_connection()
    try:
        assert connection.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='mentor_research_memory'").fetchone()[0] == 0
    finally:
        connection.close()


def test_comparison_range_skips_completed_pairs_without_changing_order_or_budget():
    from backend.benchmarks import run_mentor_teaching_probe as probe
    report = probe.run_paired_comparison(live=False, start_pair=2, max_pairs=2)
    assert report['max_provider_calls'] == 4 and report['provider_calls'] == 0
    assert [(p['schedule_pair'],p['case'],p['scenario']) for p in report['pairs']] == [
        (2,'sensors','error'), (3,'service','evidence')]
    assert report['pairs'][0]['call_order'] == ['simple','current']
    assert report['pairs'][1]['call_order'] == ['current','simple']
    with pytest.raises(ValueError): probe.run_paired_comparison(live=True, start_pair=9, max_pairs=2)


def test_current_provider_failure_records_safe_categories_even_when_app_catches_exception():
    from backend.benchmarks import run_mentor_teaching_probe as probe
    class SyntheticBadRequest(Exception):
        status_code = 400
        body = {'error': {'code':'json_validate_failed','type':'invalid_request_error',
                          'message':'private-provider-text', 'failed_generation':'private-candidate'}}
    runtime = SimpleNamespace(provider='groq', model='controlled', client=object())
    def provider(*args, **kwargs):
        if kwargs['text_format'] is probe.ComparisonAnswer:
            return SimpleNamespace(status='completed', output_parsed=probe.ComparisonAnswer(answer='Kısa sentetik cevap.'))
        raise SyntheticBadRequest('private-exception-text')
    with patch.object(probe, 'get_ai_runtime', return_value=runtime), \
         patch.object(probe, 'get_ai_billing_policy', return_value={'free_only':True,'allowed_free_providers':['groq']}), \
         patch.object(probe, 'guarded_responses_parse', side_effect=provider) as model:
        report = probe.run_paired_comparison(live=True, start_pair=2, max_pairs=2, delay=0)
    assert model.call_count == 4 and report['status'] == 'completed_with_arm_failures'
    assert report['pairs'][0]['arms']['current']['comparison_outcome'] == 'provider_schema_rejection'
    failure = report['pairs'][0]['arms']['current']['failure']
    assert failure == {'error_type':'SyntheticBadRequest','http_status':400,
        'provider_error_code':'json_validate_failed','provider_error_type':'invalid_request_error'}
    assert 'private-' not in json.dumps(report)
    assert report['pairs'][0]['arms']['simple']['provider_candidate']['answer']
    assert report['comparison_winner'] is None


def test_unknown_provider_metadata_does_not_disclose_arbitrary_values():
    from backend.benchmarks.run_mentor_teaching_probe import comparison_failure_metadata
    class Failure(Exception):
        status_code = 400
        body = {'error':{'code':'private-code','type':'private-type','message':'private-message'}}
    result = comparison_failure_metadata(Failure('private-error'))
    assert result['provider_error_code'] == result['provider_error_type'] == 'other'
    assert 'private-' not in json.dumps(result)


@pytest.mark.parametrize('value', [{'nested':'private'}, ['private'], 7])
def test_malformed_provider_error_codes_do_not_mask_the_original_failure(value):
    from backend.benchmarks.run_mentor_teaching_probe import comparison_failure_metadata
    class Failure(Exception):
        status_code = 400
        body = {'error': {'code':value,'type':value}}
    result = comparison_failure_metadata(Failure())
    assert result['http_status'] == 400
    assert result['provider_error_code'] == result['provider_error_type'] == 'other'


@pytest.mark.parametrize('rejected_arm', ['current','simple'])
@pytest.mark.parametrize('status,code', [(400,'json_validate_failed'),(429,'rate_limit_exceeded')])
def test_comparison_classifies_schema_failure_symmetrically_and_stops_on_quota(rejected_arm, status, code):
    from backend.benchmarks import run_mentor_teaching_probe as probe
    class Failure(Exception):
        status_code = status
        body = {'error':{'code':code,'type':'invalid_request_error'}}
    def provider(*args, **kwargs):
        arm = 'simple' if kwargs['text_format'] is probe.ComparisonAnswer else 'current'
        if arm == rejected_arm: raise Failure()
        if arm == 'simple': parsed = probe.ComparisonAnswer(answer='Kısa sentetik cevap.')
        else:
            payload = json.loads(kwargs['input'])
            parsed = TeachingExplanation(task_id=payload['task_id'],approach='contrast',
                explanation='Sayım ile seçim farklı işlemlerdir.',first_action=None,why=None)
        return SimpleNamespace(status='completed',output_parsed=parsed)
    with patch.object(probe,'get_ai_runtime',return_value=SimpleNamespace(provider='groq',model='controlled',client=object())), \
         patch.object(probe,'get_ai_billing_policy',return_value={'free_only':True,'allowed_free_providers':['groq']}), \
         patch.object(probe,'guarded_responses_parse',side_effect=provider) as model:
        report = probe.run_paired_comparison(live=True,max_pairs=2,delay=0)
    if status == 400:
        assert report['status'] == 'completed_with_arm_failures' and model.call_count == 4
        assert len(report['pairs']) == 2
    else:
        assert report['status'] == 'blocked' and model.call_count == (1 if rejected_arm == 'current' else 2)
        assert len(report['pairs']) == 1
    assert report['comparison_winner'] is None
