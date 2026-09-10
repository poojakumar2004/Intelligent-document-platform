import sqlite3
import os
from contextlib import contextmanager
from backend.app.core.config import settings
from backend.app.core.logging import logger

def init_db():
    db_path = settings.DATABASE_PATH
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    logger.info(f"Initializing SQLite database at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_name TEXT NOT NULL,
            document_type TEXT NOT NULL,
            processing_status TEXT NOT NULL,
            overall_confidence REAL,
            file_validation TEXT NOT NULL,
            extracted_data TEXT NOT NULL,
            validation TEXT NOT NULL,
            processing_metadata TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_document_name ON documents(document_name)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_document_type ON documents(document_type)
    """)
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully.")

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(settings.DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
