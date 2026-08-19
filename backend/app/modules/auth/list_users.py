import sqlite3

from app.core.config import AUTH_DATABASE_PATH


def main() -> int:
    connection = sqlite3.connect(AUTH_DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT username, role, is_active
            FROM users
            ORDER BY created_at, username
            """
        ).fetchall()
    except sqlite3.OperationalError as error:
        print(f"Could not read users: {error}")
        return 1
    finally:
        connection.close()

    if not rows:
        print("No registered users were found.")
        return 0

    print("Registered PragyaAI users:")
    for row in rows:
        status = "active" if row["is_active"] else "inactive"
        print(f"- {row['username']} ({row['role']}, {status})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
