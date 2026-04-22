from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import get_db
from app.models import User
from app.schemas import LoginRequest, TokenResponse
from app.utils import verify_password, create_access_token, create_refresh_token

router = APIRouter(tags=["authentication"])

@router.post("/login", response_model=TokenResponse)
async def login(login_data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where((User.username == login_data.username_or_email) | (User.email == login_data.username_or_email))
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(
        data={"sub": user.id},
        role=user.role.value,
        username=user.username   # ← añadido
    )
    refresh_token = create_refresh_token(
        data={"sub": user.id},
        role=user.role.value
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)