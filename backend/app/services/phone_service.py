from datetime import datetime, timezone
import re
from typing import Iterable

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.phone_number import PhoneNumber, CallStatus
from ..schemas.phone_number import PhoneNumberCreate, PhoneNumberStatusUpdate

PHONE_PATTERN = re.compile(r"^09\d{9}$")


def normalize_phone(raw: str) -> str | None:
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("0098"):
        digits = "0" + digits[4:]
    elif digits.startswith("98"):
        digits = "0" + digits[2:]
    elif digits.startswith("+98"):
        digits = "0" + digits[3:]
    if digits.startswith("9") and len(digits) == 10:
        digits = "0" + digits
    if not PHONE_PATTERN.match(digits):
        return None
    return digits


def add_numbers(db: Session, payload: PhoneNumberCreate):
    normalized = [normalize_phone(p) for p in payload.phone_numbers]
    invalid_numbers = [p for p, norm in zip(payload.phone_numbers, normalized) if norm is None]
    valid_numbers = [norm for norm in normalized if norm]
    existing_numbers = set(
        n[0]
        for n in db.execute(select(PhoneNumber.phone_number).where(PhoneNumber.phone_number.in_(valid_numbers)))
    )
    to_insert = [n for n in valid_numbers if n not in existing_numbers]

    for number in to_insert:
        db.add(PhoneNumber(phone_number=number, status=CallStatus.IN_QUEUE))
    db.commit()

    return {
        "inserted": len(to_insert),
        "duplicates": len(valid_numbers) - len(to_insert),
        "invalid": len(invalid_numbers),
        "invalid_samples": invalid_numbers[:5],
    }


def list_numbers(db: Session, status: CallStatus | None = None, search: str | None = None, skip: int = 0, limit: int = 50):
    query = db.query(PhoneNumber)
    if status:
        query = query.filter(PhoneNumber.status == status)
    if search:
        query = query.filter(PhoneNumber.phone_number.ilike(f"%{search}%"))
    return query.order_by(PhoneNumber.created_at.desc()).offset(skip).limit(limit).all()


def update_number_status(db: Session, number_id: int, data: PhoneNumberStatusUpdate) -> PhoneNumber:
    number = db.get(PhoneNumber, number_id)
    if not number:
        raise HTTPException(status_code=404, detail="Number not found")
    number.status = data.status
    number.last_status_change_at = datetime.now(timezone.utc)
    if data.note:
        number.note = data.note
    db.commit()
    db.refresh(number)
    return number


def bulk_reset(db: Session, ids: Iterable[int], status: CallStatus = CallStatus.IN_QUEUE) -> int:
    numbers = db.query(PhoneNumber).filter(PhoneNumber.id.in_(list(ids))).all()
    for num in numbers:
        num.status = status
        num.assigned_at = None
        num.assigned_batch_id = None
    db.commit()
    return len(numbers)
