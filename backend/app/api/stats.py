from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..api.deps import get_active_admin
from ..core.db import get_db
from ..schemas.stats import NumbersSummary, AttemptTrendResponse
from ..services import stats_service

router = APIRouter(dependencies=[Depends(get_active_admin)])


@router.get("/numbers-summary", response_model=NumbersSummary)
def get_numbers_summary(db: Session = Depends(get_db)):
    return stats_service.numbers_summary(db)


@router.get("/attempt-trend", response_model=AttemptTrendResponse)
def get_attempt_trend(
    days: int = Query(default=14, ge=1, le=180, description="Number of days to include (ending today)"),
    db: Session = Depends(get_db),
):
    return stats_service.attempt_trend(db, days=days)
