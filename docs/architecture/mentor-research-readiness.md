# Mentor: güncel durum ve kabul ölçütleri

Güncelleme: 23 Ekim 2026. Kullanıcı kararıyla çalışma dalı artık `main`.
Flight projesi beklemede. Ana hedef, acemi kullanıcının uygulamadaki mentorla
veriyi tanımadan proje çıktılarının tamamlanmasına kadar ilerleyebilmesidir.
Bu hedef henüz kanıtlanmadı. Test sayısı veya yapısal kabul, bu hedefin yerine geçmez.

## Neyi doğruladık, neyi doğrulamadık?

| Alan | Mevcut kanıt | Açık kabul ölçütü |
| --- | --- | --- |
| Notebook kapsamı | Kullanıcı 10.000 satırın uygulamada göründüğünü doğruladı. Yürütmenin kendi kapsamı kaydediliyor. | Örneklem, mevcut df ve tam kaynak ayrımını uzun araştırmada korumak. |
| Sayımı açıklama | 21 Ekim canlı `report(6)` denemesinde 5.000 eksik `temperature` sayımı tek denemede doğru gösterildi. Kaynak tur test fixture'ında saklı. | Diğer desteklenen işlemleri ve gerçek kullanıcı sorularını doğrulamak. |
| Yardımcı kontrolün satır grubu | AST sözleşmesi ve gerçek `report(5)` regresyonları, seçilen grubu ölçülen sütundan ayırıyor. Sıfır için boş grup olasılığı belirtiliyor. | Birbirine bağlı canlı incelemelerde aynı disiplini korumak. |
| Kaynak açıklaması isteme | `report(6)` veri sözlüğünü sordu. Canlı `report(7)`, kullanıcı sözlüğün olmadığını söylediğinde aynı sorunun tekrarlandığını ve ilerlemenin başarısız olduğunu gösterdi. | Aynı soruyu reddeden yeni bellek/denetim düzeltmesinden sonra canlı ilerlemeyi doğrulamak. |
| İnceleme kararını aktarma | Canlı `report(8)` eksik hedef satırlarının önizlemesini seçti; eski şemada iç evidence_ids eksik olduğu için reddedildi. Yeni küçük sözleşmeyle aynı kod yerelde değişmeden kabul ediliyor. | Gerçek modelin yeni sözleşmeyle tek denemede geçerli karar vermesini ve sonraki çıktıyı doğru yorumlamasını doğrulamak. |
| Son çıktıyı yanıta bağlama | 23 Ekim gerçek Flight kaydında iki karar da son hücre kimliği seçilmediği için reddedildi. Backend artık son gözlemi derlenmiş plana kendisi ekler. Gerçek ilk karar yerelde geçerken desteklenmeyen kanıt seçen ikinci karar reddedilmeye devam eder. | Aynı kullanıcının canlı sohbetinde gereksiz ret olmadan devamı doğrulamak. |
| Cevaplanan soruyu kapatma | Canlı `report(9)` yeni şemaya uydu ama yine clarify seçti; tekrar denetimi bunu reddetti. İncelemede sözlük kısıtı kaydedilirken eski sorunun açık ve önerinin proposed kaldığı görüldü. | Düzeltilen soru yaşam döngüsü ve bağlama göre daraltılan işlem şemasıyla canlı ilerlemeyi doğrulamak. |
| Güvenle seçilebilen küçük adım | `report(10)` kapanmış sorudan sonra null döndürdü; geçerli biçim ilerleme sağlamadı. Yeni yerel kural, güncel pozitif eksik sayımından ilk eksik örnekleri önermeyi gerçek üretim takip komutunda AI çağrısı olmadan geçti. | Kullanıcının bu adımı uygulamasını ve sonraki çıktıyla araştırmanın doğru sürmesini doğrulamak. Bu sonuç canlı modelin ilerlediğini kanıtlamaz. |
| Birbirine bağlı çıktı takibi | Üç sentetik şemada üretim mentorunun gerçek önerisi sınırlı yorumlayıcıyla uygulanıp sonraki hücreye kaydedildi: sayım → 5 eksik örnek → yardımcı dağılım → yalnız açıklama. Yerel zincir sağlayıcısız geçti. | Gerçek acemi UI kullanımı, belirsiz yardımcı seçimi ve daha uzun/diğer aşamalardaki rehberlik. |
| Bekleyen adımda yardım | Aynı üretim zincirine "nasıl yapacağımı bilmiyorum", daha basit açıklama, kodu gösterme ve açık kod isteği eklendi; üç şemada yerel destek geçti. `/chat` bağlama kaynağı sabitlenmiş entegrasyon kontrolü de geçti. | Gerçek kullanıcının ipucunu anlayıp uygulayabilmesi; hata ayıklama, diğer işlemler ve UI kullanılabilirliği. |
| Araştırmayı ilerletme | Sabit model yanıtlarıyla üç bağlı yerel kontrolün çıktıları sonraki adıma taşındı. | Canlı mentorun önerileriyle aynı ilerlemeyi göstermek. |
| Temizleme/dönüşüm kararı | Yeni inceleme yolu otomatik dönüşüm önerisini kabul etmez. | Kanıta ve kullanıcı hedefine dayalı karar, uygulama ve sonuç doğrulaması. |
| SQL, veri modeli, KPI, dashboard, insights, docs | Önceki ürün yolları mevcut. Bu çalışma bunları kapsamlı biçimde yeniden doğrulamadı. | Aşamalar arası mentor rehberliğini ve kullanıcıya faydayı sınamak. |
| Baştan sona proje | Henüz bir acemi kullanıcının yeni mentorla tamamlaması gösterilmedi. | Dışarıdan yoğun destek gerektirmeden bütün proje aşamalarını tamamlamak. |

