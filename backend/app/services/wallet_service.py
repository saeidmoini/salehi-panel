from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timezone
from urllib import request
import logging
import json
import re
import jdatetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..models.schedule import ScheduleConfig
from ..models.user import AdminUser
from ..models.wallet import BankIncomingSms, WalletTransaction
from .schedule_service import TEHRAN_TZ, ensure_config

settings = get_settings()
logger = logging.getLogger(__name__)


@dataclass
class ParsedBankSms:
    amount_rial: int
    amount_toman: int
    transaction_at_utc: datetime
    is_credit: bool


PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")


def _to_ascii_digits(value: str) -> str:
    return value.translate(PERSIAN_DIGITS)


def parse_bank_sms(body: str) -> tuple[ParsedBankSms | None, str | None]:
    text = _to_ascii_digits(body or "")
    amount_match = re.search(r"(?m)^\s*([0-9][0-9,]{2,})\s*([+-])\s*$", text)
    if not amount_match:
        return None, "amount_sign_not_found"

    sign = amount_match.group(2)
    amount_rial = int(amount_match.group(1).replace(",", ""))
    amount_toman = amount_rial // 10

    dt_match = re.search(r"(\d{4}/\d{2}/\d{2})-(\d{2}):(\d{2})", text)
    if not dt_match:
        return None, "datetime_not_found"

    jalali_date = dt_match.group(1)
    hour = int(dt_match.group(2))
    minute = int(dt_match.group(3))
    try:
        tx_utc = build_utc_datetime_from_jalali_minute(jalali_date, hour, minute)
    except ValueError:
        return None, "invalid_datetime"

    return ParsedBankSms(
        amount_rial=amount_rial,
        amount_toman=amount_toman,
        transaction_at_utc=tx_utc,
        is_credit=(sign == "+"),
    ), None


def build_utc_datetime_from_jalali_minute(jalali_date: str, hour: int, minute: int) -> datetime:
    date_match = re.fullmatch(r"(\d{4})/(\d{2})/(\d{2})", _to_ascii_digits(jalali_date or ""))
    if not date_match:
        raise ValueError("invalid_jalali_date")
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError("invalid_time")
    jy, jm, jd = map(int, date_match.groups())
    g_date = jdatetime.date(jy, jm, jd).togregorian()
    tehran_dt = datetime.combine(g_date, time(hour=hour, minute=minute), tzinfo=TEHRAN_TZ)
    return tehran_dt.astimezone(timezone.utc)


def jalali_date_range_to_utc(from_jalali: str | None, to_jalali: str | None) -> tuple[datetime | None, datetime | None]:
    start_utc = None
    end_utc = None

    if from_jalali:
        start_utc = build_utc_datetime_from_jalali_minute(from_jalali, 0, 0)

    if to_jalali:
        to_start = build_utc_datetime_from_jalali_minute(to_jalali, 0, 0).astimezone(TEHRAN_TZ)
        end_tehran = to_start.replace(hour=23, minute=59, second=59, microsecond=999999)
        end_utc = end_tehran.astimezone(timezone.utc)

    return start_utc, end_utc


def _manager_numbers() -> list[str]:
    raw = settings.manager_alert_numbers or ""
    return [n.strip() for n in raw.split(",") if n.strip()]


def _forward_sms_to_managers(text: str) -> None:
    numbers = _manager_numbers()
    if not numbers:
        return

    api_key = (settings.melipayamak_api_key or "").strip()
    if not api_key:
        return

    payload = {
        "from": settings.melipayamak_from,
        "to": numbers,
        "text": text,
        "udh": "",
    }
    base_url = (settings.melipayamak_advanced_url or "").rstrip("/")
    endpoint_url = base_url if base_url.endswith(f"/{api_key}") else f"{base_url}/{api_key}"
    req = request.Request(
        endpoint_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=10):
            pass
    except Exception:
        # Forwarding failure should not block SMS ingestion.
        return


def notify_google_sheet_topup(*, company_name: str, amount_toman: int, transaction_at: datetime) -> None:
    webhook_url = (settings.google_sheet_webhook_url or "").strip()
    webhook_token = (settings.google_sheet_webhook_token or "").strip()
    if not webhook_url or not webhook_token:
        return
    if (company_name or "").strip().lower() != "salehi":
        return

    tx_dt = transaction_at
    if tx_dt.tzinfo is None:
        tx_dt = tx_dt.replace(tzinfo=timezone.utc)
    tx_date = tx_dt.astimezone(TEHRAN_TZ).strftime("%Y-%m-%d")

    payload = {
        "token": webhook_token,
        "amount": amount_toman,
        "date": tx_date,
    }
    req = request.Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=settings.google_sheet_webhook_timeout_seconds):
            pass
    except Exception as exc:
        # Webhook is best-effort and must not fail wallet charge.
        logger.warning("Google Sheet webhook failed for company=%s: %s", company_name, exc)


def should_store_bank_sms(parsed: ParsedBankSms | None) -> bool:
    # Only credit (+) bank SMS messages with valid parsed structure are stored for wallet matching.
    return bool(parsed and parsed.is_credit)


