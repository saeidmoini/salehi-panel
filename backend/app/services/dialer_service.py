from datetime import datetime, timezone, timedelta
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..core.config import get_settings
from ..models.phone_number import PhoneNumber, CallStatus, GlobalStatus
from ..models.dialer_batch import DialerBatch
from ..models.call_result import CallResult, CallDirection
from ..models.dialer_batch_item import DialerBatchItem
from ..models.user import AdminUser, UserRole, AgentType
from ..models.company import Company
from ..models.scenario import Scenario
from ..models.outbound_line import OutboundLine
from ..schemas.dialer import DialerReport
from .schedule_service import is_call_allowed, ensure_config, TEHRAN_TZ, charge_for_connected_call
from .phone_service import normalize_phone, _sync_global_status_from_call_status
from . import auth_service

settings = get_settings()

# CRITICAL: Only these 6 statuses are billable (use bot, charge customer)
BILLABLE_STATUSES = {
    CallStatus.CONNECTED,
    CallStatus.NOT_INTERESTED,
    CallStatus.HANGUP,
    CallStatus.UNKNOWN,
    CallStatus.DISCONNECTED,
    CallStatus.FAILED
}

# NOT billable: MISSED, BUSY, POWER_OFF, INBOUND_CALL, IN_QUEUE, BANNED