## Aktif kod yolu

Yeni notebook araştırma yolu `AI_NOTEBOOK_RESEARCH_ENABLED` bayrağına bağlıdır;
varsayılanı kapalıdır. Kodun `main`de bulunması, normal UI sohbetinin bu yolu kullandığı
anlamına gelmez. Kabul komutları yeni servisi doğrudan çağırır ve bu bayrağı açmaz.
Diğer ürün aşamaları kendi mevcut mentor yollarında çalışmaya devam eder.
Normal kullanıcı akışını açmak ayrı bir kabul kararıdır.

Sağlayıcı model şeması artık `GroundedResearchDecision`: `next_action` ve
`evidence_ids`. İşlem yalnızca `{kind, code}` içerir veya `null` olur; kanıt
kimlikleri yalnızca üst düzeyde bulunur. Hedef, kullanılan sütunlar ve gösterim
metinleri backend tarafından türetilir. `GroundedResearchPlan`, genişletilmiş iç
plan ve eski kayıtları okumak için korunur; sağlayıcıya şema olarak gönderilmez.
Modelin serbest gözlem açıklaması kullanıcıya gösterilmez. Backend şu bilgileri
kaydedilmiş Python kodundan ve çıktısından çıkarıp gösterir:

- Mevcut notebook df'si üzerinde birebir satır seçimi; AND/OR/NOT korunur.
- Ölçülen sütun, işlem ve kayıtlı sonuç.
- Yürütme başarısı, yükleme kapsamı ve veri/örneklem sürümünün güncelliği.

Model sonraki işlemi seçer. Backend hedef, bilinen sütunlar, izin verilen inceleme
kodu ve tekrar kontrollerini uygular; instruction/why metni desteklenen işlemden
oluşturulur. Hangi işlemin öğretici açıdan en yararlı olduğunu bu kontroller tek
başına kanıtlamaz.

## Destek ve sınırlar

- Desteklenen açıklamalar: literal df seçimleri ve `.loc`; karşılaştırma,
  isna/notna filtreleri; eksik sayımı, value_counts, head/tail ve basit özetler.
- Alias, query, groupby ve keyfi Python ifadeleri bu yeni açıklama yolunda henüz
  desteklenmez. Son hücre eşleştirilemiyorsa AI çağrısı harcanmadan sınır belirtilir.
  Bu, notebook'un normal kod çalıştırma kabiliyetini değiştirmez.
- Girdi satır sayısı, önceki dönüşümlerden sonraki df uzunluğunun paydası sayılmaz.
  Önizleme genel kural değildir; count=0 grubun dolu veya kategorilerin geçerli
  olduğunu kanıtlamaz. Örneklem sonucu tam kaynak sonucu diye sunulmaz.
- Araştırma belleği workspace/notebook bazında ayrı SQLite tablosundadır. Yardımcı
  sütun ana hedefi kendiliğinden değiştirmez. İstek bağlamı boyutla sınırlandırılır.
- Bağımlı hücrelerin eski yürütmeleri ilgili kod/veri değişikliklerinde
  geçersizleşir. Tazelik kaydı boyut/mtime ve örneklem seçimine dayanır; dosya
  içeriğinin kriptografik doğrulaması değildir.
