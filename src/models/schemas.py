from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"


class UserRole(str, Enum):
    """Predefined roles from requirements"""

    MECANICO = "mecanico"
    MECANICO_GERENTE = "mecanico_gerente"
    GERENTE = "gerente"
    ADMIN = "admin"


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    email: EmailStr | None = None
    full_name: str
    role: UserRole


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: EmailStr | None = None
    full_name: str
    created_at: datetime
