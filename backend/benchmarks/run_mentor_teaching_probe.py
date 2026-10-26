"""Two bounded live teaching calls on invented data, then a local code check.

No user project is touched. Mechanical passage does not prove novice learning.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd

from backend.app import database
from backend.app.mentor_relationship_service import build_relationship_map
from backend.app.mentor_research_service import generate_research_reply
from backend.app.mentor_research_store import load_research_state
from backend.benchmarks.run_mentor_connected_followup import recorded_cell


def synthetic_context(*, public=False, shared=False):
    frame = pd.DataFrame({
        'delivery_days': [None if i % 4 == 0 else i % 8 for i in range(1000)],
        'shipment_status': ['pending' if i % 4 == 0 else 'delivered' for i in range(1000)],
    })
    cell = recorded_cell('count', "df['delivery_days'].isna().sum()", 250,
                         'delivery_days', 'teaching-synthetic-v1', 1000)
    return {'workspace_id': 'synthetic-teaching-only', 'ui_context': {'language': 'tr'},
        'mentor_setup': {'experience_level': 'beginner', **({'notebook_teaching_context': 'question_and_code'} if shared else {})},
        'teaching_data_policy': {'usage_context': 'personal', 'data_sensitivity': 'public' if public else None},
        'dataset_profile_summary': {'columns': list(frame.columns)},
        'local_relationship_map': build_relationship_map(frame, input_version='teaching-synthetic-v1'),
        'artifacts': {'selected_notebook': {'notebook_id': 'n1', 'dataset_kind': 'working',
            'configured_development_rows': 1000, 'current_input_version': 'teaching-synthetic-v1',
            'latest_cell': cell, 'recent_cells': [cell]}}}


def run_probe(*, public=False, shared=False):
    context = synthetic_context(public=public, shared=shared)
    generate_research_reply(context,
        'delivery_days sayımını yaptım. Kaynak açıklaması elimde yok. Sonraki tek adımı söyle.', [], allow_provider=False)
    before = load_research_state(context['workspace_id'], 'n1')
    task = deepcopy(before['workflow']['active_step'])
    turns, history = [], []
    for index, message in enumerate((
        'Önce neyi seçmeliyim? Kodu verme.',
        'Tam anlamadım. Ben yalnız eksikleri saydım, satır seçmedim. Daha basit anlat; kodu verme.',
        'Kodu göster.',
    )):
        reply = generate_research_reply(context, message, history, allow_provider=index < 2)
        after = load_research_state(context['workspace_id'], 'n1')
        trace = after['last_validation']
        turns.append({'message': message, 'reply': reply, 'diagnostics': trace,
            'same_pending_task': after['workflow']['active_step']['id'] == task['id']
                and after['workflow']['active_step']['status'] == 'awaiting_execution'
                and after['proposals'] == before['proposals']})
        history += [{'role': 'user', 'content': message}, {'role': 'assistant', 'content': reply}]
        if index < 2 and not trace.get('teaching_accepted'):
            break
    passed = (len(turns) == 3 and all(x['same_pending_task'] for x in turns)
              and all(x['diagnostics'].get('teaching_accepted') for x in turns[:2]))
    if passed:
        passed = all('```' not in x['reply'] for x in turns[:2]) and '```python\n' + task['code'] + '\n```' in turns[2]['reply']
    return {'synthetic_data_only': True, 'turns': turns, 'mechanical_checks_passed': passed,
        'novice_usability_accepted': False, 'project_completion_proven': False, 'human_review_required': True,
        'review_questions': [
            'Does it distinguish counting missing cells from selecting rows?',
            'Does the second explanation address the difficulty differently?',
            'Is the first action small enough to attempt without knowing the full expression?',
            'Are normalized values described as proportions rather than raw counts?',
            'Does it avoid inventing results or claiming the learner already filtered rows?']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', required=True, help='Allow at most two configured provider attempts.')
    parser.add_argument('--public-synthetic', action='store_true')
    parser.add_argument('--question-and-code', action='store_true', help='Exercise explicit scoped sharing on an unclassified personal project.')
    parser.add_argument('--output-dir', type=Path, default=Path('backend/benchmarks/results/teaching-probe'))
    args = parser.parse_args(argv)
    folder = args.output_dir / datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True, exist_ok=False)
    previous = database.DATABASE_PATH
    try:
        database.DATABASE_PATH = folder / 'isolated.sqlite'
        database.init_db()
        report = run_probe(public=args.public_synthetic, shared=args.question_and_code)
        path = folder / 'report.json'
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    finally:
        database.DATABASE_PATH = previous
    print('REPORT:', path.resolve())
    for turn in report['turns']:
        print('LEARNER:', turn['message'])
        print('MENTOR:', turn['reply'])
        print('TEACHING:', turn['diagnostics'].get('teaching_accepted'), turn['diagnostics'].get('reason', ''))
    print('Mechanical checks:', report['mechanical_checks_passed'])
    print('Novice learning and project completion are unproven. Human review required.')
    return 0 if report['mechanical_checks_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
