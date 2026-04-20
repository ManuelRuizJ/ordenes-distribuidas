from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from app.models import UserRole

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: UserRole

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    created_at: str
    role: UserRole

class LoginRequest(BaseModel):
    username_or_email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshRequest(BaseModel):
    refresh_token: str

class MessageResponse(BaseModel):
    message: str

class RoleUpdate(BaseModel):
    new_role: UserRole