- AST imzası eşdeğer bütün hesaplamaları tanımaz. Bu yapı tam semantik veya
  pedagojik doğruluk garantisi değildir.

## Mevcut test araçları

Yerel testler AI kotası harcamaz:

```powershell
python -m pytest backend/tests -q
python -m backend.benchmarks.run_mentor_research_acceptance
```

İlk canlı protokol kontrolü, bir konuşma turu ve bir uygulama denemesi:

```powershell
python -m backend.benchmarks.run_mentor_research_acceptance --live --case sensors --max-turns 1 --model-attempts 1
```

`--max-turns` konuşma turunu, `--model-attempts` o turdaki üretim/düzeltme denemelerini
sınırlar. SDK'nın mevcut HTTP/bağlantı tekrar politikası ayrıdır. İlk ret ikinci
bekleme/istekten önce kaydedilir. Normal iki denemelik mod beklemeyi ve ret nedenini
CLI'da gösterir. Ctrl+C tamamlanmış denemeleri korur; rapor kesildi olarak kaydedilir,
başarı sayılmaz. Raporlar UTF-8 okunur ve yazılır.

Eski dört turluk replay, hazırlanmış notebook görüntülerini kullanır. Modelin
önerdiği kodu gerçekten uygulayan bir acemi simülasyonu değildir. Eski başarılı
replay'i sürdürmek için `--live --resume-latest` vardır; eski açıklamalar güncel
kanıt sözleşmesiyle yeniden kurulur. İlk denemenin canlı başarısı, dört turun veya
bütün mentorun geçtiği anlamına gelmez.

## Yeni takip testi: "Bilmiyorum, veri sözlüğüm yok"

Bu test, gerçek kabul raporundaki başarılı ilk `clarify` turunu yeniden doğrular.
Kanıt, başlangıç sorusu, grounded-v1 kabulü ve ham model önerisi eşleşmelidir.
İlk tur yeniden üretilmez. Dosyadaki serbest reply metni güvenilir sayılmaz;
önceki yanıt kayıtlı kod/çıktıdan yeniden kurularak konuşma geçmişine eklenir.
Önceki `clarify` önerisi yeni, ayrı test veritabanındaki araştırma belleğine taşınır.

Yeni kullanıcı mesajı:

> Bilmiyorum, veri sözlüğüm de yok. Mevcut veriye bakarak araştırmaya devam
> edebilir miyiz? Kod vermeden tek bir küçük adımla yönlendir.

Önce kaynak raporu kotasız doğrulama:

```powershell
python -m backend.benchmarks.run_mentor_clarification_followup --from-latest
```

Ardından üretim mentoruyla takip: uygun yerel adım varsa AI çağrısı yapılmaz;
yoksa en fazla tek yeni model denemesi kullanılır:

```powershell
python -m backend.benchmarks.run_mentor_clarification_followup --live --from-latest
```

Varsayılan kaynak arama yeri `backend/benchmarks/results/research-acceptance`;
`--source-report <yol>` ile belirli rapor seçilebilir. Uyumlu kaynak yoksa test
yeni bir başlangıç turunu sessizce üretmez. Canlı komut mevcut `.env`/sağlayıcı
ayarlarını kullanır; yalnızca sağlayıcıya başvurulursa gerçek kotayı tüketir.

Raporda yapısal kabul ve bu senaryonun ilerleme ölçütü ayrıdır. Ölçüt şunları ister:

1. Güncel kanıt ve işlem denetiminden geçen yanıt.
2. Ana hedefi koruyan bir `inspect` önerisi.
3. Eksik hedef satırlarına odaklanan, daha önce tamamlanmamış bir kontrol.

Aynı açıklamayı yeniden istemek, görev vermemek veya mevcut sayımı tekrarlamak bu
ilerleme ölçütünü geçmez. OR koşulunun bir dalının başka satırları dahil etmesi,
"yalnız eksik hedef satırları" diye kabul edilmez. Bu, bu senaryoya ait dar bir
kabul ölçütüdür; diğer bütün araştırma adımlarının uygunluğuna ilişkin genel hüküm
değildir. Test modelin önerdiği kodu çalıştırmaz; önerinin öğretici niteliği insan
incelemesi gerektirir. Proje tamamlama kanıtı üretilmez.

Yeni rapor `backend/benchmarks/results/clarification-followup/<zaman>/report.json`
altındadır. Test kendi SQLite dosyasını kullanır ve çağrı bitince test sürecinin
önceki veritabanı ayarını geri yükler. Flight veya kullanıcının gerçek çalışma
verileri bu testte açılmaz.

