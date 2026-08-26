import sqlite3
from pathlib import Path
import json


# DATABASE_PATH
# ↓
# Veritabanı dosyasının yerini belirler
# 
# get_connection()
# ↓
# SQLite veritabanına bağlantı açar
# 
# mkdir()
# ↓
# data klasörü yoksa oluşturur
# 
# row_factory
# ↓
# Veritabanı sonuçlarına kolon adıyla erişmemizi sağlar

DATABASE_PATH = Path("data/datapilot.db")


# ==================================================
# VERİTABANI BAĞLANTISI
# ==================================================

# Veritabanının kapısını açar
def get_connection():
    DATABASE_PATH.parent.mkdir(exist_ok=True) # data klasoru olusturur.

    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.row_factory = sqlite3.Row

    return connection

# mkdir       → klasörü hazırlar
# PRAGMA      → tablo ilişkilerini denetler
# row_factory → SELECT sonuçlarını kolon adıyla okumamızı sağlar


# ==================================================
# TABLOLARIN OLUŞTURULMASI
# ==================================================

#veritabanının başlangıç hazırlığını yapar.
# Tablolar yoksa oluşturur; varsa mevcut tablolara dokunmaz.
def init_db():
    connection = get_connection()

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id)
                REFERENCES sessions(session_id)
                ON DELETE CASCADE   
        )
        """
    )

        # Yüklenen belgelerin bilgilerini saklar.
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            content_type TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Belgelerden oluşturulan metin parçalarını saklar. (chunk lari saklar)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            embedding TEXT NOT NULL,                
            FOREIGN KEY (document_id)
                REFERENCES documents(id)
                ON DELETE CASCADE
        )
        """
    )
    # NEDEN embedding TEXT NOT NULLSQLite’ta doğrudan list[float] türü yok.
    # Embedding listesini önce JSON metnine çevirip saklayacağız; okurken tekrar listeye çevireceğiz.
     
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS learner_profiles(
            learner_id TEXT PRIMARY KEY,
            answer_length TEXT NOT NULL,
            learning_style TEXT NOT NULL,
            code_support TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
              )

        """
    )


  
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS skill_states(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            learner_id TEXT NOT NULL,
            skill_name TEXT NOT NULL,
            status TEXT NOT NULL,
            attempts INTEGER DEFAULT 0,
            successful_attempts INTEGER DEFAULT 0,
            last_difficulty TEXT,
            last_used_at TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (learner_id)
                REFERENCES learner_profiles(learner_id),
            UNIQUE (learner_id, skill_name)
        )
        """
    )


    connection.execute(
        """
        

        """

    )
    connection.commit()
    connection.close()
    




# ==================================================
# SESSION İŞLEMLERİ
# ==================================================

# session_id alır
# ↓
# sessions tablosuna yeni satır ekler
# ↓
# kaydedip bağlantıyı kapatır
def insert_session(session_id: str): # session kaydi olusturmak icin
    connection = get_connection()

    connection.execute(
        "INSERT INTO sessions (session_id) VALUES (?)",
        (session_id,),
    )

    connection.commit()
    connection.close()


# Veritabanına bağlan
# ↓
# sessions tablosunda verilen ID’yi ara
# ↓
# fetchone() ile tek satırı al
# ↓
# bağlantıyı kapat
# ↓
# bulunan session’ı döndür
def get_session_by_id(session_id: str):
    connection = get_connection()

    session = connection.execute(
        "SELECT * FROM sessions WHERE session_id = ?",
        (session_id,),
    ).fetchone()

    connection.close()

    return session


# Session ID’yi bul
# ↓
# O satırı sil
# ↓
# Değişikliği kaydet
# ↓
# Kaç satır silindiğini döndür
def delete_session_by_id(session_id: str):
    connection = get_connection()

    cursor = connection.execute(
        "DELETE FROM sessions WHERE session_id = ?",
        (session_id,),
    )

    connection.commit()
    connection.close()

    return cursor.rowcount



# ==================================================
# MESAJ İŞLEMLERİ
# ==================================================

# insert_message()
# ↓
# Hangi session? → session_id
# Mesajı kim yazdı? → role
# Mesaj nedir? → content
# ↓
# messages tablosuna kaydet
def insert_message(session_id: str, role: str, content: str):
    connection = get_connection()

    connection.execute(
        """
        INSERT INTO messages (session_id, role, content)
        VALUES (?, ?, ?)
        """,
        (session_id, role, content),
    )

    connection.commit()
    connection.close()



# Verilen session_id’ye ait mesajları bul
# ↓
# id sırasına göre eskiden yeniye diz
# ↓
# fetchall() ile tüm mesajları getir
# ↓
# OpenAI’nin kullandığı role/content formatına çevir
def get_messages_by_session(session_id: str):
    connection = get_connection()

    messages = connection.execute(
        """
        SELECT role, content
        FROM messages
        WHERE session_id = ?
        ORDER BY id ASC
        """,
        (session_id,),
    ).fetchall()

    connection.close()

    return [
        {
            "role": message["role"],
            "content": message["content"],
        }
        for message in messages
    ]


