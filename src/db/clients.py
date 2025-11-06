from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.auth import Role, User


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    """Get user by username"""
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_roles_by_user_id(db: AsyncSession, user_id: str) -> list[Role]:
    """Get all roles for a specific user"""
    result = await db.execute(
        select(User)
        .options(selectinload(User.roles))  # ← Eager load relationships
        .where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if user:
        return user.roles
    return []


async def create_user(
    db: AsyncSession, username: str, hashed_password: str, full_name: str, email: str | None = None
) -> User:
    """Create a new user"""
    db_user = User(username=username, password_hash=hashed_password, full_name=full_name, email=email)
    db.add(db_user)
    await db.flush()
    await db.refresh(db_user)
    return db_user
