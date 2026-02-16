from collections import defaultdict
from datetime import datetime, time, timedelta, date, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..models.phone_number import PhoneNumber, CallStatus
from ..models.call_result import CallResult
from ..models.scenario import Scenario
from ..models.outbound_line import OutboundLine
from ..models.company import Company
from ..schemas.stats import NumbersSummary, StatusShare, AttemptTrendResponse, TimeBucketBreakdown, AttemptSummary
from .schedule_service import TEHRAN_TZ, ensure_config

settings = get_settings()

# Billable statuses (charges wallet)
BILLABLE_STATUSES = {
    CallStatus.CONNECTED,
    CallStatus.NOT_INTERESTED,
    CallStatus.HANGUP,
    CallStatus.UNKNOWN,
    CallStatus.DISCONNECTED,
    CallStatus.FAILED,
}

# Legacy connected statuses (for backward compatibility)
CONNECTED_STATUSES = {
    CallStatus.DISCONNECTED,
    CallStatus.CONNECTED,
    CallStatus.FAILED,
    CallStatus.NOT_INTERESTED,
    CallStatus.HANGUP,
    CallStatus.UNKNOWN,
}


def numbers_summary(db: Session) -> NumbersSummary:
    total = db.query(func.count(PhoneNumber.id)).scalar() or 0
    rows = (
        db.query(PhoneNumber.status, func.count(PhoneNumber.id))
        .group_by(PhoneNumber.status)
        .all()
    )
    status_shares: list[StatusShare] = []
    for status, count in rows:
        status_shares.append(
            StatusShare(
                status=status,
                count=count,
                percentage=(count / total * 100) if total else 0.0,
            )
        )
    # include zero-count statuses for completeness
    existing_statuses = {s.status for s in status_shares}
    for status in CallStatus:
        if status not in existing_statuses:
            status_shares.append(StatusShare(status=status, count=0, percentage=0.0))
    status_shares.sort(key=lambda s: s.status.value)
    return NumbersSummary(total_numbers=total, status_counts=status_shares)


def attempt_summary(db: Session, days: int | None = None, hours: int | None = None) -> AttemptSummary:
    # Prefer hours when provided
    start_utc = None
    if hours and hours > 0:
        start_tehran = datetime.now(TEHRAN_TZ) - timedelta(hours=hours)
        start_utc = start_tehran.astimezone(timezone.utc)
    elif days and days > 0:
        start_tehran = _tehran_start_of_day(days - 1)
        start_utc = start_tehran.astimezone(timezone.utc)

    query = db.query(CallResult.status, func.count(CallResult.id))
    if start_utc:
        query = query.filter(CallResult.attempted_at >= start_utc)
    rows = query.group_by(CallResult.status).all()
    total = sum(count for _, count in rows)
    status_shares: list[StatusShare] = []
    for status, count in rows:
        try:
            parsed_status = CallStatus(status)
        except ValueError:
            continue
        status_shares.append(
            StatusShare(
                status=parsed_status,
                count=count,
                percentage=(count / total * 100) if total else 0.0,
            )
        )
    existing = {s.status for s in status_shares}
    for status in CallStatus:
        if status not in existing:
            status_shares.append(StatusShare(status=status, count=0, percentage=0.0))
    status_shares.sort(key=lambda s: s.status.value)
    connected_count = sum(s.count for s in status_shares if s.status in CONNECTED_STATUSES)
    connected_percentage = (connected_count / total * 100) if total else 0.0
    return AttemptSummary(
        total_attempts=total,
        status_counts=status_shares,
        connected_count=connected_count,
        connected_percentage=connected_percentage,
    )


def _tehran_start_of_day(days_back: int) -> datetime:
    now = datetime.now(TEHRAN_TZ)
    start_date = now.date() - timedelta(days=days_back)
    return datetime.combine(start_date, time(0, 0), tzinfo=TEHRAN_TZ)


