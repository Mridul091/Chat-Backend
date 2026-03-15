from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from sqlalchemy import Select

class UserRepository:

    async def create_user(db: AsyncSession, user: User):
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    
    async def get_user_by_email(db: AsyncSession, email: str):
        result = await db.execute(
            Select(User).where(User.email == email)
        )

        return result.scalar_one_or_none()
    
    async def get_user_by_username(db: AsyncSession, username: str):
        result = await db.execute(
            Select(User).where(User.username == username)
        )

        return result.scalar_one_or_none()
    
    async def get_user_by_id(db: AsyncSession, user_id: int):
        result = await db.execute(
            Select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    