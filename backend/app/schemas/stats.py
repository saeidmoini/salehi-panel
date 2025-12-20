from datetime import date
from pydantic import BaseModel, Field

from ..models.phone_number import CallStatus


class StatusShare(BaseModel):
    status: CallStatus
    count: int
    percentage: float


class NumbersSummary(BaseModel):
    total_numbers: int
    status_counts: list[StatusShare]


class DailyStatusBreakdown(BaseModel):
    day: date = Field(..., description="Tehran-local date")
    total_attempts: int
    status_counts: list[StatusShare]


class AttemptTrendResponse(BaseModel):
    days: list[DailyStatusBreakdown]
