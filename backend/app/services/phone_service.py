import io
from datetime import datetime, timezone, date
import re
from typing import Iterable, Sequence

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.dialects.postgresql import insert

from ..models.phone_number import PhoneNumber, CallStatus
from ..models.call_attempt import CallAttempt
from ..models.user import AdminUser, UserRole
from ..schemas.phone_number import (
    PhoneNumberCreate,
    PhoneNumberStatusUpdate,
    PhoneNumberBulkAction,
    PhoneNumberBulkResult,
    PhoneNumberExportRequest,
)
from openpyxl import Workbook

PHONE_PATTERN = re.compile(r"^09\d{9}$")
MUTABLE_STATUSES = {
    CallStatus.IN_QUEUE,
    CallStatus.MISSED,
    CallStatus.BUSY,
    CallStatus.POWER_OFF,
    CallStatus.BANNED,
}


def _require_admin(user: AdminUser):
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admins only")


def _ensure_mutable_status(number: PhoneNumber, current_user: AdminUser):
    if current_user.is_superuser:
        return
    if number.status not in MUTABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only numbers in IN_QUEUE, MISSED, BUSY, POWER_OFF, or BANNED can be changed",
        )


def _ensure_can_access(number: PhoneNumber, current_user: AdminUser):
    if current_user.is_superuser:
        return
    if current_user.role == UserRole.AGENT and number.assigned_agent_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for this number")


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


def add_numbers(db: Session, payload: PhoneNumberCreate, current_user: AdminUser):
    _require_admin(current_user)
    normalized = [normalize_phone(p) for p in payload.phone_numbers]
    invalid_numbers = [p for p, norm in zip(payload.phone_numbers, normalized) if norm is None]

    # Keep first occurrence of each valid number to avoid duplicate work in one batch
    seen: set[str] = set()
    unique_valid: list[str] = []
    for norm in normalized:
        if not norm:
            continue
        if norm in seen:
            continue
        seen.add(norm)
        unique_valid.append(norm)

    inserted = 0
    if unique_valid:
        stmt = (
            insert(PhoneNumber)
            .values([{"phone_number": n, "status": CallStatus.IN_QUEUE} for n in unique_valid])
            .on_conflict_do_nothing(index_elements=[PhoneNumber.phone_number])
        )
        result = db.execute(stmt)
        inserted = result.rowcount or 0
        db.commit()

    return {
        "inserted": inserted,
        "duplicates": len(unique_valid) - inserted,
        "invalid": len(invalid_numbers),
        "invalid_samples": invalid_numbers[:5],
    }


def list_numbers(
    db: Session,
    current_user: AdminUser,
    status: CallStatus | None = None,
    search: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    skip: int = 0,
    limit: int = 50,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    agent_id: int | None = None,
):
    query = db.query(PhoneNumber).options(joinedload(PhoneNumber.assigned_agent))
    if current_user.role == UserRole.AGENT:
        query = query.filter(PhoneNumber.assigned_agent_id == current_user.id)
    elif agent_id:
        query = query.filter(PhoneNumber.assigned_agent_id == agent_id)
    if status:
        query = query.filter(PhoneNumber.status == status)
    if start_date:
        query = query.filter(
            PhoneNumber.created_at >= datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
        )
    if end_date:
        query = query.filter(
            PhoneNumber.created_at <= datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)
        )
    if search:
        query = (
            query.outerjoin(AdminUser, PhoneNumber.assigned_agent_id == AdminUser.id)
            .filter(
                (PhoneNumber.phone_number.ilike(f"%{search}%"))
                | (AdminUser.username.ilike(f"%{search}%"))
                | (AdminUser.first_name.ilike(f"%{search}%"))
                | (AdminUser.last_name.ilike(f"%{search}%"))
                | (AdminUser.phone_number.ilike(f"%{search}%"))
            )
        )

    sort_map = {
        "created_at": PhoneNumber.created_at,
        "last_attempt_at": PhoneNumber.last_attempt_at,
        "status": PhoneNumber.status,
    }
    column = sort_map.get(sort_by, PhoneNumber.created_at)
    if sort_order == "asc":
        query = query.order_by(column.asc().nulls_last())
    else:
        query = query.order_by(column.desc().nulls_last())

    return query.offset(skip).limit(limit).all()


