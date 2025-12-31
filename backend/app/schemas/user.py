from datetime import datetime
from pydantic import BaseModel
from ..models.user import UserRole


class AdminUserBase(BaseModel):
    username: str
    is_active: bool = True
    role: UserRole = UserRole.ADMIN
    is_superuser: bool = False
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None


class AdminUserCreate(AdminUserBase):
    password: str


class AdminUserUpdate(BaseModel):
    username: str | None = None
    password: str | None = None
    is_active: bool | None = None
    role: UserRole | None = None
    is_superuser: bool | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None


class AdminUserOut(BaseModel):
    id: int
    username: str
    is_active: bool
    is_superuser: bool
    role: UserRole
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


class AdminSelfUpdate(BaseModel):
    username: str | None = None
    password: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
