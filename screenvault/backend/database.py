"""
database.py — SQLite connection, schema creation, and FTS5 index setup.
"""

import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.expanduser(os.getenv("DB_PATH", "~/.screenvault/db.sqlite"))


def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # WAL mode allows concurrent reads while a write is in progress
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def db():
    """Context manager that yields a connection and commits on exit."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create all tables and indexes if they don't already exist."""
    with db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id          TEXT PRIMARY KEY,
                email       TEXT UNIQUE NOT NULL,
                plan        TEXT NOT NULL DEFAULT 'free',
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS screenshots (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       TEXT NOT NULL REFERENCES users(id),
                filename      TEXT NOT NULL,
                filepath      TEXT NOT NULL,
                thumbnail     TEXT,
                captured_at   DATETIME,
                ocr_text      TEXT,
                description   TEXT,
                tags          TEXT DEFAULT '[]',
                embedding     TEXT,
                status        TEXT NOT NULL DEFAULT 'pending',
                created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            -- FTS5 virtual table for full-text search across filename, descriptions and OCR text
            CREATE VIRTUAL TABLE IF NOT EXISTS screenshots_fts USING fts5(
                filename,
                ocr_text,
                description,
                tags,
                content='screenshots',
                content_rowid='id'
            );

            -- Keep FTS index in sync when a screenshot row is updated
            CREATE TRIGGER IF NOT EXISTS screenshots_ai AFTER INSERT ON screenshots BEGIN
                INSERT INTO screenshots_fts(rowid, filename, ocr_text, description, tags)
                VALUES (new.id, new.filename, new.ocr_text, new.description, new.tags);
            END;

            CREATE TRIGGER IF NOT EXISTS screenshots_au AFTER UPDATE ON screenshots BEGIN
                UPDATE screenshots_fts
                SET filename = new.filename,
                    ocr_text = new.ocr_text,
                    description = new.description,
                    tags = new.tags
                WHERE rowid = new.id;
            END;

            CREATE TRIGGER IF NOT EXISTS screenshots_ad AFTER DELETE ON screenshots BEGIN
                DELETE FROM screenshots_fts WHERE rowid = old.id;
            END;
        """)
        # Migration: add embedding column to existing databases (no-op if already present)
        try:
            conn.execute("ALTER TABLE screenshots ADD COLUMN embedding TEXT")
        except Exception:
            pass
        # Migration: add type column to classify screenshots vs documents
        try:
            conn.execute("ALTER TABLE screenshots ADD COLUMN type TEXT NOT NULL DEFAULT 'screenshot'")
        except Exception:
            pass
        # Migration: add page_count for multi-page documents (NULL for screenshots)
        try:
            conn.execute("ALTER TABLE screenshots ADD COLUMN page_count INTEGER")
        except Exception:
            pass

    # Migration: rebuild FTS5 index to include filename column (for title-based search)
    needs_rebuild = False
    try:
        with db() as conn:
            conn.execute("SELECT filename FROM screenshots_fts LIMIT 1")
    except Exception:
        needs_rebuild = True

    if needs_rebuild:
        conn = get_connection()
        try:
            for stmt in [
                "DROP TRIGGER IF EXISTS screenshots_ai",
                "DROP TRIGGER IF EXISTS screenshots_au",
                "DROP TRIGGER IF EXISTS screenshots_ad",
                "DROP TABLE IF EXISTS screenshots_fts",
                """CREATE VIRTUAL TABLE screenshots_fts USING fts5(
                    filename, ocr_text, description, tags,
                    content='screenshots', content_rowid='id'
                )""",
                """CREATE TRIGGER screenshots_ai AFTER INSERT ON screenshots BEGIN
                    INSERT INTO screenshots_fts(rowid, filename, ocr_text, description, tags)
                    VALUES (new.id, new.filename, new.ocr_text, new.description, new.tags);
                END""",
                """CREATE TRIGGER screenshots_au AFTER UPDATE ON screenshots BEGIN
                    UPDATE screenshots_fts
                    SET filename = new.filename, ocr_text = new.ocr_text,
                        description = new.description, tags = new.tags
                    WHERE rowid = new.id;
                END""",
                """CREATE TRIGGER screenshots_ad AFTER DELETE ON screenshots BEGIN
                    DELETE FROM screenshots_fts WHERE rowid = old.id;
                END""",
                """INSERT INTO screenshots_fts(rowid, filename, ocr_text, description, tags)
                    SELECT id, filename, ocr_text, description, tags FROM screenshots""",
            ]:
                conn.execute(stmt)
            conn.commit()
        finally:
            conn.close()

    print(f"[db] Initialised at {DB_PATH}")


if __name__ == "__main__":
    init_db()
