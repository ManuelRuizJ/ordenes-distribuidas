import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import get_db
from app.models import User
from app.schemas import UserCreate, UserResponse, LoginRequest, TokenResponse, RefreshRequest, MessageResponse
from app.utils import generate_user_id, hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from datetime import timedelta
from app.config import settings
import redis.asyncio as redis
from app.redis_client import redis_client

router = APIRouter(prefix="/auth", tags=["authentication"])

async def is_token_blacklisted(token: str) -> bool:
    return await redis_client.get(f"blacklist:{token}") is not None

async def blacklist_token(token: str, expires_in: int):
    await redis_client.setex(f"blacklist:{token}", expires_in, "1")

async def get_current_user_id(token: str = Header(..., alias="Authorization")) -> str:
    if not token.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = token.split(" ")[1]
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Not an access token")
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    # Verificar si username o email ya existen
    result = await db.execute(
        select(User).where((User.username == user_data.username) | (User.email == user_data.email))
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already registered")
    
    new_user = User(
        id=generate_user_id(),
        username=user_data.username,
        email=user_data.email,
        hashed_password=hash_password(user_data.password)
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return UserResponse(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        created_at=new_user.created_at.isoformat()
    )

@router.post("/login", response_model=TokenResponse)
async def login(login_data: LoginRequest, db: AsyncSession = Depends(get_db)):
    # Buscar por username o email
    result = await db.execute(
        select(User).where((User.username == login_data.username_or_email) | (User.email == login_data.username_or_email))
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user.id})
    refresh_token = create_refresh_token(data={"sub": user.id})
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_data: RefreshRequest):
    try:
        payload = decode_token(refresh_data.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        # Verificar si el token está blacklistado
        if await is_token_blacklisted(refresh_data.refresh_token):
            raise HTTPException(status_code=401, detail="Token revoked")
        new_access_token = create_access_token(data={"sub": user_id})
        # Opcional: también se podría rotar refresh token, pero aquí solo devolvemos nuevo access
        return TokenResponse(access_token=new_access_token, refresh_token=refresh_data.refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

@router.post("/logout", response_model=MessageResponse)
async def logout(refresh_data: RefreshRequest):
    try:
        payload = decode_token(refresh_data.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        # Calcular tiempo restante de vida del token
        exp = payload.get("exp")
        if exp:
            import time
            expires_in = exp - int(time.time())
            if expires_in > 0:
                await blacklist_token(refresh_data.refresh_token, expires_in)
        return MessageResponse(message="Successfully logged out")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    
@router.get("/me", response_model=UserResponse)
async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        created_at=user.created_at.isoformat()
    )