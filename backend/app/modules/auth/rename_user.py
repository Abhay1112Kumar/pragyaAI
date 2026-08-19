import argparse
import sqlite3

from app.core.config import AUTH_DATABASE_PATH


def rename_user(username: str, new_username: str) -> tuple[str, str]:
    current_username = username.strip()
    normalized_new_username = new_username.strip().lower()
    if not normalized_new_username:
        raise ValueError("New username cannot be empty.")

    connection = sqlite3.connect(AUTH_DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        try:
            with connection:
                cursor = connection.execute(
                    """
                    UPDATE users
                    SET username = ?
                    WHERE username = ? COLLATE NOCASE
                    """,
                    (normalized_new_username, current_username),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError("New username is already registered.") from error

        if cursor.rowcount == 0:
            raise ValueError("User was not found.")

        row = connection.execute(
            "SELECT username, role FROM users WHERE username = ? COLLATE NOCASE",
            (normalized_new_username,),
        ).fetchone()
        return row["username"], row["role"]
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Rename a PragyaAI user locally.")
    parser.add_argument("username", help="Current username")
    parser.add_argument("new_username", help="New username")
    args = parser.parse_args()

    try:
        username, role = rename_user(args.username, args.new_username)
    except ValueError as error:
        print(f"User rename failed: {error}")
        return 1

    print(f"User renamed successfully to {username} with role {role}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
