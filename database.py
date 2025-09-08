# database.py
import os
import psycopg
from psycopg.rows import dict_row

# Render/12-factor: DATABASE_URL 환경변수 사용
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Render PostgreSQL는 보통 SSL이 요구됩니다. sslmode 파라미터가 없으면 require로 보강합니다.
if DATABASE_URL and "sslmode=" not in DATABASE_URL:
    sep = "&" if "?" in DATABASE_URL else "?"
    DATABASE_URL = f"{DATABASE_URL}{sep}sslmode=require"


def _get_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL 환경변수가 설정되지 않았습니다. Render PostgreSQL 연결 정보가 필요합니다.")
    return psycopg.connect(DATABASE_URL)


def init_db():
    """
    PostgreSQL에 필요한 테이블을 생성합니다.
    - posts(link UNIQUE)
    - subscribers(user_id UNIQUE)
    """
    with _get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS posts (
                    id SERIAL PRIMARY KEY,
                    link TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS subscribers (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL UNIQUE,
                    subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()


def add_sent_post(link: str, title: str) -> None:
    with _get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO posts (link, title) VALUES (%s, %s) ON CONFLICT (link) DO NOTHING",
                (link, title),
            )
            conn.commit()
            print(f"✅ DB에 공지 기록 완료: {title[:30]}...")


def is_post_sent(link: str) -> bool:
    with _get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM posts WHERE link = %s LIMIT 1", (link,))
            row = cur.fetchone()
            return row is not None


# ==========================
# 구독자 관리 유틸 함수
# ==========================

def add_subscriber(user_id: str) -> bool:
    with _get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO subscribers (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
                (user_id,),
            )
            changed = cur.rowcount
            conn.commit()
            if changed:
                print(f"✅ 구독자 추가: {user_id}")
                return True
            print(f"ℹ️ 이미 구독 중인 사용자: {user_id}")
            return False


def remove_subscriber(user_id: str) -> bool:
    with _get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM subscribers WHERE user_id = %s", (user_id,))
            deleted = cur.rowcount
            conn.commit()
            if deleted:
                print(f"✅ 구독자 제거: {user_id}")
                return True
            print(f"ℹ️ 구독자 없음: {user_id}")
            return False


def list_subscribers() -> list[str]:
    with _get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM subscribers ORDER BY id ASC")
            rows = cur.fetchall()
            return [r[0] for r in rows]


def is_subscribed(user_id: str) -> bool:
    with _get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM subscribers WHERE user_id = %s LIMIT 1", (user_id,))
            row = cur.fetchone()
            return row is not None
