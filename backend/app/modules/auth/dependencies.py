import hmac
from collections.abc import Callable

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.modules.auth.store import user_store
from app.modules.auth.tokens import TokenError, decode_access_token
from app.shared.config import settings


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired access token.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
    except TokenError as error:
        raise credentials_error from error

    user = user_store.get_by_id(str(payload["sub"]))
    if user is None or not user["is_active"]:
        raise credentials_error

    return user


def require_roles(*roles: str) -> Callable:
    def dependency(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["role"] not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return current_user

    return dependency


def verify_internal_mcp_key(
    x_mcp_internal_key: str = Header(default=""),
) -> None:
    if not hmac.compare_digest(x_mcp_internal_key, settings.mcp_internal_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MCP internal key.",
        )
