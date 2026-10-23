"""Evidence-based small steps that do not require a domain guess or an AI call.

These are proposed read-only inspections, never executed operations. Other
research states continue through the normal planner; there is no generic filler.
"""
import re
from backend.app.mentor_preview_evidence_service import missing_preview_rows


def new_task_declined(message: str) -> bool:
    return bool(re.search(r'(?:yeni\s+(?:görev|gorev|işlem|islem).{0,15}(?:verme|önerme|onerme)|'
                 r'no\s+(?:new\s+)?(?:task|exercise)|geen\s+(?:nieuwe\s+)?opdracht)', message, re.I))


def guidance_requested(message: str) -> bool:
    if new_task_declined(message):
        return False
    return bool(re.search(r'devam|ilerle|yönlendir|yonlendir|sonraki|sıradaki|siradaki|'
                          r'next\s+step|continue|guide\s+me|volgende\s+stap|verder|help\s+me', message, re.I))


def plan_missing_preview(state: dict, message: str) -> dict | None:
    """After a positive simple null count, inspect examples if a source is absent.

    Restrict to the exact current unfiltered target count and a known version.
    A recorded or pending equivalent preview means this step is already covered.
    """
    if not guidance_requested(message):
        return None
    focus = state.get('focus_column')
    definition = state.get('definition_availability') or {}
    if not focus or definition.get('focus_column') != focus or definition.get('status') != 'unavailable':
        return None
    current = state.get('current_evidence_ids') or []
    latest = next((x for x in state.get('observations', []) if current and x['id'] == current[0]), None)
    if (not latest or not latest.get('success') or latest.get('stale_scope')
            or not latest.get('version_verified') or latest.get('input_rows') is None):
        return None
    contract = latest.get('analysis_contract') or {}
    if (not contract.get('supported') or contract.get('operation') != 'missing_count'
            or contract.get('measured_columns') != [focus]
            or contract.get('row_predicate') != {'op': 'all_current_df'}
            or type(contract.get('result')) is not int or contract['result'] <= 0):
        return None
    scope = lambda x: (x.get('input_rows'), x.get('dataset_kind'), x.get('input_data_version'))
    for item in state.get('observations', []):
        old = item.get('analysis_contract') or {}
        if (item.get('success') and not item.get('stale_scope') and scope(item) == scope(latest)
                and old.get('supported') and old.get('operation') in {'preview_head', 'preview_tail'}
                and old.get('row_predicate') == {'op': 'missing', 'column': focus}):
            return None
    if any(x.get('kind') == 'inspect' and x.get('status') == 'proposed' for x in state.get('proposals', [])):
        return None
    # repr quotes a literal column name; it is never interpolated as Python code.
    code = f'df.loc[df[{focus!r}].isna()].head(5)'
    return {'next_action': {'kind': 'inspect', 'code': code}, 'evidence_ids': [latest['id']]}


def plan_preview_continuation(state: dict, message: str) -> dict | None:
    focus = state.get('focus_column')
    current = state.get('current_evidence_ids') or []
    latest = next((x for x in state.get('observations', []) if current and x['id'] == current[0]), None)
    if (not latest or not latest.get('success') or latest.get('stale_scope')
            or not latest.get('version_verified') or latest.get('input_rows') is None):
        return None
    contract = latest.get('analysis_contract') or {}
    if (not focus or not contract.get('supported')
            or contract.get('row_predicate') != {'op': 'missing', 'column': focus}
            or contract.get('operation') not in {'preview_head', 'preview_tail', 'distribution'}):
        return None
    if not guidance_requested(message):
        if re.search(r'sonu[cç]|[cç][ıi]kt[ıi]|result|output|uitvoer|uitkomst', message, re.I):
            return {'next_action': None, 'evidence_ids': [latest['id']]}
        return None
    preferred = [key for key in state.get('available_columns', [])
                 if re.search(r'(?<!\w)' + re.escape(key) + r'(?!\w)', message, re.I)]
    rows = missing_preview_rows(latest, preferred)
    if not rows:
        return None
    definition = state.get('definition_availability') or {}
    if definition.get('focus_column') != focus or definition.get('status') != 'unavailable':
        return None
    helpers = [key for key in rows[0] if key != focus and key in state.get('available_columns', [])]
    named = [key for key in helpers if re.search(r'(?<!\w)' + re.escape(key) + r'(?!\w)', message, re.I)]
    if len(named) == 1:
        helper = named[0]
    elif named:
        return None
    else:
        # A single observed boolean is an unambiguous grouping candidate,
        # never proof that True/False has any business meaning.
        boolean = [key for key in helpers if all(type(row[key]) is bool for row in rows)]
        if len(boolean) != 1:
            return None
        helper = boolean[0]
    scope = lambda x: (x.get('input_rows'), x.get('dataset_kind'), x.get('input_data_version'))
    for item in state.get('observations', []):
        old = item.get('analysis_contract') or {}
        if (item.get('success') and not item.get('stale_scope') and scope(item) == scope(latest)
                and old.get('supported') and old.get('operation') == 'distribution'
                and old.get('measured_columns') == [helper] and old.get('row_predicate') == contract['row_predicate']):
            return None
    if any(x.get('kind') == 'inspect' and x.get('status') == 'proposed' for x in state.get('proposals', [])):
        return None
    code = f'df.loc[df[{focus!r}].isna(), {helper!r}].value_counts(dropna=False)'
    return {'next_action': {'kind': 'inspect', 'code': code}, 'evidence_ids': [latest['id']]}