def ingest_incoming_sms(db: Session, sender: str, receiver: str | None, body: str) -> BankIncomingSms | None:
    is_bank_sender = sender == settings.bank_sms_sender
    parsed, _parse_error = parse_bank_sms(body) if is_bank_sender else (None, None)

    # Forward every message from bank sender to manager numbers, regardless of parse outcome.
    if is_bank_sender:
        _forward_sms_to_managers(body)

    # Store only valid deposit-format bank SMS records.
    if not is_bank_sender or not should_store_bank_sms(parsed):
        return None

    sms = BankIncomingSms(
        sender=sender,
        receiver=receiver,
        body=body,
        is_bank_sender=True,
        parsed_amount_rial=parsed.amount_rial if parsed else None,
        parsed_amount_toman=parsed.amount_toman if parsed else None,
        parsed_transaction_at=parsed.transaction_at_utc if parsed else None,
        parsed_is_credit=parsed.is_credit if parsed else None,
        parse_error=None,
    )
    db.add(sms)
    db.commit()
    db.refresh(sms)

    return sms


def _apply_wallet_delta(
    db: Session,
    *,
    company_id: int,
    amount_toman: int,
    source: str,
    note: str | None,
    transaction_at: datetime,
    created_by_user_id: int | None,
    bank_sms_id: int | None = None,
) -> WalletTransaction:
    if amount_toman == 0:
        raise HTTPException(status_code=400, detail="Transaction amount cannot be zero")

    cfg = ensure_config(db, company_id=company_id)
    cfg = (
        db.query(ScheduleConfig)
        .filter(ScheduleConfig.id == cfg.id)
        .with_for_update()
        .first()
    )
    if not cfg:
        raise HTTPException(status_code=500, detail="Billing config missing")

    current_balance = cfg.wallet_balance or 0
    new_balance = current_balance + amount_toman
    if new_balance < 0:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance for this deduction")

    if bank_sms_id is not None:
        sms = (
            db.query(BankIncomingSms)
            .filter(BankIncomingSms.id == bank_sms_id)
            .with_for_update()
            .first()
        )
        if not sms:
            raise HTTPException(status_code=404, detail="Bank transaction not found")
        if sms.consumed:
            raise HTTPException(status_code=400, detail="This bank transaction is already used")
        sms.consumed = True
        sms.consumed_at = datetime.now(timezone.utc)

    cfg.wallet_balance = new_balance
    cfg.version += 1
    if new_balance > 0:
        cfg.disabled_by_dialer = False

    tx = WalletTransaction(
        company_id=company_id,
        amount_toman=amount_toman,
        balance_after=new_balance,
        source=source,
        note=note,
        transaction_at=transaction_at,
        created_by_user_id=created_by_user_id,
        bank_sms_id=bank_sms_id,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def create_manual_adjustment(
    db: Session,
    *,
    company_id: int,
    amount_toman: int,
    operation: str,
    note: str | None,
    user: AdminUser | None,
) -> WalletTransaction:
    if amount_toman <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero")
    if operation not in {"ADD", "SUBTRACT"}:
        raise HTTPException(status_code=400, detail="Invalid operation")

    signed_amount = amount_toman if operation == "ADD" else -amount_toman
    return _apply_wallet_delta(
        db,
        company_id=company_id,
        amount_toman=signed_amount,
        source="MANUAL_ADJUST",
        note=note,
        transaction_at=datetime.now(timezone.utc),
        created_by_user_id=user.id if user else None,
    )


def match_and_charge_from_bank_sms(
    db: Session,
    *,
    company_id: int,
    amount_toman: int,
    jalali_date: str,
    hour: int,
    minute: int,
    user: AdminUser | None,
) -> WalletTransaction:
    if amount_toman <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero")

    try:
        tx_at_utc = build_utc_datetime_from_jalali_minute(jalali_date, hour, minute)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date or time")

    sms = (
        db.query(BankIncomingSms)
        .filter(
            BankIncomingSms.is_bank_sender == True,
            BankIncomingSms.parsed_is_credit == True,
            BankIncomingSms.parsed_amount_toman == amount_toman,
            BankIncomingSms.parsed_transaction_at == tx_at_utc,
            BankIncomingSms.consumed == False,
        )
        .order_by(BankIncomingSms.id.asc())
        .with_for_update()
        .first()
    )
    if not sms:
        raise HTTPException(status_code=404, detail="Matching bank transaction not found")

    return _apply_wallet_delta(
        db,
        company_id=company_id,
        amount_toman=amount_toman,
        source="BANK_MATCH",
        note=f"Matched bank SMS #{sms.id}",
        transaction_at=tx_at_utc,
        created_by_user_id=user.id if user else None,
        bank_sms_id=sms.id,
    )


def list_wallet_transactions(
    db: Session,
    *,
    company_id: int,
    from_jalali: str | None,
    to_jalali: str | None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[WalletTransaction], int]:
    try:
        start_utc, end_utc = jalali_date_range_to_utc(from_jalali, to_jalali)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date filter")
    query = db.query(WalletTransaction).filter(WalletTransaction.company_id == company_id)
    if start_utc:
        query = query.filter(WalletTransaction.transaction_at >= start_utc)
    if end_utc:
        query = query.filter(WalletTransaction.transaction_at <= end_utc)

    total = query.count()
    items = (
        query.order_by(WalletTransaction.transaction_at.desc(), WalletTransaction.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return items, total
