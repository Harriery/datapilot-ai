# Mentor araştırma akışı: geliştirme ve kabul durumu

18 Ekim 2026. Flight incelemesi durduruldu. Yeni bir gerçek veri projesine
geçmeden önce aşağıdaki kabul değerlendirmeleri tamamlanmalıdır.

## Neden değişti?

Son notebook hücresini görmek, araştırmanın amacını korumak anlamına gelmiyordu.
Mentor AIR_SYSTEM_DELAY araştırmasından yardımcı iptal nedeni kontrolüne kaydı;
beş örnekten geniş bir eksiklik yorumuna geçti. Önceki testler bağlam taşımayı
kanıtlıyor, gerçek yanıtın öğretici ve mantıklı olduğunu kanıtlamıyordu.

## Uygulanan değişiklikler

- Seçili notebook için serbest metin üretimi ve ayrı beceri sınıflandırıcısı yerine
  tek yapılandırılmış araştırma önerisi üretilir. Diğer ürün aşamalarının mevcut
  mentor yolları bu değişiklikle yeniden doğrulanmış sayılmaz.
- Workspace/notebook başına ayrı SQLite araştırma belleği: hedef sütun, gözlem
  kimlikleri, önceki öneriler ve açık soru. Yardımcı kontrol hedefi değiştirmez;
  açık kullanıcı konu değişimi yeni hedef başlatabilir.
- Ham gözlemler, hipotezler ve sınırlamalar farklı alanlardır. Notebook kanıtından
  tam kaynak iddiası, olmayan kanıt kimliği, farklı hedefe öneri ve aynı başarılı
  hesaplamanın tekrarı denetlenir. Kullanıcıya görünür yanıtta hedef ve kanıt
  kapsamı ayrıca gösterilir.
- Önerilen inceleme kodu çalıştırılmaz. Kolonları ve izin verilen inceleme işlemleri
  AST üzerinden kontrol edilir. Kuralı geçmeyen öneri için en fazla bir uygulama
  düzeltme turu vardır; hâlâ reddediliyorsa öneri kullanıcıya görev olarak verilmez.
- Kod/tür/sıralama/silme/ekleme/dataset değişikliği sonrasındaki bağımlı hücrelerin
  eski yürütmeleri frontend ve backend tarafında geçersizleşir. Bölüm etiketi
  değişikliği yürütmeleri silmez. Kaydedilmiş Quality Checks korunur.
- Girdi tazelik kaydı dosya boyutu/mtime, veri türü, processed kimliği ve örneklem
  seçimine bağlıdır. Bu kayıt dosya içeriğinin kriptografik kanıtı değildir.
- Kalıcı araştırma belleği her turda tamamen AI'a gönderilmez. İstek JSON'u
  karakter bütçesiyle sınırlandırılır; geçmiş kayıtlar ve mevcut kanıt ayrılır.

## Yayın kapısı

Yeni araştırma yolu `AI_NOTEBOOK_RESEARCH_ENABLED` bayrağıyla korunur ve
varsayılan olarak kapalıdır. Canlı teknik/öğretici kabul değerlendirmesi yapılmadan
normal kullanıcı akışına açılmaz. Kabul komutu bayrağa ihtiyaç duymadan doğrudan
yeni üretim planner/validator servisini sınar. Sonradan arayüz değerlendirmesi için
`.env` içinde `AI_NOTEBOOK_RESEARCH_ENABLED=true` ayarlanıp backend yeniden
başlatılabilir. Bu seçenek mentorun tüm aşamalarının hazır olduğu anlamına gelmez.

## Kabul testini çalıştırma

Proje kökünden, uygulamanın mevcut sanal ortamıyla:

```powershell
python -m pytest -q
python -m backend.benchmarks.run_mentor_research_acceptance
python -m backend.benchmarks.run_mentor_research_acceptance --live
```

Offline komut dış AI çağrısı yapmaz. Live komut mevcut yerel `.env` ayarlarını
kullanır; anahtar rapora yazılmaz. Varsayılan üç sentetik şemada dörder tur vardır:
boş sayımı, dağılım, yardımcı kontrol, kendi önceki cevabını denetleme. Her turda
normal üretim planner/validator yolu çağrılır. Ücretsiz sağlayıcının TPM sınırı
nedeniyle turlar arasında 65 saniye beklenir. Her üretim turunda gerekirse bir
öneri düzeltmesi daha yapılabilir. Sağlayıcı hatasında test durur; rapora başarısız
olarak kaydeder. Windows terminalinde Ctrl+C ile durdurulabilir.

