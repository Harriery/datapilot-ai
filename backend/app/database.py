import sqlite3
from pathlib import Path


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
            FOREIGN KEY (document_id)
                REFERENCES documents(id)
                ON DELETE CASCADE
        )
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
def insert_chunks(document_id: int, chunks: list[str]):
    connection = get_connection()

    for chunk_index, content in enumerate(chunks):  # her chunk’a sıra numarası verir:
        connection.execute(
            """
            INSERT INTO chunks (document_id, chunk_index, content)
            VALUES (?, ?, ?)
            """,
            (document_id, chunk_index, content),
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

    chunks = connection.execute(
        """
        SELECT chunk_index, content
        FROM chunks
        WHERE document_id = ?
        ORDER BY chunk_index ASC
        """,
        (document_id,),
    ).fetchall()

    connection.close()

    return chunks