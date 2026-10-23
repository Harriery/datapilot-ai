"""One durable active step for notebook learning; no model calls or execution.

The evidence compiler owns factual validity. This module owns task identity,
completion, assistance and the investigation journal. Legacy proposal lists are
kept as a compatibility projection, never a second source of task ownership.
"""
from copy import deepcopy
import hashlib
import json

from backend.app.mentor_observation_contract import expression_contract
from backend.app.mentor_orchestration_service import determine_assistance_level
from backend.app.mentor_stage_playbook_service import STAGE_PLAYBOOKS
from backend.app.mentor_tutoring_service import normalized


def signature(code):
    contract = expression_contract(code or '')
    if contract.get('supported') is False:
        return None
    return hashlib.sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest()[:20]


def execution_receipt(item):
    value = json.dumps([item.get('cell_id'), item.get('executed_at'),
                        item.get('input_data_version'), item.get('output')], sort_keys=True)
    return hashlib.sha256(value.encode()).hexdigest()[:24]


def workflow(state):
    value = state.get('workflow')
    if not isinstance(value, dict) or value.get('focus_column') != state.get('focus_column'):
        value = {'schema_version': 2, 'focus_column': state.get('focus_column'),
                 'question': 'Which observations and source definitions justify a treatment or deferral?',
                 'phase': 'observe', 'status': 'investigating', 'active_step': None,
                 'step_history': [], 'findings': [], 'sequence': 0}
        state['workflow'] = value
    ledger = state.setdefault('finding_ledger', deepcopy(value.get('findings', [])))
    value['findings'] = [x for x in ledger if x.get('focus_column') == state.get('focus_column')]
    return value


def _new_step(state, action, notebook):
    flow = workflow(state)
    flow['sequence'] += 1
    return {**deepcopy(action), 'id': f"step-{flow['sequence']}",
            'status': 'awaiting_execution' if action['kind'] in {'inspect', 'refresh'} else 'awaiting_answer',
            'signature': signature(action.get('code')),
            'baseline_evidence_ids': [x['id'] for x in state.get('observations', [])],
            'baseline_execution_receipts': [execution_receipt(x) for x in state.get('observations', [])],
            'expected_version': notebook.get('current_input_version'),
            'dataset_kind': notebook.get('dataset_kind'), 'help_requests': 0}


def register_action(state, action, notebook):
    """Install one checked action. A pending task may be explained, not replaced."""
    flow = workflow(state)
    current = flow.get('active_step')
    if current and current['status'] in {'awaiting_execution', 'awaiting_answer', 'needs_revalidation'}:
        same = current['kind'] == action['kind'] and (
            current.get('signature') == signature(action.get('code')) if action['kind'] == 'inspect'
            else current.get('focus_column') == action.get('focus_column'))
        if same:
            return current
        raise ValueError('Resolve the active mentor step before assigning another')
    if current:
        flow['step_history'] = (flow['step_history'] + [deepcopy(current)])[-30:]
    step = _new_step(state, action, notebook)
    flow['active_step'] = step
    state.setdefault('proposals', []).append({**deepcopy(action), 'status': 'proposed', 'step_id': step['id']})
    state['proposals'] = state['proposals'][-12:]
    state['open_questions'] = [action.get('instruction', flow['question'])]
    return step


def register_refresh(state, refresh, notebook):
    flow = workflow(state)
    current = flow.get('active_step')
    if current and current['kind'] == 'refresh' and current.get('cell_id') == refresh['cell_id']:
        return current
    if current:
        flow['step_history'] = (flow['step_history'] + [deepcopy(current)])[-30:]
    observation = next(x for x in state['observations'] if x['id'] == refresh['evidence_id'])
    step = _new_step(state, {**deepcopy(refresh), 'kind': 'refresh', 'code': observation['code']}, notebook)
    flow['active_step'] = step
    return step


def reconcile_workflow(state, notebook):
    """Migrate old journals, then consume only a NEW matching verified execution."""
    flow = workflow(state)
    if flow['active_step'] is None:
        candidates = [p for p in state.get('proposals', []) if p.get('status') == 'proposed'
                      and p.get('focus_column') == state.get('focus_column')]
        if candidates:
            chosen = candidates[-1]
            if chosen.get('kind') == 'clarify' or signature(chosen.get('code')):
                flow['active_step'] = _new_step(state, chosen, notebook)
                chosen['step_id'] = flow['active_step']['id']
                for old in candidates[:-1]:
                    old['status'] = 'superseded'
    step = flow.get('active_step')
    if not step:
        return
    if step['kind'] == 'clarify':
        definition = state.get('definition_availability') or {}
        if definition.get('focus_column') == flow['focus_column'] and definition.get('status') in {'available', 'unavailable'}:
            step['status'] = 'answered_' + definition['status']
        return
    if step['status'] not in {'awaiting_execution', 'needs_revalidation'}:
        return
    current_version = notebook.get('current_input_version')
    current_kind = notebook.get('dataset_kind')
    version_changed = current_version and step.get('expected_version') and current_version != step['expected_version']
    kind_changed = current_kind and step.get('dataset_kind') and current_kind != step['dataset_kind']
    if version_changed or kind_changed:
        step['status'] = 'needs_revalidation'
        step['expected_version'] = current_version
        step['dataset_kind'] = current_kind
        step['scope_changed'] = True
    current_ids = set(state.get('current_evidence_ids') or [])
    for item in state.get('observations', []):
        if (item['id'] not in current_ids or item['id'] in step['baseline_evidence_ids']
                or not item.get('executed_at')
                or execution_receipt(item) in step.get('baseline_execution_receipts', [])
                or not item.get('success') or item.get('stale_scope') or not item.get('version_verified')
                or item.get('dataset_kind') != step.get('dataset_kind')
                or signature(item.get('code')) != step.get('signature')):
            continue
        step['status'] = 'observed'
        step['completion_evidence_id'] = item['id']
        flow['phase'] = 'reason'
        for proposal in state.get('proposals', []):
            if proposal.get('step_id') == step['id']:
                proposal['status'] = 'observed'
        return
    # The old proposal projection must not claim completion from an old record.
    for proposal in state.get('proposals', []):
        if proposal.get('step_id') == step['id']:
            proposal['status'] = 'proposed'


