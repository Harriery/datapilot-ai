"""Scaffold an already-validated pending inspection without assigning a new one."""
import hashlib
import json
import re
import unicodedata

from backend.app.mentor_observation_contract import expression_contract, field_label


def normalized(text: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', text.casefold())
                   if not unicodedata.combining(c)).replace('ı', 'i').replace('’', "'")


def explicit_code_requested(message: str) -> bool:
    text = normalized(message)
    if re.search(r'kod\w*\s+(?:gosterme\w*|verme\w*|yazma\w*|paylasma\w*)|'
                 r'cozum\w*\s+(?:verme\w*|gosterme\w*|soyleme\w*)|'
                 r'without\s+(?:giving\s+(?:me\s+)?)?(?:(?:any|the)\s+)?(?:code|solution)|no\s+(?:(?:python|sql)\s+)?(?:code|solution)|'
                 r'(?:do not|don\x27t)\s+(?:show|give|write|provide).{0,20}(?:code|solution)|'
                 r'zonder\s+(?:de\s+)?(?:code|oplossing)|geen\s+(?:code|oplossing)|'
                 r'(?:toon|geef)\s+de\s+code\s+niet', text):
        return False
    return bool(re.search(r'\bkodu\s+(?:goster|yaz|ver)\b|\bkodu\s+(?:gosterebilir|gosterir|yazabilir|verebilir)\s*mi\w*\b|\bkod\s+ornegi\s+ver\b|'
                          r'\b(?:show|give)\s+(?:me\s+)?(?:the\s+)?code\b|'
                          r'\b(?:toon|geef)\s+de\s+code\b|\blaat\s+de\s+code\s+zien\b', text))


def support_requested(message: str) -> bool:
    if explicit_code_requested(message):
        return True
    text = normalized(message)
    return bool(re.search(r'nasil\s+(?:yap|yaz|uygula)|nasil.{0,40}bilmiyorum|'
                          r'ipucu\s+ver|anlamadim|ne\s+yapacagimi\s+bilmiyorum|daha\s+(?:basit|ayrintili|detayli|kolay)|'
                          r'(?:don\x27t|do not)\s+know\s+(?:how|what to do)|how\s+(?:do|can)\s+i|'
                          r'give\s+me\s+a\s+hint|still\s+don\x27t\s+understand|'
                          r'explain\s+(?:it\s+)?more\s+simply|'
                          r'weet\s+niet\s+hoe|hoe\s+(?:doe|kan|moet)\s+ik|'
                          r'geef\s+(?:me\s+)?een\s+hint|nog\s+steeds\s+niet|eenvoudiger|simpeler', text))


