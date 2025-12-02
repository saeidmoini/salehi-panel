from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..api.deps import get_active_admin
from ..schemas.user import AdminUserCreate, AdminUserUpdate, AdminUserOut
from ..services import auth_service
from ..models.user import AdminUser

router = APIRouter(dependencies=[Depends(get_active_admin)])


@router.get("/", response_model=list[AdminUserOut])
def list_admins(db: Session = Depends(get_db)):
    return db.query(AdminUser).all()


@router.post("/", response_model=AdminUserOut)
def create_admin(payload: AdminUserCreate, db: Session = Depends(get_db)):
    return auth_service.create_admin_user(db, payload)


@router.put("/{user_id}", response_model=AdminUserOut)
def update_admin(user_id: int, payload: AdminUserUpdate, db: Session = Depends(get_db)):
    return auth_service.update_admin_user(db, user_id, payload)
