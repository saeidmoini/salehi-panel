from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
from typing import Iterable

from fastapi import HTTPException
from sqlalchemy import delete, text, inspect
from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..models.schedule import ScheduleConfig, ScheduleWindow
from ..schemas.schedule import ScheduleConfigUpdate, ScheduleInterval

settings = get_settings()
TEHRAN_TZ = ZoneInfo(settings.timezone)


def ensure_config(db: Session) -> ScheduleConfig:
    _ensure_enabled_column(db)
    _ensure_disabled_by_dialer_column(db)
    config = db.get(ScheduleConfig, 1)
    if not config:
        config = ScheduleConfig(
            skip_holidays=settings.skip_holidays_default,
            enabled=True,
            disabled_by_dialer=False,
            version=1,
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    if config.enabled is None:
        config.enabled = True
        db.commit()
        db.refresh(config)
    return config


def _ensure_enabled_column(db: Session) -> None:
    # Backward-compat: add enabled column if missing (for existing deployments)
    conn = db.connection()
    inspector = inspect(conn)
    cols = [c["name"] for c in inspector.get_columns("schedule_configs")]
    if "enabled" not in cols:
        conn.execute(text("ALTER TABLE schedule_configs ADD COLUMN IF NOT EXISTS enabled BOOLEAN DEFAULT TRUE"))
        db.commit()


def _ensure_disabled_by_dialer_column(db: Session) -> None:
    conn = db.connection()
    inspector = inspect(conn)
    cols = [c["name"] for c in inspector.get_columns("schedule_configs")]
    if "disabled_by_dialer" not in cols:
        conn.execute(text("ALTER TABLE schedule_configs ADD COLUMN IF NOT EXISTS disabled_by_dialer BOOLEAN DEFAULT FALSE"))
        db.commit()


def get_config(db: Session) -> ScheduleConfig:
    return ensure_config(db)


def list_intervals(db: Session) -> list[ScheduleWindow]:
    return db.query(ScheduleWindow).order_by(ScheduleWindow.day_of_week, ScheduleWindow.start_time).all()


def update_schedule(db: Session, data: ScheduleConfigUpdate) -> ScheduleConfig:
    config = ensure_config(db)
    changed = False
    if data.intervals is not None:
        db.execute(delete(ScheduleWindow))
        for interval in data.intervals:
            if interval.start_time >= interval.end_time:
                raise HTTPException(status_code=400, detail="start_time must be before end_time")
            db.add(
                ScheduleWindow(
                    day_of_week=interval.day_of_week,
                    start_time=interval.start_time,
                    end_time=interval.end_time,
                )
            )
        changed = True
    if data.skip_holidays is not None:
        config.skip_holidays = data.skip_holidays
        changed = True
    if data.enabled is not None:
        config.enabled = data.enabled
        # manual toggle clears dialer error flag
        config.disabled_by_dialer = False
        changed = True
    if changed:
        config.version += 1
    db.commit()
    db.refresh(config)
    return config


def is_holiday(date_value: datetime) -> bool:
    # Placeholder: hook for Iranian holiday calendar integration
    return False


def is_call_allowed(now: datetime | None, db: Session) -> tuple[bool, str | None, int]:
    config = ensure_config(db)
    now = (now or datetime.now(TEHRAN_TZ)).astimezone(TEHRAN_TZ)
    if not config.enabled:
        return False, "disabled", settings.long_retry_seconds
    if config.skip_holidays and is_holiday(now):
        return False, "holiday", settings.short_retry_seconds

    intervals = list_intervals(db)
    todays_intervals = [i for i in intervals if i.day_of_week == _iran_weekday(now)]
    if not todays_intervals:
        return False, "no_window", settings.long_retry_seconds
    current_time = now.time()
    for interval in todays_intervals:
        if interval.start_time <= current_time <= interval.end_time:
            return True, None, 0
    # outside windows
    next_start = _next_start(now, intervals)
    if next_start:
        delta = (next_start - now).total_seconds()
        retry = max(settings.short_retry_seconds, int(delta))
    else:
        retry = settings.long_retry_seconds
    return False, "outside_allowed_time_window", retry


def _next_start(now: datetime, intervals: Iterable[ScheduleWindow]) -> datetime | None:
    # compute next start time from now, considering weekly repetition
    now_date = now.date()
    for day_offset in range(0, 8):
        check_date = now_date + timedelta(days=day_offset)
        weekday = _iran_weekday(datetime.combine(check_date, time(0, 0), tzinfo=TEHRAN_TZ))
        candidates = [i for i in intervals if i.day_of_week == weekday]
        if not candidates:
            continue
        for interval in sorted(candidates, key=lambda i: i.start_time):
            candidate_dt = datetime.combine(check_date, interval.start_time, tzinfo=TEHRAN_TZ)
            if candidate_dt > now:
                return candidate_dt
    return None


def _iran_weekday(current: datetime) -> int:
    # Convert Python weekday (Mon=0) to Iran convention (Sat=0)
    return (current.weekday() + 2) % 7
