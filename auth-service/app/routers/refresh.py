from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.schemas import RefreshRequest, TokenResponse
from app.utils import create_access_token, decode_token
from app.redis_client import redis_client
from jose import JWTError

router = APIRouter(tags=["authentication"])


async def is_token_blacklisted(token: str) -> bool:
    return await redis_client.get(f"blacklist:{token}") is not None


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshRequest, db: AsyncSession = Depends(get_db)
):
    try:
        payload = decode_token(refresh_data.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(401, "Invalid token type")
        # Verificar blacklist en Redis
        if await redis_client.get(f"blacklist:{refresh_data.refresh_token}"):
            raise HTTPException(401, "Token revoked")
        user_id = payload.get("sub")
        role = payload.get("role")
        # Generar nuevo access_token
        new_access_token = create_access_token(data={"sub": user_id}, role=role)
        return TokenResponse(
            access_token=new_access_token, refresh_token=refresh_data.refresh_token
        )
    except JWTError:
        raise HTTPException(401, "Invalid or expired refresh token")
