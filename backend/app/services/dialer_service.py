from datetime import datetime, timezone, timedelta
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..models.phone_number import PhoneNumber, CallStatus
from ..models.dialer_batch import DialerBatch
from ..models.call_attempt import CallAttempt
from ..schemas.dialer import DialerReport
from .schedule_service import is_call_allowed, ensure_config, TEHRAN_TZ
from .phone_service import normalize_phone

settings = get_settings()


def fetch_next_batch(db: Session, size: int | None = None):
    config = ensure_config(db)
    now = datetime.now(TEHRAN_TZ)
    allowed, reason, retry_after = is_call_allowed(now, db)
    if not allowed:
        return {
            "call_allowed": False,
            "timezone": settings.timezone,
            "server_time": now,
            "schedule_version": config.version,
            "reason": reason,
            "retry_after_seconds": retry_after,
        }

    requested_size = size or settings.default_batch_size
    requested_size = min(requested_size, settings.max_batch_size)
    if requested_size <= 0:
        requested_size = settings.default_batch_size

    unlock_stale_assignments(db)

    stmt = (
        select(PhoneNumber)
        .where(PhoneNumber.status == CallStatus.IN_QUEUE, PhoneNumber.assigned_at.is_(None))
        .order_by(PhoneNumber.created_at)
        .limit(requested_size)
        .with_for_update(skip_locked=True)
    )

    numbers = db.execute(stmt).scalars().all()
    batch_id = uuid4().hex
    now_utc = datetime.now(timezone.utc)
    for num in numbers:
        num.assigned_at = now_utc
        num.assigned_batch_id = batch_id
    db.add(
        DialerBatch(
            id=batch_id,
            requested_size=requested_size,
            returned_size=len(numbers),
        )
    )
    db.commit()

    return {
        "call_allowed": True,
        "timezone": settings.timezone,
        "server_time": now,
        "schedule_version": config.version,
        "batch": {
            "batch_id": batch_id,
            "size_requested": requested_size,
            "size_returned": len(numbers),
            "numbers": [
                {"id": num.id, "phone_number": num.phone_number}
                for num in numbers
            ],
        },
    }


def report_result(db: Session, report: DialerReport):
    number: PhoneNumber | None = None
    if report.number_id is not None:
        number = db.get(PhoneNumber, report.number_id)
        if not number or number.phone_number != report.phone_number:
            raise HTTPException(status_code=404, detail="Number not found or mismatch")
    else:
        normalized = normalize_phone(report.phone_number)
        if not normalized:
            raise HTTPException(status_code=404, detail="Number not found")
        number = db.query(PhoneNumber).filter(PhoneNumber.phone_number == normalized).first()
        if not number:
            raise HTTPException(status_code=404, detail="Number not found")

    if report.call_allowed is not None:
        config = ensure_config(db)
        if config.enabled != report.call_allowed:
            config.enabled = report.call_allowed
            config.version += 1
        config.disabled_by_dialer = not report.call_allowed

    number.status = report.status
    number.last_attempt_at = report.attempted_at
    number.total_attempts += 1
    number.last_status_change_at = datetime.now(timezone.utc)
    number.assigned_at = None
    number.assigned_batch_id = None
    db.add(
        CallAttempt(
            phone_number_id=number.id,
            status=report.status.value,
            reason=report.reason,
            attempted_at=report.attempted_at,
            created_at=datetime.now(timezone.utc),
        )
    )
    db.commit()
    db.refresh(number)
    return number


def unlock_stale_assignments(db: Session) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.assignment_timeout_minutes)
    stale = (
        db.query(PhoneNumber)
        .filter(
            PhoneNumber.status == CallStatus.IN_QUEUE,
            PhoneNumber.assigned_at.is_not(None),
            PhoneNumber.assigned_at <= cutoff,
        )
        .all()
    )
    for num in stale:
        num.assigned_at = None
        num.assigned_batch_id = None
    if stale:
        db.commit()
    return len(stale)
