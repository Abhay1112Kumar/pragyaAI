import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import RLock

from app.core.config import METRICS_DATABASE_PATH


class UsageMetricsStore:
    def __init__(
        self,
        database_path: str | Path = METRICS_DATABASE_PATH,
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
        self._initialize()

    def _initialize(self) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    route TEXT NOT NULL,
                    duration_ms REAL NOT NULL,
                    success INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def record_chat(
        self,
        user_id: str,
        route: str,
        duration_ms: float,
        success: bool,
    ) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO chat_metrics (
                    user_id,
                    route,
                    duration_ms,
                    success,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    route,
                    duration_ms,
                    int(success),
                    datetime.now(UTC).isoformat(),
                ),
            )

    def summary(self) -> dict:
        cutoff = (datetime.now(UTC) - timedelta(hours=24)).isoformat()
        with self._lock:
            totals = self._connection.execute(
                """
                SELECT
                    COUNT(*) AS total_requests,
                    COALESCE(AVG(duration_ms), 0) AS average_latency_ms,
                    COALESCE(AVG(success) * 100, 100) AS success_rate
                FROM chat_metrics
                """
            ).fetchone()
            recent = self._connection.execute(
                """
                SELECT COUNT(*) AS requests_24h
                FROM chat_metrics
                WHERE created_at >= ?
                """,
                (cutoff,),
            ).fetchone()
            routes = self._connection.execute(
                """
                SELECT route, COUNT(*) AS count
                FROM chat_metrics
                GROUP BY route
                ORDER BY count DESC
                """
            ).fetchall()

        return {
            "total_requests": int(totals["total_requests"]),
            "requests_24h": int(recent["requests_24h"]),
            "average_latency_ms": round(
                float(totals["average_latency_ms"]),
                2,
            ),
            "success_rate": round(float(totals["success_rate"]), 2),
            "route_counts": {
                str(row["route"]): int(row["count"])
                for row in routes
            },
        }

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def __del__(self) -> None:
        try:
            self._connection.close()
        except Exception:
            pass


usage_metrics_store = UsageMetricsStore()
