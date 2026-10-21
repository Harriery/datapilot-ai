"""Compile model-selected evidence into a reply without model-authored facts."""
from copy import deepcopy

from backend.app.mentor_observation_contract import expression_contract, observation_text, predicate_label, field_label


def predicate_columns(where):
    if where['op'] in {'and','or'}:
        return set().union(*(predicate_columns(x) for x in where['args']))
    if where['op'] == 'not':
        return predicate_columns(where['arg'])
    return {where['column']} if 'column' in where else set()


def compile_reply(plan, state, message):
    # Imported lazily to keep the parser independent from the planner/runtime.
    from backend.app.mentor_research_service import ResearchTurn, ResearchClaim
    language = state.get('response_language','tr')
    current = state.get('current_evidence_ids',[])
    by_id = {x['id']:x for x in state['observations'] if x['id'] in current}
    errors = []
    refs = list(dict.fromkeys(plan.evidence_ids))
    if not refs or len(refs)>3 or any(ref not in by_id for ref in refs):
        return None, ['Select only current evidence IDs; at least the latest observation is required']
    if not current or current[0] not in refs:
        return None, ['The latest executed observation must be addressed']
    for ref in refs:
        item=by_id[ref]
        if not item.get('success') or item.get('stale_scope'):
            errors.append('Selected observation is failed or stale')
        if not (item.get('analysis_contract') or {}).get('supported'):
            errors.append('Selected expression/output has no supported observation contract')
    if errors:
        return None, list(dict.fromkeys(errors))
    # Latest first, at most two earlier observations: bounded, no recap loop.
    selected = [by_id[ref] for ref in current if ref in refs][:3]
    latest=selected[0]['analysis_contract']
    answer=observation_text(latest,language)
    if latest['operation']=='missing_count' and latest['result']==0:
        answer += {'tr':' Sıfır sonucu, seçilen grubun boş olmadığını veya değerlerin geçerli kategoriler olduğunu tek başına kanıtlamaz.',
                   'en':' Zero alone does not establish that the selected group is nonempty or that its values are valid categories.',
                   'nl':' Nul bewijst op zichzelf niet dat de geselecteerde groep niet leeg is of dat de waarden geldige categorieën zijn.'}[language]
    focus=state.get('focus_column')
    fields=predicate_columns(latest['row_predicate']) | set(latest.get('measured_columns') or [])
    if focus and focus not in fields:
        answer += {'tr':f' Bu yardımcı kontrol, {field_label(focus)} eksik olan satırları seçmiyor; o satırlar için aynı sonucu çıkarmayız.',
                   'en':f' This helper check does not select rows with missing {field_label(focus)}; it does not establish the same result for those rows.',
                   'nl':f' Deze hulpcontrole selecteert geen rijen met ontbrekende {field_label(focus)}; voor die rijen volgt niet dezelfde conclusie.'}[language]
    claims=[ResearchClaim(text=observation_text(item['analysis_contract'],language),kind='observation',
                          evidence_ids=[item['id']],coverage='shown_output') for item in selected[1:]]
    claims.append(ResearchClaim(text={
        'tr':'Bu çıktılar eksikliğin nedenini veya bir iş kuralını tek başına kanıtlamaz. Araştırma hedefi değişmedi.',
        'en':'These outputs alone establish neither the cause of missingness nor a business rule. The research focus is unchanged.',
        'nl':'Deze resultaten bewijzen op zichzelf geen oorzaak van ontbrekende waarden of bedrijfsregel. Het onderzoeksdoel is ongewijzigd.'}[language],kind='limitation',evidence_ids=refs,coverage='shown_output'))
    action=deepcopy(plan.next_action)
    if action:
        if action.kind=='inspect':
            contract=expression_contract(action.code or '')
            if contract.get('supported') is False:
                return None,['Inspection cannot be explained safely: use a supported direct df expression or clarify']
            group=predicate_label(contract['row_predicate'],language)
            columns=', '.join(field_label(x) for x in contract.get('measured_columns') or [])
            name={'missing_count':{'tr':'eksik değer sayısını bul','en':'count missing values','nl':'tel ontbrekende waarden'},
                  'distribution':{'tr':'değer dağılımını incele','en':'inspect the value distribution','nl':'bekijk de waardeverdeling'},
                  'preview_head':{'tr':f"ilk {contract['options'].get('limit',5)} satırı görüntüle",'en':f"show the first {contract['options'].get('limit',5)} rows",'nl':f"toon de eerste {contract['options'].get('limit',5)} rijen"},
                  'preview_tail':{'tr':f"son {contract['options'].get('limit',5)} satırı görüntüle",'en':f"show the last {contract['options'].get('limit',5)} rows",'nl':f"toon de laatste {contract['options'].get('limit',5)} rijen"}}.get(contract['operation'])
            if name is None:
                name={
                    'max':{'tr':'en yüksek değeri bul','en':'find the maximum','nl':'bepaal het maximum'},
                    'min':{'tr':'en düşük değeri bul','en':'find the minimum','nl':'bepaal het minimum'},
                    'mean':{'tr':'ortalamayı bul','en':'find the mean','nl':'bepaal het gemiddelde'},
                    'median':{'tr':'ortancayı bul','en':'find the median','nl':'bepaal de mediaan'},
                    'count':{'tr':'dolu değerleri say','en':'count nonmissing values','nl':'tel niet-ontbrekende waarden'},
                    'nunique':{'tr':'farklı dolu değerleri say','en':'count distinct nonmissing values','nl':'tel verschillende niet-ontbrekende waarden'},
                }[contract['operation']]
            action.instruction={'tr':f'Satır seçimi: {group}. {columns or "Tüm sütunlar"} için {name[language]}.',
                                'en':f'Row selection: {group}. For {columns or "all columns"}, {name[language]}.',
                                'nl':f'Rijselectie: {group}. Voor {columns or "alle kolommen"}: {name[language]}.'}[language]
            action.why={'tr':f'Bu kontrol {field_label(focus)} araştırmasına ek bir gözlem sağlar; tek başına neden-sonuç ilişkisini kanıtlamaz.',
                        'en':f'This adds an observation to the {field_label(focus)} investigation; it does not alone prove causation.',
                        'nl':f'Dit voegt een waarneming toe aan het onderzoek naar {field_label(focus)}; het bewijst op zichzelf geen oorzakelijk verband.'}[language]
        elif action.kind=='clarify':
            action.instruction={'tr':f'{field_label(focus)} sütununun veri sözlüğündeki tanımını ve hangi koşullarda boş kalmasının beklendiğini biliyor musun? Varsa kaynak açıklamasını paylaş.',
                                'en':f'Do you know the data-dictionary definition of {field_label(focus)} and when it is expected to be missing? Share the source definition if available.',
                                'nl':f'Ken je de definitie van {field_label(focus)} in het gegevenswoordenboek en wanneer de waarde mag ontbreken? Deel de bronbeschrijving als die beschikbaar is.'}[language]
            action.why={'tr':'Eksikliği yorumlamak için belgelenmiş anlamı gözlemden ayırıyoruz.',
                        'en':'We distinguish the documented meaning from the recorded observation.',
                        'nl':'We onderscheiden de gedocumenteerde betekenis van de waarneming.'}[language]
        else:
            return None,['Grounded notebook review currently supports inspect or clarify actions only']
    return ResearchTurn(answer=answer,claims=claims,next_action=action),[]
