from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "Paseto"


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    email: Optional[EmailStr] = None
    full_name: str


class UserResponse(BaseModel):
    id: UUID
    username: str
    email: Optional[EmailStr] = None
    full_name: str
    created_at: datetime

    class Config:
        from_attributes = True
