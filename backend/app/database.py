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


def get_connection():
    DATABASE_PATH.parent.mkdir(exist_ok=True) # data klasoru olusturur.

    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.row_factory = sqlite3.Row

    return connection


# mkdir       → klasörü hazırlar
# PRAGMA      → tablo ilişkilerini denetler
# row_factory → SELECT sonuçlarını kolon adıyla okumamızı sağlar

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
    
     
    connection.commit()
    connection.close()




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