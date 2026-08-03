import math




# İki embedding vektörü arasındaki benzerliği hesaplar.
# 1. Aynı sıradaki sayıları çarpıp toplamak
# 2. vector_a'nın büyüklüğünü hesaplamak
# 3. vector_b'nin büyüklüğünü hesaplamak
# 4. Çarpım toplamını iki büyüklüğün çarpımına bölmek

# Kullanıcının sorusuyla bir belge chunk'ının anlam benzerliğini hesaplar.
def cosine_similarity(
    question_embedding: list[float],  # Kullanıcı sorusunun sayı listesi
    chunk_embedding: list[float],     # Veritabanındaki bir chunk'ın sayı listesi
) -> float:
    
    # İki embedding içindeki aynı sıradaki sayıları eşleştirir. 
    # Eslesmeler konuma(index) gore yapilir. [1, 2] [3, 4] 1-3, 2-4 ile eslesir.
    pairs = zip(question_embedding, chunk_embedding)

    # Eşleşen sayıları birbiriyle çarpar.
    products = [
        question_value * chunk_value
        for question_value, chunk_value in pairs
    ]

    # Bütün çarpım sonuçlarını toplar.
    dot_product = sum(products)

    # Soru embedding’indeki her sayının karesini alır.
    question_squares = [
        question_value * question_value
        for question_value in question_embedding
    ]

    # Kareleri toplar.
    question_square_sum = sum(question_squares)

    # Toplamın karekökünü alarak soru embedding’inin büyüklüğünü hesaplar.
    question_magnitude = math.sqrt(question_square_sum)
    
        # Chunk embedding’indeki her sayının karesini alır.
    chunk_squares = [
        chunk_value * chunk_value
        for chunk_value in chunk_embedding
    ]

    # Chunk karelerini toplar.
    chunk_square_sum = sum(chunk_squares)

    # Toplamın karekökünü alarak chunk embedding’inin büyüklüğünü hesaplar.
    chunk_magnitude = math.sqrt(chunk_square_sum)

        # Vektörlerden biri tamamen sıfırlardan oluşuyorsa sıfıra bölmeyi önler.
    if question_magnitude == 0 or chunk_magnitude == 0:
        return 0.0

    # İki embedding arasındaki anlam benzerliği puanını hesaplar.
    similarity = dot_product / (
        question_magnitude * chunk_magnitude
    )

    return similarity


    # Kullanıcının sorusuna en yakın chunk'ları bulur.
def find_relevant_chunks(
    question_embedding: list[float],  # Kullanıcı sorusunun embedding'i
    chunks: list[dict],               # Veritabanından gelen chunk'lar
    top_k: int = 3,                   # En yüksek puanlı kaç chunk dönecek?
) -> list[dict]:

    # Benzerlik puanı eklenmiş chunk'ları burada toplayacağız.
    scored_chunks = []

    # Her chunk'ı soru embedding'iyle ayrı ayrı karşılaştırır.
    for chunk in chunks:

        # Veritabanından gelen bu chunk'ın embedding listesini alır.
        chunk_embedding = chunk["embedding"]

        # Soru embedding'i ile bu chunk'ın embedding'ini karşılaştırır.
        similarity = cosine_similarity(     #yukardaki cosine_similtary fonk cagsiriyoruz
            question_embedding,
            chunk_embedding,
        )

        # Chunk bilgilerini benzerlik puanıyla birlikte yeni listeye ekler.
        scored_chunks.append({
            "chunk_index": chunk["chunk_index"],    # → hangi chunk olduğunu alır
            "content": chunk["content"],            # → chunk metnini alır
            "similarity": similarity,               # → az önce hesapladığımız puanı ekler
        })

        # Chunk'ları benzerlik puanına göre yüksekten düşüğe sıralar.
    sorted_chunks = sorted(
        scored_chunks,                              # → Bütün chunk'lar ve puanları
        key=lambda chunk: chunk["similarity"],      # → Her chunk için hangi değere bakacağını söyler.
        reverse=True,                               # → Büyük puandan küçük puana sırala
    )

    # Sadece en yüksek puanlı ilk top_k chunk'ı döndürür.
    return sorted_chunks[:top_k]        