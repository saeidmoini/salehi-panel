import io
from datetime import datetime, timezone, date
import re
from typing import Iterable, Sequence
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import select, func, or_, literal
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.dialects.postgresql import insert

from ..models.phone_number import PhoneNumber, CallStatus, GlobalStatus
from ..models.call_result import CallResult
from ..models.dialer_batch_item import DialerBatchItem
from ..models.user import AdminUser, UserRole
from ..models.company import Company
from ..core.config import get_settings
from ..schemas.phone_number import (
    PhoneNumberCreate,
    PhoneNumberStatusUpdate,
    PhoneNumberBulkAction,
    PhoneNumberBulkResult,
    PhoneNumberExportRequest,
)
from openpyxl import Workbook

PHONE_PATTERN = re.compile(r"^09\d{9}$")
settings = get_settings()
LOCAL_TZ = ZoneInfo(settings.timezone)
MUTABLE_STATUSES = {
    CallStatus.IN_QUEUE,
    CallStatus.MISSED,
    CallStatus.BUSY,
    CallStatus.POWER_OFF,
    CallStatus.BANNED,
}


def _sync_global_status_from_call_status(number: PhoneNumber, status: CallStatus) -> None:
    """
    Sync shared/global status on numbers table for statuses that must apply to all companies.
    """
    if status == CallStatus.POWER_OFF:
        number.global_status = GlobalStatus.POWER_OFF
    elif status == CallStatus.COMPLAINED:
        number.global_status = GlobalStatus.COMPLAINED
    else:
        number.global_status = GlobalStatus.ACTIVE


def _require_admin(user: AdminUser):
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admins only")


def _resolve_company_id(db: Session, current_user: AdminUser, company_name: str | None) -> int | None:
    """Return the target company_id based on user context and optional company_name override."""
    target = current_user.company_id
    if company_name:
        company_obj = db.query(Company).filter(Company.name == company_name).first()
        if not company_obj:
            raise HTTPException(status_code=404, detail="Company not found")
        if not current_user.is_superuser and current_user.company_id != company_obj.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this company")
        target = company_obj.id
    elif not current_user.is_superuser and current_user.company_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not assigned to a company")
    return target


def _latest_status_for_company(db: Session, number_id: int, company_id: int) -> CallStatus:
    latest_call = (
        db.query(CallResult)
        .filter(CallResult.phone_number_id == number_id, CallResult.company_id == company_id)
        .order_by(CallResult.id.desc())
        .first()
    )
    if not latest_call or not latest_call.status:
        return CallStatus.IN_QUEUE
    return CallStatus(latest_call.status)


def _ensure_mutable_for_user(db: Session, number_id: int, company_id: int, current_user: AdminUser) -> None:
    if current_user.is_superuser:
        return
    current_status = _latest_status_for_company(db, number_id, company_id)
    if current_status not in MUTABLE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Status {current_status.value} cannot be changed by non-superuser",
        )


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
            .values([{"phone_number": n} for n in unique_valid])
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


def _apply_latest_call_filters(
    query,
    *,
    status: CallStatus | None,
    target_company_id: int | None,
    agent_id: int | None,
    db: Session,
):
    """Apply latest-call-based filters (status and agent) in one set-based join."""
    if not target_company_id:
        return query

    if status == CallStatus.IN_QUEUE:
        # IN_QUEUE = no call record for this company yet
        query = query.filter(
            ~db.query(CallResult.id).filter(
                CallResult.phone_number_id == PhoneNumber.id,
                CallResult.company_id == target_company_id,
            ).correlate(PhoneNumber).exists()
        )
        # A latest assigned agent cannot exist when there are no call rows.
        if agent_id is not None:
            query = query.filter(False)
        return query

    if status is None and agent_id is None:
        return query

    latest_per_number_subq = (
        db.query(
            CallResult.phone_number_id.label("phone_number_id"),
            func.max(CallResult.id).label("latest_id"),
        )
        .filter(CallResult.company_id == target_company_id)
        .group_by(CallResult.phone_number_id)
        .subquery()
    )
    query = query.join(latest_per_number_subq, latest_per_number_subq.c.phone_number_id == PhoneNumber.id).join(
        CallResult, CallResult.id == latest_per_number_subq.c.latest_id
    )
    if status is not None:
        query = query.filter(CallResult.status == status.value)
    if agent_id is not None:
        query = query.filter(CallResult.agent_id == agent_id)
    return query


