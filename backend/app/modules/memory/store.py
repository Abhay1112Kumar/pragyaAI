import sqlite3
from pathlib import Path
from threading import RLock


class ConversationMemoryStore:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)

        self._connection = sqlite3.connect(
            self.database_path,
            check_same_thread=False,
        )
        self._connection.row_factory = sqlite3.Row
        self._lock = RLock()
        self._initialize()

    def _initialize(self) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self._connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_conversation_messages_thread
                ON conversation_messages (conversation_id, id)
                """
            )

    def load_messages(
        self,
        conversation_id: str,
        limit: int = 20,
    ) -> list[dict[str, str]]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT role, content
                FROM conversation_messages
                WHERE conversation_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (conversation_id, limit),
            ).fetchall()

        return [
            {"role": row["role"], "content": row["content"]}
            for row in reversed(rows)
        ]

    def append_exchange(
        self,
        conversation_id: str,
        user_message: str,
        assistant_message: str,
    ) -> None:
        with self._lock, self._connection:
            self._connection.executemany(
                """
                INSERT INTO conversation_messages (
                    conversation_id,
                    role,
                    content
                )
                VALUES (?, ?, ?)
                """,
                [
                    (conversation_id, "user", user_message),
                    (conversation_id, "assistant", assistant_message),
                ],
            )

    def clear(self, conversation_id: str) -> int:
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                DELETE FROM conversation_messages
                WHERE conversation_id = ?
                """,
                (conversation_id,),
            )
        return cursor.rowcount


    def stats(self) -> dict[str, int]:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT
                    COUNT(*) AS messages,
                    COUNT(DISTINCT conversation_id) AS conversations
                FROM conversation_messages
                """
            ).fetchone()
        return {
            "messages": int(row["messages"]),
            "conversations": int(row["conversations"]),
        }

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def __del__(self) -> None:
        try:
            self._connection.close()
        except Exception:
            pass


from app.core.config import CONVERSATION_DATABASE_PATH


conversation_memory_store = ConversationMemoryStore(CONVERSATION_DATABASE_PATH)
