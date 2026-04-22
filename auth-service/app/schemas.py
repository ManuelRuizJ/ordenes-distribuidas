from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
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

""" class OrderResponse(BaseModel):
    order_id: str
    status: str """

""" class OrderStatusResponse(BaseModel):
    order_id: str
    status: str
    reason: str | None = None
    last_update: str | None = None """

class Item(BaseModel):
    sku: str
    qty: int

""" class OrderRequest(BaseModel):
    items: List[Item] """

""" def generate_order_id() -> str:
    import uuid
    return str(uuid.uuid4()) """