def fetch_next_batch(
    db: Session,
    company: Company,
    size: int | None = None,
    active_lines_count: int | None = None,
):
    """
    Fetch next batch for a company with:
    1. Global cooldown: no number called by ANY company in last N days
    2. Company dedup: no number called by THIS company ever
    3. Global status: exclude COMPLAINED and POWER_OFF
    """
    config = ensure_config(db, company_id=company.id)
    now = datetime.now(TEHRAN_TZ)
    allowed, reason, retry_after = is_call_allowed(now, db, company_id=company.id)

    if not allowed:
        return {
            "call_allowed": False,
            "timezone": settings.timezone,
            "server_time": now,
            "schedule_version": config.version,
            "reason": reason,
            "retry_after_seconds": retry_after,
            "active_scenarios": [],
            "outbound_lines": [],
            "inbound_agents": [],
            "outbound_agents": [],
        }

    active_outbound_lines = db.query(OutboundLine).filter(
        OutboundLine.company_id == company.id,
        OutboundLine.is_active == True
    ).all()
    company_active_lines_count = len(active_outbound_lines)
    if active_lines_count is None:
        effective_lines_count = company_active_lines_count
    else:
        # Prevent over-allocation if dialer sends an invalid high value.
        effective_lines_count = min(max(active_lines_count, 0), company_active_lines_count)

    if size is None:
        # DEFAULT_BATCH_SIZE is treated as "per active outbound line".
        requested_size = settings.default_batch_size * effective_lines_count
    else:
        requested_size = size
    requested_size = max(0, requested_size)
    if settings.max_batch_size > 0:
        requested_size = min(requested_size, settings.max_batch_size)

    unlock_stale_assignments(db)

    # Calculate cooldown cutoff
    cooldown_cutoff = datetime.now(timezone.utc) - timedelta(days=settings.call_cooldown_days)

    # OPTIMIZED: Use NOT EXISTS instead of NOT IN for better performance
    # NOT EXISTS works with FOR UPDATE (unlike LEFT JOIN)
    stmt = (
        select(PhoneNumber)
        .where(
            # Global status must be ACTIVE
            PhoneNumber.global_status == GlobalStatus.ACTIVE,
            # Number not assigned to any batch currently
            PhoneNumber.assigned_at.is_(None),
            # Never called by this company - use NOT EXISTS with indexed lookup
            ~select(CallResult.id)
            .where(
                CallResult.phone_number_id == PhoneNumber.id,
                CallResult.company_id == company.id
            )
            .exists(),
            # Global 3-day cooldown (across all companies)
            or_(
                PhoneNumber.last_called_at.is_(None),
                PhoneNumber.last_called_at < cooldown_cutoff
            ),
        )
        .order_by(PhoneNumber.id)
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
            DialerBatchItem(
                batch_id=batch_id,
                company_id=company.id,
                phone_number_id=num.id,
                assigned_at=now_utc,
            )
        )

    db.add(
        DialerBatch(
            id=batch_id,
            requested_size=requested_size,
            returned_size=len(numbers),
        )
    )
    db.commit()

    # Get split agent lists
    inbound_agents = db.query(AdminUser).filter(
        AdminUser.company_id == company.id,
        AdminUser.is_active == True,
        AdminUser.role == UserRole.AGENT,
        AdminUser.agent_type.in_([AgentType.INBOUND, AgentType.BOTH])
    ).all()

    outbound_agents = db.query(AdminUser).filter(
        AdminUser.company_id == company.id,
        AdminUser.is_active == True,
        AdminUser.role == UserRole.AGENT,
        AdminUser.agent_type.in_([AgentType.OUTBOUND, AgentType.BOTH])
    ).all()

    # Get active scenarios
    active_scenarios = db.query(Scenario).filter(
        Scenario.company_id == company.id,
        Scenario.is_active == True
    ).all()
    return {
        "call_allowed": True,
        "timezone": settings.timezone,
        "server_time": now,
        "schedule_version": config.version,
        "active_scenarios": [
            {"id": s.id, "name": s.name, "display_name": s.display_name}
            for s in active_scenarios
        ],
        "outbound_lines": [
            {"id": line.id, "phone_number": line.phone_number, "display_name": line.display_name}
            for line in active_outbound_lines
        ],
        "inbound_agents": [
            {
                "id": agent.id,
                "full_name": " ".join(filter(None, [agent.first_name, agent.last_name])).strip() or agent.username,
                "phone_number": agent.phone_number,
            }
            for agent in inbound_agents
        ],
        "outbound_agents": [
            {
                "id": agent.id,
                "full_name": " ".join(filter(None, [agent.first_name, agent.last_name])).strip() or agent.username,
                "phone_number": agent.phone_number,
            }
            for agent in outbound_agents
        ],
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


def report_result(db: Session, report: DialerReport, company: Company):
    """
    Process call result:
    1. Update number's global last_called fields
    2. Set global_status if POWER_OFF or COMPLAINED
    3. Create CallResult record with company, scenario, line
    4. Charge billing if status is billable
    """
    normalized_phone = normalize_phone(report.phone_number) if report.phone_number else None
    if not normalized_phone and report.number_id is None:
        raise HTTPException(status_code=400, detail="phone_number or number_id is required")

    number: PhoneNumber | None = None
    if report.number_id is not None:
        number = db.get(PhoneNumber, report.number_id)
        if number and normalized_phone and number.phone_number != normalized_phone:
            number = None

    if not number:
        if not normalized_phone:
            raise HTTPException(status_code=404, detail="Number not found")
        number = (
            db.query(PhoneNumber)
            .filter(PhoneNumber.phone_number == normalized_phone)
            .with_for_update(skip_locked=True)
            .first()
        )

    if not number:
        # Auto-create number if it doesn't exist
        try:
            number = PhoneNumber(
                phone_number=normalized_phone,
                global_status=GlobalStatus.ACTIVE,
            )
            db.add(number)
            db.commit()
            db.refresh(number)
        except IntegrityError:
            db.rollback()
            number = (
                db.query(PhoneNumber)
                .filter(PhoneNumber.phone_number == normalized_phone)
                .with_for_update(skip_locked=True)
                .first()
            )
        if not number:
            raise HTTPException(status_code=404, detail="Number not found")

    agent = _resolve_agent(db, report, company)

    # Update schedule config if call_allowed changed
    if report.call_allowed is not None:
        config = ensure_config(db, company_id=company.id)
        if config.enabled != report.call_allowed:
            config.enabled = report.call_allowed
            config.version += 1
        config.disabled_by_dialer = not report.call_allowed

    assigned_batch_snapshot = number.assigned_batch_id

    # Update global tracking on the number
    number.last_called_at = report.attempted_at
    number.last_called_company_id = company.id
    number.assigned_at = None
    number.assigned_batch_id = None

    # Set shared/global status on numbers table for statuses that apply to all companies
    _sync_global_status_from_call_status(number, report.status)

    # Create call result
    call_direction = CallDirection.INBOUND if report.number_id is None else CallDirection.OUTBOUND
    call_result = CallResult(
        phone_number_id=number.id,
        company_id=company.id,
        scenario_id=report.scenario_id,
        outbound_line_id=report.outbound_line_id,
        call_direction=call_direction,
        status=report.status.value,
        reason=report.reason,
        attempted_at=report.attempted_at,
        agent_id=agent.id if agent else None,
        user_message=report.user_message,
    )
    db.add(call_result)
    db.flush()

    now_utc = datetime.now(timezone.utc)
    batch_item = None
    if report.batch_id:
        batch_item = (
            db.query(DialerBatchItem)
            .filter(
                DialerBatchItem.batch_id == report.batch_id,
                DialerBatchItem.company_id == company.id,
                DialerBatchItem.phone_number_id == number.id,
            )
            .order_by(DialerBatchItem.id.desc())
            .first()
        )
    if not batch_item and assigned_batch_snapshot:
        batch_item = (
            db.query(DialerBatchItem)
            .filter(
                DialerBatchItem.batch_id == assigned_batch_snapshot,
                DialerBatchItem.company_id == company.id,
                DialerBatchItem.phone_number_id == number.id,
            )
            .order_by(DialerBatchItem.id.desc())
            .first()
        )
    if not batch_item:
        batch_item = (
            db.query(DialerBatchItem)
            .filter(
                DialerBatchItem.company_id == company.id,
                DialerBatchItem.phone_number_id == number.id,
            )
            .order_by(DialerBatchItem.id.desc())
            .first()
        )
    if not batch_item:
        batch_item = DialerBatchItem(
            batch_id=report.batch_id or assigned_batch_snapshot or f"unknown-{uuid4().hex[:12]}",
            company_id=company.id,
            phone_number_id=number.id,
            assigned_at=report.attempted_at,
        )
        db.add(batch_item)

    batch_item.reported_at = now_utc
    batch_item.report_batch_id = report.batch_id
    batch_item.report_call_result_id = call_result.id
    batch_item.report_attempted_at = report.attempted_at
    batch_item.report_status = report.status.value
    batch_item.report_scenario_id = report.scenario_id
    batch_item.report_outbound_line_id = report.outbound_line_id
    batch_item.report_reason = report.reason

    db.commit()

    # Charge billing only for billable statuses
    if report.status in BILLABLE_STATUSES:
        charge_for_connected_call(db, company_id=company.id, scenario_id=report.scenario_id)

    db.refresh(number)
    return {
        "id": number.id,
        "global_status": number.global_status.value,
        "phone_number": number.phone_number,
    }


def unlock_stale_assignments(db: Session) -> int:
    """Unlock numbers that have been assigned for too long"""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.assignment_timeout_minutes)
    stale = (
        db.query(PhoneNumber)
        .filter(
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


def _resolve_agent(db: Session, report: DialerReport, company: Company) -> AdminUser | None:
    """Resolve agent from report, ensuring they belong to the company"""
    agent: AdminUser | None = None

    if report.agent_id is not None:
        agent = db.get(AdminUser, report.agent_id)
        # Verify agent belongs to this company
        if agent and agent.company_id != company.id:
            agent = None

    normalized_agent_phone = normalize_phone(report.agent_phone) if report.agent_phone else None
    if not agent and normalized_agent_phone:
        agent = (
            db.query(AdminUser)
            .filter(
                AdminUser.phone_number == normalized_agent_phone,
                AdminUser.company_id == company.id
            )
            .first()
        )

    if agent and agent.role != UserRole.AGENT:
        agent = None

    if agent and not agent.is_active:
        raise HTTPException(status_code=400, detail="Agent is inactive")

    return agent