Sonuçlar `backend/benchmarks/results/research-acceptance/<zaman>/report.json`
altındadır. Raporun içindeki gerçek yanıtlar teknik doğruluk ve öğreticilik
bakımından ayrıca incelenmelidir. "Structurally accepted" bunu kanıtlamaz.
Testler ayrı SQLite dosyası kullanır; Flight projesi, kullanıcı ilerlemesi ve
uygulamanın normal veritabanı değiştirilmez.

## Bu çalışma neyi henüz kanıtlamıyor?

Bu sürüm araştırma denetiminin geliştirme adımıdır; mentorun tamamen düzeldiği
veya yeni bir kullanıcının projeyi baştan sona bitirebildiği iddiası değildir.

- Canlı model cevaplarının semantik doğruluğu ve öğretici kalitesi bu ortamda
  ölçülemedi: Groq kimlik bilgisi yok. Model çıktıları taklit edilerek geçirilen
  testler canlı doğrulama diye sunulmamalıdır.
- AST imzası semantik olarak eşdeğer bütün kodları tanımaz. Bir iddiada geçerli
  kanıt kimliği bulunması, yorumun gerçekten o kanıttan çıktığını ispatlamaz.
- Kalıcı hedef ve yapısal denetim, doğal dildeki bütün yanlış anlamaları yakalamaz.
- Şu an yeni notebook inceleme yolunda dönüşüm önerileri otomatik kabul edilmez;
  gerekçeli karar ve dönüşüm için ayrı kabul akışı tamamlanmalıdır. Python
  inceleme önerileri denetlenir; SQL için eşdeğer öneri denetimi henüz yoktur.
- Sentetik senaryolar bir acemi kullanıcı simülasyonu veya uçtan uca tarayıcı testi
  değildir. Büyük veri performansını veya bilinmeyen gerçek bir dataset'i sınamaz.
- Diğer aşamalar: veri modeli, KPI, dashboard, dokümantasyon ve aşamalar arası
  geçişler için çok turlu canlı kabul testleri ve başlangıç kullanıcısı denemesi
  yapılmadan ürünün ana öğrenme amacı kanıtlanmış sayılmaz.

## Devam kapısı

1. Canlı raporlardaki hedef, kapsam ve teknik yorum hataları giderilmeli.
2. Rehberli karar/dönüşüm ve SQL akışları aynı denetim çerçevesine alınmalı.
3. Model/KPI/analiz/dashboard/docs geçişleri çok turlu kabul senaryolarıyla sınanmalı.
4. Daha önce kullanılmamış gerçek bir dataset'te uygulama içi mentorla tamamlama
   denemesi yapılmalı; dışarıdan yapılan müdahaleler ayrıca kaydedilmeli.
5. Bu kanıtlar oluşana kadar Flight durur; "ürün hazır" veya "mentorla bağımsız
   proje tamamlama doğrulandı" denmez.

## Canlı protokol raporu sonrası düzeltme

İlk gerçek raporda iki öneri zorunlu iç kolon/kod alanları nedeniyle reddedildi;
üçüncü turda BadRequestError oluştu. Raporda modelin asıl önerileri ve HTTP hata
detayı yoktu. Bu yüzden hataların öğretici kalite sorunu mu yoksa protokol
uyumsuzluğu mu olduğu kesinleştirilemedi; başarı iddiası yapılmadı.

Yeni sürüm kullanıcıya kod göstermeme isteğini backend-only code alanından açıkça
ayırır; alan açıklamaları ve düzeltme girdisi aynı sözleşmeyi kullanır. Her model
önerisi, reddedilme nedenleri ve seçili sağlayıcı hata alanları yerel rapora alınır.
Reddedilen ilk turdan sonra senaryo durur. Önce kısa kontrol:

```powershell
python -m backend.benchmarks.run_mentor_research_acceptance --live --case sensors --max-turns 1
```

Bu komut yalnız bir konuşma turudur (gerekirse bir düzeltme çağrısı daha).
`full_scenario_exercised=false` beklenir; tek tur geçmesi bütün senaryonun veya
mentor kalitesinin geçtiği anlamına gelmez. Tam suite ancak bu protokol kontrolü
başarılı olduktan sonra çalıştırılmalıdır.

## Kayıtlı kod alıntısı için gerçek yanıt regresyonu

İkinci tam deneme ilk turda durdu: model kayıtlı sayım ifadesini açıklamasında
alıntıladığı için yeni çözüm kodu vermiş gibi reddediliyordu. İlk yanıt ayrıca
Türkçe isteğe İngilizceydi. Bu iki gerçek öneri, notebook kanıtıyla birlikte
`backend/tests/fixtures/research_recorded_code_review.json` içine alındı.

