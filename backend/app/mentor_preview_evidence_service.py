"""Bounded observations from recorded missing-row examples, never domain rules."""
import json
import math

from backend.app.mentor_observation_contract import field_label


def preview_contradicts_selection(observation: dict) -> bool:
    contract = observation.get('analysis_contract') or {}
    where = contract.get('row_predicate') or {}
    rows = observation.get('preview_rows')
    if contract.get('operation') not in {'preview_head', 'preview_tail'} or where.get('op') != 'missing' or not isinstance(rows, list):
        return False
    target = where.get('column')
    for row in rows[:5]:
        if isinstance(row, dict) and target in row:
            value = row[target]
            if value is not None and not (type(value) is float and math.isnan(value)):
                return True
    return False


def missing_preview_rows(observation: dict) -> list[dict]:
    contract = observation.get('analysis_contract') or {}
    where = contract.get('row_predicate') or {}
    rows = observation.get('preview_rows')
    if (not contract.get('supported') or contract.get('operation') not in {'preview_head', 'preview_tail'}
            or where.get('op') != 'missing' or not isinstance(rows, list)
            or not 0 < len(rows) <= min(5, contract.get('options', {}).get('limit', 5))):
        return []
    target = where.get('column')
    projection = contract.get('measured_columns')
    clean = []
    for row in rows:
        if not isinstance(row, dict) or target not in row or len(row) > 12:
            return []
        if projection is not None and set(row) - set(projection):
            return []
        value = row[target]
        if value is not None and not (type(value) is float and math.isnan(value)):
            return []
        if any(not isinstance(key, str) or not (value is None or type(value) in (str, int, float, bool))
               or isinstance(value, str) and len(value) > 120 for key, value in row.items()):
            return []
        clean.append({key: None if type(value) is float and not math.isfinite(value) else value
                      for key, value in row.items()})
    if any(set(row) != set(clean[0]) for row in clean):
        return []
    return clean


def preview_summary(observation: dict, language: str) -> str | None:
    rows = missing_preview_rows(observation)
    if not rows:
        return None
    target = observation['analysis_contract']['row_predicate']['column']
    parts = []
    # Values are exact counts in at most five recorded examples. Keep types
    # distinct (True is not integer 1), with no population/causation inference.
    for field in [key for key in rows[0] if key != target][:2]:
        counts = {}
        for row in rows:
            value = row[field]
            label = json.dumps(value, ensure_ascii=False)
            counts[label] = counts.get(label, 0) + 1
        parts.append(field_label(field) + ': ' + ', '.join(field_label(value[:50]) + f' ({count})' for value, count in counts.items()))
    if not parts:
        return None
    lead = {'tr': f'Yalnızca gösterilen {len(rows)} örnek satırda görülen değerler: ',
            'en': f'Values in only the {len(rows)} displayed example rows: ',
            'nl': f'Waarden in alleen de {len(rows)} getoonde voorbeeldrijen: '}[language]
    tail = {'tr': ' Bu sayılar eksik grubun tamamının dağılımı değildir.',
            'en': ' These counts are not the distribution of the whole missing-value group.',
            'nl': ' Deze aantallen zijn niet de verdeling van de hele groep met ontbrekende waarden.'}[language]
    # If labels would make a misleadingly shortened statement, omit the entire
    # optional summary rather than truncate individual facts into another claim.
    result = lead + '; '.join(parts) + tail
    return result if len(result) <= 850 else None