def _local_date_start_utc(value: date) -> datetime:
    local_start = datetime(value.year, value.month, value.day, 0, 0, 0, tzinfo=LOCAL_TZ)
    return local_start.astimezone(timezone.utc)


def _local_date_end_utc(value: date) -> datetime:
    local_end = datetime(value.year, value.month, value.day, 23, 59, 59, 999999, tzinfo=LOCAL_TZ)
    return local_end.astimezone(timezone.utc)


def _apply_date_filter(
    query,
    db: Session,
    target_company_id: int | None,
    start_date: date | None,
    end_date: date | None,
):
    if not start_date and not end_date:
        return query

    if target_company_id:
        predicates = [
            CallResult.phone_number_id == PhoneNumber.id,
            CallResult.company_id == target_company_id,
        ]
        if start_date:
            predicates.append(CallResult.attempted_at >= _local_date_start_utc(start_date))
        if end_date:
            predicates.append(CallResult.attempted_at <= _local_date_end_utc(end_date))
        return query.filter(
            db.query(CallResult.id).filter(*predicates).correlate(PhoneNumber).exists()
        )

    if start_date:
        query = query.filter(PhoneNumber.last_called_at >= _local_date_start_utc(start_date))
    if end_date:
        query = query.filter(PhoneNumber.last_called_at <= _local_date_end_utc(end_date))
    return query


def list_numbers(
    db: Session,
    current_user: AdminUser,
    company_name: str | None = None,
    status: CallStatus | None = None,
    global_status: GlobalStatus | None = None,
    search: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    skip: int = 0,
    limit: int = 50,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    agent_id: int | None = None,
):
    target_company_id = _resolve_company_id(db, current_user, company_name)

    numbers = db.query(PhoneNumber)

    if search:
        numbers = numbers.filter(PhoneNumber.phone_number.ilike(f"%{search}%"))
    if global_status is not None:
        numbers = numbers.filter(PhoneNumber.global_status == global_status)

    numbers = _apply_date_filter(numbers, db, target_company_id, start_date, end_date)

    numbers = _apply_latest_call_filters(
        numbers,
        status=status,
        target_company_id=target_company_id,
        agent_id=agent_id,
        db=db,
    )

    # Build sort column — last_attempt_at and status live in call_results
    if sort_by == "last_attempt_at" and target_company_id:
        column = (
            select(func.max(CallResult.attempted_at))
            .where(
                CallResult.phone_number_id == PhoneNumber.id,
                CallResult.company_id == target_company_id,
            )
            .correlate(PhoneNumber)
            .scalar_subquery()
        )
    elif sort_by == "total_attempts" and target_company_id:
        column = (
            select(func.count(CallResult.id))
            .where(
                CallResult.phone_number_id == PhoneNumber.id,
                CallResult.company_id == target_company_id,
            )
            .correlate(PhoneNumber)
            .scalar_subquery()
        )
    elif sort_by == "status" and target_company_id:
        column = (
            select(CallResult.status)
            .where(
                CallResult.phone_number_id == PhoneNumber.id,
                CallResult.company_id == target_company_id,
                CallResult.id == (
                    select(func.max(CallResult.id))
                    .where(
                        CallResult.phone_number_id == PhoneNumber.id,
                        CallResult.company_id == target_company_id,
                    )
                    .correlate(PhoneNumber)
                    .scalar_subquery()
                ),
            )
            .correlate(PhoneNumber)
            .scalar_subquery()
        )
    else:
        sort_map = {"created_at": PhoneNumber.id, "id": PhoneNumber.id, "last_called_at": PhoneNumber.last_called_at}
        column = sort_map.get(sort_by, PhoneNumber.id)

    numbers = numbers.order_by(column.desc().nulls_last() if sort_order == "desc" else column.asc().nulls_last())

    number_list = numbers.offset(skip).limit(limit).all()

    # For each number, enrich with company-specific call data
    if target_company_id and number_list:
        _enrich_with_call_data(db, number_list, target_company_id)

    return number_list


