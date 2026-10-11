# DataPilot AI — Geliştirme ve Öğrenme Yol Haritası

**Başlangıç:** 11 Ekim 2026  
**Durum:** Yaşayan plan / uygulanmadan önce güncel kod ve çalışma ortamı doğrulanacak  
**Ana hedef:** Gerçek veri projelerinde güvenilir, veri setinden bağımsız, öğretici ve düşük AI maliyetli bir DataPilot AI; Flight üzerinden kullanıcının kendi SQL/Pandas yetkinliğini geliştirmesi.

## Üç sabit ilke

1. **İki hat, tek iş akışı:** Ürün geliştirme ve Flight'ta SQL/Pandas öğrenme aynı gerçek görevler üzerinden yürür. Ek, kapsamlı mimari çalışma programı yok.
2. **Doğruluk → Öğreticilik → Maliyet:** Deterministik/yerel çözümler tercih edilir; gerektiğinde LLM kontrollü kullanılır. Düşük token tüketimi yanlış cevap pahasına hedeflenmez.
3. **Önce kanıt, sonra kod:** Sorun yeniden üretilir, beklenen davranış tanımlanır, test oluşturulur, onay alınır, sonra uygulama değiştirilir. Repo üzerinde izinsiz commit/push/değişiklik yapılmaz.

## Başlangıçta doğrulayacağımız durum

- Melbourne Housing: son teknik rapora göre 13.580 satır, 21 sütun; kayıtlı data preparation, validation, logical model, KPI, analysis, dashboard; 8/9 teslimat, açık review/documentation/handoff.
- Flight: önceki oturum bilgisine göre 5.819.079 satır, 31 sütun; 5.000/10.000/20.000 örneklem seçenekleri; geliştirme için 10.000 satır, Notebook'ta 5.000 satır örneklemi kullanılmış olabilir. **Bu değerler çalışma ekranında yeniden teyit edilecek.**
- Son teknik denetim: 42 **seçilmiş** test başarılı; bu, tüm test paketinin sonucu değildir. Notebook/Practice/Mentor'un tüm canlı senaryoları son denetimde doğrulanmadı.
- Mevcut backend DuckDB/Parquet yolları içeriyor; bunların Flight tam veri akışında uçtan uca etkin çalıştığı varsayılmayacak.

## Çalışma sırası ve tamamlanma koşulları

| Sıra | Aşama | Yapacağımız | Bittiğini nasıl anlarız? |
|---|---|---|---|
| 0 | **Temel durum / envanter** | Yerel branch–GitHub farkı, frontend build, tüm testler, kritik modül ekranları, hatalar ve mevcut teknik maliyet sınırları okunur/doğrulanır. | Tek kanıtlı hata listesi ve güvenilir test başlangıç sonucu elde edildi. |
| 1 | **Flight + veri kapsamı** | Raw/full data, sample (5k/10k/20k), null/duplicate, filtre, SQL/Pandas karşılaştırmaları ve full-data verification kontrol edilir. | Örneklem sonuçları tam veri diye sunulmaz; aynı veri kapsamındaki Pandas/SQL sonuçları eşleşir; tam-veri kontrolleri çalışır. |
| 2 | **Mentor kalitesi ve backend kararları** | Gerçek kullanıcı senaryoları ile evidence, veri sürümü/scope, local dispatcher, cevap uzunluğu, yardım düzeyi, fallback, token/call davranışı test edilir; sadece kanıtlı eksikler düzeltilir. | Mentor kanıtsız sayı uydurmaz, raw/sample farkını bilir, kullanıcı adına ödevi çözmeye koşmaz, gereksiz çağrıları azaltır. |
| 3 | **Notebook ↔ Mentor ↔ Practice ↔ Progress ↔ Tasks bütünlüğü** | Çalıştırılan kod/çıktı, yardım, alıştırma sonucu, beceri durumu ve sonraki görev arasındaki akışlar doğrulanır; durum çelişkileri çözülür. | Başla → çalıştır → değerlendir → kaydet → yeniden aç → devam et akışı gerçek tarayıcıda tutarlı çalışır. |
| 4 | **Melbourne'u tamamla** | Açık review, handoff, dokümantasyon; dashboard/filter ve modelin mevcut kayıtlı hâlini doğrulama. | Tamamlanma durumu görevlerle aynı; gerçek vaka çalışması ekranları ve notları hazır. |
| 5 | **Dataset-agnostic + büyük veri dayanıklılığı** | Melbourne, Flight ve farklı şemalı ek bir test verisiyle akışları karşılaştır; Flight full processing, DuckDB/Parquet, stream, memory/time benchmark ve hata geri dönüşleri değerlendir. | Özel kolon ismi/hard-code gerekmeden çalışma; büyük veride kabul edilen ve ölçülmüş performans/kararlılık. |
| 6 | **Beta hazırlığı ve doküman** | Kullanıcı deneyimi, veri kaybı, geri yükleme, kullanıcı kimliği/veri izolasyonu ihtiyacı, loglama/backup/güvenlik ve sürüm yayın planı. Profesyonel portfolyoda AI destekli geliştirmenin gerçek rolü belirtilir. | Beta kapsamı, blocker listesi, sınırlamalar ve doğrulanmış demo/portfolyo hazır. |

