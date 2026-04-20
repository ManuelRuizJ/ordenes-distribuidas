from fastapi import APIRouter, HTTPException
from app.schemas import RefreshRequest, TokenResponse
from app.utils import decode_token, create_access_token
from app.redis_client import redis_client

router = APIRouter(tags=["authentication"])

async def is_token_blacklisted(token: str) -> bool:
    return await redis_client.get(f"blacklist:{token}") is not None

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_data: RefreshRequest):
    try:
        payload = decode_token(refresh_data.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        if await is_token_blacklisted(refresh_data.refresh_token):
            raise HTTPException(status_code=401, detail="Token revoked")
        new_access_token = create_access_token(data={"sub": user_id})
        return TokenResponse(access_token=new_access_token, refresh_token=refresh_data.refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")