def count_numbers(
    db: Session,
    current_user: AdminUser,
    status: CallStatus | None = None,
    search: str | None = None,
    agent_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> int:
    query = db.query(func.count(PhoneNumber.id))
    if current_user.role == UserRole.AGENT:
        query = query.filter(PhoneNumber.assigned_agent_id == current_user.id)
    elif agent_id:
        query = query.filter(PhoneNumber.assigned_agent_id == agent_id)
    if status:
        query = query.filter(PhoneNumber.status == status)
    if start_date:
        query = query.filter(
            PhoneNumber.created_at >= datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
        )
    if end_date:
        query = query.filter(
            PhoneNumber.created_at <= datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)
        )
    if search:
        query = (
            query.outerjoin(AdminUser, PhoneNumber.assigned_agent_id == AdminUser.id)
            .filter(
                (PhoneNumber.phone_number.ilike(f"%{search}%"))
                | (AdminUser.username.ilike(f"%{search}%"))
                | (AdminUser.first_name.ilike(f"%{search}%"))
                | (AdminUser.last_name.ilike(f"%{search}%"))
                | (AdminUser.phone_number.ilike(f"%{search}%"))
            )
        )
    return query.scalar() or 0


def update_number_status(db: Session, number_id: int, data: PhoneNumberStatusUpdate, current_user: AdminUser) -> PhoneNumber:
    number = db.get(PhoneNumber, number_id)
    if not number:
        raise HTTPException(status_code=404, detail="Number not found")
    _ensure_can_access(number, current_user)
    _ensure_mutable_status(number, current_user)
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
        num.total_attempts = 0
        num.last_attempt_at = None
        num.last_status_change_at = datetime.now(timezone.utc)
    db.commit()
    return len(numbers)


def delete_number(db: Session, number_id: int, current_user: AdminUser) -> None:
    number = db.get(PhoneNumber, number_id)
    if not number:
        raise HTTPException(status_code=404, detail="Number not found")
    _ensure_can_access(number, current_user)
    _ensure_mutable_status(number, current_user)
    db.query(CallAttempt).filter(CallAttempt.phone_number_id == number_id).delete(synchronize_session=False)
    db.delete(number)
    db.commit()


def reset_number(db: Session, number_id: int, current_user: AdminUser) -> PhoneNumber:
    number = db.get(PhoneNumber, number_id)
    if not number:
        raise HTTPException(status_code=404, detail="Number not found")
    _ensure_can_access(number, current_user)
    _ensure_mutable_status(number, current_user)
    number.status = CallStatus.IN_QUEUE
    number.assigned_at = None
    number.assigned_batch_id = None
    number.assigned_agent_id = None
    number.total_attempts = 0
    number.last_attempt_at = None
    number.last_status_change_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(number)
    return number


def _build_query(
    db: Session,
    current_user: AdminUser,
    select_all: bool,
    ids: Sequence[int],
    filter_status: CallStatus | None,
    search: str | None,
    excluded_ids: Sequence[int],
    agent_id: int | None = None,
    require_mutable: bool = False,
    start_date: date | None = None,
    end_date: date | None = None,
):
    query = db.query(PhoneNumber)
    if current_user.role == UserRole.AGENT:
        query = query.filter(PhoneNumber.assigned_agent_id == current_user.id)
    elif agent_id:
        query = query.filter(PhoneNumber.assigned_agent_id == agent_id)
    if filter_status:
        query = query.filter(PhoneNumber.status == filter_status)
    if search:
        query = query.filter(PhoneNumber.phone_number.ilike(f"%{search}%"))
    if start_date:
        query = query.filter(
            PhoneNumber.created_at >= datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
        )
    if end_date:
        query = query.filter(
            PhoneNumber.created_at <= datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)
        )
    if require_mutable and not current_user.is_superuser:
        query = query.filter(PhoneNumber.status.in_(MUTABLE_STATUSES))
    if select_all:
        if excluded_ids:
            query = query.filter(~PhoneNumber.id.in_(excluded_ids))
    else:
        query = query.filter(PhoneNumber.id.in_(ids))
    return query


