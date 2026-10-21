"""Windows locale must not change the bytes used by recorded mentor regressions."""
import json
from pathlib import Path

import pytest

from backend.tests import (
    test_mentor_observation_contract as groups,
    test_mentor_research_review_guard as review,
    test_mentor_research_length_resume as length,
    test_mentor_research_output_budget as budget,
)


@pytest.mark.parametrize('loader,filename', [
    (groups.actual.__wrapped__, 'research_group_confusion.json'),
    (review.actual_report.__wrapped__, 'research_recorded_code_review.json'),
    (length.actual.__wrapped__, 'research_long_response.json'),
    (budget.recorded_attempts, 'research_truncated_output.json'),
])
def test_recorded_utf8_is_independent_of_windows_default_encoding(monkeypatch,loader,filename):
    path=Path(__file__).parent/'fixtures'/filename
    correct=json.loads(path.read_bytes().decode('utf-8'))
    if filename=='research_truncated_output.json':
        correct=correct['model_attempts']
    original_open=Path.open
    def windows_default(self,mode='r',buffering=-1,encoding=None,errors=None,newline=None):
        if 'b' not in mode and encoding in (None,'locale'):
            encoding='cp1252'
        return original_open(self,mode,buffering,encoding,errors,newline)
    monkeypatch.setattr(Path,'open',windows_default)
    assert loader()==correct
