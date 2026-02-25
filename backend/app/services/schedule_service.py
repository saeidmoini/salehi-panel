from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
from typing import Iterable
import jdatetime

from fastapi import HTTPException
from sqlalchemy import delete, text, inspect
from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..models.scenario import Scenario
from ..models.schedule import ScheduleConfig, ScheduleWindow
from ..schemas.schedule import ScheduleConfigUpdate

settings = get_settings()
TEHRAN_TZ = ZoneInfo(settings.timezone)


def ensure_config(db: Session, company_id: int | None = None) -> ScheduleConfig:
    """Get or create schedule config for a company"""
    _ensure_enabled_column(db)
    _ensure_disabled_by_dialer_column(db)
    _ensure_billing_columns(db)
    _ensure_scenario_billing_column(db)

    # Find config by company_id
    config = db.query(ScheduleConfig).filter_by(company_id=company_id).first()

    if not config:
        config = ScheduleConfig(
            company_id=company_id,
            skip_holidays=settings.skip_holidays_default,
            enabled=True,
            disabled_by_dialer=False,
            wallet_balance=0,
            cost_per_connected=150,
            version=1,
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    if config.enabled is None:
        config.enabled = True
        db.commit()
        db.refresh(config)
    if config.cost_per_connected is None:
        config.cost_per_connected = 150
        db.commit()
        db.refresh(config)
    if config.wallet_balance is None:
        config.wallet_balance = 0
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


def _ensure_billing_columns(db: Session) -> None:
    conn = db.connection()
    inspector = inspect(conn)
    cols = [c["name"] for c in inspector.get_columns("schedule_configs")]
    if "wallet_balance" not in cols:
        conn.execute(text("ALTER TABLE schedule_configs ADD COLUMN IF NOT EXISTS wallet_balance INTEGER DEFAULT 0"))
        db.commit()
    if "cost_per_connected" not in cols:
        conn.execute(text("ALTER TABLE schedule_configs ADD COLUMN IF NOT EXISTS cost_per_connected INTEGER DEFAULT 150"))
        db.commit()


def _ensure_scenario_billing_column(db: Session) -> None:
    conn = db.connection()
    inspector = inspect(conn)
    cols = [c["name"] for c in inspector.get_columns("scenarios")]
    if "cost_per_connected" not in cols:
        conn.execute(text("ALTER TABLE scenarios ADD COLUMN IF NOT EXISTS cost_per_connected INTEGER"))
        db.commit()


def get_config(db: Session, company_id: int | None = None) -> ScheduleConfig:
    return ensure_config(db, company_id=company_id)


def list_intervals(db: Session, company_id: int | None = None) -> list[ScheduleWindow]:
    return db.query(ScheduleWindow).filter_by(company_id=company_id).order_by(ScheduleWindow.day_of_week, ScheduleWindow.start_time).all()


def update_schedule(db: Session, data: ScheduleConfigUpdate, company_id: int | None = None) -> ScheduleConfig:
    config = ensure_config(db, company_id=company_id)
    changed = False
    if data.intervals is not None:
        # Delete only this company's windows
        db.query(ScheduleWindow).filter_by(company_id=company_id).delete()
        for interval in data.intervals:
            if interval.start_time >= interval.end_time:
                raise HTTPException(status_code=400, detail="start_time must be before end_time")
            db.add(
                ScheduleWindow(
                    company_id=company_id,
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
        if data.enabled and config.wallet_balance is not None and config.wallet_balance <= 0:
            raise HTTPException(status_code=400, detail="Wallet balance is zero. Please recharge before enabling.")
        config.enabled = data.enabled
        # manual toggle clears dialer error flag
        config.disabled_by_dialer = False
        changed = True
    if changed:
        config.version += 1
    db.commit()
    db.refresh(config)
    return config


def charge_for_connected_call(db: Session, company_id: int | None = None, scenario_id: int | None = None) -> int:
    """
    Deducts cost per connected call from wallet. Returns remaining balance.
    Automatically disables dialing if balance hits zero.
    """
    cfg = ensure_config(db, company_id=company_id)
    # Lock the config row for update
    cfg = db.query(ScheduleConfig).filter_by(company_id=company_id).with_for_update().first()
    if not cfg:
        raise HTTPException(status_code=500, detail="Billing config missing")
    cost = cfg.cost_per_connected or 0
    if company_id is not None and scenario_id is not None:
        scenario = db.query(Scenario).filter(
            Scenario.id == scenario_id,
            Scenario.company_id == company_id,
        ).first()
        if scenario and scenario.cost_per_connected is not None:
            cost = scenario.cost_per_connected
    if cost <= 0:
        return cfg.wallet_balance or 0

    current_balance = cfg.wallet_balance or 0
    if current_balance <= 0:
        cfg.enabled = False
        cfg.disabled_by_dialer = True
        cfg.version += 1
        db.commit()
        return 0

    new_balance = current_balance - cost
    if new_balance < 0:
        new_balance = 0
    cfg.wallet_balance = new_balance
    if new_balance == 0:
        cfg.enabled = False
        cfg.disabled_by_dialer = True
        cfg.version += 1
    db.commit()
    db.refresh(cfg)
    return new_balance


def get_billing_info(db: Session, company_id: int | None = None) -> dict:
    cfg = ensure_config(db, company_id=company_id)
    return {
        "wallet_balance": cfg.wallet_balance or 0,
        "cost_per_connected": cfg.cost_per_connected or 0,
        "currency": "Toman",
        "disabled_by_dialer": cfg.disabled_by_dialer,
    }


def update_billing(db: Session, wallet_balance: int | None = None, cost_per_connected: int | None = None, company_id: int | None = None) -> ScheduleConfig:
    cfg = ensure_config(db, company_id=company_id)
    changed = False
    if wallet_balance is not None:
        cfg.wallet_balance = wallet_balance
        changed = True
    if cost_per_connected is not None:
        cfg.cost_per_connected = cost_per_connected
        changed = True
    if changed:
        cfg.version += 1
        # If balance now > 0, allow manual enabling later (do not force enable automatically)
        if cfg.wallet_balance and cfg.wallet_balance > 0:
            cfg.disabled_by_dialer = False if cfg.enabled else cfg.disabled_by_dialer
        db.commit()
        db.refresh(cfg)
    return cfg


def is_holiday(date_value: datetime) -> bool:
    """
    Shared Iran holidays based on Jalali calendar (applies equally to all companies).
    """
    jalali = jdatetime.date.fromgregorian(date=date_value.astimezone(TEHRAN_TZ).date())
    mm_dd = (jalali.month, jalali.day)
    # Fixed Jalali public holidays (shared nationwide)
    fixed_jalali_holidays = {
        (1, 1), (1, 2), (1, 3), (1, 4),   # Nowruz
        (1, 12), (1, 13),                 # Islamic Republic Day / Nature Day
        (3, 14), (3, 15),                 # Khomeini death / 15 Khordad uprising
        (11, 22),                         # Islamic Revolution Victory Day
        (12, 29),                         # Oil nationalization day
    }
    return mm_dd in fixed_jalali_holidays


def is_call_allowed(now: datetime | None, db: Session, company_id: int | None = None) -> tuple[bool, str | None, int]:
    config = ensure_config(db, company_id=company_id)
    now = (now or datetime.now(TEHRAN_TZ)).astimezone(TEHRAN_TZ)
    if config.wallet_balance is not None and config.wallet_balance <= 0:
        if config.enabled:
            config.enabled = False
            config.disabled_by_dialer = True
            config.version += 1
            db.commit()
            db.refresh(config)
        return False, "insufficient_funds", settings.short_retry_seconds
    if not config.enabled:
        return False, "disabled", settings.short_retry_seconds
    if config.skip_holidays and is_holiday(now):
        return False, "holiday", settings.long_retry_seconds

    intervals = list_intervals(db, company_id=company_id)
    todays_intervals = [i for i in intervals if i.day_of_week == _iran_weekday(now)]
    if not todays_intervals:
        return False, "no_window", settings.long_retry_seconds
    current_time = now.time()
    for interval in todays_intervals:
        if interval.start_time <= current_time <= interval.end_time:
            return True, None, 0
    # outside windows: fixed polling interval
    return False, "outside_allowed_time_window", settings.long_retry_seconds


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