## Git üzerinden çalışma

Kaynak kodu, testler ve bu durum belgesi açıklamalı commit'lerle `main`de tutulur.
Yeni çalışma dalı açılmaz. `main`de bulunmak ürünün hazır olduğu anlamına gelmez;
deneysel notebook yolu, kabulü tamamlanana kadar mevcut bayrağıyla kapalı kalır.
Kullanıcı güncellemeyi Git üzerinden alır. Test sonuçları, aktarım
ZIP'leri ve eski yama dosyaları kaynak commit'lerine eklenmez. Her çalışma birimi
bir kullanıcı davranışı ve onun kabul ölçütüyle değerlendirilir.

Eski dalların ayrı commit'leri otomatik olarak ürüne birleştirilmez. Temizlik aracı
önce bütün commit uçlarını GitHub `archive/<zaman>/...` etiketlerine taşır ve proje
klasörünün dışında doğrulanmış bir `.bundle` yedeği oluşturur. Ardından `main`
dışındaki remote dalları atomik ve SHA kontrollü siler; değişmiş bir dal silinmez.
Yerel dallar da arşivlenir. Kaydedilmemiş kaynak değişikliği, yarım merge/rebase
ve ek worktree varsa işlem durur. Takipsiz rapor/ZIP/veri dosyaları silinmez;
Git bundle bu takipsiz dosyaların yedeği değildir. Arşivdeki bağımsız özellikler
gerektiğinde incelenip ayrı commit olarak `main`e alınabilir.

```powershell
python scripts/consolidate_git_branches.py
python scripts/consolidate_git_branches.py --apply
```

İlk komut yalnızca inceler; ikinci komut kullanıcının GitHub yazma yetkisiyle
arşivler ve temizler. Önce güncel `main` alınmalıdır.

## report(7) sonrasındaki konuşma düzeltmesi

Eski kabul denetimi aynı `clarify` sorusunu geçirebiliyordu. Yeni düzen, kullanıcı
tanımı/sözlüğü sağlayamadığını açıkça söylediğinde bunu aktif hedefe ait bir kısıt
olarak saklar, sonraki istekte modele iletir ve aynı sözlük sorusunu reddeder.
Hedef değiştiğinde kısıt taşınmaz; kullanıcı sözlüğü sonradan bulduğunu söylerse
yeniden kaynak görüşmesi yapılabilir. Belirsiz veya ilgisiz olumsuz ifadelerden
otomatik iş kuralı çıkarılmaz. TR/EN/NL açık yanıtları için sınırlı yerel tanıma
vardır; bu bir genel doğal dil anlama garantisi değildir.

Mevcut `clarify` gösterimi yalnızca veri sözlüğü sorusu üretebilir; bu nedenle bu
kısıt altında `clarify` kabul edilmez. Öneri, mevcut normal en fazla iki denemelik
akışta düzeltilebilir; model yine uygun inceleme seçmezse rehberlik başarısız
olarak gösterilir. Sessizce hazır bir inceleme eklenmez ve veri çalıştırılmaz.
Yerel test, gerçek hatanın tekrarını reddetmeyi ve kontrollü ikinci önerinin yeni
incelemeye dönüşmesini doğrular. Gerçek modelin sonraki canlı yanıtı henüz
ölçülmedi; projenin tamamlanması hâlâ kanıtlanmış değildir.

## report(8) sonrasındaki karar sözleşmesi

Gerçek `failed_generation` belgesi regresyon fixture'ında aynen saklanır.
JSON çözüldüğünde kod Python açısından geçerlidir; görünümdeki kaçışlar bir
sözdizimi hatası değildir. Eski şema işlem içinde aynı kanıtları ve koddan
türetilebilen sütunları tekrar istiyordu. Yeni wire bunları istemez. Kodda açık
projeksiyon bulunmayan önizleme bütün sütunları gösterir; filtrede geçen sütunlar
ayrıca AST'den çıkarılır. Model bu iki kümeyi ayrı metinlerde yeniden üretmez.

