import argparse
from getpass import getpass

from app.modules.auth.store import user_store


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reset a PragyaAI user's password locally.",
    )
    parser.add_argument("username", help="Username whose password will be reset")
    args = parser.parse_args()

    new_password = getpass("New password: ")
    confirmation = getpass("Confirm new password: ")

    if len(new_password) < 8:
        print("Password must contain at least 8 characters.")
        return 1
    if new_password != confirmation:
        print("Passwords do not match.")
        return 1

    try:
        user = user_store.reset_password(args.username, new_password)
    except ValueError as error:
        print(f"Password reset failed: {error}")
        return 1

    print(f"Password reset successfully for {user['username']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
