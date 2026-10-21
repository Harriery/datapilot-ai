# Mentor: güncel durum ve kabul ölçütleri

Güncelleme: 21 Ekim 2026. Çalışma dalı: `mentor/reliability-review`.
Flight projesi beklemede. Ana hedef, acemi kullanıcının uygulamadaki mentorla
veriyi tanımadan proje çıktılarının tamamlanmasına kadar ilerleyebilmesidir.
Bu hedef henüz kanıtlanmadı. Test sayısı veya yapısal kabul, bu hedefin yerine geçmez.

## Neyi doğruladık, neyi doğrulamadık?

| Alan | Mevcut kanıt | Açık kabul ölçütü |
| --- | --- | --- |
| Notebook kapsamı | Kullanıcı 10.000 satırın uygulamada göründüğünü doğruladı. Yürütmenin kendi kapsamı kaydediliyor. | Örneklem, mevcut df ve tam kaynak ayrımını uzun araştırmada korumak. |
| Sayımı açıklama | 21 Ekim canlı `report(6)` denemesinde 5.000 eksik `temperature` sayımı tek denemede doğru gösterildi. Kaynak tur test fixture'ında saklı. | Diğer desteklenen işlemleri ve gerçek kullanıcı sorularını doğrulamak. |
| Yardımcı kontrolün satır grubu | AST sözleşmesi ve gerçek `report(5)` regresyonları, seçilen grubu ölçülen sütundan ayırıyor. Sıfır için boş grup olasılığı belirtiliyor. | Birbirine bağlı canlı incelemelerde aynı disiplini korumak. |
| Kaynak açıklaması isteme | `report(6)` model önerisi veri sözlüğünü sordu. | Kullanıcı açıklamayı bilmiyorsa araştırmayı sürdürebilmek. Yeni takip testi bunu ölçer; canlı sonucu henüz yok. |
| Araştırmayı ilerletme | Sabit model yanıtlarıyla üç bağlı yerel kontrolün çıktıları sonraki adıma taşındı. | Canlı mentorun önerileriyle aynı ilerlemeyi göstermek. |
| Temizleme/dönüşüm kararı | Yeni inceleme yolu otomatik dönüşüm önerisini kabul etmez. | Kanıta ve kullanıcı hedefine dayalı karar, uygulama ve sonuç doğrulaması. |
| SQL, veri modeli, KPI, dashboard, insights, docs | Önceki ürün yolları mevcut. Bu çalışma bunları kapsamlı biçimde yeniden doğrulamadı. | Aşamalar arası mentor rehberliğini ve kullanıcıya faydayı sınamak. |
| Baştan sona proje | Henüz bir acemi kullanıcının yeni mentorla tamamlaması gösterilmedi. | Dışarıdan yoğun destek gerektirmeden bütün proje aşamalarını tamamlamak. |

## Aktif kod yolu

Yeni notebook araştırma yolu `AI_NOTEBOOK_RESEARCH_ENABLED` bayrağına bağlıdır;
varsayılanı kapalıdır. Kodun dalda bulunması, normal UI sohbetinin bu yolu kullandığı
anlamına gelmez. Kabul komutları yeni servisi doğrudan çağırır ve bu bayrağı açmaz.
Diğer ürün aşamaları kendi mevcut mentor yollarında çalışmaya devam eder.
Normal kullanıcı akışını açmak ayrı bir kabul kararıdır.

Yeni model şeması `GroundedResearchPlan`: `next_action` ve `evidence_ids`.
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

Ardından tek yeni model denemesi:

```powershell
python -m backend.benchmarks.run_mentor_clarification_followup --live --from-latest
```

Varsayılan kaynak arama yeri `backend/benchmarks/results/research-acceptance`;
`--source-report <yol>` ile belirli rapor seçilebilir. Uyumlu kaynak yoksa test
yeni bir başlangıç turunu sessizce üretmez. Canlı komut mevcut `.env`/sağlayıcı
ayarlarını kullanır; gerçek sağlayıcı kotası tüketir.

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

Kaynak kodu, testler ve bu durum belgesi açıklamalı commit'lerle aynı geliştirme
dalında tutulur. Kullanıcı güncellemeyi Git üzerinden alır. Test sonuçları, aktarım
ZIP'leri ve eski yama dosyaları kaynak commit'lerine eklenmez. Her çalışma birimi
bir kullanıcı davranışı ve onun kabul ölçütüyle değerlendirilir.
