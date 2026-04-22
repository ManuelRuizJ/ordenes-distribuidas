from fastapi import HTTPException, Header, Depends
from jose import JWTError, jwt
from app.config import settings

async def get_current_user_id(token: str = Header(..., alias="Authorization")) -> str:
    if not token.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = token.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

async def get_current_user_role(token: str = Header(..., alias="Authorization")) -> str:
    if not token.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = token.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        role = payload.get("role", "user")
        return role
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

async def require_admin(role: str = Depends(get_current_user_role)):
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return role

async def get_username_from_token(token: str = Header(..., alias="Authorization")) -> str:
    if not token.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = token.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        username = payload.get("username")
        if not username:
            raise HTTPException(status_code=401, detail="Username not found in token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")