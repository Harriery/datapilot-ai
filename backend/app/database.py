import sqlite3
from pathlib import Path
import json
from uuid import uuid4

from backend.app.models import (
    DataEngineeringTask,
    PracticeChallenge,
    PracticeChallengeRecord,
    PracticeAttemptRequest,
    PracticeAttemptValidation,
    PracticeDiagnosis,
    PracticeMentorDecision,
    PracticeAttemptRecord,
)

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
    CREATE TABLE IF NOT EXISTS learning_evidence(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        learner_id TEXT NOT NULL,
        skill_name TEXT NOT NULL,
        assistance_level TEXT NOT NULL,
        success INTEGER NOT NULL,
        evidence_type TEXT NOT NULL,
        note TEXT,
        session_id TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (learner_id)
            REFERENCES learner_profiles(learner_id),

        FOREIGN KEY (session_id)
            REFERENCES sessions(session_id)
    )
    """
    )

        # ==================================================
    # DATA ENGINEERING TASKS
    # ==================================================
    #
    # Junior'ın multi-step task durumunu saklar.
    #
    # task_json:
    # DataEngineeringTask modelinin tamamını JSON olarak tutar.
    #
    # Böylece junior daha sonra geri geldiğinde
    # hangi step'te kaldığını tekrar okuyabiliriz.
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS data_engineering_tasks (
            task_id TEXT PRIMARY KEY,
            learner_id TEXT NOT NULL,
            task_json TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (learner_id)
                REFERENCES learner_profiles(learner_id)
        )
        """
    )

    
    # ==================================================
    # PRACTICE CHALLENGES
    # ==================================================
    #
    # Practice sırasında oluşturulan challenge'ları saklar.
    #
    # public_challenge_json:
    # Junior'ın görebileceği challenge.
    #
    # expected_outcome:
    # Validation için backend'de kalır.
    # Frontend'e gönderilmez.
    connection.execute(
    """
    CREATE TABLE IF NOT EXISTS practice_challenges (
        challenge_id TEXT PRIMARY KEY,
        learner_id TEXT NOT NULL,
        skill_name TEXT NOT NULL,
        difficulty TEXT NOT NULL,
        challenge_type TEXT NOT NULL,

        public_challenge_json TEXT NOT NULL,
        expected_outcome TEXT NOT NULL,

        status TEXT NOT NULL DEFAULT 'active',

        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (learner_id)
            REFERENCES learner_profiles(learner_id)
    )
    """
    )

    # ==================================================
    # PRACTICE ATTEMPTS
    # ==================================================
    #
    # Junior'ın bir practice challenge için yaptığı
    # her denemeyi saklar.
    #
    # Bu geçmiş daha sonra adaptive mentor tarafından
    # kullanılacak:
    #
    # - Kaçıncı deneme?
    # - Daha önce aynı skill'de başarılı olmuş mu?
    # - Aynı hatayı tekrar ediyor mu?
    # - Ne kadar yardım gerekiyordu?
    #
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS practice_attempts (
            attempt_id TEXT PRIMARY KEY,

            learner_id TEXT NOT NULL,
            challenge_id TEXT NOT NULL,

            attempt_number INTEGER NOT NULL,

            answer TEXT NOT NULL,
            execution_output TEXT,
            execution_error TEXT,

            success INTEGER NOT NULL,
            validation_feedback TEXT NOT NULL,

            diagnosis_json TEXT,
            mentor_decision_json TEXT,

            assistance_level TEXT,
            support_strategy TEXT,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (learner_id)
                REFERENCES learner_profiles(learner_id),

            FOREIGN KEY (challenge_id)
                REFERENCES practice_challenges(challenge_id)
        )
        """
    )

    # --------------------------------------------------
    # PRACTICE ATTEMPTS SCHEMA MIGRATION
    # --------------------------------------------------
    #
    # practice_attempts tablosu daha önce oluşturulmuşsa
    # CREATE TABLE IF NOT EXISTS yeni kolon eklemez.
    #
    # Bu nedenle mentor_decision_json kolonu eksikse
    # mevcut tabloya güvenli şekilde ekliyoruz.

    practice_attempt_columns = {
        row["name"]
        for row in connection.execute(
            "PRAGMA table_info(practice_attempts)"
        ).fetchall()
    }

    if "mentor_decision_json" not in practice_attempt_columns:
        connection.execute(
            """
            ALTER TABLE practice_attempts
            ADD COLUMN mentor_decision_json TEXT
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