## Mentor için hedef davranış ve test matrisi

**Karar akışı (hedef tasarım):** Kullanıcı niyeti → Aktif proje/aşama → Veri kapsamı (raw/working/sample) → Son doğrulanmış işlem/çıktı → Yerel kural veya araç → Öğretici yanıt; yalnızca gerektiğinde izinli LLM çağrısı.

Önce gerçek kodda bu akışın hangi parçalarının zaten bulunduğu doğrulanır; diyagram mevcut uygulamanın tüm yanıtları için kesin bir yürütme sırası olarak kabul edilmez.

| Örnek test | Beklenen davranış |
|---|---|
| Flight: `CANCELLED = 0` ve `CANCELLATION_REASON IS NOT NULL` | Satır sayımı aynı kapsam için doğru; örneklem ile tam kaynak birbirine karışmaz. |
| Melbourne: Car null sayımı | Kaynakta 62 ile önceki örneklemdeki 23'ü karıştırmaz; bağlamı açıklar. |
| Kullanıcı sadece küçük bir ipucu ister | Adım adım, çözümü hemen vermeyen NUDGE/GUIDE yanıtı. |
| Kullanıcı SQL hatası yapar | Somut hatayı açıklar; kullanıcı isterse düzeltmesi için yönlendirir. |
| Sonuç boş, kesilmiş veya veri sürümü uyumsuz | Güvenli biçimde belirsizliği söyler; iş kuralını uydurmaz. |
| LLM kotası dolu / provider yanıt vermiyor | Yerel olası yanıt varsa onu kullanır; yoksa anlamlı hata verir; ücretliye izinsiz geçmez. |
| Melbourne dışı Flight soruları | Melbourne sütun adları veya ezberlenmiş cevapları kullanmaz. |

**Ölçeceğimiz değerler:** senaryo başarı oranı (testlerle tanımlanacak), veri kapsamı hatası, tekrar/yanlış yardım, LLM çağrı sayısı ve token miktarı, yanıt süresi, yanıtın öğrenmeyi desteklemesi. Başlangıç ölçümü olmadan başarı yüzdesi iddia edilmeyecek.

## Flight: kullanıcının öğrenme yolu

