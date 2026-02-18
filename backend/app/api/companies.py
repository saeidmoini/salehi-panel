from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..core.security import get_current_active_user
from ..api.deps import get_superuser
from ..schemas.company import CompanyCreate, CompanyUpdate, CompanyOut, CompanyDeleteRequest
from ..models.company import Company
from ..models.user import AdminUser
from ..models.schedule import ScheduleConfig, ScheduleWindow
from ..models.call_result import CallResult
from ..models.scenario import Scenario
from ..models.outbound_line import OutboundLine
from ..models.phone_number import PhoneNumber

router = APIRouter()


@router.get("/", response_model=list[CompanyOut])
def list_companies(db: Session = Depends(get_db), _: AdminUser = Depends(get_superuser)):
    """List all companies (superuser only)"""
    return db.query(Company).all()


@router.get("/{company_name}", response_model=CompanyOut)
def get_company(
    company_name: str,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_active_user),
):
    """Get company by name if user has access"""
    company = db.query(Company).filter(Company.name == company_name).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if not current_user.is_superuser and current_user.company_id != company.id:
        raise HTTPException(status_code=403, detail="Access denied to this company")
    return company


@router.post("/", response_model=CompanyOut)
def create_company(payload: CompanyCreate, db: Session = Depends(get_db), _: AdminUser = Depends(get_superuser)):
    """Create a new company (superuser only)"""
    existing = db.query(Company).filter(Company.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Company name already exists")

    company = Company(
        name=payload.name,
        display_name=payload.display_name,
        is_active=payload.is_active,
        settings=payload.settings,
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@router.put("/{company_id}", response_model=CompanyOut)
def update_company(
    company_id: int,
    payload: CompanyUpdate,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_superuser),
):
    """Update company (superuser only)"""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if payload.name is not None and payload.name != company.name:
        existing = db.query(Company).filter(Company.name == payload.name, Company.id != company_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Company name already exists")
        company.name = payload.name
    if payload.display_name is not None:
        company.display_name = payload.display_name
    if payload.is_active is not None:
        company.is_active = payload.is_active
    if payload.settings is not None:
        company.settings = payload.settings

    db.commit()
    db.refresh(company)
    return company


@router.delete("/{company_id}")
def delete_company(
    company_id: int,
    payload: CompanyDeleteRequest,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_superuser),
):
    """Hard delete company data (superuser only), while preserving global numbers."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if payload.confirm_name != company.name:
        raise HTTPException(status_code=400, detail="Company name confirmation does not match")

    # Safety: never delete the currently logged-in superuser.
    if current_user.company_id == company_id:
        current_user.company_id = None

    # 1) Delete company-bound call history and detach shared-number back reference.
    db.query(CallResult).filter(CallResult.company_id == company_id).delete(synchronize_session=False)
    db.query(PhoneNumber).filter(PhoneNumber.last_called_company_id == company_id).update(
        {PhoneNumber.last_called_company_id: None},
        synchronize_session=False,
    )

    # 2) Remove company-owned scenarios/lines.
    scenario_ids = [row[0] for row in db.query(Scenario.id).filter(Scenario.company_id == company_id).all()]
    if scenario_ids:
        db.query(Scenario).filter(Scenario.id.in_(scenario_ids)).delete(synchronize_session=False)

    line_ids = [row[0] for row in db.query(OutboundLine.id).filter(OutboundLine.company_id == company_id).all()]
    if line_ids:
        db.query(OutboundLine).filter(OutboundLine.id.in_(line_ids)).delete(synchronize_session=False)

    # 3) Remove company-specific schedule/billing config.
    db.query(ScheduleWindow).filter(ScheduleWindow.company_id == company_id).delete(synchronize_session=False)
    db.query(ScheduleConfig).filter(ScheduleConfig.company_id == company_id).delete(synchronize_session=False)

    # 4) Delete users belonging to this company; keep superusers and detach them.
    db.query(AdminUser).filter(AdminUser.company_id == company_id, AdminUser.is_superuser == True).update(
        {AdminUser.company_id: None},
        synchronize_session=False,
    )
    db.query(AdminUser).filter(AdminUser.company_id == company_id, AdminUser.is_superuser == False).delete(
        synchronize_session=False
    )

    # 5) Finally delete the company row itself.
    db.delete(company)
    db.commit()
    return {"deleted": True, "id": company_id, "name": company.name}
