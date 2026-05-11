from pydantic import BaseModel, ConfigDict
from datetime import datetime


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    username: str
    full_name: str | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str | None
    role: str
    is_active: bool
    created_at: datetime | None = None


class CreateUserRequest(BaseModel):
    username: str
    password: str
    full_name: str | None = None
    role: str = "doctor"


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class AdminResetPasswordRequest(BaseModel):
    new_password: str