- **En son çalışılan SQL kavramları:** `SELECT` hangi alan/sonucu döndürür; `WHERE` hangi satırları filtreler; `COUNT(*)` kaç eşleşme olduğunu sayar; `AND`, `IS NULL`, `IS NOT NULL`.
- **En son somut sorgu:** `SELECT COUNT(*) FROM df WHERE CANCELLED = 0 AND CANCELLATION_REASON IS NOT NULL;` — **beklenen** 0; gerçek sonuç ve kapsam çalıştırılarak teyit edilir.
- **Pandas eşleniği (örnek):** `((df['CANCELLED'] == 0) & (df['CANCELLATION_REASON'].notna())).sum()`; iki sorgu aynı DataFrame üzerinde çalışırsa karşılaştırılabilir.
- **Sonraki küçük adımlar:** filtre → eksiklik sayımı → `GROUP BY` / Pandas `groupby` → basit join → tarih alanları; yalnızca veri işine ihtiyaç çıktıkça.
- Her oturum: kullanıcı önce kısa bir sorgu dener → sonuç görülür → aynı soru diğer araçta karşılaştırılır → tam veri gerekiyorsa backend ile doğrulanır. AI kullanıcının yerine hemen kod yazmaz.

## Büyük veri ilkeleri

- `raw` kaynak değiştirilmez; `working` dönüşüm sonucu, `sample` öğrenme/önizleme bağlamıdır.
- 5k/10k/20k örneklerin temsiliyetini veri dağılımlarıyla test et; küçük gruptaki nadir durumların örnekte kaybolabileceğini kontrol et.
- Büyük veri için stream/SQL/DuckDB/Parquet yolları işlev ve kaynak kullanımı açısından ölçülerek değerlendirilir; herkese açık büyük veri performansı iddiası ancak benchmark sonrası yapılır.
- Pipeline full-data preflight ve tam veri doğrulaması yapılmadan tek başına sample sonucuyla veri kararı genellenmez.
- Dataset-agnostic ilke: özellikler yalnızca `CANCELLED` veya Melbourne `Car/Price` kolonlarına özel kodla uygulanmaz; kullanıcı tarafından seçilen alan, tip ve genel kurallarla çalışır.

## Her geliştirmede değişmeyecek iş akışımız

1. **Sorun:** Kullanıcı ekranı/çıktıyı gösterir, beklediği davranışı bir cümlede söyler.
2. **İnceleme:** Asistan ilgili kodu, mevcut testleri ve veri kapsamını inceler; nedeni ve riskleri sade açıklar.
3. **Onay:** Yapılacak teknik değişiklik ve test kabul koşulu kullanıcıya sunulur.
4. **Uygulama:** Yetkili AI coding aracı yalnızca onaylanan dosyaları düzenler.
5. **Doğrulama:** Hedefli test + tam regresyon + frontend build (mümkünse) + gerçek UI senaryosu.
6. **Kayıt:** Yapılan iş, test sonucu, açık sorun ve sonraki tek adım kısa notla güncellenir.

**Oturum temposu:** Bir oturumda tek ana ürün sorunu ve gerekliyse tek küçük SQL/Pandas öğrenme adımı. Mimari bilgisi yalnızca sorunla doğrudan ilgiliyse basit bir görselle açıklanır; ayrıca öğrenme yükü oluşturulmaz.

## İlk oturum (kaldığımız yer)

1. Flight çalışma alanında **hangi dataset kapsamında** olduğumuzu (raw/working/10k/5k notebook) görüntüle ve not et.
2. Kullanıcı şu sorguyu önce kendi yazsın: `SELECT COUNT(*) FROM df WHERE CANCELLED = 0 AND CANCELLATION_REASON IS NOT NULL;`
3. Eşdeğer Pandas sorgusunu deneyip aynı kapsamda karşılaştır.
4. Sonucu gördükten sonra **tam Flight verisinde** aynı iş kuralını doğrulama yolunu incele; zorunlu olmadıkça uygulama kodunu değiştirme.
5. Mentor'un bu soruya nasıl tepki verdiğini gözlemle; gereksiz bir LLM çağrısı gerekiyorsa önce beklenen faydayı ve limit durumunu değerlendir.