Eski hatalı sağlayıcı belgesi yeni üretim biçimi olarak sessizce çevrilmez veya
onarılmaz. Yeni biçimde aynı kodun kullanılabildiği, farklı şema/dillerde geçiş,
geçersiz/tekrarlanan kodun reddi, yeni biçimdeki ilk turun yeniden kullanılması,
HTTP sohbet yönlendirmesi ve birbirine bağlı kayıtlı sonuçlar yerelde test edilir.
Tam ve yeni şemaya uygun bir sağlayıcı hata belgesi kurtarıldığında da bütün
kanıt/kod/odak denetimleri uygulanır; eksik veya kesilmiş belgeden karar üretilmez.
Modelin sonraki canlı yanıtı ve gerçek acemi kullanıcının adımı uygulayabilmesi
ayrı kabul ölçütleridir. Yeni desteklenmeyen bir model yanıtı otomatik olarak
başarılı sayılmaz; aynı en fazla iki denemelik normal düzeltme sınırı korunur.

## report(9): cevaplanmış soru ve işlem seçenekleri

"Sözlüğüm yok/bilmiyorum" cevabı sonrasında sözlük sorusu artık
`answered_unavailable` durumuna geçer ve açık sorular kuyruğundan çıkar.
Kullanıcının tanımı sonradan bulması `available` durumunu açar; hedef sütun
değiştiğinde eski hedefin kısıtı yeni hedefe taşınmaz. Önceki sürümden kalmış
unavailable/proposed çelişkisi de durum hazırlanırken yerelde düzeltilir.
Tarihçe silinmez; ilgisiz açık sorular korunur.

Tanım sağlanamıyorsa sağlayıcıya gönderilen şema `GroundedInspectionDecision`
olur: işlem türü yalnızca inspect olabilir. Mevcut clarify gösterimi yalnızca
sözlük sorusunu üretebildiği için bu seçim o bağlamda seçenek değildir. Null,
yeni görev istenmediğinde veya haklı bir inceleme bulunamadığında geçerlidir;
sırf test geçsin diye bir işlem zorlanmaz. Yeni incelemenin kod/kanıt/odak/tekrar
denetimleri korunur. Bu, yeni kanıtı olmayan null yanıtın ilerleme testini geçtiği
anlamına gelmez. Rehberlik hâlâ gerçek canlı yanıtla doğrulanmalıdır.

Yerel regresyon gerçek report(9) kararının bu bağlamın şemasından geçemediğini,
cevaplanmış sorunun model isteğinde açık soru olarak kalmadığını, yeni kaynağın
ve hedef değişikliğinin seçenekleri yeniden açtığını kontrol eder. Takip raporu
artık `research_context` altında kısıtı, açık soruları ve öneri durumlarını;
`validation.runtime.decision_schema` altında kullanılan şemayı kaydeder.

## report(10): null yerine gerekçeli yerel inceleme

Canlı modelin null yanıtı geçerli biçimdedir fakat araştırmayı ilerletmemiştir;
bu eski sonuç regresyon fixture'ında başarısız olarak korunur. Üretim mentorunda
artık `mentor_local_progress_service` küçük, kanıta dayalı bir adımı modelden önce
seçebilir. Bu bir model hatasını sessizce düzeltme veya başarılı model cevabı
uydurma değildir; önerinin kaynağı ayrı kaydedilir.

İlk desteklenen geçiş: kullanıcı yönlendirme isterken hedef tanımı sağlanamıyorsa,
güncel ve sürümü bilinen df'deki filtresiz hedef eksik sayımı pozitifse, eksik
hedef satırlarının ilk beşini bütün sütunlarıyla incelemek. Daha önce aynı
kapsamda eksik örnek önizlemesi kaydedilmişse veya bekleyen bir inceleme varsa bu
adım yeniden önerilmez. Sıfır sayım, yardımcı sütun sayımı, filtreli grup,
bilinmeyen/eski kapsam ve yalnız açıklama talebi yerel adım için uygun sayılmaz.
Diğer durumlar mevcut planlayıcı yolunda kalır; genel bir görev doldurucusu yoktur.

Üretilen yerel karar da aynı derleyici ve kanıt/odak/tekrar/kod denetiminden geçer.
Hiçbir kod çalıştırılmaz, veri doldurulmaz/silinmez ve bir neden tahmin edilmez.
`validation.origin=local_progress_policy`, `provider_calls=0`, boş
`model_attempts` ve ayrı `local_plan`/`local_proposal` gerçek kaynağı gösterir.
Takip testi yerel öneriyi de aynı ilerleme ölçütleriyle inceler ve konsolda AI
çağrısı yapılmadığını açıkça yazar. Bu sonucun anlamı hibrit mentorun bu küçük
adımı sunabilmesidir; canlı LLM kalitesi veya proje tamamlanması değildir.