def insert_learning_evidence(
    learner_id: str,
    skill_name: str,
    assistance_level: str,
    success: bool,
    evidence_type: str,
    note: str | None = None,
    session_id: str | None = None,
    ):
    connection = get_connection()
    connection.execute(

        """
            INSERT INTO learning_evidence(learner_id,skill_name, assistance_level, success, evidence_type,note, session_id)
            VALUES (?,?,?,?,?,?,?)
        """,
        (learner_id, skill_name, assistance_level, success, evidence_type,note, session_id)
    )
    connection.commit()
    connection.close()


def get_learning_evidence_by_skill(
        learner_id: str,
        skill_name: str,
        ):
    connection= get_connection()
    evidence = connection.execute(
        """
        SELECT * 
        FROM learning_evidence
        WHERE learner_id = ?
        AND skill_name = ?
        ORDER BY id ASC
        """,
        (learner_id, skill_name)
        
    ).fetchall()


    connection.close()
    return evidence

def update_skill_state_after_evidence(
    learner_id: str,
    skill_name: str,
    success: bool,
    ):
    connection = get_connection()
    connection.execute(
    """
    UPDATE skill_states
    SET
        attempts = attempts + 1,
        successful_attempts = successful_attempts + ?,
        last_used_at = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP
    WHERE learner_id = ?
    AND skill_name = ?
    """,
    (
        int(success),
        learner_id,
        skill_name,
    ),
    )
    connection.commit()
    connection.close()

def record_learning_evidence(
    learner_id: str,
    skill_name: str,
    assistance_level: str,
    success: bool,
    evidence_type: str,
    note: str | None = None,    # str | None → string de olabilir, None da olabilir
    session_id: str | None = None,  # = None → kullanıcı değer vermezse varsayılan olarak None kullan

    ):
    connection = get_connection()
    
    try:
        connection.execute(
            """
                INSERT INTO learning_evidence(learner_id,skill_name, assistance_level, success, evidence_type,note, session_id)
                VALUES (?,?,?,?,?,?,?)
            """,
            (learner_id, skill_name, assistance_level, success, evidence_type,note, session_id)
        ),
        cursor = connection.execute(
            """
                UPDATE skill_states
                SET
                    attempts = attempts + 1,
                    successful_attempts = successful_attempts + ?,
                    last_used_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE learner_id = ?
                AND skill_name = ?
                """,
                (
                    int(success),
                    learner_id,
                    skill_name,
                ),

        )
        # kontrolettigimiz, kac kayit etkilendi.
        if cursor.rowcount == 0:                        # rowcount = 1 → skill bulundu ve update edildi
                                                        # rowcount = 0 → skill bulunamadı, hiçbir şey update edilmedi
            raise ValueError("Skill state bulunamadı.")
        connection.commit()
        
       
    except Exception:
        connection.rollback() # Bu transaction içinde şimdiye kadar yaptığımız değişiklikleri iptal et.
        raise

    finally:
        connection.close()

def update_skill_status(
  learner_id: str,
  skill_name: str,
  new_status: str,      
    ):
    valid_statuses = {"new", "learning", "practicing", "comfortable"}
    if new_status not in valid_statuses:
        raise ValueError("Geçersiz skill status.")
    connection = get_connection()
    cursor= connection.execute(
        """
            UPDATE skill_states
            SET status = ?
            WHERE learner_id = ?
            AND skill_name = ?
        """,
        (new_status, learner_id, skill_name) # Mevcut status değerini new_status ile güncelliyoruz.
    )
    # kontrolettigimiz, kac kayit etkilendi.
    if cursor.rowcount == 0:                        # rowcount = 1 → skill bulundu ve update edildi
        connection.close()                                            # rowcount = 0 → skill bulunamadı, hiçbir şey update edilmedi
        raise ValueError("Skill state bulunamadı.")
    connection.commit()
   
    connection.close()

        
    # ==================================================
# DATA ENGINEERING TASK İŞLEMLERİ
# ==================================================

