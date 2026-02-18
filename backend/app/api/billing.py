from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..api.deps import get_superuser, get_company
from ..core.db import get_db
from ..schemas.billing import BillingInfo, BillingUpdate
from ..services import schedule_service
from ..models.company import Company
from ..models.user import AdminUser

router = APIRouter()


@router.get("/{company_name}/billing", response_model=BillingInfo, dependencies=[Depends(get_superuser)])
def get_billing(
    company: Company = Depends(get_company),
    user: AdminUser = Depends(get_superuser),
    db: Session = Depends(get_db),
):
    """Get company billing information"""
    info = schedule_service.get_billing_info(db, company_id=company.id)
    return BillingInfo(**info)


@router.put("/{company_name}/billing", response_model=BillingInfo, dependencies=[Depends(get_superuser)])
def update_billing(
    payload: BillingUpdate,
    company: Company = Depends(get_company),
    db: Session = Depends(get_db),
):
    """Update company billing (superuser only)"""
    schedule_service.update_billing(
        db,
        wallet_balance=payload.wallet_balance,
        cost_per_connected=payload.cost_per_connected,
        company_id=company.id,
    )
    info = schedule_service.get_billing_info(db, company_id=company.id)
    return BillingInfo(**info)