Gerçek üretim takip komutu yerelde kaynak turuyla çalıştırıldı; beş ilerleme
ölçütü geçti, sağlayıcı çağrısı yapılmadı. Üç veri yapısı/üç dil, kapsam sınırları,
tekrar önleme ve özel karakterli sütunun doğru satır seçimi ayrıca test edildi.
Sağlayıcı hatası testleri, model yolunu bağımsız sınamak için yerel politikayı
bilerek devre dışı bırakır; yerel politikanın üretim testlerinde modelden başarılı
yanıt taklit edilmez. Gerçek veride sonraki hücre/çıktı ve aşamalar arası rehberlik
hâlâ ayrı kabul çalışmalarını gerektirir. Notebook araştırma bayrağı varsayılan
olarak kapalı kalır; diğer aşamaların mentor akışı bu kuralla değişmez.

## Bağlı önizleme ve dağılım kontrolü

Yerel devam kuralı kaydedilmiş örneklerin gerçekten hedefi eksik satırlar olduğunu
kontrol eder. En çok beş örnekte, en çok iki yardımcı sütunun görünen değerlerini
ayrı bir gözlem olarak sayar. "5 örnekte 2 true/3 false", eksik grubun tamamının
dağılımı olarak sunulmaz. Kodun eksik filtrelediğini söylemesine rağmen kayıtlı
örneklerde hedef doluysa yürütme/önizleme uyuşmazlığı sayılır ve AI çağrısı
yapılmadan yorum durur. Eksik/uygunsuz metadata'dan bir dağılım tahmin edilmez.

Bir sonraki yerel dağılım adımı için kullanıcı açıkça tek bir görünen yardımcı
sütun seçebilir. Seçmediyse yalnız örneklerde tam olarak tek boolean aday varsa
bu aday kullanılır. True/False'a iş anlamı atanmaz; sayısal 0/1 veya "True"
metni boolean kabul edilmez. Birden fazla aday olduğunda rastgele tercih yapılmaz.
Adım mevcut df içinde hedefi eksik grubun yardımcı değerlerini dropna=False ile
sayar; diğer hedef grubuyla ilişki veya nedensellik bu kontrolden çıkarılmaz.
Daha önce kaydedilmiş dağılım/pending inceleme tekrar önerilmez. Sadece sonuç
açıklaması isteyen mesajda yeni görev verilmez.

Desteklenen ifadenin anlamsal seçimi de karşılaştırılır: head() ve head(5),
df[mask] ve df.loc[mask] gibi desteklenen eşdeğerler yapılmış görevi observed
durumuna geçirir. Tamamlanan görevin eski yönergesi açık sorulardan çıkar.
Bu sınırlı parser bütün Python ifadelerinin eşdeğerliğini kanıtlamaz.

Yeni doğrulama komutu AI çağrısını açıkça kapatır:

```powershell
python -m backend.benchmarks.run_mentor_connected_followup
```

Komut her çalışmada ayrı test SQLite dosyası ve 10.000 satırlık sentetik veriler
kullanır. Sonraki çıktılar önceden yerleştirilmez: üretim mentorunun önerdiği kodun
desteklenen seçim sözleşmesi yalnızca beş eksik örnek/tek yardımcı dağılım için
yorumlanır. eval veya genel Python çalıştırması yoktur. Çıkan veri gerçekten
sonraki notebook hücresine kaydedilir ve tekrar üretim mentoruna verilir.
Öneri sözleşmenin dışına çıkarsa veya yerel adım bulunmazsa test durur; sağlayıcıya
sessizce geçmez. `allow_provider=False` yalnız bu çevrimdışı çağrı için kullanılır;
normal ürün çağrısının varsayılan sağlayıcı davranışı korunur.

Her şemada hedef, son çıktının kullanılması, yalnız eksik örnek seçimi, yardımcı
dağılımının bağımsız referansla eşleşmesi, açıklama isteğinde görev olmaması ve
ham çerçevenin değişmemesi kontrol edilir. Sonuçlar
`backend/benchmarks/results/connected-followup/<zaman>/report.json` altındadır.
Rapor local üretim zinciri olduğunu açıkça yazar; acemi kullanıcı, gerçek büyük
veri, canlı LLM, aşamalar arası pedagojik yarar veya proje bitirme kanıtı değildir.
Kodun gizli planını test yürütücüsünün uygulayabilmesi, acemi kullanıcının aynı
adımı arayüzde yardımsız uygulayabildiğini göstermemektedir.

## Aynı bekleyen işlem için öğretici destek