def save_data_engineering_task(
    learner_id: str,
    task,
):
    """
    DataEngineeringTask'in mevcut durumunu veritabanına kaydeder.

    Task daha önce yoksa oluşturur.
    Aynı task_id zaten varsa mevcut kaydı günceller.
    """

    connection = get_connection()

    # Pydantic modelini JSON metnine çeviriyoruz.
    task_json = task.model_dump_json()

    connection.execute(
        """
        INSERT INTO data_engineering_tasks (
            task_id,
            learner_id,
            task_json,
            status
        )
        VALUES (?, ?, ?, ?)

        ON CONFLICT(task_id)
        DO UPDATE SET
            learner_id = excluded.learner_id,
            task_json = excluded.task_json,
            status = excluded.status,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            task.task_id,
            learner_id,
            task_json,
            task.status,
        ),
    )


    connection.commit()
    connection.close()

def get_data_engineering_task(
    task_id: str,
    learner_id: str,
):
    """
    Belirli bir learner'a ait task kaydını bulur
    ve tekrar DataEngineeringTask modeline dönüştürür.
    """

    connection = get_connection()

    row = connection.execute(
        """
        SELECT task_json
        FROM data_engineering_tasks
        WHERE task_id = ?
        AND learner_id = ?
        """,
        (
            task_id,
            learner_id,
        ),
    ).fetchone()

    connection.close()

    if row is None:
        return None

    return DataEngineeringTask.model_validate_json(
        row["task_json"]
    )

# ==================================================
# PRACTICE CHALLENGE İŞLEMLERİ
# ==================================================


def save_practice_challenge(
    learner_id: str,
    record: PracticeChallengeRecord,
):
    """
    Oluşturulan practice challenge'ı DB'ye kaydeder.

    Public challenge junior'a gösterilebilir.
    expected_outcome ise sadece backend validation için saklanır.
    """

    connection = get_connection()

    challenge = record.challenge

    public_challenge_json = challenge.model_dump_json()

    connection.execute(
        """
        INSERT INTO practice_challenges (
            challenge_id,
            learner_id,
            skill_name,
            difficulty,
            challenge_type,
            public_challenge_json,
            expected_outcome,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            challenge.challenge_id,
            learner_id,
            challenge.skill_name,
            challenge.difficulty,
            challenge.challenge_type,
            public_challenge_json,
            record.expected_outcome,
            "active",
        ),
    )

    connection.commit()
    connection.close()


def get_practice_challenge(
    challenge_id: str,
    learner_id: str,
) -> PracticeChallengeRecord | None:
    """
    Belirli learner'a ait practice challenge'ı DB'den getirir.

    Public challenge JSON tekrar PracticeChallenge modeline çevrilir.
    Internal expected_outcome ile birlikte PracticeChallengeRecord döner.
    """

    connection = get_connection()

    row = connection.execute(
        """
        SELECT
            public_challenge_json,
            expected_outcome
        FROM practice_challenges
        WHERE challenge_id = ?
        AND learner_id = ?
        """,
        (
            challenge_id,
            learner_id,
        ),
    ).fetchone()

    connection.close()

    if row is None:
        return None

    challenge = PracticeChallenge.model_validate_json(
        row["public_challenge_json"]
    )

    return PracticeChallengeRecord(
        challenge=challenge,
        expected_outcome=row["expected_outcome"],
    )

# ==================================================
# PRACTICE ATTEMPT İŞLEMLERİ
# ==================================================