Yeni gösterim normalleştirmesi yalnız daha önce gözlenmiş tek ifadeli Python
kodunun tam alıntısını açıklama içinde "kayıtlı hücre" olarak sadeleştirir.
Yeni kod, uzatılmış ifadeler ve önerilen işlem kodu bu işlemle değiştirilmez.
Ham model önerisi ve sadeleştirilmiş gösterim kopyası ayrı ayrı raporlanır.

Yanıt dili isteğe eklenir; belirgin TR/EN/NL uyuşmazlığı yerel denetimde yakalanır.
Bu denetim tam bir dil sınıflandırıcısı değildir. Sistemin kendi hedef/kapsam/ret
metinleri de aynı dilde gösterilir. İlk İngilizce canlı öneri dil nedeniyle
reddedilirken ikinci Türkçe öneri, kayıtlı kod alıntısı sadeleştirildiğinde diğer
kanıt/tekrar/hedef kontrollerini geçmektedir. Bu gerçek yanıt tekrarı çevrimdışı
regresyondur; yeni bir canlı model denemesi veya bütün senaryonun başarısı değildir.

## Uzun yanıt ve kaldığı yerden devam etme düzeltmesi

Üçüncü gerçek raporda iki tur geçti. Üçüncü turdaki 1727 karakterlik geçerli
JSON açıklaması, sağlayıcının şemadaki 1100 karakterlik sınıra takılmasıyla HTTP
400'e dönüştü. Metin uzunluğu artık wire şemasını geçersiz yapmaz: kısalık yerel
denetimde değerlendirilir ve gerekirse tek düzeltme turuyla istenir. İçerik
kesilerek başarılı sayılmaz; hedef, kanıt, tekrar ve dil kontrolleri korunur.

Sağlayıcının `json_validate_failed` hatasında tam bir `failed_generation` JSON'u
varsa yalnız o JSON yerel şemayla okunur ve aynı kontrollerden geçirilir. Başka
sağlayıcı hataları veya eksik JSON için başarı varsayılmaz. HTTP hata mesajı da
rapordaki özgün kullanıcı sorusunun üzerine yazılmaz.

Aynı klasördeki önceki canlı test ve izole veritabanıyla devam etmek için:

```powershell
python -m backend.benchmarks.run_mentor_research_acceptance --live --resume-latest
```

Önceki başarılı turlar, sentetik kanıtın değişmediği ve öneriler güncel yerel
kontrolleri geçtiği takdirde AI çağrısı yapılmadan kullanılır. Bu raporun ilk iki
turu gerçek yanıt regresyonunda tekrar doğrulandı. Test üçüncü turdan sürer;
sensors tamamlanırsa kalan retail/service senaryolarına geçer. Eski başarısız
rapor zaman damgalı bir kopyada korunur. Uygun kayıt yoksa sessizce baştan başlamaz.
65 saniyelik koruyucu aralık düzeltme çağrıları dahil gerçek model isteklerine
uygulanır; önbellekten alınan turlar sağlayıcı kotası tüketmez.


## Çıktı bütçesi ve kesilmiş planların reddi

Dördüncü canlı rapor, iki başarılı turu tekrar kullanarak üçüncü turda durdu.
Her iki denemede sağlayıcı `max_completion_tokens` nedeniyle kesilme bildirdi;
geçerli JSON'a benzeyen hata çıktısında zorunlu `next_action` yoktu. Eksik alanı
`null` varsaymak doğru değildir. Bu gerçek iki çıktı regresyon fixture'ına alındı.

Varsayılan genel çıktı bütçesi 1500 tokendir. Groq Responses API'de bu bütçe
hem görünür çıktıyı hem düşünme tokenlarını kapsar. Yalnız Groq GPT-OSS 20B/120B
notebook araştırma yolu `reasoning={"effort":"low"}` gönderir. Başka modele
bu parametre gönderilmez; mevcut kullanıcı token sınırı artırılmaz veya aşılmaz.
Modelden tek kısa açıklama, tekrarsız en çok iki iddia ve bir eylem istenir;
şemada karar alanı önce gelir. Bu sıralama tek başına tamamlanma garantisi değildir.

Sağlayıcı kesilme bildirdiyse şema tamamlanmış görünse bile o çıktı kabul edilmez.
HTTP 200 ile `status=incomplete` veya incomplete_details gelen yanıt da reddedilir.
En fazla bir kısa düzeltme çağrısı yapılır; aynı günlük/aylık kullanım koruması ve
çağrı aralığı uygulanır. İkinci yanıt da kesilirse işlem atanmaz; kullanıcıya
kesilme açıkça bildirilir. Raporda yapılandırılmış token sınırı, kullanılan düşünme
ayarı ve varsa gerçek sayısal token kullanımı saklanır; düşünme metni kaydedilmez.

