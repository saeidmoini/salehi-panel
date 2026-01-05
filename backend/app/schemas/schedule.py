from datetime import time, datetime
from pydantic import BaseModel, Field


class ScheduleInterval(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6, description="0=Saturday, 6=Friday")
    start_time: time
    end_time: time


class ScheduleConfigOut(BaseModel):
    skip_holidays: bool
    enabled: bool
    disabled_by_dialer: bool = False
    version: int
    intervals: list[ScheduleInterval]
    updated_at: datetime | None = None


class ScheduleConfigUpdate(BaseModel):
    skip_holidays: bool | None = None
    enabled: bool | None = None
    intervals: list[ScheduleInterval] | None = None
