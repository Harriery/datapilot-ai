# DataPilot Practice System

## Goal

Practice alanının amacı Workspace sırasında gözlemlenen teknik eksikleri, junior'ın seviyesine uygun ve Data Engineering bağlamında hazırlanmış challenge'larla geliştirmektir.

Practice gerçek işi bölmez.

```text
Workspace
↓
Learning Evidence
↓
Weak / Developing Skills
↓
Practice Recommendations
↓
Adaptive Challenges
↓
New Learning Evidence
```

---

## Challenge Types

DataPilot Practice yalnızca soru-cevap veya çoktan seçmeli egzersizlerden oluşmaz.

Farklı skill'ler için farklı çalışma biçimleri kullanılır.

### Code Challenge

Junior verilen probleme çözüm olacak kodu kendisi yazar.

Örnek:

```text
Bir records listesindeki eksik city değerlerini bul
ve eksik kayıt sayısını hesapla.
```

Amaç sıfırdan küçük bir çözüm üretebilme yeteneğini geliştirmektir.

---

### Debug Challenge

Junior'a hata veren veya mantıksal olarak yanlış çalışan kod verilir.

Junior:

```text
kodu çalıştırır
↓
terminal çıktısını okur
↓
hatayı analiz eder
↓
kodu düzeltir
↓
tekrar çalıştırır
```

Bu challenge tipi gerçek junior Data Engineer çalışma biçimine özellikle yakındır.

---

### Output Prediction

Junior kodu çalıştırmadan önce çıktının ne olacağını tahmin eder.

Amaç:

* program flow
* variables
* data structures
* loops
* functions
* transformations

gibi kavramların gerçekten anlaşılıp anlaşılmadığını görmek ve geliştirmektir.

Junior tahminini yaptıktan sonra kodu çalıştırıp gerçek sonuçla karşılaştırabilir.

---

### SQL Challenge

Junior verilen küçük dataset veya tablolar üzerinde SQL sorgusu yazar.

Örnek konular:

* SELECT / WHERE
* GROUP BY
* aggregate functions
* JOIN
* CTE
* window functions
* duplicate analysis
* data quality checks

Query gerçek SQL engine üzerinde çalıştırılır ve sonuç tablosu gösterilir.

---

### Data Investigation

Junior'a küçük bir dataset verilir ancak problem doğrudan söylenmez.

Amaç junior'ın veriyi inceleyerek problemi kendisinin bulmasıdır.

Örnek:

```text
employees.csv dosyasını incele.

Veride temizlenmesi veya araştırılması gereken
problemleri tespit et.
```

Junior:

* null values
* duplicates
* suspicious values
* incorrect types
* schema problems

gibi konuları araştırabilir.

---

### Transformation Challenge

Junior'dan veriyi belirli bir hedefe göre dönüştürmesi istenir.

Örnek:

```text
Eksik age değerlerini ele al.
Duplicate kayıtları temizle.
Sonuç dataset'ini oluştur.
```

Transformation sonrası before/after data deterministic olarak kontrol edilebilir.

---

### Validation Challenge

Junior'a yapılmış bir transformation veya SQL sonucu verilir.

Bu sefer görev çözümü yazmak değil:

> "Bu işlemin gerçekten doğru olduğunu nasıl kontrol edersin?"

sorusuna cevap vermektir.

Amaç junior'ın yalnızca kod yazmasını değil, yaptığı işi doğrulamayı öğrenmesidir.

---

### Explain Challenge

Junior yaptığı çözümü kısa şekilde açıklar.

Örnek sorular:

```text
Neden LEFT JOIN kullandın?

Neden dropna() yerine fillna() tercih ettin?

Bu transformation'ın doğru olduğunu nasıl biliyorsun?
```

Bu challenge tipi ezberlenmiş kod ile gerçekten anlaşılmış çözüm arasındaki farkı anlamaya yardımcı olur.

---

# Coding Workspace

Practice coding challenge'ları küçük bir development workspace içinde çalıştırılır.

Temel görünüm:

```text
┌───────────────────────────────────────────────────────┐
│ Challenge                                             │
├───────────────────┬───────────────────────────────────┤
│ Task              │ Code Editor                       │
│                   │                                   │
│ Goal              │                                   │
│ Dataset           │                                   │
│ Difficulty        │                                   │
│ Skill             │                                   │
│                   ├───────────────────────────────────┤
│ Mentor            │ Terminal / Output                 │
│                   │                                   │
│ Hint              │ traceback / stdout / test result  │
└───────────────────┴───────────────────────────────────┘
```

Coding workspace V1 için şu teknik bileşenlerden oluşabilir:

```text
Monaco Editor
→ code editing

xterm.js
→ terminal/output presentation

Pyodide
→ browser-side Python execution

DuckDB-Wasm
→ browser-side SQL execution
```

Terminal görünümü execution engine değildir.

Örneğin Python challenge:

```text
Monaco
↓
Run
↓
Pyodide
↓
stdout / exception / traceback
↓
xterm.js
```

SQL challenge:

```text
Monaco SQL Editor
↓
Run
↓
DuckDB-Wasm
↓
query result
↓
result table
```

Bu sayede V1 sırasında junior kodu gerçek bir execution environment içinde deneyebilir ancak arbitrary user code doğrudan DataPilot backend server üzerinde çalıştırılmaz.

---

## Progressive Help

Challenge sırasında mentor çözümü hemen göstermez.

```text
Independent Attempt
↓
NUDGE
↓
GUIDE
↓
TEACH
↓
DEMONSTRATE
```

Örneğin terminalde:

```text
KeyError: 'city'
```

görülüyorsa practicing seviyesindeki junior'a doğrudan çözüm kodu verilmez.

Mentor önce:

```text
Traceback'in son satırına bak.
Hangi key bulunamıyor?
```

gibi küçük bir yönlendirme verebilir.

Junior'ın assistance ihtiyacı yeni learning evidence olarak learner profile'a kaydedilir.

---

## Practice Principle

Practice'in amacı challenge sayısını artırmak değildir.

Amaç junior'ın:

```text
problemi anlaması
↓
kendi çözümünü denemesi
↓
çıktıyı okuyabilmesi
↓
hatayı analiz edebilmesi
↓
çözümü doğrulayabilmesi
↓
giderek daha az yardım istemesi
```

sürecinde ilerlemesidir.