def bulk_action(db: Session, payload: PhoneNumberBulkAction, current_user: AdminUser) -> PhoneNumberBulkResult:
    if not payload.select_all and not payload.ids:
        raise HTTPException(status_code=400, detail="No numbers selected")

    base_query = _build_query(
        db,
        current_user=current_user,
        select_all=payload.select_all,
        ids=payload.ids,
        filter_status=payload.filter_status,
        search=payload.search,
        excluded_ids=payload.excluded_ids,
        agent_id=payload.agent_id,
        start_date=_parse_iso_date(payload.start_date),
        end_date=_parse_iso_date(payload.end_date),
    )
    mutable_query = _build_query(
        db,
        current_user=current_user,
        select_all=payload.select_all,
        ids=payload.ids,
        filter_status=payload.filter_status,
        search=payload.search,
        excluded_ids=payload.excluded_ids,
        require_mutable=True,
        agent_id=payload.agent_id,
        start_date=_parse_iso_date(payload.start_date),
        end_date=_parse_iso_date(payload.end_date),
    )

    result = PhoneNumberBulkResult()

    total_selected = base_query.count()
    if total_selected == 0:
        return result

    def _require_mutable_selection():
        if current_user.is_superuser:
            return
        mutable_count = mutable_query.count()
        if mutable_count != total_selected:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only numbers in IN_QUEUE, MISSED, BUSY, POWER_OFF, or BANNED can be changed",
            )

    if payload.action == "delete":
        _require_mutable_selection()
        id_subquery = mutable_query.with_entities(PhoneNumber.id)
        db.query(CallAttempt).filter(CallAttempt.phone_number_id.in_(id_subquery)).delete(synchronize_session=False)
        result.deleted = mutable_query.delete(synchronize_session=False)
        db.commit()
        return result

    if payload.action == "reset":
        _require_mutable_selection()
        now = datetime.now(timezone.utc)
        result.reset = (
            mutable_query.update(
                {
                    PhoneNumber.status: CallStatus.IN_QUEUE,
                    PhoneNumber.assigned_at: None,
                    PhoneNumber.assigned_batch_id: None,
                    PhoneNumber.assigned_agent_id: None,
                    PhoneNumber.total_attempts: 0,
                    PhoneNumber.last_attempt_at: None,
                    PhoneNumber.last_status_change_at: now,
                },
                synchronize_session=False,
            )
            or 0
        )
        db.commit()
        return result

    if payload.action == "update_status":
        if not payload.status:
            raise HTTPException(status_code=400, detail="status is required for update_status action")
        _require_mutable_selection()
        now = datetime.now(timezone.utc)
        updates = {
            PhoneNumber.status: payload.status,
            PhoneNumber.last_status_change_at: now,
        }
        if payload.note is not None:
            updates[PhoneNumber.note] = payload.note
        result.updated = mutable_query.update(updates, synchronize_session=False) or 0
        db.commit()
        return result

    raise HTTPException(status_code=400, detail="Unsupported action")


def export_numbers(db: Session, payload: PhoneNumberExportRequest, current_user: AdminUser) -> io.BytesIO:
    if not payload.select_all and not payload.ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No numbers selected")
    start = _parse_iso_date(payload.start_date)
    end = _parse_iso_date(payload.end_date)
    query = _build_query(
        db,
        current_user=current_user,
        select_all=payload.select_all,
        ids=payload.ids,
        filter_status=payload.filter_status,
        search=payload.search,
        excluded_ids=payload.excluded_ids,
        agent_id=payload.agent_id,
        start_date=start,
        end_date=end,
    ).options(joinedload(PhoneNumber.assigned_agent))

    sort_map = {
        "created_at": PhoneNumber.created_at,
        "last_attempt_at": PhoneNumber.last_attempt_at,
        "status": PhoneNumber.status,
    }
    sort_col = sort_map.get(payload.sort_by, PhoneNumber.created_at)
    if payload.sort_order == "asc":
        query = query.order_by(sort_col.asc().nulls_last())
    else:
        query = query.order_by(sort_col.desc().nulls_last())

    numbers = query.all()

    wb = Workbook()
    ws = wb.active
    ws.title = "numbers"
    ws.append(
        [
            "ID",
            "Phone Number",
            "Status",
            "Total Attempts",
            "Last Attempt",
            "Last Status Change",
            "Agent Name",
            "Agent Phone",
            "Last User Message",
        ]
    )

    for num in numbers:
        agent_name = None
        agent_phone = None
        if num.assigned_agent:
            agent_name = " ".join(filter(None, [num.assigned_agent.first_name, num.assigned_agent.last_name])).strip()
            if not agent_name:
                agent_name = num.assigned_agent.username
            agent_phone = num.assigned_agent.phone_number
        ws.append(
            [
                num.id,
                num.phone_number,
                num.status.value if isinstance(num.status, CallStatus) else num.status,
                num.total_attempts,
                num.last_attempt_at.isoformat() if num.last_attempt_at else None,
                num.last_status_change_at.isoformat() if num.last_status_change_at else None,
                agent_name,
                agent_phone,
                num.last_user_message,
            ]
        )

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return stream
def _parse_iso_date(date_str: str | None) -> date | None:
    if not date_str:
        return None
    mapping = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    normalized = date_str.translate(mapping)
    try:
        return datetime.fromisoformat(normalized).date()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format")
