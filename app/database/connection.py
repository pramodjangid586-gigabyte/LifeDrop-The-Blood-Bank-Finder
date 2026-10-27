import sqlite3
import contextlib
from typing import Generator, Any, List, Dict, Optional
from app.core.config import settings

def get_db_connection() -> sqlite3.Connection:
    """Create a configured SQLite database connection with row factory."""
    conn = sqlite3.connect(settings.DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

@contextlib.contextmanager
def db_session() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for SQLite connections with automatic commit/rollback."""
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def query_all(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """Execute query and return all matching rows as dictionaries."""
    with db_session() as conn:
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def query_one(sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
    """Execute query and return single row as dictionary, or None."""
    with db_session() as conn:
        cursor = conn.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None

def execute_cmd(sql: str, params: tuple = ()) -> int:
    """Execute write query and return number of affected rows."""
    with db_session() as conn:
        cursor = conn.execute(sql, params)
        return cursor.rowcount

def execute_insert(sql: str, params: tuple = ()) -> int:
    """Execute insert query and return the last inserted row ID."""
    with db_session() as conn:
        cursor = conn.execute(sql, params)
        return cursor.lastrowid
