from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..api.deps import get_active_admin
from ..core.db import get_db
from ..schemas.stats import NumbersSummary, AttemptTrendResponse, AttemptSummary
from ..services import stats_service

router = APIRouter(dependencies=[Depends(get_active_admin)])


@router.get("/numbers-summary", response_model=NumbersSummary)
def get_numbers_summary(db: Session = Depends(get_db)):
    return stats_service.numbers_summary(db)


@router.get("/attempt-trend", response_model=AttemptTrendResponse)
def get_attempt_trend(
    span: int = Query(default=14, ge=1, le=240, description="Number of buckets to include"),
    granularity: str = Query(default="day", pattern="^(day|hour)$"),
    db: Session = Depends(get_db),
):
    return stats_service.attempt_trend(db, span=span, granularity=granularity)


@router.get("/attempts-summary", response_model=AttemptSummary)
def get_attempts_summary(
    days: int | None = Query(default=None, ge=1, le=365, description="Optional: limit to last N days (Tehran)"),
    hours: int | None = Query(default=None, ge=1, le=720, description="Optional: limit to last N hours (Tehran)"),
    db: Session = Depends(get_db),
):
    return stats_service.attempt_summary(db, days=days, hours=hours)
