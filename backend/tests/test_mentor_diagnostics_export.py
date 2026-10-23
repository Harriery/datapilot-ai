"""A rejected production turn can be investigated without another AI call."""
import hashlib
import json
import sqlite3
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from backend.app import database
from backend.app.mentor_research_service import generate_research_reply
from backend.app.mentor_research_store import save_research_state, load_research_state
from backend.benchmarks.export_mentor_diagnostics import main, read_diagnostics
from backend.tests.test_mentor_research_service import state, grounded_proposal, context


def test_export_retains_actual_rejected_attempts_without_replaying_or_writing_memory(tmp_path, monkeypatch):
    db = tmp_path / 'mentor.sqlite'
    monkeypatch.setattr(database, 'DATABASE_PATH', db)
    database.init_db()
    invalid = grounded_proposal(state())
    invalid.next_action.code = None
    with patch('backend.app.mentor_research_service.get_ai_runtime',
               return_value=SimpleNamespace(client=None, provider='groq', model='test')), \
         patch('backend.app.mentor_research_service.guarded_responses_parse',
               return_value=SimpleNamespace(output_parsed=invalid)) as provider:
        reply = generate_research_reply(context(), 'sensor_value için kod verme, yönlendir', [])
    assert 'denetiminden geçmedi' in reply and provider.call_count == 2
    saved = load_research_state('w1', 'n1')
    before = hashlib.sha256(db.read_bytes()).hexdigest()
    report = read_diagnostics(db, focus='SENSOR_VALUE')
    output = tmp_path / 'export' / 'report.json'
    with patch('backend.app.mentor_research_service.get_ai_runtime') as runtime:
        assert main(['--database', str(db), '--focus', 'sensor_value', '--output', str(output)]) == 0
    runtime.assert_not_called()
    exported = json.loads(output.read_text(encoding='utf-8'))
    assert exported == report
    assert hashlib.sha256(db.read_bytes()).hexdigest() == before
    record = exported['records'][0]
    assert record['last_validation']['errors'] == saved['last_validation']['errors']
    assert len(record['last_validation']['model_attempts']) == 2
    for original, attempt in zip(saved['last_validation']['model_attempts'], record['last_validation']['model_attempts']):
        assert attempt['errors'] == original['errors']
        assert attempt['raw_plan']['next_action']['code'] is None
        assert attempt['raw_plan']['evidence_ids'] == original['raw_plan']['evidence_ids']
    assert record['current_evidence_ids'] == saved['current_evidence_ids']
    assert record['observations'][0]['analysis_contract'] == saved['observations'][0]['analysis_contract']


def test_export_selects_notebooks_and_omits_unneeded_payloads(tmp_path, monkeypatch):
    db = tmp_path / 'mentor.sqlite'
    monkeypatch.setattr(database, 'DATABASE_PATH', db)
    database.init_db()
    secret = 'SHOULD_NOT_LEAVE_MEMORY'
    s = state()
    s['observations'][0].update(output=secret, preview_rows=[{'private': secret}])
    s['runtime'] = {'api_key': secret}
    s['history'] = [secret]
    s['last_validation'] = {'accepted': False, 'errors': ['Inspection code omits the active target'],
                            'runtime': {'api_key': secret}, 'provider_failure': {'body': secret},
                            'model_attempts': [{'answer': secret, 'proposal': {'answer': secret},
                                                'raw_plan': {'answer': secret, 'evidence_ids': ['e1'],
                                                             'next_action': {'kind': 'inspect', 'code': 'df.head()', 'why': secret}},
                                                'response_metadata': {'body': secret}}]}
    save_research_state('w1', 'n1', s)
    save_research_state('w2', 'n2', {**s, 'focus_column': 'other'})
    report = read_diagnostics(db, focus='sensor_value')
    assert len(report['records']) == 1
    assert secret not in json.dumps(report)
    assert report['records'][0]['last_validation']['model_attempts'][0]['raw_plan']['next_action']['code'] == 'df.head()'
    assert len(read_diagnostics(db)['records']) == 2
    assert read_diagnostics(db, focus='absent')['records'] == []


def test_missing_database_is_not_created(tmp_path):
    path = tmp_path / 'absent.sqlite'
    with pytest.raises(FileNotFoundError):
        read_diagnostics(path)
    assert not path.exists()


def test_database_without_research_memory_is_not_migrated(tmp_path):
    path = tmp_path / 'old.sqlite'
    sqlite3.connect(path).close()
    assert read_diagnostics(path)['records'] == []
    with sqlite3.connect(path) as connection:
        assert connection.execute('SELECT name FROM sqlite_master').fetchall() == []


def test_export_cannot_overwrite_database_or_existing_report(tmp_path, monkeypatch):
    path = tmp_path / 'mentor.sqlite'
    monkeypatch.setattr(database, 'DATABASE_PATH', path)
    database.init_db()
    save_research_state('w1', 'n1', state())
    before = path.read_bytes()
    with pytest.raises(SystemExit):
        main(['--database', str(path), '--output', str(path)])
    assert path.read_bytes() == before
    output = tmp_path / 'report.json'
    output.write_text('previous report', encoding='utf-8')
    with pytest.raises(FileExistsError):
        main(['--database', str(path), '--output', str(output)])
    assert output.read_text(encoding='utf-8') == 'previous report'
