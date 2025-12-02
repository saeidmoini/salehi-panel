from datetime import datetime
from pydantic import BaseModel


class AdminUserBase(BaseModel):
    username: str
    is_active: bool = True


class AdminUserCreate(AdminUserBase):
    password: str


class AdminUserUpdate(BaseModel):
    username: str | None = None
    password: str | None = None
    is_active: bool | None = None


class AdminUserOut(BaseModel):
    id: int
    username: str
    is_active: bool
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True
