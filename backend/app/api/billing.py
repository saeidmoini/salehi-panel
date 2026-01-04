from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..api.deps import get_active_admin, get_superuser
from ..core.db import get_db
from ..schemas.billing import BillingInfo, BillingUpdate
from ..services import schedule_service

router = APIRouter()


@router.get("/", response_model=BillingInfo, dependencies=[Depends(get_active_admin)])
def get_billing(db: Session = Depends(get_db)):
    info = schedule_service.get_billing_info(db)
    return BillingInfo(**info)


@router.put("/", response_model=BillingInfo, dependencies=[Depends(get_superuser)])
def update_billing(payload: BillingUpdate, db: Session = Depends(get_db)):
    schedule_service.update_billing(
        db,
        wallet_balance=payload.wallet_balance,
        cost_per_connected=payload.cost_per_connected,
    )
    info = schedule_service.get_billing_info(db)
    return BillingInfo(**info)
