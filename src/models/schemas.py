from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "Paseto"


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    email: EmailStr | None = None
    full_name: str


class UserResponse(BaseModel):
    id: UUID
    username: str
    email: EmailStr | None = None
    full_name: str
    created_at: datetime

    class Config:
        from_attributes = True