# Verilen session’ın mesajlarını bul
# ↓
# En büyük id’ye sahip olanı seç
# ↓
# Yani en son eklenen mesajı sil
# OpenAI cevap veremezse session'a en son eklenen mesajı siler.
def delete_last_message(session_id: str):
    connection = get_connection()

    connection.execute(
        """
        DELETE FROM messages
        WHERE id = (
            SELECT id
            FROM messages
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT 1
        )
        """,
        (session_id,),
    )

    connection.commit()
    connection.close()



# ==================================================
# BELGE VE CHUNK İŞLEMLERİ
# ==================================================

# Yüklenen belgeyi documents tablosuna kaydeder
# ve oluşturulan document id'sini geri döndürür.
def insert_document(filename: str, content_type: str) -> int:
    connection = get_connection()

    cursor = connection.execute(
        """
        INSERT INTO documents (filename, content_type)
        VALUES (?, ?)
        """,
        (filename, content_type),
    )

    connection.commit()

    document_id = cursor.lastrowid  # ise yeni oluşturulan belgenin otomatik id değerini verir.

    connection.close()

    return document_id          # Bu document_idyi sonraki adımda chunk’ları kaydederken kullanacağız:
                                #Belge id = 1
                                #↓
                                #Chunk 0 → document_id 1
                                #Chunk 1 → document_id 1
                                #Chunk 2 → document_id 1

# Bir belgeye ait bütün chunk'ları chunks tablosuna kaydeder.
def insert_chunks(
        document_id: int,
        chunks: list[str],
        embeddings: list[list[float]]
    ):
    

    if len(chunks) != len(embeddings):
        raise ValueError("Chunk ve embedding sayıları eşit olmalıdır.") 

    connection = get_connection()

    for chunk_index,(content, embedding) in enumerate(zip(chunks, embeddings)):  # zip() → aynı sıradaki chunk ve embedding’i eşleştirir
        embedding_json = json.dumps(embedding)

        connection.execute(
            """
            INSERT INTO chunks (document_id, chunk_index, content, embedding)
            VALUES (?, ?, ?, ?)
            """,
            (document_id, chunk_index, content, embedding_json),
        )

    connection.commit()
    connection.close()


    # Verilen ID'ye ait belge kaydını getirir.
def get_document_by_id(document_id: int):
    connection = get_connection()

    document = connection.execute(
        """
        SELECT *
        FROM documents
        WHERE id = ?
        """,
        (document_id,),
    ).fetchone()

    connection.close()

    return document


# Verilen belgeye ait bütün chunk'ları sırasıyla getirir.
def get_chunks_by_document(document_id: int):
    connection = get_connection()

    # rows -> SQLite’tan gelen ham satırlardır. Hemen altına dönüşüm
    # Yani: row["embedding"] -> "[0.12, -0.04, 0.08]"   → str seklinde geliyor asagida
    # SQLite sorgusundan gelen satırlar henüz uygulamanın kullanacağı
    # Python sözlüklerine dönüştürülmemiş sqlite3.Row nesneleridir.
    rows = connection.execute(
        """
        SELECT chunk_index, content, embedding
        FROM chunks
        WHERE document_id = ?
        ORDER BY chunk_index ASC
        """,
        (document_id,),
    ).fetchall()

    # Dönüştürülmüş chunk sözlüklerini burada toplayacağız.
    chunks = []

    for row in rows:
        chunks.append({
            "chunk_index": row["chunk_index"],  
            "content": row["content"],    
            # Embedding veritabanında JSON metni olarak saklanır.
            # json.loads() bu metni tekrar Python sayı listesine dönüştürür.      
            "embedding": json.loads(row["embedding"]),    # json.loads() ile listeye çevir
        })

    connection.close()

    return chunks


def insert_learner_profile(
        learner_id: str,
        answer_length: str,
        learning_style: str,
        code_support:str
        ):
    connection = get_connection()
    connection.execute(
        """
            INSERT INTO learner_profiles(learner_id, answer_length, learning_style, code_support)
            VALUES (?,?,?,?)
        """,
        (learner_id, answer_length, learning_style, code_support)

    )


    connection.commit()
    connection.close()

def get_learner_profile_by_id(learner_id:str):
    connection = get_connection()
    profile = connection.execute(
        """
        SELECT *
        FROM learner_profiles
        WHERE learner_id = ?
        """,
        (learner_id,),  #python da tek elemanli tupple icin virgul gerekli.
    ).fetchone()

    connection.close()
    
    return profile


def insert_skill_state(
        learner_id: str,
        skill_name: str,
        status: str,
        last_difficulty: str | None = None,
        last_used_at: str | None = None
        ):
    connection = get_connection()
    connection.execute(

        """
            INSERT INTO skill_states(learner_id, skill_name, status, last_difficulty, last_used_at)    
            VALUES(?,?,?,?,?)
        """,
        (learner_id, skill_name, status, last_difficulty, last_used_at)
    )
    connection.commit()
    connection.close()


def get_skill_state(learner_id: str, skill_name):
    connection = get_connection()
    skill = connection.execute(
        """
        SELECT *
        FROM skill_states
        WHERE learner_id = ?
        AND skill_name = ?
        """,
        (learner_id, skill_name),
    ).fetchone()

    connection.close()
    return skill

def get_skill_states_by_learner(learner_id: str):
    connection= get_connection()
    skills = connection.execute(
        """
        SELECT * 
        FROM skill_states
        WHERE learner_id = ?
        ORDER BY id ASC
        """,
        (learner_id,),
    ).fetchall()

    connection.close()
    
    return skills



