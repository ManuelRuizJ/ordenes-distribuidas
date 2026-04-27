import time
from fastapi import APIRouter, HTTPException
from app.schemas import RefreshRequest, MessageResponse
from app.utils import decode_token
from app.redis_client import redis_client

router = APIRouter(tags=["authentication"])


async def blacklist_token(token: str, expires_in: int):
    await redis_client.setex(f"blacklist:{token}", expires_in, "1")


@router.post("/logout", response_model=MessageResponse)
async def logout(refresh_data: RefreshRequest):
    try:
        payload = decode_token(refresh_data.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        exp = payload.get("exp")
        if exp:
            expires_in = exp - int(time.time())
            if expires_in > 0:
                await blacklist_token(refresh_data.refresh_token, expires_in)
        return MessageResponse(message="Successfully logged out")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
