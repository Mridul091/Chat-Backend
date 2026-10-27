from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import UserPublic
from app.core.dependencies import get_current_user
from app.core.limiter import limiter

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=UserPublic)
@limiter.limit("60/minute")
async def get_user(
    request: Request,
    user_id: int = Query(..., description="ID of the user to fetch"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = await UserRepository.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/batch", response_model=list[UserPublic])
@limiter.limit("60/minute")
async def get_users_by_ids(
    request: Request,
    user_ids: list[int] = Query(
        ..., max_length=100, description="List of user IDs to fetch"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not user_ids:
        return []
    return await UserRepository.get_users_by_ids(db, user_ids)


@router.get("/lookup", response_model=list[UserPublic])
@limiter.limit("60/minute")
async def lookup_users_by_username(
    request: Request,
    usernames: list[str] = Query(
        ..., max_length=50, description="Usernames to resolve"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Resolve a list of usernames to full user objects (for adding members by name)."""
    if not usernames:
        return []
    return await UserRepository.get_users_by_usernames(db, usernames)
