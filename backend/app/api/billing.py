from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..api.deps import get_superuser, get_company, get_company_admin
from ..core.db import get_db
from ..schemas.billing import (
    BillingInfo,
    BillingUpdate,
    WalletManualAdjustRequest,
    WalletTopupMatchRequest,
    WalletTransactionOut,
    WalletTransactionListOut,
)
from ..services import schedule_service, wallet_service
from ..models.company import Company
from ..models.user import AdminUser

router = APIRouter()


def _creator_display_name(user: AdminUser | None) -> str | None:
    if not user:
        return None
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    return full_name or user.username


@router.get("/{company_name}/billing", response_model=BillingInfo)
def get_billing(
    company: Company = Depends(get_company),
    user: AdminUser = Depends(get_company_admin),
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


@router.post("/{company_name}/billing/manual-adjust", response_model=WalletTransactionOut, dependencies=[Depends(get_superuser)])
def manual_wallet_adjust(
    payload: WalletManualAdjustRequest,
    company: Company = Depends(get_company),
    user: AdminUser = Depends(get_superuser),
    db: Session = Depends(get_db),
):
    tx = wallet_service.create_manual_adjustment(
        db,
        company_id=company.id,
        amount_toman=payload.amount_toman,
        operation=payload.operation,
        note=payload.note,
        user=user,
    )
    wallet_service.notify_google_sheet_topup(
        company_name=company.name,
        amount_toman=tx.amount_toman,
        transaction_at=tx.transaction_at,
    )
    return WalletTransactionOut(
        id=tx.id,
        amount_toman=tx.amount_toman,
        balance_after=tx.balance_after,
        source=tx.source,
        note=tx.note,
        transaction_at=tx.transaction_at,
        created_at=tx.created_at,
        created_by_user_id=tx.created_by_user_id,
        created_by_username=_creator_display_name(tx.created_by),
    )


@router.post("/{company_name}/billing/topup-match", response_model=WalletTransactionOut)
def topup_match(
    payload: WalletTopupMatchRequest,
    company: Company = Depends(get_company),
    user: AdminUser = Depends(get_company_admin),
    db: Session = Depends(get_db),
):
    tx = wallet_service.match_and_charge_from_bank_sms(
        db,
        company_id=company.id,
        amount_toman=payload.amount_toman,
        jalali_date=payload.jalali_date,
        hour=payload.hour,
        minute=payload.minute,
        user=user,
    )
    wallet_service.notify_google_sheet_topup(
        company_name=company.name,
        amount_toman=tx.amount_toman,
        transaction_at=tx.transaction_at,
    )
    wallet_service.notify_managers_wallet_topup_success(
        db,
        company_name=company.name,
        tx=tx,
    )
    return WalletTransactionOut(
        id=tx.id,
        amount_toman=tx.amount_toman,
        balance_after=tx.balance_after,
        source=tx.source,
        note=tx.note,
        transaction_at=tx.transaction_at,
        created_at=tx.created_at,
        created_by_user_id=tx.created_by_user_id,
        created_by_username=_creator_display_name(tx.created_by),
    )


@router.get("/{company_name}/billing/transactions", response_model=WalletTransactionListOut)
def list_wallet_transactions(
    company: Company = Depends(get_company),
    user: AdminUser = Depends(get_company_admin),
    db: Session = Depends(get_db),
    from_jalali: str | None = Query(default=None, pattern=r"^\d{4}/\d{2}/\d{2}$"),
    to_jalali: str | None = Query(default=None, pattern=r"^\d{4}/\d{2}/\d{2}$"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
):
    items, total = wallet_service.list_wallet_transactions(
        db,
        company_id=company.id,
        from_jalali=from_jalali,
        to_jalali=to_jalali,
        skip=skip,
        limit=limit,
    )
    return WalletTransactionListOut(
        total=total,
        items=[
            WalletTransactionOut(
                id=tx.id,
                amount_toman=tx.amount_toman,
                balance_after=tx.balance_after,
                source=tx.source,
                note=tx.note,
                transaction_at=tx.transaction_at,
                created_at=tx.created_at,
                created_by_user_id=tx.created_by_user_id,
                created_by_username=_creator_display_name(tx.created_by),
            )
            for tx in items
        ],
    )
