import hashlib
import json
import math
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import RLock

from langchain_ollama import OllamaEmbeddings

from app.core.config import (
    EMBEDDING_MODEL,
    SEMANTIC_CACHE_DATABASE_PATH,
    SEMANTIC_CACHE_MAX_ENTRIES,
    SEMANTIC_CACHE_THRESHOLD,
    SEMANTIC_CACHE_TTL_DAYS,
)


class SemanticCacheService:
    def __init__(
        self,
        database_path: str | Path = SEMANTIC_CACHE_DATABASE_PATH,
        embed_query: Callable[[str], list[float]] | None = None,
        threshold: float = SEMANTIC_CACHE_THRESHOLD,
        ttl_days: int = SEMANTIC_CACHE_TTL_DAYS,
        max_entries: int = SEMANTIC_CACHE_MAX_ENTRIES,
    ) -> None:
        self.database_path = str(database_path)
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)

        self._connection = sqlite3.connect(
            self.database_path,
            check_same_thread=False,
        )
        self._connection.row_factory = sqlite3.Row
        self._lock = RLock()
        self.threshold = threshold
        self.ttl_days = ttl_days
        self.max_entries = max_entries
        self._embed_query = embed_query or OllamaEmbeddings(
            model=EMBEDDING_MODEL,
        ).embed_query
        self._initialize()

    def _initialize(self) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS semantic_cache_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    namespace TEXT NOT NULL,
                    prompt_hash TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_accessed TEXT NOT NULL,
                    hit_count INTEGER NOT NULL DEFAULT 0,
                    UNIQUE (namespace, prompt_hash)
                )
                """
            )
            self._connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_semantic_cache_namespace
                ON semantic_cache_entries (namespace, created_at)
                """
            )

    def get(self, prompt: str, namespace: str) -> str | None:
        embedding = self._embed_query(prompt)
        cutoff = (
            datetime.now(UTC) - timedelta(days=self.ttl_days)
        ).isoformat()

        with self._lock:
            rows = self._connection.execute(
                """
                SELECT id, embedding, answer
                FROM semantic_cache_entries
                WHERE namespace = ? AND created_at >= ?
                """,
                (namespace, cutoff),
            ).fetchall()

        best_row = None
        best_similarity = -1.0

        for row in rows:
            stored_embedding = json.loads(row["embedding"])
            similarity = self._cosine_similarity(
                embedding,
                stored_embedding,
            )
            if similarity > best_similarity:
                best_similarity = similarity
                best_row = row

        if best_row is None or best_similarity < self.threshold:
            return None

        with self._lock, self._connection:
            self._connection.execute(
                """
                UPDATE semantic_cache_entries
                SET last_accessed = ?, hit_count = hit_count + 1
                WHERE id = ?
                """,
                (datetime.now(UTC).isoformat(), best_row["id"]),
            )

        return str(best_row["answer"])

    def put(self, prompt: str, namespace: str, answer: str) -> None:
        embedding = self._embed_query(prompt)
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        now = datetime.now(UTC).isoformat()

        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO semantic_cache_entries (
                    namespace,
                    prompt_hash,
                    prompt,
                    embedding,
                    answer,
                    created_at,
                    last_accessed
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(namespace, prompt_hash) DO UPDATE SET
                    embedding = excluded.embedding,
                    answer = excluded.answer,
                    created_at = excluded.created_at,
                    last_accessed = excluded.last_accessed
                """,
                (
                    namespace,
                    prompt_hash,
                    prompt,
                    json.dumps(embedding),
                    answer,
                    now,
                    now,
                ),
            )
            self._connection.execute(
                """
                DELETE FROM semantic_cache_entries
                WHERE id IN (
                    SELECT id
                    FROM semantic_cache_entries
                    ORDER BY last_accessed DESC
                    LIMIT -1 OFFSET ?
                )
                """,
                (self.max_entries,),
            )

    def _cosine_similarity(
        self,
        first: list[float],
        second: list[float],
    ) -> float:
        if not first or len(first) != len(second):
            return -1.0

        dot_product = sum(a * b for a, b in zip(first, second))
        first_norm = math.sqrt(sum(value * value for value in first))
        second_norm = math.sqrt(sum(value * value for value in second))

        if not first_norm or not second_norm:
            return -1.0

        return dot_product / (first_norm * second_norm)


    def stats(self) -> dict[str, int]:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT
                    COUNT(*) AS entries,
                    COALESCE(SUM(hit_count), 0) AS hits
                FROM semantic_cache_entries
                """
            ).fetchone()
        return {
            "entries": int(row["entries"]),
            "hits": int(row["hits"]),
        }

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def __del__(self) -> None:
        try:
            self._connection.close()
        except Exception:
            pass


semantic_cache_service = SemanticCacheService()