def save_practice_attempt(
    attempt: PracticeAttemptRequest,
    validation: PracticeAttemptValidation,
    diagnosis: PracticeDiagnosis | None = None,
    mentor_decision: PracticeMentorDecision | None = None,
) -> PracticeAttemptRecord:
    """
    Junior'ın practice denemesini DB'ye kaydeder.

    attempt_number backend tarafından otomatik hesaplanır.
    attempt_id backend tarafından UUID olarak oluşturulur.
    """

    connection = get_connection()

    # Aynı challenge için daha önce kaç attempt yapılmış?
    row = connection.execute(
        """
        SELECT MAX(attempt_number) AS max_attempt_number
        FROM practice_attempts
        WHERE learner_id = ?
        AND challenge_id = ?
        """,
        (
            attempt.learner_id,
            attempt.challenge_id,
        ),
    ).fetchone()

    previous_attempt_number = (
        row["max_attempt_number"]
        if row["max_attempt_number"] is not None
        else 0
    )

    attempt_number = previous_attempt_number + 1

    attempt_id = str(uuid4())

    diagnosis_json = (
        diagnosis.model_dump_json()
        if diagnosis is not None
        else None
    )

    mentor_decision_json = (
        mentor_decision.model_dump_json()
        if mentor_decision is not None
        else None
    )

    assistance_level = (
        mentor_decision.assistance_level
        if mentor_decision is not None
        else None
    )

    support_strategy = (
        mentor_decision.support_strategy
        if mentor_decision is not None
        else None
    )

    connection.execute(
        """
        INSERT INTO practice_attempts (
            attempt_id,
            learner_id,
            challenge_id,
            attempt_number,
            answer,
            execution_output,
            execution_error,
            success,
            validation_feedback,
            diagnosis_json,
            mentor_decision_json,
            assistance_level,
            support_strategy
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            attempt_id,
            attempt.learner_id,
            attempt.challenge_id,
            attempt_number,
            attempt.answer,
            attempt.execution_output,
            attempt.execution_error,
            int(validation.success),
            validation.feedback,
            diagnosis_json,
            mentor_decision_json,
            assistance_level,
            support_strategy,
        ),
    )

    connection.commit()
    connection.close()

    return PracticeAttemptRecord(
        attempt_id=attempt_id,
        attempt_number=attempt_number,
        attempt=attempt,
        validation=validation,
        diagnosis=diagnosis,
        mentor_decision=mentor_decision,
    )


def get_practice_attempts(
    learner_id: str,
    challenge_id: str,
) -> list[PracticeAttemptRecord]:
    """
    Belirli learner'ın belirli challenge için yaptığı
    bütün attempt'leri eski → yeni sırasıyla getirir.
    """

    connection = get_connection()

    rows = connection.execute(
        """
        SELECT *
        FROM practice_attempts
        WHERE learner_id = ?
        AND challenge_id = ?
        ORDER BY attempt_number ASC
        """,
        (
            learner_id,
            challenge_id,
        ),
    ).fetchall()

    connection.close()

    attempts = []

    for row in rows:

        attempt = PracticeAttemptRequest(
            learner_id=row["learner_id"],
            challenge_id=row["challenge_id"],
            answer=row["answer"],
            execution_output=row["execution_output"],
            execution_error=row["execution_error"],
        )

        validation = PracticeAttemptValidation(
            success=bool(row["success"]),
            feedback=row["validation_feedback"],
        )

        diagnosis = (
            PracticeDiagnosis.model_validate_json(
                row["diagnosis_json"]
            )
            if row["diagnosis_json"] is not None
            else None
        )

        mentor_decision = (
            PracticeMentorDecision.model_validate_json(
                row["mentor_decision_json"]
            )
            if row["mentor_decision_json"] is not None
            else None
        )

        record = PracticeAttemptRecord(
            attempt_id=row["attempt_id"],
            attempt_number=row["attempt_number"],
            attempt=attempt,
            validation=validation,
            diagnosis=diagnosis,
            mentor_decision=mentor_decision,
        )

        attempts.append(record)

    return attempts

def get_practice_attempts_by_skill(
    learner_id: str,
    skill_name: str,
) -> list[PracticeAttemptRecord]:
    """
    Belirli learner'ın belirli bir skill için yaptığı
    bütün practice attempt'lerini eski → yeni sırasıyla getirir.

    Aynı challenge ile sınırlı değildir.
    Farklı challenge'lar içindeki aynı skill geçmişini de toplar.
    """

    connection = get_connection()

    rows = connection.execute(
        """
        SELECT
            pa.*
        FROM practice_attempts AS pa
        JOIN practice_challenges AS pc
            ON pa.challenge_id = pc.challenge_id
        WHERE pa.learner_id = ?
        AND pc.skill_name = ?
        ORDER BY pa.created_at ASC, pa.attempt_number ASC
        """,
        (
            learner_id,
            skill_name,
        ),
    ).fetchall()

    connection.close()

    attempts = []

    for row in rows:

        attempt = PracticeAttemptRequest(
            learner_id=row["learner_id"],
            challenge_id=row["challenge_id"],
            answer=row["answer"],
            execution_output=row["execution_output"],
            execution_error=row["execution_error"],
        )

        validation = PracticeAttemptValidation(
            success=bool(row["success"]),
            feedback=row["validation_feedback"],
        )

        diagnosis = (
            PracticeDiagnosis.model_validate_json(
                row["diagnosis_json"]
            )
            if row["diagnosis_json"] is not None
            else None
        )

        mentor_decision = (
            PracticeMentorDecision.model_validate_json(
                row["mentor_decision_json"]
            )
            if row["mentor_decision_json"] is not None
            else None
        )

        attempts.append(
            PracticeAttemptRecord(
                attempt_id=row["attempt_id"],
                attempt_number=row["attempt_number"],
                attempt=attempt,
                validation=validation,
                diagnosis=diagnosis,
                mentor_decision=mentor_decision,
            )
        )

    return attempts