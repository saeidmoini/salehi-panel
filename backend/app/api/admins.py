from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..api.deps import get_active_admin, get_company, get_company_user
from ..schemas.user import AdminUserCreate, AdminUserUpdate, AdminUserOut
from ..services import auth_service
from ..models.user import AdminUser
from ..models.company import Company

router = APIRouter()


@router.get("/{company_name}/admins", response_model=list[AdminUserOut], dependencies=[Depends(get_active_admin)])
def list_admins(
    company: Company = Depends(get_company),
    user: AdminUser = Depends(get_company_user),
    db: Session = Depends(get_db),
):
    """List all users for a company"""
    users = db.query(AdminUser).filter(
        AdminUser.company_id == company.id,
        AdminUser.is_superuser == False,
    ).all()
    # Add company_name to each user
    for u in users:
        u.company_name = company.name
    return users


@router.post("/{company_name}/admins", response_model=AdminUserOut, dependencies=[Depends(get_active_admin)])
def create_admin(
    payload: AdminUserCreate,
    company: Company = Depends(get_company),
    user: AdminUser = Depends(get_company_user),
    db: Session = Depends(get_db),
):
    """Create a new user for a company"""
    # Override company_id from path parameter
    payload.company_id = company.id
    payload.is_superuser = False
    new_user = auth_service.create_admin_user(db, payload)
    new_user.company_name = company.name
    return new_user


@router.put("/{company_name}/admins/{user_id}", response_model=AdminUserOut, dependencies=[Depends(get_active_admin)])
def update_admin(
    user_id: int,
    payload: AdminUserUpdate,
    company: Company = Depends(get_company),
    user: AdminUser = Depends(get_company_user),
    db: Session = Depends(get_db),
):
    """Update a user (must belong to the company)"""
    if payload.username is not None:
        raise HTTPException(status_code=400, detail="Username cannot be changed from company users page")
    if payload.is_superuser is not None:
        raise HTTPException(status_code=400, detail="Superuser flag cannot be changed from company users page")
    if payload.company_id is not None:
        raise HTTPException(status_code=400, detail="Company assignment cannot be changed from company users page")

    target = db.query(AdminUser).filter(AdminUser.id == user_id).first()
    if not target or target.company_id != company.id:
        raise HTTPException(status_code=404, detail="User not found in this company")
    if target.is_superuser:
        raise HTTPException(status_code=400, detail="Superuser cannot be managed from company users page")
    updated_user = auth_service.update_admin_user(db, user_id, payload)
    updated_user.company_name = company.name
    return updated_user


@router.delete("/{company_name}/admins/{user_id}", dependencies=[Depends(get_active_admin)])
def delete_admin(
    user_id: int,
    company: Company = Depends(get_company),
    user: AdminUser = Depends(get_company_user),
    db: Session = Depends(get_db),
):
    """Delete a user (must belong to the company)"""
    target = db.query(AdminUser).filter(AdminUser.id == user_id).first()
    if not target or target.company_id != company.id:
        raise HTTPException(status_code=404, detail="User not found in this company")
    if target.is_superuser:
        raise HTTPException(status_code=400, detail="Superuser cannot be managed from company users page")
    auth_service.delete_admin_user(db, user_id)
    return {"deleted": True, "id": user_id}