def attempt_trend(db: Session, span: int = 14, granularity: str = "day") -> AttemptTrendResponse:
    granularity = granularity if granularity in {"day", "hour"} else "day"
    now_tehran = datetime.now(TEHRAN_TZ)
    if granularity == "hour":
        start_tehran = now_tehran.replace(minute=0, second=0, microsecond=0) - timedelta(hours=span - 1)
    else:
        start_tehran = _tehran_start_of_day(span - 1)

    start_utc = start_tehran.astimezone(timezone.utc)

    attempts = db.query(CallResult).filter(CallResult.attempted_at >= start_utc).all()

    # Bucket attempts by Tehran-local bucket and status
    buckets: dict[datetime, dict[CallStatus, int]] = defaultdict(lambda: defaultdict(int))
    for attempt in attempts:
        try:
            status = CallStatus(attempt.status)
        except ValueError:
            continue
        local_dt = attempt.attempted_at.astimezone(TEHRAN_TZ)
        if granularity == "hour":
            bucket_start = local_dt.replace(minute=0, second=0, microsecond=0)
        else:
            bucket_start = datetime.combine(local_dt.date(), time(0, 0), tzinfo=TEHRAN_TZ)
        buckets[bucket_start][status] += 1

    # Fill missing buckets with zeros to keep chart continuous
    bucket_list: list[TimeBucketBreakdown] = []
    for offset in range(span):
        if granularity == "hour":
            bucket_time = start_tehran + timedelta(hours=offset)
        else:
            bucket_time = datetime.combine(start_tehran.date() + timedelta(days=offset), time(0, 0), tzinfo=TEHRAN_TZ)
        counts = buckets.get(bucket_time, {})
        total = sum(counts.values())
        status_shares: list[StatusShare] = []
        for status in CallStatus:
            count = counts.get(status, 0)
            status_shares.append(
                StatusShare(
                    status=status,
                    count=count,
                    percentage=(count / total * 100) if total else 0.0,
                )
            )
        status_shares.sort(key=lambda s: s.status.value)
        bucket_list.append(
            TimeBucketBreakdown(
                bucket=bucket_time,
                total_attempts=total,
                status_counts=status_shares,
            )
        )

    return AttemptTrendResponse(granularity=granularity, buckets=bucket_list)


def cost_summary(db: Session, company_id: int) -> dict:
    # Get company billing config from settings
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company or not company.settings:
        rate = 0
    else:
        rate = company.settings.get("cost_per_connected", 0)

    now_tehran = datetime.now(TEHRAN_TZ)
    start_of_day = datetime.combine(now_tehran.date(), time(0, 0), tzinfo=TEHRAN_TZ).astimezone(timezone.utc)
    start_of_month = datetime.combine(now_tehran.date().replace(day=1), time(0, 0), tzinfo=TEHRAN_TZ).astimezone(timezone.utc)

    daily_count = (
        db.query(func.count(CallResult.id))
        .filter(CallResult.company_id == company_id)
        .filter(CallResult.status.in_([status.value for status in CONNECTED_STATUSES]))
        .filter(CallResult.attempted_at >= start_of_day)
        .scalar()
        or 0
    )
    monthly_count = (
        db.query(func.count(CallResult.id))
        .filter(CallResult.company_id == company_id)
        .filter(CallResult.status.in_([status.value for status in CONNECTED_STATUSES]))
        .filter(CallResult.attempted_at >= start_of_month)
        .scalar()
        or 0
    )
    return {
        "currency": "Toman",
        "cost_per_connected": rate,
        "daily_count": daily_count,
        "daily_cost": daily_count * rate,
        "monthly_count": monthly_count,
        "monthly_cost": monthly_count * rate,
    }


