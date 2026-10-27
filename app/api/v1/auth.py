from fastapi import APIRouter, Depends, HTTPException, Response, Cookie, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.user import User
from app.repositories.user import UserRepository
from app.repositories.refresh_token import RefreshTokenRepository
from app.schemas.user import UserResponse, UserCreate, UserLogin, Token
from app.services.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from app.core.config import settings
from app.core.dependencies import get_current_user
from app.core.limiter import limiter
from app.core.logger import logger

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"
_COOKIE_OPTS = {"httponly": True, "secure": True, "samesite": "strict"}


async def _issue_refresh_token(db: AsyncSession, response: Response, user_id: int):
    """Store a new refresh token and set it as a cookie. Caller commits."""
    token, jti, expires_at = create_refresh_token(user_id)
    RefreshTokenRepository.add(db, jti, user_id, expires_at)
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
        **_COOKIE_OPTS,
    )


def _clear_refresh_cookie(response: Response):
    response.delete_cookie(key=REFRESH_COOKIE, **_COOKIE_OPTS)


@router.post("/register", response_model=UserResponse)
@limiter.limit("5/minute")
async def register(
    request: Request, user_Data: UserCreate, db: AsyncSession = Depends(get_db)
):
    existing_user = await UserRepository.get_user_by_email(db, user_Data.email)
    existing_username = await UserRepository.get_user_by_username(
        db, user_Data.username
    )
    if existing_user or existing_username:
        raise HTTPException(
            status_code=400, detail="Email or username already registered"
        )
    hashed_password = hash_password(user_Data.password)

    new_user = User(
        email=user_Data.email,
        username=user_Data.username,
        password_hash=hashed_password,
    )

    saved_user = await UserRepository.create_user(db, new_user)
    return saved_user


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
async def login(
    request: Request,
    user_data: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    user = await UserRepository.get_user_by_email(db, user_data.email)
    if not user:
        logger.warning("failed_login_attempt", reason="invalid_email")
        raise HTTPException(status_code=400, detail="Invalid email or password")

    if not verify_password(user_data.password, user.password_hash):
        logger.warning(
            "failed_login_attempt", reason="invalid_password", user_id=user.id
        )
        raise HTTPException(status_code=400, detail="Invalid email or password")

    access_token = create_access_token(user.id)
    await _issue_refresh_token(db, response, user.id)
    await db.commit()
    return Token(access_token=access_token, token_type="bearer")


@router.post("/refresh", response_model=Token)
@limiter.limit("10/minute")
async def refresh(
    request: Request,
    response: Response,
    refresh_token: str = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    if refresh_token is None:
        raise HTTPException(status_code=401, detail="Refresh token missing")
    decoded = decode_refresh_token(refresh_token)
    if decoded is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    user_id, jti = decoded

    stored = await RefreshTokenRepository.get(db, jti)
    if stored is None or stored.user_id != user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    if stored.revoked_at is not None:
        # A rotated or logged-out token was presented again: assume it was
        # stolen and end every session for this user.
        logger.warning("refresh_token_reuse_detected", user_id=user_id)
        await RefreshTokenRepository.revoke_all_for_user(db, user_id)
        await db.commit()
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user = await UserRepository.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    # Rotate: the old token is single-use
    await RefreshTokenRepository.revoke(db, jti)
    new_access_token = create_access_token(user.id)
    await _issue_refresh_token(db, response, user.id)
    await db.commit()
    return Token(access_token=new_access_token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/logout")
async def logout(
    response: Response,
    refresh_token: str = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    if refresh_token is not None:
        decoded = decode_refresh_token(refresh_token)
        if decoded is not None:
            await RefreshTokenRepository.revoke(db, decoded[1])
            await db.commit()
    _clear_refresh_cookie(response)
    return {"message": "Logged out"}
