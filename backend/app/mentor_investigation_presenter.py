"""Short learner-facing explanations of a checked task, not another planner."""
from backend.app.mentor_observation_contract import expression_contract, field_label, predicate_label
from backend.app.mentor_preview_evidence_service import preview_summary
from backend.app.mentor_tutoring_service import explicit_code_requested, normalized


def task_purpose(contract, state, language):
    operation = contract['operation']
    if operation == 'missing_count':
        historical = any(x.get('analysis_contract', {}).get('operation') == 'missing_count'
                         and x.get('analysis_contract', {}).get('measured_columns') == contract.get('measured_columns')
                         and x.get('analysis_contract', {}).get('row_predicate') == contract.get('row_predicate')
                         and not x.get('version_verified') for x in state.get('observations', []))
        return {
            'tr': 'Önceki sayımın veri sürümü belli olmadığı için sayıyı güncelleyeceğiz; sonra eksik grubun ne kadar büyük olduğunu güvenle karşılaştırabiliriz.' if historical else 'Eksikliğin kaç kaydı etkilediğini belirleyerek incelemeye bir başlangıç ölçüsü oluşturacağız.',
            'en': 'Refresh the older unversioned count so the affected group can be compared reliably.' if historical else 'Establish how many records are affected before comparing possible patterns.',
            'nl': 'Ververs de oude telling zonder dataversie zodat we de betrokken groep betrouwbaar kunnen vergelijken.' if historical else 'Bepaal hoeveel records betroffen zijn voordat we patronen vergelijken.',
        }[language]
    purpose = {
        'distribution': ('Seçtiğimiz grupta hangi değerlerin ne sıklıkta görüldüğünü karşılaştıracağız; bu dağılım tek başına nedeni kanıtlamaz.',
                         'Compare how often values occur within the selected group; this alone does not establish a cause.',
                         'Vergelijk hoe vaak waarden in de geselecteerde groep voorkomen; dit bewijst op zichzelf geen oorzaak.'),
        'preview_head': ('Eksik kayıtların örneklerini görerek sonraki karşılaştırma için hangi alanların işe yarayabileceğini inceleyeceğiz.',
                         'Inspect examples to decide which fields may help the next comparison.',
                         'Bekijk voorbeelden om te bepalen welke velden bij de volgende vergelijking kunnen helpen.'),
        'preview_tail': ('Seçilen grubun son örneklerini inceleyerek görünen kayıtları tanıyacağız.',
                         'Inspect examples from the end of the selected group.',
                         'Bekijk voorbeelden aan het einde van de geselecteerde groep.'),
    }.get(operation)
    if purpose:
        return purpose[{'tr': 0, 'en': 1, 'nl': 2}[language]]
    return {'tr': 'Seçilen grubun bu özelliğini ölçerek karşılaştırmada kullanabileceğimiz bir değer elde edeceğiz.',
            'en': 'Measure this property of the selected group for a supported comparison.',
            'nl': 'Meet deze eigenschap van de geselecteerde groep voor een onderbouwde vergelijking.'}[language]