def bind_learning_context(state, context):
    flow = workflow(state)
    profile = context.get('learner_skills') or []
    relevant = {'null_analysis', 'pandas_dataframe', 'data_analysis', 'data_interpretation'}
    profile = sorted([item for item in profile if isinstance(item, dict)],
                     key=lambda item: item.get('skill_name') not in relevant)
    flow['learner_skills'] = [{k: item.get(k) for k in ('skill_name', 'status')}
                             for item in profile[:4]]
    flow['project_goal'] = str(context.get('task_brief') or '')[:400]
    flow['stage_goal'] = STAGE_PLAYBOOKS['prepare.profile']['goal']
    flow['learning_sequence'] = STAGE_PLAYBOOKS['prepare.profile']['sequence']


def pending_step(state, message):
    flow = workflow(state)
    step = flow.get('active_step')
    if not step or step['status'] not in {'awaiting_execution', 'needs_revalidation', 'awaiting_answer'}:
        return None
    if step['kind'] == 'clarify':
        step['help_requests'] += 1
        return step
    if step['kind'] not in {'inspect', 'refresh'}:
        return None
    if signature(step.get('code')) is None:
        step['status'] = 'blocked'
        step['blocker'] = 'Saved task expression is unsupported; it was not executed.'
        return None
    step['help_requests'] += 1
    skill = {'missing_count': 'null_analysis', 'distribution': 'data_analysis'}.get(
        (expression_contract(step.get('code') or '') or {}).get('operation'), 'pandas_dataframe')
    status = next((x.get('status') for x in flow.get('learner_skills', []) if x.get('skill_name') == skill), 'new')
    step['assistance_level'] = determine_assistance_level(skill_status=status, learner_message=message)
    return step


def prompt_workflow(state):
    flow = workflow(state)
    result = {key: flow.get(key) for key in ('schema_version', 'question', 'phase', 'status',
                                            'project_goal', 'stage_goal', 'learning_sequence', 'learner_skills')}
    active = flow.get('active_step') or {}
    result['active_step'] = {key: active.get(key) for key in ('id', 'kind', 'status', 'instruction', 'blocker')}
    result['completed_steps'] = [{key: x.get(key) for key in ('id', 'kind', 'status', 'completion_evidence_id')}
                                 for x in flow.get('step_history', [])[-4:]]
    return result


def document_deferral(state, message):
    """Record a learner-requested unresolved finding, never a treatment decision."""
    text = normalized(message)
    recording = any(word in text for word in ('kaydet', 'belgele', 'record', 'document', 'leg vast'))
    deferring = any(word in text for word in ('degisiklik yapmadan', 'degistirmeden', 'ertele', 'defer', 'without changing', 'onopgelost'))
    if not recording or not deferring:
        return None
    flow = workflow(state)
    active = flow.get('active_step')
    if active and active['status'] in {'awaiting_execution', 'needs_revalidation', 'awaiting_answer'}:
        return None
    current = set(state.get('current_evidence_ids') or [])
    evidence = [x for x in state.get('observations', []) if x['id'] in current
                and x.get('success') and x.get('version_verified') and not x.get('stale_scope')
                and x.get('input_rows') is not None and (x.get('analysis_contract') or {}).get('supported')
                and flow['focus_column'] in x.get('fields', [])]
    if len({signature(x['code']) for x in evidence}) < 2:
        return None
    facts = [{'evidence_id': x['id'], 'contract': deepcopy(x['analysis_contract']),
              'input_rows': x['input_rows'], 'data_version': x.get('input_data_version'),
              'dataset_kind': x.get('dataset_kind')} for x in evidence[:8]]
    identity = hashlib.sha256(json.dumps([flow['focus_column'], sorted(x['evidence_id'] for x in facts)]).encode()).hexdigest()[:20]
    finding = {'id': identity, 'focus_column': flow['focus_column'], 'decision': 'deferred',
               'user_requested': True, 'facts': facts, 'data_changed': False,
               'uncertainties': ['No missingness cause or treatment rule established by these observations.'],
               'coverage': 'recorded_notebook_observations', 'full_source_verified': False}
    if not any(x['id'] == identity for x in state['finding_ledger']):
        state['finding_ledger'].append(finding)
    flow['findings'] = [x for x in state['finding_ledger'] if x.get('focus_column') == flow['focus_column']]
    flow['status'] = 'documented_deferred'
    flow['phase'] = 'decide'
    return finding


def schema_start_action(state, notebook):
    """Start without fabricated execution evidence, using a verified schema only."""
    focus = state.get('focus_column')
    if (not focus or focus not in state.get('available_columns', [])
            or not notebook.get('current_input_version')
            or not notebook.get('configured_development_rows')
            # The workspace profile describes the source/working schema, not
            # necessarily a transformed processed table. That path needs a
            # recorded observation until it has its own verified schema.
            or notebook.get('dataset_kind') not in {'raw', 'working'}):
        return None
    code = f'df[{focus!r}].isna().sum()'
    if signature(code) is None:
        return None
    return {'kind': 'inspect', 'code': code, 'focus_column': focus, 'columns': [focus],
            'evidence_ids': [], 'instruction': '', 'why': ''}
