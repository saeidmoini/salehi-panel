from datetime import date
from datetime import datetime
from pydantic import BaseModel, Field

from ..models.phone_number import CallStatus


class StatusShare(BaseModel):
    status: CallStatus
    count: int
    percentage: float


class NumbersSummary(BaseModel):
    total_numbers: int
    status_counts: list[StatusShare]


class AttemptSummary(BaseModel):
    total_attempts: int
    status_counts: list[StatusShare]


class TimeBucketBreakdown(BaseModel):
    bucket: datetime = Field(..., description="Start time of bucket in Tehran time")
    total_attempts: int
    status_counts: list[StatusShare]


class AttemptTrendResponse(BaseModel):
    granularity: str = Field(..., description="day or hour")
    buckets: list[TimeBucketBreakdown]
