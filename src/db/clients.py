from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.authentication.services.password import PasswordService
from src.models.auth import Role, User, user_roles
from src.models.schemas import UserUpdate

# ========== USER FUNCTIONS ==========


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    """Get user by username"""
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession, username: str, hashed_password: str, full_name: str, email: str | None = None
) -> User:
    """Create a new user"""
    db_user = User(username=username, password_hash=hashed_password, full_name=full_name, email=email)
    db.add(db_user)
    await db.flush()
    await db.refresh(db_user)
    return db_user


async def get_roles_by_user_id(db: AsyncSession, user_id: str) -> list[Role]:
    """Get all roles for a specific user"""
    result = await db.execute(select(User).options(selectinload(User.roles)).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user:
        return list(user.roles)
    return []


# ========== ROLE FUNCTIONS ==========


async def get_role_by_name(db: AsyncSession, role_name: str) -> Role | None:
    """Get role by name from the roles table"""
    result = await db.execute(select(Role).where(Role.name == role_name))
    return result.scalar_one_or_none()


async def get_role_by_id(db: AsyncSession, role_id: int) -> Role | None:
    """Get role by ID"""
    result = await db.execute(select(Role).where(Role.id == role_id))
    return result.scalar_one_or_none()


async def create_role(db: AsyncSession, role_name: str) -> Role:
    """Create a new role"""
    role = Role(name=role_name)
    db.add(role)
    await db.flush()
    await db.refresh(role)
    return role


async def get_or_create_role(db: AsyncSession, role_name: str) -> Role:
    """Get role by name or create if it doesn't exist"""
    role = await get_role_by_name(db, role_name)

    if not role:
        role = await create_role(db, role_name)

    return role


async def assign_role_to_user(db: AsyncSession, user_id: str, role_id: int):
    """
    Assign a role to a user by creating an entry in the user_roles junction table.

    Args:
        db: Database session
        user_id: UUID of the user (as string)
        role_id: ID of the role (integer)
    """
    stmt = insert(user_roles).values(user_id=user_id, role_id=role_id)
    await db.execute(stmt)
    await db.flush()


async def remove_role_from_user(db: AsyncSession, user_id: str, role_id: int):
    """Remove a role from a user"""

    stmt = delete(user_roles).where((user_roles.c.user_id == user_id) & (user_roles.c.role_id == role_id))
    await db.execute(stmt)
    await db.flush()


async def get_all_roles(db: AsyncSession) -> list[Role]:
    """Get all available roles"""
    result = await db.execute(select(Role).order_by(Role.name))
    return list(result.scalars().all())


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    """Get user by ID"""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def update_user(
    db: AsyncSession,
    user_id: str,
    user_update: UserUpdate,
    password_service: PasswordService | None = None,
) -> User | None:
    """
    Update user fields in the database.

    Args:
        db: Database session
        user_id: The UUID of the user to update
        user_update: The Pydantic model with update data
        password_service: Service to hash new password if provided
    """

    # 1. Check if user exists
    user = await get_user_by_id(db, user_id)
    if not user:
        return None

    # 2. Prepare update data
    update_data = user_update.model_dump(exclude_unset=True)

    # 3. Handle Password Hashing
    if "password" in update_data and update_data["password"]:
        if not password_service:
            raise ValueError("Password service required for password updates")

        hashed = password_service.hash_password(update_data["password"])
        update_data["password_hash"] = hashed
        del update_data["password"]

    # 4. Remove role from direct user update (handled via role functions)
    if "role" in update_data:
        del update_data["role"]

    if not update_data:
        return user

    # 5. Execute Update
    stmt = update(User).where(User.id == user_id).values(**update_data).execution_options(synchronize_session="fetch")

    await db.execute(stmt)
    await db.commit()
    await db.refresh(user)

    return user


async def delete_user(db: AsyncSession, user_id: str) -> bool:
    """
    Delete a user by ID.

    Returns:
        True if deleted, False if not found.
    """

    stmt = delete(User).where(User.id == user_id)
    result = await db.execute(stmt)
    await db.commit()

    return result.rowcount > 0  # type: ignore
