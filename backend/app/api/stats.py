from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from ..api.deps import get_active_admin, get_current_active_user
from ..core.db import get_db
from ..schemas.stats import NumbersSummary, AttemptTrendResponse, AttemptSummary, CostSummary
from ..services import stats_service
from ..models.company import Company
from ..models.user import AdminUser

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


@router.get("/costs", response_model=CostSummary)
def get_costs(
    company: str = Query(..., description="Company slug"),
    user: AdminUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get cost summary for a company"""
    company_obj = db.query(Company).filter(Company.name == company, Company.is_active == True).first()
    if not company_obj:
        raise HTTPException(status_code=404, detail="Company not found")

    # Verify user has access to this company
    if not user.is_superuser and user.company_id != company_obj.id:
        raise HTTPException(status_code=403, detail="Access denied to this company")

    return stats_service.cost_summary(db, company_obj.id)


@router.get("/dashboard-stats")
def get_dashboard_stats(
    company: str = Query(..., description="Company slug"),
    group_by: str = Query("scenario", pattern="^(scenario|line)$", description="Group by scenario or line"),
    time_filter: str = Query("today", pattern="^(1h|today|yesterday|7d|30d)$", description="Time filter"),
    user: AdminUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get dashboard statistics grouped by scenario or outbound line"""
    company_obj = db.query(Company).filter(Company.name == company, Company.is_active == True).first()
    if not company_obj:
        raise HTTPException(status_code=404, detail="Company not found")

    # Verify user has access to this company
    if not user.is_superuser and user.company_id != company_obj.id:
        raise HTTPException(status_code=403, detail="Access denied to this company")

    return stats_service.dashboard_stats(db, company_obj.id, group_by, time_filter)
