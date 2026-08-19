from typing import Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=128)


class RegisterRequest(LoginRequest):
    pass


class AdminCreateUserRequest(LoginRequest):
    role: Literal["user", "admin"] = "user"


class UserResponse(BaseModel):
    id: str
    username: str
    role: Literal["user", "admin"]
    is_active: bool


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