`mentor_tutoring_service`, yalnız doğrulanmış ve hâlâ proposed olan bir eksik-hedef
önizlemesi/tek yardımcı dağılımı için destek sunar. Hedef, güncel kanıt kimlikleri
ve sürüm eşleşmesi korunur; aynı kod normal derleyici/denetimden tekrar geçirilir.
Yardım yeni bir görev değildir: öneri listesi değişmez, görev observed/completed
olmaz ve kod çalıştırılmaz. Tamamlanan, eski, bilinmeyen veya mutasyon içeren
göreve destek bağlanmaz.

Birinci istek temel kavrama ait kısa ipucu, sonraki istek süzgeç/seçim veya sütun
sayımı açıklaması verir. Ayrıntı seviyesi görev imzasına bağlıdır ve yeni görevde
yeniden başlar. Tam kod yalnız mevcut mesajdaki açık istekle gösterilir; geçmişte
kod istenmiş olması sonraki turda otomatik izin sayılmaz. "Kodu gösterme" gibi
olumsuz istekler, "kodu göster" alt dizisine sahip diye kod isteği sayılmaz.
TR/EN/NL kontrollü ifadeleri için yerel intent kuralları vardır; genel doğal dil
anlama veya her belirsiz isteğin doğru çözülmesi garantisi yoktur.

Yardım yanıtı mevcut görevi ve ipucunu gösterir; her tur bütün sayım/çıktı
geçmişini yeniden dökmez. Destek `validation.origin=local_tutoring`, provider_calls=0,
boş model_attempts, support_level ve supported_proposal ile kaydedilir. Gösterim
planındaki next_action null kalır; destek verilen eski kod ayrı tutulur. Bu,
sayım sonrasında hiç yönlendirme vermeyen eski null problemiyle aynı olay değildir.

Bu zinciri burada sağlayıcı çağrısı olmadan çalıştırıp sonuçları incelemek için:

```powershell
python -m backend.benchmarks.run_mentor_connected_followup --beginner-support
```

Her şemada beş yazılı yardım isteği gerçek üretim servisine verilir. Kod
istenmeden gösterilmemesi, açık istekte aynı doğrulanmış kodun gösterilmesi,
bekleyen işin değişmemesi, destekten sonra gerçek çıktıyla devam ve görev
seviyesinin sıfırlanması denetlenir. Senaryo yardıma ihtiyaç duyan bir insan
değildir; senaryo sürücüsü kodu sınırlı yorumlayıcıyla uygular. İnsan anlama düzeyi,
öğrenme kazanımı ve gerçek UI kullanım kolaylığı bu testten çıkarılmaz.

HTTP entegrasyon testi gerçek `/chat` uç noktasından yardım isteğini geçirir;
notebook bağlamının kaynağı test görüntüsüyle sabitlenir. Böylece sohbet
gösterimi/kayıt ve kod-vermeme davranışı sınanır; tarayıcı veya bütün bağlam toplama
zinciri için uçtan uca doğrulama sayılmaz. Araştırma bayrağının varsayılanı kapalı
kalmıştır; Windows'taki normal sohbetin yeni yolu kullandığı varsayılmaz.

### Kaydedilmiş notebook ile sohbet bağlamı kontrolü

`test_mentor_saved_notebook_chat.py`, üç farklı alan çifti için geçici SQLite
çalışma alanı ve gerçek 10.000 satırlık CSV oluşturur. `/chat` uç noktası,
bağlam oluşturucu ve mentor servisi birlikte çalışır; notebook bağlamı ve mentor
yanıtı mock edilmez. Yalnız veri dizini geçici konuma yönlendirilir, AI ve eski
mentor yolu çağrılmadığı doğrulanır.

Kaydedilmiş sayımın 5.000 eksik ve 10.000 giriş satırı olarak alınması, yardımda
görevin korunması, kaydedilmiş eşdeğer önizleme ifadesinin önceki görevi observed
yapması ve yardımcı dağılımına geçiş kontrol edilir. En yeni çalıştırma hücre
sırasından değil zamanından bulunur. Seçim 5.000 satıra değiştirildiğinde eski
10.000 satırlık çıktı güncel kabul edilmez ve eski görev kodu gösterilmez.

Önizleme sonucu testte bilinen salt okunur pandas ifadesiyle hesaplanıp kaydedilir;
notebook çalıştırma uç noktası veya tarayıcı kullanılmaz. Bu kontrol, kaydedilmiş
kanıttan sohbete aktarımı doğrular; canlı model kalitesi, insan öğrenmesi veya
baştan sona proje tamamlama kanıtı değildir. Araştırma yolu testte açıkça
etkinleştirilir; ürünün varsayılan ayarı değiştirilmez.

