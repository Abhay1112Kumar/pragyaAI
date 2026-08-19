import sqlite3
from pathlib import Path
from threading import RLock
from uuid import uuid4

import bcrypt

from app.core.config import AUTH_DATABASE_PATH


class UserStore:
    def __init__(self, database_path: str | Path = AUTH_DATABASE_PATH) -> None:
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
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('user', 'admin')),
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def count_users(self) -> int:
        with self._lock:
            row = self._connection.execute(
                "SELECT COUNT(*) AS count FROM users"
            ).fetchone()
        return int(row["count"])

    def create_user(
        self,
        username: str,
        password: str,
        role: str = "user",
    ) -> dict:
        normalized_username = username.strip().lower()
        password_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt(),
        ).decode("utf-8")
        user_id = str(uuid4())

        try:
            with self._lock, self._connection:
                self._connection.execute(
                    """
                    INSERT INTO users (
                        id,
                        username,
                        password_hash,
                        role
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (user_id, normalized_username, password_hash, role),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError("Username is already registered.") from error

        return self.get_by_id(user_id)

    def authenticate(self, username: str, password: str) -> dict | None:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT *
                FROM users
                WHERE username = ? COLLATE NOCASE
                """,
                (username.strip(),),
            ).fetchone()

        if row is None or not bcrypt.checkpw(
            password.encode("utf-8"),
            row["password_hash"].encode("utf-8"),
        ):
            return None

        return self._public_user(row)

    def reset_password(self, username: str, new_password: str) -> dict:
        normalized_username = username.strip()
        password_hash = bcrypt.hashpw(
            new_password.encode("utf-8"),
            bcrypt.gensalt(),
        ).decode("utf-8")

        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                UPDATE users
                SET password_hash = ?
                WHERE username = ? COLLATE NOCASE
                """,
                (password_hash, normalized_username),
            )

        if cursor.rowcount == 0:
            raise ValueError("User was not found.")

        row = self._connection.execute(
            "SELECT * FROM users WHERE username = ? COLLATE NOCASE",
            (normalized_username,),
        ).fetchone()
        return self._public_user(row)

    def get_by_id(self, user_id: str) -> dict | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        return self._public_user(row) if row is not None else None

    def _public_user(self, row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "username": row["username"],
            "role": row["role"],
            "is_active": bool(row["is_active"]),
        }

    def stats(self) -> dict[str, int]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT role, COUNT(*) AS count
                FROM users
                WHERE is_active = 1
                GROUP BY role
                """
            ).fetchall()
        role_counts = {row["role"]: int(row["count"]) for row in rows}
        return {
            "total": sum(role_counts.values()),
            "admins": role_counts.get("admin", 0),
            "users": role_counts.get("user", 0),
        }

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def __del__(self) -> None:
        try:
            self._connection.close()
        except Exception:
            pass


user_store = UserStore()