def render_pending_step(step, state, message):
    language = state.get('response_language', 'tr')
    if step['kind'] == 'clarify':
        return {
            'tr': 'Burada senden bir analiz sonucu istemiyorum. Veri sözlüğü, sütunun ne anlama geldiğini açıklayan kaynak metindir. Elinde varsa ilgili açıklamayı paylaş; yoksa bunu söylemen yeterli. Açıklama olmadan da verideki örüntüleri inceleyebiliriz; bulduğumuz örüntüyü kesin bir iş kuralı saymayacağız.',
            'en': 'This asks about a source description, not an analysis result. A data dictionary explains what the column means. Share the relevant definition if you have it, or say it is unavailable. We can inspect patterns without it, while keeping them separate from established business rules.',
            'nl': 'Dit gaat om een bronbeschrijving, niet om een analyseresultaat. Een gegevenswoordenboek legt de betekenis van de kolom uit. Deel de definitie als je die hebt, of zeg dat die ontbreekt. We kunnen patronen onderzoeken zonder ze als vastgestelde bedrijfsregels te behandelen.',
        }[language]
    contract = expression_contract(step['code'])
    group = predicate_label(contract['row_predicate'], language)
    columns = ', '.join(field_label(x) for x in contract.get('measured_columns') or [])
    operation = contract['operation']
    concepts = {
        'missing_count': ('`isna` her boş hücreyi True olarak işaretler. Bu işaretleri `sum` ile sayarız; dolu değerleri değiştirmeyiz.',
                          '`isna` marks missing cells as True; `sum` counts those marks without changing values.',
                          '`isna` markeert ontbrekende cellen als True; `sum` telt die markeringen zonder waarden te wijzigen.'),
        'distribution': ('`value_counts` her farklı değerin kaç kez geçtiğini sayar. Önce satır grubunu, sonra sayılacak sütunu seçeriz.',
                         '`value_counts` counts occurrences of each distinct value after selecting the rows and column.',
                         '`value_counts` telt hoe vaak elke verschillende waarde voorkomt na de rij- en kolomselectie.'),
        'preview_head': ('Önce belirtilen koşula uyan satırları seçer, ardından `head` ile birkaç örneğini gösteririz.',
                         'Select rows matching the condition, then use `head` to show a few examples.',
                         'Selecteer rijen die aan de voorwaarde voldoen en toon met `head` enkele voorbeelden.'),
        'preview_tail': ('Önce belirtilen koşula uyan satırları seçer, ardından `tail` ile son örnekleri gösteririz.',
                         'Select matching rows, then use `tail` to show the last examples.',
                         'Selecteer passende rijen en toon met `tail` de laatste voorbeelden.'),
        'min': ('`min` seçilen değerlerin en küçüğünü bulur.', '`min` finds the smallest selected value.', '`min` vindt de kleinste geselecteerde waarde.'),
        'max': ('`max` seçilen değerlerin en büyüğünü bulur.', '`max` finds the largest selected value.', '`max` vindt de grootste geselecteerde waarde.'),
        'mean': ('`mean` dolu sayısal değerlerin ortalamasını bulur.', '`mean` finds the average of nonmissing numeric values.', '`mean` berekent het gemiddelde van aanwezige numerieke waarden.'),
        'median': ('`median` dolu değerler sıralandığında ortadaki değeri bulur.', '`median` finds the middle of the ordered nonmissing values.', '`median` vindt het midden van de gesorteerde aanwezige waarden.'),
        'count': ('`count` boş olmayan değerleri sayar; toplam satır sayısı ile aynı olmak zorunda değildir.', '`count` counts nonmissing values, which may differ from the row count.', '`count` telt aanwezige waarden; dat kan afwijken van het aantal rijen.'),
        'nunique': ('`nunique` boş olmayan farklı değerlerin sayısını bulur.', '`nunique` counts distinct nonmissing values.', '`nunique` telt verschillende aanwezige waarden.'),
    }
    concept = concepts[operation][{'tr': 0, 'en': 1, 'nl': 2}[language]]
    if step.get('help_requests', 0) >= 2:
        examples = {
            'missing_count': ('Temsili örnek: boş, 8, boş hücreleri için iki boş hücre sayarız. Bu örnek senin verinden alınmadı.',
                              'Illustrative example, not your data: missing, 8, missing gives two missing cells.',
                              'Fictief voorbeeld, niet jouw data: ontbrekend, 8, ontbrekend geeft twee ontbrekende cellen.'),
            'distribution': ('Temsili örnek: A, A, B grubunda A iki kez, B bir kez görünür. Burada da aynı mantığı seçtiğimiz gruba uygulayacağız.',
                             'Illustrative example: in A, A, B, A occurs twice and B once. Apply this idea within the selected group.',
                             'Fictief voorbeeld: bij A, A, B komt A twee keer voor en B één keer. Pas dit idee toe binnen de geselecteerde groep.'),
        }.get(operation)
        if examples:
            concept += ' ' + examples[{'tr': 0, 'en': 1, 'nl': 2}[language]]
        elif operation in {'min', 'max', 'mean', 'median', 'count', 'nunique'}:
            sample = {'min': '2', 'max': '8', 'mean': '4', 'median': '2', 'count': '3', 'nunique': '2'}[operation]
            concept += {'tr': f' Temsili 2, 2, 8, boş örneğinde bu işlemin sonucu {sample} olur; bu senin verinin sonucu değildir.',
                        'en': f' For the illustrative values 2, 2, 8, missing, this operation gives {sample}; this is not your data.',
                        'nl': f' Bij de fictieve waarden 2, 2, 8, ontbrekend geeft deze bewerking {sample}; dit is niet jouw data.'}[language]
    if operation == 'distribution':
        included = contract['options'].get('dropna', True) is False
        concept += {'tr': ' `dropna=False` ise boş değerler de sayılır.' if included else ' Bu görevde boş değerler dağılım sayımına dahil değildir.',
                    'en': ' Missing values are included.' if included else ' Missing values are excluded.',
                    'nl': ' Ontbrekende waarden tellen mee.' if included else ' Ontbrekende waarden tellen niet mee.'}[language]
        if contract['options'].get('normalize'):
            concept += {'tr': ' Bu görevde normalize=True kullanıldığı için sonuç oran olarak gösterilir.',
                        'en': ' With normalize=True, this task displays proportions.',
                        'nl': ' Met normalize=True toont deze opdracht verhoudingen.'}[language]
    instruction = step.get('instruction') or f'{group}; {columns}'
    lines = {
        'tr': [f"Şu anki adımımız: {instruction}", task_purpose(contract, state, language),
               f'Nasıl yapacağız: {concept}', 'Bu adım için yeni bir çalıştırma çıktısı bekliyorum.'],
        'en': [f'Our current step: {instruction}', task_purpose(contract, state, language),
               f'How: {concept}', 'I am waiting for a new execution result for this step.'],
        'nl': [f'Onze huidige stap: {instruction}', task_purpose(contract, state, language),
               f'Hoe: {concept}', 'Ik wacht op een nieuw uitvoerresultaat voor deze stap.'],
    }[language]
    if step.get('scope_changed'):
        lines.insert(1, {'tr': 'Veri kapsamı değişti; önceki çıktı güncel değil. Bu adımı güncel kapsamda doğrulayacağız.',
                         'en': 'The data scope changed; verify this step in the current scope.',
                         'nl': 'Het gegevensbereik is gewijzigd; controleer deze stap in het huidige bereik.'}[language])
    current = state.get('current_evidence_ids') or []
    latest = next((x for x in state.get('observations', []) if current and x['id'] == current[0]), None)
    if latest and (not latest.get('success') or not latest.get('analysis_contract', {}).get('supported')):
        lines.insert(0, {'tr': 'Son çalıştırma bu adımı doğrulamıyor: hata verdi veya ifade bu inceleme yolunda desteklenmiyor. Görevi tamamlandı saymıyorum.',
                         'en': 'The last execution failed or uses an unsupported expression; this step is not complete.',
                         'nl': 'De laatste uitvoering gaf een fout of gebruikt een niet-ondersteunde expressie; deze stap is niet voltooid.'}[language])
    if explicit_code_requested(message) and step['status'] != 'needs_revalidation':
        lines.append('```python\n' + step['code'] + '\n```')
    return '\n\n'.join(lines)


