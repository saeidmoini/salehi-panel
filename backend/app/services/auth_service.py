from datetime import timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from ..models.user import AdminUser, UserRole
from ..schemas.auth import LoginRequest
from ..schemas.user import AdminUserCreate, AdminUserUpdate, AdminSelfUpdate
from ..core.security import verify_password, get_password_hash, create_access_token
from ..core.config import get_settings
from .phone_service import normalize_phone

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
    # First admin becomes superuser automatically
    total_admins = db.query(AdminUser).count()
    existing = db.query(AdminUser).filter(AdminUser.username == data.username).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
    normalized_phone = None
    if data.phone_number:
        normalized_phone = normalize_phone(data.phone_number)
        if not normalized_phone:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid phone number")
        phone_taken = (
            db.query(AdminUser)
            .filter(AdminUser.phone_number == normalized_phone)
            .first()
        )
        if phone_taken:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone number already in use")
    hashed = get_password_hash(data.password)
    user = AdminUser(
        username=data.username,
        password_hash=hashed,
        is_active=data.is_active,
        role=data.role or UserRole.ADMIN,
        is_superuser=data.is_superuser or total_admins == 0,
        first_name=data.first_name,
        last_name=data.last_name,
        phone_number=normalized_phone,
        company_id=data.company_id,
        agent_type=data.agent_type,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_admin_user(db: Session, user_id: int, data: AdminUserUpdate) -> AdminUser:
    user = db.query(AdminUser).filter(AdminUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_superuser:
        if data.is_active is not None and data.is_active is False:
            raise HTTPException(status_code=400, detail="Cannot deactivate primary admin")
        if data.role is not None and data.role != UserRole.ADMIN:
            raise HTTPException(status_code=400, detail="Primary admin role cannot be changed")
        if data.is_superuser is not None and data.is_superuser is False:
            raise HTTPException(status_code=400, detail="Primary admin cannot lose superuser status")
    if data.username:
        existing = (
            db.query(AdminUser)
            .filter(AdminUser.username == data.username, AdminUser.id != user_id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
    if data.username:
        user.username = data.username
    if data.password:
        user.password_hash = get_password_hash(data.password)
    if data.role is not None:
        if user.role == UserRole.ADMIN and data.role != UserRole.ADMIN:
            remaining_admins = (
                db.query(AdminUser)
                .filter(AdminUser.role == UserRole.ADMIN, AdminUser.is_active == True, AdminUser.id != user_id)
                .count()
            )
            if remaining_admins == 0:
                raise HTTPException(status_code=400, detail="At least one active admin is required")
        user.role = data.role
    if data.is_active is not None:
        if user.role == UserRole.ADMIN and not data.is_active:
            remaining_admins = (
                db.query(AdminUser)
                .filter(AdminUser.role == UserRole.ADMIN, AdminUser.is_active == True, AdminUser.id != user_id)
                .count()
            )
            if remaining_admins == 0:
                raise HTTPException(status_code=400, detail="At least one active admin is required")
        user.is_active = data.is_active
    if data.is_superuser is not None:
        user.is_superuser = data.is_superuser
    if data.first_name is not None:
        user.first_name = data.first_name
    if data.last_name is not None:
        user.last_name = data.last_name
    if data.phone_number is not None:
        normalized_phone = normalize_phone(data.phone_number) if data.phone_number else None
        if data.phone_number and not normalized_phone:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid phone number")
        existing_phone = (
            db.query(AdminUser)
            .filter(AdminUser.phone_number == normalized_phone, AdminUser.id != user_id)
            .first()
        )
        if existing_phone:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone number already in use")
        user.phone_number = normalized_phone
    if data.company_id is not None:
        user.company_id = data.company_id
    if data.agent_type is not None:
        user.agent_type = data.agent_type
    db.commit()
    db.refresh(user)
    return user


def delete_admin_user(db: Session, user_id: int) -> None:
    user = db.query(AdminUser).filter(AdminUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_superuser:
        raise HTTPException(status_code=400, detail="Primary admin cannot be deleted")
    if user.role == UserRole.ADMIN:
        remaining_admins = (
            db.query(AdminUser)
            .filter(AdminUser.role == UserRole.ADMIN, AdminUser.is_active == True, AdminUser.id != user_id)
            .count()
        )
        if remaining_admins == 0:
            raise HTTPException(status_code=400, detail="At least one active admin is required")
    db.delete(user)
    db.commit()


def list_active_agents(db: Session) -> list[AdminUser]:
    return (
        db.query(AdminUser)
        .filter(AdminUser.role == UserRole.AGENT, AdminUser.is_active == True)
        .order_by(AdminUser.first_name.nullslast(), AdminUser.last_name.nullslast(), AdminUser.id)
        .all()
    )


def update_self(db: Session, user_id: int, data: AdminSelfUpdate) -> AdminUser:
    user = db.query(AdminUser).filter(AdminUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if data.username and data.username != user.username:
        existing = (
            db.query(AdminUser)
            .filter(AdminUser.username == data.username, AdminUser.id != user_id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
        user.username = data.username
    if data.password:
        user.password_hash = get_password_hash(data.password)
    if data.first_name is not None:
        user.first_name = data.first_name
    if data.last_name is not None:
        user.last_name = data.last_name
    if data.phone_number is not None:
        normalized_phone = normalize_phone(data.phone_number) if data.phone_number else None
        if data.phone_number and not normalized_phone:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid phone number")
        existing_phone = (
            db.query(AdminUser)
            .filter(AdminUser.phone_number == normalized_phone, AdminUser.id != user_id)
            .first()
        )
        if existing_phone:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone number already in use")
        user.phone_number = normalized_phone
    db.commit()
    db.refresh(user)
    return user
