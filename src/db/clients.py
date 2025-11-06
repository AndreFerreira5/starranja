from sqlalchemy.orm import Session
from src.models.auth import User, Role


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def get_roles_by_user_id(db: Session, user_id: str) -> list[Role]:
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        return user.roles
    return []


def create_user(db: Session, username: str, hashed_password: str, full_name: str, email: Optional[str] = None) -> User:
    db_user = User(
        username=username,
        password_hash=hashed_password,
        full_name=full_name,
        email=email
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
