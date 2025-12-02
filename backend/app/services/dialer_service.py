from datetime import datetime, timezone
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
    number = db.get(PhoneNumber, report.number_id)
    if not number or number.phone_number != report.phone_number:
        raise HTTPException(status_code=404, detail="Number not found or mismatch")

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