def plan_pending_support(state: dict, message: str) -> dict | None:
    if not support_requested(message):
        return None
    focus = state.get('focus_column')
    task = next((p for p in reversed(state.get('proposals', []))
                 if p.get('kind') == 'inspect' and p.get('status') == 'proposed'
                 and p.get('focus_column') == focus), None)
    if not task or not task.get('code'):
        return None
    ids = state.get('current_evidence_ids') or []
    refs = task.get('evidence_ids') or []
    by_id = {item['id']: item for item in state.get('observations', [])}
    if (not ids or ids[0] not in refs or not refs or any(ref not in ids for ref in refs)
            or any(not by_id[ref].get('success') or by_id[ref].get('stale_scope')
                   or not by_id[ref].get('version_verified') for ref in refs)):
        return None
    contract = expression_contract(task['code'])
    if (contract.get('supported') is False
            or contract.get('row_predicate') != {'op': 'missing', 'column': focus}
            or contract.get('operation') not in {'preview_head', 'distribution'}):
        return None
    measured = contract.get('measured_columns') or []
    if contract['operation'] == 'distribution' and len(measured) != 1:
        return None
    signature = hashlib.sha256(json.dumps([focus, contract, refs], sort_keys=True).encode()).hexdigest()[:20]
    previous = state.get('tutoring') or {}
    previous = previous if previous.get('task_signature') == signature else {}
    show_code = explicit_code_requested(message)
    level = 3 if show_code else min(3, int(previous.get('level', 0)) + 1)
    language = state.get('response_language', 'tr')
    target = field_label(focus)
    if contract['operation'] == 'preview_head':
        count = contract['options'].get('limit', 5)
        hints = {
            'tr': [f'{target} sütununda boş olan satırları işaretleyen bir koşul düşün. `isna`, boş hücre için True, dolu hücre için False üretir.',
                   f'Bir süzgeç gibi düşün: yalnız koşulu True olan satırlar kalır. {target} doluysa o satır bu önizlemeye girmez. Aynı önizleme adımındayız.',
                   f'`isna` ile oluşan koşulu satır seçiminde kullan; seçilen sonucun ilk {count} kaydını `head` ile görüntüle. Amaç, eksik kayıtların birkaç örneğini görmektir.'],
            'en': [f'Think of a condition marking rows where {target} is empty. `isna` gives True for a missing value and False for a present value.',
                   f'Think of a sieve: only rows where the condition is True remain. A row with a present {target} value does not enter this preview. We are on the same preview task.',
                   f'Use the condition from `isna` to select rows, then display the first {count} selected records with `head`. The aim is to see a few missing-value examples.'],
            'nl': [f'Denk aan een voorwaarde die rijen markeert waarin {target} ontbreekt. `isna` geeft True bij een ontbrekende waarde en False bij een aanwezige waarde.',
                   f'Denk aan een zeef: alleen rijen waarvoor de voorwaarde True is blijven over. Een rij met een aanwezige {target} komt niet in dit voorbeeld. We blijven bij dezelfde opdracht.',
                   f'Gebruik de voorwaarde van `isna` om rijen te selecteren en toon daarna de eerste {count} geselecteerde rijen met `head`. Het doel is een paar ontbrekende waarden te bekijken.'],
        }
    else:
        helper = field_label(measured[0])
        include_missing = contract['options'].get('dropna', True) is False
        hints = {
            'tr': [f'{helper} için `value_counts`, her farklı değerin kaç kez geçtiğini sayar. İncelemenin grubu, {target} eksik olan satırlardır.',
                   f'Aynı eksik-hedef satır seçimini koruyup yalnız {helper} sütununu incele. Değer sayımını bu seçilen sütuna uygulayacağız.',
                   f'Bu görevde yardımcı sütundaki boş değerler de sayılır; `dropna` ayarı False olur.' if include_missing else 'Bu görevde yardımcı sütundaki boş değerler sayım dışında kalır; `dropna` ayarı True olur.'],
            'en': [f'For {helper}, `value_counts` counts occurrences of each distinct value. The inspected group is the rows with missing {target}.',
                   f'Keep the same missing-target row selection and inspect only {helper}. Apply the value count to that selected column.',
                   'This task includes missing helper values in the count; `dropna` is False.' if include_missing else 'This task excludes missing helper values from the count; `dropna` is True.'],
            'nl': [f'Voor {helper} telt `value_counts` hoe vaak elke verschillende waarde voorkomt. De onderzochte groep bevat rijen met ontbrekende {target}.',
                   f'Behoud dezelfde rijselectie met ontbrekende doelwaarden en bekijk alleen {helper}. Pas de waardetelling op die geselecteerde kolom toe.',
                   'Deze opdracht telt ontbrekende hulpwaarden mee; `dropna` is False.' if include_missing else 'Deze opdracht telt ontbrekende hulpwaarden niet mee; `dropna` is True.'],
        }
    return {'decision': {'next_action': {'kind': 'inspect', 'code': task['code']}, 'evidence_ids': refs},
            'task_signature': signature, 'level': level, 'requests': int(previous.get('requests', 0)) + 1,
            'hint': hints[language][level - 1], 'show_code': show_code}