def list_number_history(
    db: Session,
    current_user: AdminUser,
    number_id: int,
    company_name: str | None = None,
):
    target_company_id = _resolve_company_id(db, current_user, company_name)

    number = db.get(PhoneNumber, number_id)
    if not number:
        raise HTTPException(status_code=404, detail="Number not found")

    query = (
        db.query(CallResult)
        .options(
            joinedload(CallResult.agent),
            joinedload(CallResult.scenario),
            joinedload(CallResult.outbound_line),
        )
        .filter(CallResult.phone_number_id == number_id)
    )
    if target_company_id:
        query = query.filter(CallResult.company_id == target_company_id)

    calls = query.order_by(CallResult.id.desc()).all()
    call_result_ids = [c.id for c in calls]
    batch_map: dict[int, DialerBatchItem] = {}
    if call_result_ids:
        batch_rows = (
            db.query(DialerBatchItem)
            .filter(DialerBatchItem.report_call_result_id.in_(call_result_ids))
            .order_by(DialerBatchItem.id.desc())
            .all()
        )
        for row in batch_rows:
            if row.report_call_result_id and row.report_call_result_id not in batch_map:
                batch_map[row.report_call_result_id] = row

    total = len(calls)
    history: list[dict] = []
    for idx, call in enumerate(calls):
        trace = batch_map.get(call.id)
        agent_payload = None
        if call.agent:
            agent_payload = {
                "id": call.agent.id,
                "username": call.agent.username,
                "first_name": call.agent.first_name,
                "last_name": call.agent.last_name,
                "phone_number": call.agent.phone_number,
            }
        history.append(
            {
                "call_result_id": call.id,
                "number_id": number.id,
                "phone_number": number.phone_number,
                "global_status": number.global_status,
                "status": call.status,
                "total_attempts": total - idx,
                "last_attempt_at": call.attempted_at,
                "last_user_message": call.user_message,
                "assigned_agent_id": call.agent_id,
                "assigned_agent": agent_payload,
                "scenario_display_name": call.scenario.display_name if call.scenario else None,
                "outbound_line_display_name": call.outbound_line.display_name if call.outbound_line else None,
                "call_direction": call.call_direction,
                "sent_batch_id": trace.batch_id if trace else None,
                "reported_batch_id": trace.report_batch_id if trace else None,
            }
        )
    return history


def _enrich_with_call_data(db: Session, number_list: list, target_company_id: int):
    """Populate virtual fields on PhoneNumber objects from call_results.
    Orders by id DESC so that when timestamps tie, the most recently inserted row wins.
    """
    number_ids = [n.id for n in number_list]
    all_calls = (
        db.query(CallResult)
        .options(
            joinedload(CallResult.scenario),
            joinedload(CallResult.outbound_line),
        )
        .filter(
            CallResult.phone_number_id.in_(number_ids),
            CallResult.company_id == target_company_id,
        )
        .order_by(CallResult.id.desc())
        .all()
    )
    call_data_map: dict = {}
    call_counts: dict = {}
    for call in all_calls:
        call_counts[call.phone_number_id] = call_counts.get(call.phone_number_id, 0) + 1
        if call.phone_number_id not in call_data_map:
            call_data_map[call.phone_number_id] = call

    for number in number_list:
        latest_call = call_data_map.get(number.id)
        if latest_call:
            number.status = latest_call.status
            number.last_attempt_at = latest_call.attempted_at
            number.last_user_message = latest_call.user_message
            number.assigned_agent_id = latest_call.agent_id
            number.total_attempts = call_counts.get(number.id, 0)
            number.scenario_display_name = latest_call.scenario.display_name if latest_call.scenario else None
            number.outbound_line_display_name = latest_call.outbound_line.display_name if latest_call.outbound_line else None
            number.call_direction = latest_call.call_direction