def detailed_evidence_requested(message):
    text = normalized(message)
    return any(marker in text for marker in ('kanit ayrintilari', 'ayrintili kanit', 'show all evidence', 'detailed evidence', 'bewijsdetails'))


def render_concise_turn(turn, state, message):
    language = state.get('response_language', 'tr')
    current = state.get('current_evidence_ids') or []
    latest = next((x for x in state.get('observations', []) if current and x['id'] == current[0]), None)
    if not latest:
        return turn.answer
    contract = latest['analysis_contract']
    if contract['operation'].startswith('preview_'):
        selection = predicate_label(contract['row_predicate'], language)
        lead = {'tr': f'Örnek çıktıyı görüyorum. Seçilen grup: {selection}. Bu örnekler grubun tamamını temsil ettiğini kanıtlamaz.',
                'en': f'I can see the example output. Selected group: {selection}. Examples do not establish that the whole group is represented.',
                'nl': f'Ik zie de voorbeelduitvoer. Geselecteerde groep: {selection}. Voorbeelden bewijzen niet dat de hele groep vertegenwoordigd is.'}[language]
        summary = preview_summary(latest, language)
        if summary:
            lead += ' ' + summary
    else:
        lead = turn.answer
    lines = [{'tr': 'Araştırma hedefi: ', 'en': 'Research focus: ', 'nl': 'Onderzoeksdoel: '}[language]
             + str(state.get('focus_column') or ''), lead]
    for claim in turn.claims:
        if claim.kind == 'hypothesis':
            lines.append({'tr': 'Olası açıklama (doğrulanmadı): ', 'en': 'Possible explanation (unverified): ',
                          'nl': 'Mogelijke verklaring (niet bevestigd): '}[language] + claim.text)
    rows = latest.get('input_rows')
    if rows is not None:
        lines.append({'tr': f'Kapsam: çalıştırmada yüklenen {rows:,} satır. Tam kaynak doğrulanmış sayılmaz.',
                      'en': f'Scope: {rows:,} input rows loaded at execution, not full-source verification.',
                      'nl': f'Bereik: {rows:,} invoerrijen geladen bij uitvoering, geen validatie van de volledige bron.'}[language])
    if not latest.get('version_verified'):
        lines.append({'tr': ('Bu eski çıktının veri sürümü kaydedilmemiş; güncel veriyle eşleşmesi doğrulanmadı.'
                             if not latest.get('input_data_version') else 'Bu çıktının güncel veri sürümüyle eşleşmesi doğrulanmadı.'),
                      'en': 'This older output has no verified match to the current data version.',
                      'nl': 'Deze oude uitvoer is niet bevestigd voor de huidige dataversie.'}[language])
    if turn.next_action:
        action = turn.next_action
        lines.append({'tr': 'Sonraki tek adım: ', 'en': 'One next step: ', 'nl': 'Eén volgende stap: '}[language] + action.instruction)
        lines.append({'tr': 'Neden: ', 'en': 'Why: ', 'nl': 'Waarom: '}[language] + action.why)
        if action.code and explicit_code_requested(message):
            lines.append('```python\n' + action.code + '\n```')
    return '\n\n'.join(lines)
