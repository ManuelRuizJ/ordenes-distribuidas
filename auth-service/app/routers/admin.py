from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import get_db
from app.models import User, UserRole
from app.schemas import UserResponse, RoleUpdate
from app.dependencies import require_admin

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/users", response_model=list[UserResponse])
async def list_users(
    admin_id: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return [
        UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            created_at=user.created_at.isoformat(),
            role=user.role
        )
        for user in users
    ]

@router.put("/users/{user_id}/role")
async def change_role(
    user_id: str,
    role_update: RoleUpdate,  # ← leer del body
    admin_id: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    user.role = role_update.new_role
    await db.commit()
    return {"message": "Role updated"}