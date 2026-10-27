from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func
from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    @staticmethod
    def add(db: AsyncSession, jti: str, user_id: int, expires_at: datetime):
        # Caller commits, so rotation (revoke old + add new) is one transaction
        db.add(RefreshToken(jti=jti, user_id=user_id, expires_at=expires_at))

    @staticmethod
    async def get(db: AsyncSession, jti: str) -> RefreshToken | None:
        result = await db.execute(select(RefreshToken).where(RefreshToken.jti == jti))
        return result.scalar_one_or_none()

    @staticmethod
    async def revoke(db: AsyncSession, jti: str):
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.jti == jti, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=func.now())
        )

    @staticmethod
    async def revoke_all_for_user(db: AsyncSession, user_id: int):
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=func.now())
        )
