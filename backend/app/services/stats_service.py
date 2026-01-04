from collections import defaultdict
from datetime import datetime, time, timedelta, date, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..models.phone_number import PhoneNumber, CallStatus
from ..models.call_attempt import CallAttempt
from ..schemas.stats import NumbersSummary, StatusShare, AttemptTrendResponse, TimeBucketBreakdown, AttemptSummary
from .schedule_service import TEHRAN_TZ, ensure_config

settings = get_settings()
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

    query = db.query(CallAttempt.status, func.count(CallAttempt.id))
    if start_utc:
        query = query.filter(CallAttempt.attempted_at >= start_utc)
    rows = query.group_by(CallAttempt.status).all()
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

    attempts = db.query(CallAttempt).filter(CallAttempt.attempted_at >= start_utc).all()

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


def cost_summary(db: Session) -> dict:
    cfg = ensure_config(db)
    rate = cfg.cost_per_connected or 0
    now_tehran = datetime.now(TEHRAN_TZ)
    start_of_day = datetime.combine(now_tehran.date(), time(0, 0), tzinfo=TEHRAN_TZ).astimezone(timezone.utc)
    start_of_month = datetime.combine(now_tehran.date().replace(day=1), time(0, 0), tzinfo=TEHRAN_TZ).astimezone(timezone.utc)

    daily_count = (
        db.query(func.count(CallAttempt.id))
        .filter(CallAttempt.status.in_([status.value for status in CONNECTED_STATUSES]))
        .filter(CallAttempt.attempted_at >= start_of_day)
        .scalar()
        or 0
    )
    monthly_count = (
        db.query(func.count(CallAttempt.id))
        .filter(CallAttempt.status.in_([status.value for status in CONNECTED_STATUSES]))
        .filter(CallAttempt.attempted_at >= start_of_month)
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