## Açık sorun kayıtları — Flight/Notebook (11 Ekim 2026)

**Çalışma kararı:** Sorunları bu listede biriktiriyoruz; Flight üzerinden SQL/Pandas öğrenme akışını gereksiz yere kesmiyoruz. Veri doğruluğunu, veri kaybını veya analizin güvenilirliğini etkileyen sorunlar ileride modelleme/dashboard'a sonuç taşımadan önce önceliklendirilip kullanıcı onayıyla giderilecek. Her kod düzeltmesinden sonra backend testleri, frontend build ve gerçek Notebook senaryosu doğrulanacak.

| ID | Öncelik | Durum | Bulgu / kanıt | Beklenen düzeltme ve kabul kriteri |
|---|---|---|---|---|
| FL-001 | **Yüksek — analiz kapsamı ve sonuç güvenilirliği** | Açık / ertelendi | Flight kaynağı **5.819.079** satır. Development/Smart Sampling'de **10.000** satır seçilmiş; Workbench sağ üstte 10.000 gösteriliyor. Notebook üstünde `5000 sampled rows from 10000 total rows`, `SELECT COUNT(*) FROM df` sonucu **5.000**. Kodda Notebook endpoint'i `notebook_limit = min(..., 5000)` ile sınırlandırılıyor; Working Data için `df.sample(..., random_state=42)` kullanılıyor. | Raw/Development/Notebook/aktif sorgu kapsamı açık ve fark edilebilir gösterilsin; sonuçlarda ve Mentor cevaplarında kapsam/örneklem bilgisi bulunsun. Örneklem sonucu tam veri sonucu olarak sunulmasın. Güvenli boyut seçimi ve uygun backend tam-veri doğrulama akışı tasarlanıp performans açısından test edilsin. |
| FL-002 | Orta — SQL öğrenme ve UX | Açık / ertelendi | Geçerli SQL `-- yorum\nSELECT ...` ile başladığında, Notebook SQL çalıştırıcısı doğrudan `SELECT` veya `WITH` başlangıcı aradığı için `Only read-only SELECT and WITH queries are supported.` hatası veriyor. | SQL yorumları ve boş satırlar doğru yorumlanıp read-only güvenliği korunarak kabul edilsin; regresyon testleri eklensin. |
| FL-003 | Orta — Run Cell ve hata görünümü | Açık / ertelendi | Tek hücre çalıştırma akışı `runNotebookCells` içinde `codes.slice(0, targetIndex + 1)` aracılığıyla önceki hücreleri de çalıştırıyor. Önceki hatalı SQL hücresi alttaki hedef hücreyi engelliyor; neden anlaşılmıyor. | Run Cell'in gerçek kapsamını göster; engelleyen önceki hücreyi vurgula. Bağımsız sorgular için izole çalıştırma olasılığını Python durum bağımlılıklarını bozmadan değerlendir. |
| NB-004 | Orta — Git entegrasyon durumu | Yerelde kullanıcı testi geçti / merge commit bekliyor | Notebook bölüm ve hücre yönetimi için frontend build, **546 backend testi** ve kullanıcının **6 UI senaryosu** başarılı. Yerelde `integration/notebook-sections` dalında başlatılan birleştirme henüz commit edilmedi. `backend/benchmarks/results/` korunmalı. | Merge durumu güvenle doğrulanıp ayrı entegrasyon dalında tamamlanmalı; `main` içine alma ayrıca kararlaştırılmalı. |
| MT-005 | **Yüksek — Mentor sohbet sürekliliği ve token limiti** | Açık / ertelendi | Mentor, iptal edilmiş ve iptal nedeni dolu 68 kaydı veren Pandas sorgusunu açıklayıp `head(10)` ile satır inceleme önerdi. Kullanıcı sorguyu çalıştırıp **10 rows × 31 columns** sonucunu gördü. “Yaptım, sonucu gördün mü?” sorusuna Mentor `Mentor context exceeded the AI provider token limit. Try a shorter question or retry after context refresh.` hatası verdi; güncel Notebook çıktısını gerçekten görüp göremediği doğrulanamadı. | Mentor'un Notebook koduna **ve gerçekten oluşan output'a** erişimini doğrula. Göremediğini görmüş gibi söylemesin. Gereksiz büyük context/token kullanımını azalt, uygun hata/fallback oluştur, 5.000 satırlık sample kapsamını bilsin, pedagojik kısa ipuçlarıyla ilerlesin; testlerle doğrula. |
| UI-006 | Orta — iki sidebar açıkken scroll/üst alan çakışması | Açık / ertelendi | Sol ana sidebar **açık** ve sağ Mentor Chat paneli **açık** iken Notebook/Workbench sayfası aşağı/yukarı kaydırıldığında sayfa içeriğinin bir kısmı üst başlık/aşama navigasyonu alanında görünüyor. Sol sidebar kapatılınca aynı problem görünmüyor. Kullanıcı 11 Ekim 2026 oturumunda ekran görüntüleri sağladı. | Her iki sidebar açık/kapalı ve farklı viewport/zoom kombinasyonlarında yeniden üret; sticky header, z-index, overflow/clip, stacking context ve container genişliği sorunlarını incele. İçerik üst navigasyon alanına sızmasın, Notebook/Mentor bağımsız kullanılabilsin; UI regresyon senaryosuyla doğrula. |

