"""Conservative comparison of two complete printed normalized Series outputs.

Labels are printed labels, not inferred Python types or business meanings.
Ambiguous, partial, empty or non-proportion outputs never yield a conclusion.
"""
import re

from backend.app.mentor_observation_contract import field_label


def proportions(observation):
    contract = observation.get('analysis_contract') or {}
    if (not contract.get('supported') or contract.get('operation') != 'distribution'
            or contract.get('output_truncated') or contract.get('options', {}).get('normalize') is not True
            or contract.get('options', {}).get('dropna') is not False):
        return None
    lines = contract.get('recorded_output', '').strip().splitlines()
    if not 2 <= len(lines) <= 16 or not re.fullmatch(r'(?:Name: .*, )?dtype: (?:float64|Float64)', lines[-1]):
        return None
    columns = contract.get('measured_columns') or []
    if len(columns) != 1:
        return None
    rows = lines[:-1]
    if rows and rows[0].strip() == columns[0]:
        rows = rows[1:]
    values = {}
    for line in rows:
        match = re.fullmatch(r'\s*(.{1,120}?)\s{2,}([0-9]+(?:\.[0-9]+)?(?:e[-+]?[0-9]+)?)\s*', line, re.I)
        if not match:
            return None
        label, value = match[1].strip(), float(match[2])
        if not label or label in values or not 0 <= value <= 1:
            return None
        values[label] = value
    if not values or abs(sum(values.values()) - 1) > .0001:
        return None
    return values


def render_relationship_comparison(state, language):
    relationship = state.get('relationship_investigation') or {}
    if relationship.get('status') != 'comparison_outputs_recorded':
        return None
    target, helper = relationship['target_column'], relationship['helper_column']
    expected_transform = 'missing_indicator' if relationship['candidate_kind'] == 'co_missingness' else None
    by_id = {x['id']: x for x in state.get('observations', [])}
    sides = {}
    for identity in state.get('current_evidence_ids', []):
        item = by_id.get(identity) or {}
        contract = item.get('analysis_contract') or {}
        predicate = contract.get('row_predicate') or {}
        if (item.get('success') and item.get('version_verified') and not item.get('stale_scope')
                and item.get('input_data_version') == relationship['input_version']
                and contract.get('measured_columns') == [helper]
                and contract.get('measurement_transform') == expected_transform
                and predicate.get('column') == target and predicate.get('op') in {'missing', 'present'}):
            sides.setdefault(predicate['op'], proportions(item))
    if not sides.get('missing') or not sides.get('present'):
        return {'tr': 'İki karşılaştırma çıktısı kaydedildi; fakat tam ve açık oran dağılımları güvenle okunamadığı için ilişki hakkında sonuç çıkarmıyorum. Veri değiştirilmedi.',
                'en': 'Both outputs are recorded, but complete unambiguous proportions could not be read safely. No relationship conclusion or data change is made.',
                'nl': 'Beide uitkomsten zijn opgeslagen, maar volledige eenduidige verhoudingen konden niet veilig worden gelezen. Geen conclusie over samenhang of gegevenswijziging.'}[language]
    left, right = sides['missing'], sides['present']
    labels = set(left) | set(right)
    label = max(sorted(labels), key=lambda x: abs(left.get(x, 0) - right.get(x, 0)))
    a, b = left.get(label, 0) * 100, right.get(label, 0) * 100
    difference = abs(a - b)
    description = {'tr': f'çıktıda {field_label(label)} olarak gösterilen etiket',
                   'en': f'the printed label {field_label(label)}',
                   'nl': f'het weergegeven label {field_label(label)}'}[language]
    if expected_transform == 'missing_indicator' and label in {'True', 'False'}:
        description = {'tr': 'yardımcı sütunun boş olması' if label == 'True' else 'yardımcı sütunun dolu olması',
                       'en': 'helper missingness' if label == 'True' else 'helper presence',
                       'nl': 'ontbrekende hulpkolomwaarde' if label == 'True' else 'aanwezige hulpkolomwaarde'}[language]
    return {
        'tr': f'Kaydedilen iki dağılımı karşılaştırınca: {field_label(helper)} için {description}, {field_label(target)} boş grubunda yaklaşık %{a:.1f}, dolu grubunda yaklaşık %{b:.1f}. Görünen oran farkı yaklaşık {difference:.1f} yüzde puan. Bu gözlem eksikliğin nedenini veya doğru temizleme kararını tek başına kanıtlamaz.',
        'en': f'Comparing the two recorded distributions: for {field_label(helper)}, {description} is approximately {a:.1f}% in the missing-{field_label(target)} group and {b:.1f}% in the present group, a visible difference of about {difference:.1f} percentage points. This alone establishes neither a cause nor a cleaning decision.',
        'nl': f'Vergelijking van de twee opgeslagen verdelingen: bij {field_label(helper)} is {description} ongeveer {a:.1f}% in de groep met ontbrekende {field_label(target)} en {b:.1f}% in de aanwezige groep, een zichtbaar verschil van ongeveer {difference:.1f} procentpunt. Dit bewijst geen oorzaak of juiste opschoningsbeslissing.',
    }[language]
