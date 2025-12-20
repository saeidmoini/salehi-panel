from collections import defaultdict
from datetime import datetime, time, timedelta, date, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..models.phone_number import PhoneNumber, CallStatus
from ..models.call_attempt import CallAttempt
from ..schemas.stats import NumbersSummary, StatusShare, AttemptTrendResponse, DailyStatusBreakdown
from .schedule_service import TEHRAN_TZ

settings = get_settings()


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


def _tehran_start_of_day(days_back: int) -> datetime:
    now = datetime.now(TEHRAN_TZ)
    start_date = now.date() - timedelta(days=days_back)
    return datetime.combine(start_date, time(0, 0), tzinfo=TEHRAN_TZ)


def attempt_trend(db: Session, days: int = 14) -> AttemptTrendResponse:
    start_tehran = _tehran_start_of_day(days - 1)
    start_utc = start_tehran.astimezone(timezone.utc)

    attempts = (
        db.query(CallAttempt)
        .filter(CallAttempt.attempted_at >= start_utc)
        .all()
    )

    # Bucket attempts by Tehran-local date and status
    buckets: dict[date, dict[CallStatus, int]] = defaultdict(lambda: defaultdict(int))
    for attempt in attempts:
        try:
            status = CallStatus(attempt.status)
        except ValueError:
            # ignore unknown statuses rather than failing the report
            continue
        local_date = attempt.attempted_at.astimezone(TEHRAN_TZ).date()
        buckets[local_date][status] += 1

    # Fill missing days with zeros to keep chart continuous
    days_list: list[DailyStatusBreakdown] = []
    for offset in range(days):
        day_date = start_tehran.date() + timedelta(days=offset)
        counts = buckets.get(day_date, {})
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
        days_list.append(
            DailyStatusBreakdown(
                day=day_date,
                total_attempts=total,
                status_counts=status_shares,
            )
        )

    return AttemptTrendResponse(days=days_list)
