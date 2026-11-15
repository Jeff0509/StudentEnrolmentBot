
import sqlite3
from pathlib import Path
from datetime import datetime, timezone


PROJECT_ROOT = Path(__file__).resolve().parent.parent

MEMORY_DB = PROJECT_ROOT / "conversation_memory.db"


def get_connection():

    connection = sqlite3.connect(MEMORY_DB)

    connection.row_factory = sqlite3.Row

    return connection


def initialise_memory():

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_messages (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,

                FOREIGN KEY (conversation_id)
                    REFERENCES conversations(conversation_id)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_conversation_messages
            ON conversation_messages (
                conversation_id,
                message_id
            )
        """)

        connection.commit()

    finally:
        connection.close()


def create_conversation(conversation_id):

    initialise_memory()

    connection = get_connection()

    try:
        now = datetime.now(timezone.utc).isoformat()

        connection.execute("""
            INSERT OR IGNORE INTO conversations (
                conversation_id,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?)
        """, (conversation_id, now, now))

        connection.commit()

    finally:
        connection.close()


def save_message(conversation_id, role, content):

    if role not in ("user", "assistant"):
        raise ValueError("Unsupported conversation message role.")

    create_conversation(conversation_id)

    connection = get_connection()

    try:
        now = datetime.now(timezone.utc).isoformat()

        connection.execute("""
            INSERT INTO conversation_messages (
                conversation_id,
                role,
                content,
                created_at
            )
            VALUES (?, ?, ?, ?)
        """, (conversation_id, role, content, now))

        connection.execute("""
            UPDATE conversations
            SET updated_at = ?
            WHERE conversation_id = ?
        """, (now, conversation_id))

        connection.commit()

    finally:
        connection.close()


def get_history(conversation_id, max_messages=10):

    initialise_memory()

    connection = get_connection()

    try:
        rows = connection.execute("""
            SELECT role, content
            FROM (
                SELECT
                    message_id,
                    role,
                    content
                FROM conversation_messages
                WHERE conversation_id = ?
                ORDER BY message_id DESC
                LIMIT ?
            )
            ORDER BY message_id ASC
        """, (conversation_id, max_messages)).fetchall()

        return [
            {
                "role": row["role"],
                "content": row["content"]
            }
            for row in rows
        ]

    finally:
        connection.close()


def clear_conversation(conversation_id):

    connection = get_connection()

    try:
        connection.execute("""
            DELETE FROM conversation_messages
            WHERE conversation_id = ?
        """, (conversation_id,))

        connection.execute("""
            DELETE FROM conversations
            WHERE conversation_id = ?
        """, (conversation_id,))

        connection.commit()

    finally:
        connection.close()


def get_recent_conversations(limit=20):

    initialise_memory()

    connection = get_connection()

    try:
        rows = connection.execute("""
            SELECT
                conversation_id,
                created_at,
                updated_at
            FROM conversations
            ORDER BY updated_at DESC
            LIMIT ?
        """, (limit,)).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:
        connection.close()

if __name__ == "__main__":

    initialise_memory()

    print("CONVERSATION MEMORY INITIALISED")
    print("--------------------------------")
    print(f"SQLite database: {MEMORY_DB}")
