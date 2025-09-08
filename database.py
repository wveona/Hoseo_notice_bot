# database.py
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Render/12-factor: DATABASE_URL 환경변수 사용
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Render PostgreSQL는 보통 SSL이 요구됩니다. sslmode 파라미터가 없으면 require로 보강합니다.
if DATABASE_URL and "sslmode=" not in DATABASE_URL:
    sep = "&" if "?" in DATABASE_URL else "?"
    DATABASE_URL = f"{DATABASE_URL}{sep}sslmode=require"

# 테이블명 상수 (기존 'posts' 명칭 충돌 회피)
POSTS_TABLE = "sent_posts"
SUBSCRIBERS_TABLE = "subscribers"


def _get_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL 환경변수가 설정되지 않았습니다. Render PostgreSQL 연결 정보가 필요합니다.")
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def init_db():
    """
    PostgreSQL에 필요한 테이블을 생성합니다.
    - sent_posts(link UNIQUE)
    - subscribers(user_id UNIQUE)
    """
    conn = _get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {POSTS_TABLE} (
                id SERIAL PRIMARY KEY,
                link TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {SUBSCRIBERS_TABLE} (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL UNIQUE,
                subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def add_sent_post(link: str, title: str) -> None:
    conn = _get_connection()
    cur = conn.cursor()
    try:
        cur.execute(f"INSERT INTO {POSTS_TABLE} (link, title) VALUES (%s, %s) ON CONFLICT (link) DO NOTHING", (link, title))
        conn.commit()
        print(f"✅ DB에 공지 기록 완료: {title[:30]}...")
    finally:
        cur.close()
        conn.close()


def is_post_sent(link: str) -> bool:
    conn = _get_connection()
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT id FROM {POSTS_TABLE} WHERE link = %s LIMIT 1", (link,))
        row = cur.fetchone()
        return row is not None
    finally:
        cur.close()
        conn.close()


# ==========================
# 구독자 관리 유틸 함수
# ==========================

def add_subscriber(user_id: str) -> bool:
    conn = _get_connection()
    cur = conn.cursor()
    try:
        cur.execute(f"INSERT INTO {SUBSCRIBERS_TABLE} (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING", (user_id,))
        changed = cur.rowcount
        conn.commit()
        if changed:
            print(f"✅ 구독자 추가: {user_id}")
            return True
        print(f"ℹ️ 이미 구독 중인 사용자: {user_id}")
        return False
    finally:
        cur.close()
        conn.close()


def remove_subscriber(user_id: str) -> bool:
    conn = _get_connection()
    cur = conn.cursor()
    try:
        cur.execute(f"DELETE FROM {SUBSCRIBERS_TABLE} WHERE user_id = %s", (user_id,))
        deleted = cur.rowcount
        conn.commit()
        if deleted:
            print(f"✅ 구독자 제거: {user_id}")
            return True
        print(f"ℹ️ 구독자 없음: {user_id}")
        return False
    finally:
        cur.close()
        conn.close()


def list_subscribers() -> list[str]:
    conn = _get_connection()
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT user_id FROM {SUBSCRIBERS_TABLE} ORDER BY id ASC")
        rows = cur.fetchall()
        return [r["user_id"] for r in rows]
    finally:
        cur.close()
        conn.close()


def is_subscribed(user_id: str) -> bool:
    conn = _get_connection()
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT id FROM {SUBSCRIBERS_TABLE} WHERE user_id = %s LIMIT 1", (user_id,))
        row = cur.fetchone()
        return row is not None
    finally:
        cur.close()
        conn.close()