Resmi parametre kaynağı: https://console.groq.com/docs/responses-api ve
https://console.groq.com/docs/api-reference (Responses max_output_tokens).
Bu düzeltmenin yerel regresyonu gerçek üçüncü tur hata çıktısını tekrarlar;
yeni canlı modelin bu bütçeyle tamamlanması veya öğretici doğruluğu henüz doğrulanmış
sayılmaz. Aynı `--live --resume-latest` komutu başarılı iki turu yeniden kullanır.


## Satır grubu ve ölçüm sözleşmesi (grounded-v1)

Beşinci canlı raporda 12 tur biçim denetiminden geçmesine rağmen retail ve service
cevaplarında yardımcı filtrenin grubu ana sütunun eksik satırlarıyla karıştırıldı.
Bu hata yalnız yeni bir prompt veya belirli sütun adlarına yönelik regex ile
çözülmedi. Notebook araştırma yolunda factual prose üretimi modelden çıkarıldı.

Yeni `GroundedResearchPlan` wire şeması yalnız `next_action` ve `evidence_ids`
alır. Serbest `answer`/`claims` içeren eski model nesnesi yeni yanıtta kabul edilmez.
Backend kodu çalıştırmadan AST üzerinden şu sözleşmeyi çıkarır:

- Doğrudan mevcut notebook `df` kaynağı ve birebir satır koşulu; AND/OR/NOT korunur.
- Ölçülen sütunlar, işlem ve kaydedilmiş çıktı. Eksik sayımı için yalnız açık tamsayı
  veya tek sütunlu tamsayı Series çıktısı kabul edilir.
- Çalıştırma başarısı, yürütmenin kendi kapsamı ve güncelliği.

Desteklenen alan sınırlıdır: literal df seçimleri ve `.loc`, karşılaştırma/isna/notna
filtreleri, eksik sayımı, tek/çok sütunlu value_counts, head/tail ve basit özetler.
Alias, query, groupby ve keyfi Python işlemleri henüz bu açıklama yolunda desteklenmez.
Bunlar yanlışlıkla bütün df olarak yorumlanmaz; son hücre desteklenmiyorsa AI çağrısı
harcanmadan bu sınır açıkça belirtilir ve yeni işlem atanmaz. Bu sınır notebook'un
kod çalıştırmasını değiştirmez. Yeni yolun özellik bayrağı hâlâ varsayılan kapalıdır.

Modelin seçtiği güncel kanıtlar backend tarafından açıklanır. En son çalıştırma
zorunludur. Sayı 0 ise grubun boş olabilmesi ve kategori geçerliliğinin ölçülmemiş
olması belirtilir. Yüklenen satır sayısı df'nin son uzunluğu için payda yapılmaz;
yüzde uydurulmaz. Dağılımın görünen çıktısı kısaltılmış gösterilir; neden, eşitlik
veya bütün kaynak hakkında modelden türetilen iddialar gösterilmez. Tam kaynak
ayrımı korunur. Model action instruction/why metni de doğrudan yayınlanmaz; inspect
önerisinin satır seçimi ve ölçümü desteklenen koddan açıklanır. Hangi kontrolün
öğretici açıdan en yararlı olduğu hâlâ model değerlendirmesi ve ayrı test gerektirir.

Eski başarılı test cevapları kaldığı yerden devam ederken aynen gösterilmez. Kanıt
ve işlem önerisi güncel sözleşmeye uyuyorsa açıklama AI çağrısı yapılmadan yeniden
kurulur. Önceki ham öneri `original_cached_proposal`, yeni derleme seçimi
`cached_recompile_plan` olarak ayrı korunur. Bunlar yeni model çıktısı diye
etiketlenmez. Eski raporun arşivlenmesi de korunur.

Gerçek report(5) fixture'ı üç senaryo/12 turu yeniden derler. Ek karşı-örnekte
flag=1 grubunun reason eksik sayısı 0 iken target eksik grubunda 1'dir; yanlış
grup aktarımı aynı sonuç sanılamaz. Üç bağlı sentetik kontrol testi önerilen sabit
ifadeyi gerçekten çalıştırıp sonraki adıma çıktısını taşır. Bu son test sabit model
cevaplarıyla yereldir; canlı veya özerk acemi kullanıcı/proje tamamlama kanıtı değildir.

Yerel kontroller:

```powershell
python -m pytest backend/tests/test_mentor_observation_contract.py -q
python -m backend.benchmarks.run_mentor_research_acceptance
```

Bunlar API kotası harcamaz. Yeni wire protokolünün gerçek sağlayıcıyla kabulü,
yönlendirme kalitesi, SQL ve bütün proje aşamalarının tamamlanması henüz açık
kriterlerdir. Bu çalışma notebook araştırmasının gözlem açıklaması çekirdeğini
güçlendirir; bütün Mentor'un hazır olduğu anlamına gelmez.
