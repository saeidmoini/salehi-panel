from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..api.deps import get_active_admin
from ..core.db import get_db
from ..services import schedule_service
from ..schemas.schedule import ScheduleConfigOut, ScheduleConfigUpdate, ScheduleInterval

router = APIRouter(dependencies=[Depends(get_active_admin)])


@router.get("/", response_model=ScheduleConfigOut)
def get_schedule(db: Session = Depends(get_db)):
    config = schedule_service.get_config(db)
    intervals = schedule_service.list_intervals(db)
    return ScheduleConfigOut(
        skip_holidays=config.skip_holidays,
        enabled=config.enabled,
        disabled_by_dialer=config.disabled_by_dialer or False,
        version=config.version,
        updated_at=config.updated_at,
        intervals=[
            ScheduleInterval(day_of_week=i.day_of_week, start_time=i.start_time, end_time=i.end_time)
            for i in intervals
        ],
    )


@router.put("/", response_model=ScheduleConfigOut)
def update_schedule(payload: ScheduleConfigUpdate, db: Session = Depends(get_db)):
    config = schedule_service.update_schedule(db, payload)
    intervals = schedule_service.list_intervals(db)
    return ScheduleConfigOut(
        skip_holidays=config.skip_holidays,
        enabled=config.enabled,
        disabled_by_dialer=config.disabled_by_dialer or False,
        version=config.version,
        updated_at=config.updated_at,
        intervals=[
            ScheduleInterval(day_of_week=i.day_of_week, start_time=i.start_time, end_time=i.end_time)
            for i in intervals
        ],
    )
