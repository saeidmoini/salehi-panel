from datetime import timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from ..models.user import AdminUser
from ..schemas.auth import LoginRequest
from ..schemas.user import AdminUserCreate, AdminUserUpdate
from ..core.security import verify_password, get_password_hash, create_access_token
from ..core.config import get_settings

settings = get_settings()


def authenticate_user(db: Session, credentials: LoginRequest) -> str:
    user = db.query(AdminUser).filter(AdminUser.username == credentials.username).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    return token


def create_admin_user(db: Session, data: AdminUserCreate) -> AdminUser:
    existing = db.query(AdminUser).filter(AdminUser.username == data.username).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
    hashed = get_password_hash(data.password)
    user = AdminUser(username=data.username, password_hash=hashed, is_active=data.is_active)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_admin_user(db: Session, user_id: int, data: AdminUserUpdate) -> AdminUser:
    user = db.query(AdminUser).filter(AdminUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if data.username:
        user.username = data.username
    if data.password:
        user.password_hash = get_password_hash(data.password)
    if data.is_active is not None:
        user.is_active = data.is_active
    db.commit()
    db.refresh(user)
    return user