def count_numbers(
    db: Session,
    current_user: AdminUser,
    company_name: str | None = None,
    status: CallStatus | None = None,
    global_status: GlobalStatus | None = None,
    search: str | None = None,
    agent_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> int:
    target_company_id = _resolve_company_id(db, current_user, company_name)

    query = db.query(func.count(PhoneNumber.id))

    if search:
        query = query.filter(PhoneNumber.phone_number.ilike(f"%{search}%"))
    if global_status is not None:
        query = query.filter(PhoneNumber.global_status == global_status)

    query = _apply_date_filter(query, db, target_company_id, start_date, end_date)

    query = _apply_latest_call_filters(
        query,
        status=status,
        target_company_id=target_company_id,
        agent_id=agent_id,
        db=db,
    )

    return query.scalar() or 0


def update_number_status(db: Session, number_id: int, data: PhoneNumberStatusUpdate, current_user: AdminUser, company_name: str | None = None) -> PhoneNumber:
    """Update the latest call_result status for this number+company."""
    _require_admin(current_user)
    number = db.get(PhoneNumber, number_id)
    if not number:
        raise HTTPException(status_code=404, detail="Number not found")

    target_company_id = _resolve_company_id(db, current_user, company_name)
    _sync_global_status_from_call_status(number, data.status)

    if target_company_id:
        _ensure_mutable_for_user(db, number_id, target_company_id, current_user)
        latest_call = (
            db.query(CallResult)
            .filter(
                CallResult.phone_number_id == number_id,
                CallResult.company_id == target_company_id,
            )
            .order_by(CallResult.id.desc())
            .first()
        )
        if latest_call:
            latest_call.status = data.status
        else:
            db.add(CallResult(
                phone_number_id=number_id,
                company_id=target_company_id,
                status=data.status,
                attempted_at=datetime.now(timezone.utc),
            ))
        db.commit()

    # Refresh virtual fields
    if target_company_id:
        _enrich_with_call_data(db, [number], target_company_id)

    return number


def bulk_reset(db: Session, ids: Iterable[int], status: CallStatus = CallStatus.IN_QUEUE) -> int:
    numbers = db.query(PhoneNumber).filter(PhoneNumber.id.in_(list(ids))).all()
    for num in numbers:
        num.assigned_at = None
        num.assigned_batch_id = None
    db.commit()
    return len(numbers)


def delete_number(db: Session, number_id: int, current_user: AdminUser, company_name: str | None = None) -> None:
    _require_admin(current_user)
    number = db.get(PhoneNumber, number_id)
    if not number:
        raise HTTPException(status_code=404, detail="Number not found")
    target_company_id = _resolve_company_id(db, current_user, company_name)
    if target_company_id:
        _ensure_mutable_for_user(db, number_id, target_company_id, current_user)
    db.query(CallResult).filter(CallResult.phone_number_id == number_id).delete(synchronize_session=False)
    db.delete(number)
    db.commit()


def reset_number(db: Session, number_id: int, current_user: AdminUser, company_name: str | None = None) -> PhoneNumber:
    """Reset a number so it can be re-dialed by this company."""
    _require_admin(current_user)
    number = db.get(PhoneNumber, number_id)
    if not number:
        raise HTTPException(status_code=404, detail="Number not found")

    target_company_id = _resolve_company_id(db, current_user, company_name)
    if target_company_id:
        _ensure_mutable_for_user(db, number_id, target_company_id, current_user)
    # Delete call_results for this company so the dialer picks it up again
    if target_company_id:
        db.query(CallResult).filter(
            CallResult.phone_number_id == number_id,
            CallResult.company_id == target_company_id,
        ).delete(synchronize_session=False)

    number.assigned_at = None
    number.assigned_batch_id = None
    db.commit()
    db.refresh(number)
    return number


def _build_query(
    db: Session,
    current_user: AdminUser,
    select_all: bool,
    ids: Sequence[int],
    filter_status: CallStatus | None,
    filter_global_status: GlobalStatus | None,
    search: str | None,
    excluded_ids: Sequence[int],
    target_company_id: int | None = None,
    agent_id: int | None = None,
    require_mutable: bool = False,
    start_date: date | None = None,
    end_date: date | None = None,
):
    query = db.query(PhoneNumber)

    if search:
        query = query.filter(PhoneNumber.phone_number.ilike(f"%{search}%"))

    query = _apply_date_filter(query, db, target_company_id, start_date, end_date)

    query = _apply_latest_call_filters(
        query,
        status=filter_status,
        target_company_id=target_company_id,
        agent_id=agent_id,
        db=db,
    )
    if filter_global_status is not None:
        query = query.filter(PhoneNumber.global_status == filter_global_status)
    if require_mutable and target_company_id and not current_user.is_superuser:
        # For non-superusers, bulk actions can only touch mutable statuses.
        latest_id_subq = (
            db.query(func.max(CallResult.id))
            .filter(
                CallResult.phone_number_id == PhoneNumber.id,
                CallResult.company_id == target_company_id,
            )
            .correlate(PhoneNumber)
            .scalar_subquery()
        )
        has_any_call = db.query(CallResult.id).filter(
            CallResult.phone_number_id == PhoneNumber.id,
            CallResult.company_id == target_company_id,
        ).correlate(PhoneNumber).exists()
        mutable_real_statuses = [s.value for s in MUTABLE_STATUSES if s != CallStatus.IN_QUEUE]
        has_mutable_latest = db.query(CallResult.id).filter(
            CallResult.id == latest_id_subq,
            CallResult.status.in_(mutable_real_statuses),
        ).correlate(PhoneNumber).exists()
        # IN_QUEUE means no call record for this company yet.
        query = query.filter(or_(~has_any_call, has_mutable_latest))

    if select_all:
        if excluded_ids:
            query = query.filter(~PhoneNumber.id.in_(excluded_ids))
    else:
        query = query.filter(PhoneNumber.id.in_(ids))
    return query


def bulk_action(db: Session, payload: PhoneNumberBulkAction, current_user: AdminUser) -> PhoneNumberBulkResult:
    _require_admin(current_user)
    if not payload.select_all and not payload.ids:
        raise HTTPException(status_code=400, detail="No numbers selected")

    target_company_id = _resolve_company_id(db, current_user, getattr(payload, "company_name", None))

    base_query = _build_query(
        db,
        current_user=current_user,
        select_all=payload.select_all,
        ids=payload.ids,
        filter_status=payload.filter_status,
        filter_global_status=payload.filter_global_status,
        search=payload.search,
        excluded_ids=payload.excluded_ids,
        target_company_id=target_company_id,
        agent_id=payload.agent_id,
        require_mutable=payload.action in {"update_status", "reset", "delete"},
        start_date=_parse_iso_date(payload.start_date),
        end_date=_parse_iso_date(payload.end_date),
    )

    result = PhoneNumberBulkResult()

    total_selected = base_query.count()
    if total_selected == 0:
        return result

    target_ids_subq = base_query.with_entities(PhoneNumber.id.label("id")).subquery()

    if payload.action == "delete":
        db.query(CallResult).filter(
            CallResult.phone_number_id.in_(select(target_ids_subq.c.id))
        ).delete(synchronize_session=False)
        result.deleted = db.query(PhoneNumber).filter(
            PhoneNumber.id.in_(select(target_ids_subq.c.id))
        ).delete(synchronize_session=False)
        db.commit()
        return result

    if payload.action == "reset":
        # Delete call_results for this company → dialer will re-call these numbers
        if target_company_id:
            db.query(CallResult).filter(
                CallResult.phone_number_id.in_(select(target_ids_subq.c.id)),
                CallResult.company_id == target_company_id,
            ).delete(synchronize_session=False)
        result.reset = db.query(PhoneNumber).filter(
            PhoneNumber.id.in_(select(target_ids_subq.c.id))
        ).update(
            {PhoneNumber.assigned_at: None, PhoneNumber.assigned_batch_id: None},
            synchronize_session=False,
        ) or 0
        db.commit()
        return result

    if payload.action == "update_status" and payload.status:
        if target_company_id:
            shared_status = (
                GlobalStatus.POWER_OFF
                if payload.status == CallStatus.POWER_OFF
                else GlobalStatus.COMPLAINED
                if payload.status == CallStatus.COMPLAINED
                else GlobalStatus.ACTIVE
            )
            db.query(PhoneNumber).filter(PhoneNumber.id.in_(select(target_ids_subq.c.id))).update(
                {PhoneNumber.global_status: shared_status},
                synchronize_session=False,
            )

            latest_call_ids_subq = (
                db.query(func.max(CallResult.id).label("id"))
                .join(target_ids_subq, CallResult.phone_number_id == target_ids_subq.c.id)
                .filter(CallResult.company_id == target_company_id)
                .group_by(CallResult.phone_number_id)
                .subquery()
            )

            updated_existing = db.query(CallResult).filter(
                CallResult.id.in_(select(latest_call_ids_subq.c.id))
            ).update(
                {CallResult.status: payload.status},
                synchronize_session=False,
            )

            missing_ids_subq = (
                select(target_ids_subq.c.id)
                .where(
                    ~select(CallResult.id).where(
                        CallResult.phone_number_id == target_ids_subq.c.id,
                        CallResult.company_id == target_company_id,
                    ).exists()
                )
                .subquery()
            )
            insert_result = db.execute(
                insert(CallResult).from_select(
                    ["phone_number_id", "company_id", "status", "attempted_at"],
                    select(
                        missing_ids_subq.c.id,
                        literal(target_company_id),
                        literal(payload.status.value),
                        literal(datetime.now(timezone.utc)),
                    ),
                )
            )
            db.commit()
            result.updated = (updated_existing or 0) + (insert_result.rowcount or 0)
        return result

    raise HTTPException(status_code=400, detail="Unsupported action")


def export_numbers(db: Session, payload: PhoneNumberExportRequest, current_user: AdminUser) -> io.BytesIO:
    _require_admin(current_user)
    if not payload.select_all and not payload.ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No numbers selected")

    target_company_id = _resolve_company_id(db, current_user, getattr(payload, "company_name", None))

    start = _parse_iso_date(payload.start_date)
    end = _parse_iso_date(payload.end_date)
    query = _build_query(
        db,
        current_user=current_user,
        select_all=payload.select_all,
        ids=payload.ids,
        filter_status=payload.filter_status,
        filter_global_status=payload.filter_global_status,
        search=payload.search,
        excluded_ids=payload.excluded_ids,
        target_company_id=target_company_id,
        agent_id=payload.agent_id,
        start_date=start,
        end_date=end,
    )

    # Sort
    if payload.sort_by == "last_attempt_at" and target_company_id:
        sort_col = (
            select(func.max(CallResult.attempted_at))
            .where(CallResult.phone_number_id == PhoneNumber.id, CallResult.company_id == target_company_id)
            .correlate(PhoneNumber)
            .scalar_subquery()
        )
    elif payload.sort_by == "total_attempts" and target_company_id:
        sort_col = (
            select(func.count(CallResult.id))
            .where(CallResult.phone_number_id == PhoneNumber.id, CallResult.company_id == target_company_id)
            .correlate(PhoneNumber)
            .scalar_subquery()
        )
    elif payload.sort_by == "status" and target_company_id:
        sort_col = (
            select(CallResult.status)
            .where(
                CallResult.phone_number_id == PhoneNumber.id,
                CallResult.company_id == target_company_id,
                CallResult.id == (
                    select(func.max(CallResult.id))
                    .where(
                        CallResult.phone_number_id == PhoneNumber.id,
                        CallResult.company_id == target_company_id,
                    )
                    .correlate(PhoneNumber)
                    .scalar_subquery()
                ),
            )
            .correlate(PhoneNumber)
            .scalar_subquery()
        )
    else:
        sort_map = {"created_at": PhoneNumber.id, "id": PhoneNumber.id, "last_called_at": PhoneNumber.last_called_at}
        sort_col = sort_map.get(payload.sort_by, PhoneNumber.id)

    if payload.sort_order == "asc":
        query = query.order_by(sort_col.asc().nulls_last())
    else:
        query = query.order_by(sort_col.desc().nulls_last())

    numbers = query.all()

    # Enrich with call data for export
    if target_company_id and numbers:
        _enrich_with_call_data(db, numbers, target_company_id)

    wb = Workbook()
    ws = wb.active
    ws.title = "numbers"
    ws.append(["شماره", "وضعیت", "تعداد تلاش", "آخرین تلاش", "پیام تماس"])

    for num in numbers:
        ws.append([
            num.phone_number,
            getattr(num, "status", None) or "IN_QUEUE",
            getattr(num, "total_attempts", 0),
            getattr(num, "last_attempt_at", None).isoformat() if getattr(num, "last_attempt_at", None) else None,
            getattr(num, "last_user_message", None),
        ])

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
