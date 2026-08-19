from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.auth.dependencies import get_current_user, require_roles
from app.modules.auth.schemas import (
    AdminCreateUserRequest,
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    UserResponse,
)
from app.modules.auth.store import user_store
from app.modules.auth.tokens import create_access_token


router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


def _auth_response(user: dict) -> AuthResponse:
    return AuthResponse(
        access_token=create_access_token(user),
        user=UserResponse(**user),
    )


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(request: RegisterRequest) -> AuthResponse:
    role = "admin" if user_store.count_users() == 0 else "user"
    try:
        user = user_store.create_user(
            username=request.username,
            password=request.password,
            role=role,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    return _auth_response(user)


@router.post("/login", response_model=AuthResponse)
def login(request: LoginRequest) -> AuthResponse:
    user = user_store.authenticate(request.username, request.password)
    if user is None or not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _auth_response(user)


@router.get("/me", response_model=UserResponse)
def me(current_user: dict = Depends(get_current_user)) -> UserResponse:
    return UserResponse(**current_user)


@router.post("/users", response_model=UserResponse, status_code=201)
def create_user(
    request: AdminCreateUserRequest,
    _admin: dict = Depends(require_roles("admin")),
) -> UserResponse:
    try:
        user = user_store.create_user(
            username=request.username,
            password=request.password,
            role=request.role,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    return UserResponse(**user)