def _resolve_time_filter(time_filter: str) -> datetime | None:
    """Resolve time filter string to UTC datetime"""
    now_tehran = datetime.now(TEHRAN_TZ)

    if time_filter == "1h":
        start_tehran = now_tehran - timedelta(hours=1)
        return start_tehran.astimezone(timezone.utc)
    elif time_filter == "today":
        start_tehran = datetime.combine(now_tehran.date(), time(0, 0), tzinfo=TEHRAN_TZ)
        return start_tehran.astimezone(timezone.utc)
    elif time_filter == "yesterday":
        yesterday = now_tehran.date() - timedelta(days=1)
        start_tehran = datetime.combine(yesterday, time(0, 0), tzinfo=TEHRAN_TZ)
        end_tehran = datetime.combine(yesterday, time(23, 59, 59), tzinfo=TEHRAN_TZ)
        return start_tehran.astimezone(timezone.utc)
    elif time_filter == "7d":
        start_tehran = _tehran_start_of_day(6)
        return start_tehran.astimezone(timezone.utc)
    elif time_filter == "30d":
        start_tehran = _tehran_start_of_day(29)
        return start_tehran.astimezone(timezone.utc)

    return None


def dashboard_stats(
    db: Session,
    company_id: int,
    group_by: str = "scenario",
    time_filter: str = "today",
) -> dict:
    """
    Returns call status counts grouped by scenario or outbound line.
    Includes row totals, billable column, and inbound column.

    Args:
        db: Database session
        company_id: Company ID to filter by
        group_by: "scenario" or "line"
        time_filter: "1h", "today", "yesterday", "7d", "30d"

    Returns:
        {
            "groups": [
                {
                    "id": int,
                    "name": str,
                    "statuses": {"CONNECTED": 10, "MISSED": 5, ...},
                    "total": int,
                    "billable": int,
                    "inbound": int
                }
            ],
            "totals": {
                "CONNECTED": int,
                "MISSED": int,
                ...,
                "total": int,
                "billable": int,
                "inbound": int
            }
        }
    """
    start_utc = _resolve_time_filter(time_filter)

    # Determine grouping column and label model
    if group_by == "scenario":
        group_col = CallResult.scenario_id
        label_model = Scenario
    else:
        group_col = CallResult.outbound_line_id
        label_model = OutboundLine

    # Query call results grouped by scenario/line and status
    query = (
        db.query(
            group_col.label("group_id"),
            CallResult.status,
            func.count(CallResult.id).label("count")
        )
        .filter(CallResult.company_id == company_id)
    )

    if start_utc:
        query = query.filter(CallResult.attempted_at >= start_utc)

    rows = query.group_by(group_col, CallResult.status).all()

    # Build matrix
    groups_dict = defaultdict(lambda: defaultdict(int))
    for group_id, status, count in rows:
        if group_id is not None:
            groups_dict[group_id][status] = count

    # Fetch group names
    group_names = {}
    if group_by == "scenario":
        scenarios = db.query(Scenario).filter(Scenario.company_id == company_id).all()
        for s in scenarios:
            group_names[s.id] = s.display_name
    else:
        lines = db.query(OutboundLine).filter(OutboundLine.company_id == company_id).all()
        for line in lines:
            group_names[line.id] = line.display_name

    # Build response with all statuses
    all_statuses = [status.value for status in CallStatus]
    groups = []
    totals = {status: 0 for status in all_statuses}
    totals["total"] = 0
    totals["billable"] = 0
    totals["inbound"] = 0

    for group_id, status_counts in groups_dict.items():
        group_data = {
            "id": group_id,
            "name": group_names.get(group_id, f"Unknown {group_by} {group_id}"),
            "statuses": {status: 0 for status in all_statuses},
            "total": 0,
            "billable": 0,
            "inbound": 0,
        }

        for status, count in status_counts.items():
            group_data["statuses"][status] = count
            group_data["total"] += count
            totals[status] += count
            totals["total"] += count

            # Count billable
            try:
                status_enum = CallStatus(status)
                if status_enum in BILLABLE_STATUSES:
                    group_data["billable"] += count
                    totals["billable"] += count

                # Count inbound
                if status_enum == CallStatus.INBOUND_CALL:
                    group_data["inbound"] += count
                    totals["inbound"] += count
            except ValueError:
                pass

        groups.append(group_data)

    # Sort groups by name
    groups.sort(key=lambda g: g["name"])

    return {
        "groups": groups,
        "totals": totals,
    }
