"""Refresh one saved legacy preview, without inventing a new analysis or running it."""
from backend.app.mentor_local_progress_service import guidance_requested, new_task_declined
from backend.app.mentor_tutoring_service import support_requested
from backend.app.mentor_observation_contract import expression_contract, field_label


def plan_evidence_refresh(state: dict, message: str) -> dict | None:
    if new_task_declined(message):
        return None
    if not (guidance_requested(message) or support_requested(message)):
        return None
    focus = state.get('focus_column')
    definition = state.get('definition_availability') or {}
    if (not focus or definition.get('focus_column') != focus
            or definition.get('status') != 'unavailable'):
        return None
    if any(p.get('kind') == 'inspect' and p.get('status') == 'proposed'
           for p in state.get('proposals', [])):
        return None
    current = state.get('current_evidence_ids') or []
    by_id = {item['id']: item for item in state.get('observations', [])}
    if any(item.get('id') in current and item.get('success')
           and not item.get('stale_scope') and item.get('version_verified')
           and (item.get('analysis_contract') or {}).get('supported')
           and item['analysis_contract'].get('operation') == 'preview_head'
           and item['analysis_contract'].get('row_predicate') == {'op': 'missing', 'column': focus}
           for item in by_id.values()):
        return None
    for ref in current:
        item = by_id.get(ref) or {}
        if (not item.get('success') or item.get('stale_scope')
                or item.get('version_verified') or not item.get('cell_id')
                or item.get('input_rows') is None
                or not (item.get('analysis_contract') or {}).get('supported')):
            continue
        code = item.get('code') or ''
        contract = expression_contract(code)
        if (contract.get('supported') is False
                or contract.get('operation') != 'preview_head'
                or contract.get('row_predicate') != {'op': 'missing', 'column': focus}
                or contract.get('options', {}).get('limit', 5) > 5):
            continue
        previous = state.get('pending_evidence_refresh') or {}
        return {'status': 'requested', 'cell_id': item['cell_id'], 'evidence_id': ref,
                'focus_column': focus, 'operation': 'preview_head',
                'limit': contract['options'].get('limit', 5),
                'section_title': item.get('section_title'),
                'input_rows_at_old_execution': item['input_rows'],
                'help_requested': support_requested(message),
                'requests': previous.get('requests', 0) + 1 if previous.get('evidence_id') == ref else 1}
    return None


def render_evidence_refresh(action: dict, language: str) -> str:
    target = field_label(action['focus_column'])
    count = action['limit']
    if action.get('help_requested') and action.get('requests', 0) > 1:
        return {
            'tr': (f'Aynı adımdayız. Notebook’ta {target} boş olan satırlardan '
                   f'{count} örnek gösteren çıktı tablosunu bul. Bu çıktının üstündeki '
                   'kod kutusunun sol kenarında bulunan ▶ düğmesine bir kez tıkla. '
                   'Böylece o hücrenin çıktısını güncellemiş olacağız.'),
            'en': (f'We are on the same step. Find the output table with {count} example '
                   f'rows where {target} is missing. Click ▶ once at the left edge of '
                   'the code box above that output to refresh this cell.'),
            'nl': (f'We blijven bij dezelfde stap. Zoek de uitvoertabel met {count} '
                   f'voorbeeldrijen waarin {target} ontbreekt. Klik eenmaal op ▶ links '
                   'van het codevak boven die uitvoer om deze cel te verversen.'),
        }[language]
    # No historical counts or output dump. Re-running a named existing cell is
    # not a claim that the recorded preview is already current or completed.
    return {
        'tr': (f'Önce mevcut örnek çıktıyı güncelleyelim. Notebook’ta {target} boş olan '
               f'satırların ilk {count} örneğini gösterdiğin kayıtlı hücreyi bul ve '
               'solundaki ▶ çalıştır düğmesine bir kez bas.\n\n'
               'Bunu istememin nedeni: Eski çıktının hangi veri sürümüne ait olduğu '
               'kayıtlı değil. Tüm notebook’u çalıştırmana veya veriyi değiştirmene gerek yok.'),
        'en': (f'First refresh the saved examples. In the notebook, find the existing cell '
               f'showing the first {count} rows where {target} is missing and click its '
               '▶ Run button once.\n\nThe older output has no recorded data version. '
               'Only this cell needs to run; no data edit is requested.'),
        'nl': (f'Ververs eerst de opgeslagen voorbeelden. Zoek in het notebook de bestaande '
               f'cel met de eerste {count} rijen waarin {target} ontbreekt en klik eenmaal '
               'op de ▶ uitvoerknop.\n\nBij de oude uitvoer is geen dataversie opgeslagen. '
               'Alleen deze cel hoeft te draaien; je hoeft de gegevens niet te wijzigen.'),
    }[language]