**Flight analizi — kaldığımız yer:** `01_Data_Cleaning` Notebook, Development/working üzerinden gelen **5.000 satırlık Notebook örnekleminde** çalışıyor. Aynı kapsamda `CANCELLED=1 AND CANCELLATION_REASON IS NOT NULL` → **68**; `CANCELLED=1 AND CANCELLATION_REASON IS NULL` → **0**; `CANCELLED=0 AND CANCELLATION_REASON IS NOT NULL` → **0**. Bunlar **10.000 satırlık Development** veya **5.819.079 satırlık kaynak** üzerinde henüz doğrulanmadı. Pandas kullanarak aynı 5.000 satırlık Notebook kapsamındaki **68** sonucu doğrulandı: `((df["CANCELLATION_REASON"].notna()) & (df["CANCELLED"] == 1)).sum()`. Sonra `df[(df["CANCELLED"] == 1) & (df["CANCELLATION_REASON"].notna())].head(10)` çalıştırıldı; çıktı **10 rows × 31 columns**. Sıradaki küçük alıştırma: `df.loc[koşul, "CANCELLATION_REASON"]` ile tek sütun seçimi ve `.value_counts()` ile iptal nedenlerinin sayımını öğrenme; Mentor'un gerçekten güncel çıktıyı görüp görmediğini test etme.

## Dokümantasyon politikası

- Mevcut portfolyo/Technical Deep Dive bir **development snapshot**; geliştirmeyi bekletmez.
- Gerçek kullanıcı katkısı: fikir, gereksinimler, mantıksal sorun tespiti, test ve AI yönlendirmesi. Büyük ölçekli kod üretimi ve teknik mimari tasarımında AI katkısı açıkça belirtilir.
- Ana portfolyo ve görseller yalnızca doğrulanmış gelişmelerde güncellenir. Türkçe ana metin, İngilizce uygulama görüntüleri korunur.
- İleride backend kararlı hâle geldiğinde, örnek işlemlerle **Visual Architecture Handbook** hazırlanır; bu, şimdi ayrı öğrenme görevine dönüşmez.

## Güncelleme kayıt şablonu

`Tarih | Repo/branch/commit | Modül | Sorun | Kanıt/veri kapsamı | Yapılan değişiklik | Test/build/UI sonucu | Açık risk | Sonraki tek adım`

**Not:** Bu belge yol haritasıdır; kod taraması, canlı test ve performans ölçümlerinin yerini almaz.