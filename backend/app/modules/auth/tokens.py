import base64
import hashlib
import hmac
import json
import time
from typing import Any

from app.shared.config import settings


class TokenError(ValueError):
    pass


def _encode_segment(value: dict[str, Any]) -> str:
    raw = json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _decode_segment(value: str) -> dict[str, Any]:
    padding = "=" * (-len(value) % 4)
    try:
        raw = base64.urlsafe_b64decode(value + padding)
        decoded = json.loads(raw)
    except (ValueError, json.JSONDecodeError) as error:
        raise TokenError("Invalid access token.") from error

    if not isinstance(decoded, dict):
        raise TokenError("Invalid access token.")
    return decoded


def create_access_token(user: dict) -> str:
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user["id"],
        "username": user["username"],
        "role": user["role"],
        "iss": "pragyaai",
        "iat": now,
        "exp": now + settings.auth_token_minutes * 60,
    }
    signing_input = f"{_encode_segment(header)}.{_encode_segment(payload)}"
    signature = hmac.new(
        settings.auth_secret_key.encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=")
    return f"{signing_input}.{encoded_signature.decode('ascii')}"


def decode_access_token(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise TokenError("Invalid access token.")

    signing_input = f"{parts[0]}.{parts[1]}"
    expected_signature = hmac.new(
        settings.auth_secret_key.encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    padding = "=" * (-len(parts[2]) % 4)

    try:
        supplied_signature = base64.urlsafe_b64decode(parts[2] + padding)
    except ValueError as error:
        raise TokenError("Invalid access token.") from error

    if not hmac.compare_digest(expected_signature, supplied_signature):
        raise TokenError("Invalid access token.")

    header = _decode_segment(parts[0])
    payload = _decode_segment(parts[1])
    if header.get("alg") != "HS256" or payload.get("iss") != "pragyaai":
        raise TokenError("Invalid access token.")

    try:
        expires_at = int(payload.get("exp", 0))
    except (TypeError, ValueError) as error:
        raise TokenError("Invalid access token.") from error

    if expires_at <= int(time.time()):
        raise TokenError("Access token has expired.")

    if not payload.get("sub"):
        raise TokenError("Invalid access token.")

    return payload