### Mevcut uygulama reddinin nedenini inceleme

Ekrandaki genel "konu, tekrar veya kanıt denetiminden geçmedi" yanıtı tek başına
hangi kontrolün başarısız olduğunu göstermez. Bu yanıt, yanlış bir önerinin
gerçekten engellendiğini veya denetimin hatalı ret verdiğini ayırt ettirmez.
Kullanıcıya aynı soruyu tekrar sordurmak yerine mevcut `last_validation`
kaydı ve her model denemesindeki gerçek kod/kanıt referansları incelenmelidir.

```powershell
python -m backend.benchmarks.export_mentor_diagnostics --focus AIR_SYSTEM_DELAY
```

Komut SQLite veritabanını salt okunur açar. Model çağırmaz, hücre çalıştırmaz,
hafızayı veya çalışma alanını değiştirmez. Eşleşen her notebook için son kayıtlı
denetimi `backend/benchmarks/results/mentor-diagnostics/<zaman>/report.json`
dosyasına çıkarır. Birden fazla eşleşme varsa hepsini listeler; tablo satır sırasını
son etkinlik zamanı gibi yorumlamaz. Ham çıktı metni, örnek satırlar, sohbet
geçmişi ve sağlayıcı yanıt gövdeleri dışarı aktarılmaz. Kanıtın ifade sözleşmesi,
kodu, kapsam/sürüm bilgileri ve denetim hataları korunur.

Bu araç hatayı düzeltmez veya canlı öneriyi yeniden üretmez. Hata nedenini
bilgisayardaki mevcut kayıttan almak içindir. İlgili kaydı almadan bu ekranın
kesin hata nedeni açıklanmış sayılmaz ve sırf devam edebilmek için denetimler
gevşetilmez. Geçerli bir veritabanı veya eşleşen kayıt yoksa yeni boş hafıza
oluşturmak yerine açıkça durur.

### 23 Ekim Flight: son gözlemi backend bağlar

Alınan gerçek tanılama dosyasında her iki model denemesi de
`The latest executed observation must be addressed` hatasını verdi. Son hücre
iptal edilen uçuşların iptal nedeni eksikliğiyle ilgiliydi; kullanıcının aktif
hedefi AIR_SYSTEM_DELAY idi. Model eski hedef kontrollerini seçerken son hücrenin
kimliğini seçmedi. Bu kayıt gerçek hatayı açıklar; yanlış veri yorumu yaptığı
sonucunu tek başına göstermez.

`expand_research_decision`, seçili kimlikleri değiştirmeden son gözlemin kimliğini
genişletilmiş plana ekler. Son çıktı backend'in kendi AST sözleşmesinden açıklanır;
ilişkili eski hedef kontrolleri ayrı iddialar olarak kalır. Ham model kararı
değiştirilmez. `model_attempts.evidence_binding`, seçilen, derlenen ve eklenen
kimlikleri ayrı kaydeder; tanılama dışa aktarımı bunu korur.

Derleyicinin son gözlemi ele alma şartı korunur. Bilinmeyen/eski/başarısız veya
desteklenmeyen kanıt hâlâ reddedilir. Dört kanıtı sınıra sığdırmak için modelin
seçimi sessizce atılmaz. Gerçek ilk clarify kararı bu bağlama sonrası geçer;
ikinci inspect kararı desteklenmeyen boolean-mask toplamını kanıt seçtiği için
geçmez. Yeni kod bu ifadeyi destekleniyor gibi işaretlemez.

Dosyadaki eski yürütmelerde `input_data_version` bulunmuyordu. Bunların kayıtlı
10.000 giriş satırı bilgisi korunur, ancak veri sürümünün güncelliği doğrulanmış
sayılmaz; yanıtta bu ayrım belirtilir. Geçmiş satır sayısından yeni sürüm kimliği
üretilmez. Gerçek karar tekrar oynatımı ve kontrollü sağlayıcı cevabıyla üretim
yolu kontrolü canlı AI veya acemi kullanıcının projeyi bitirme kanıtı değildir.
Kullanıcının gerçek tanılama dosyası ve hücre içerikleri depoya eklenmez. Depodaki
regresyon aynı son-hücre/ilgili-eski-gözlem durumunu yapay alan adları, sonuçlar
ve ifadelerle oluşturur; gerçek kayıtla inceleme ayrı yerel kontroldür.
