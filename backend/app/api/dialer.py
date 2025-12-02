from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..api.deps import get_dialer_auth
from ..core.db import get_db
from ..schemas.dialer import NextBatchResponse, DialerReport
from ..services import dialer_service

router = APIRouter(dependencies=[Depends(get_dialer_auth)])


@router.get("/next-batch", response_model=NextBatchResponse)
def next_batch(size: int | None = Query(default=None, ge=1), db: Session = Depends(get_db)):
    payload = dialer_service.fetch_next_batch(db, size=size)
    return payload


@router.post("/report-result")
def report_result(report: DialerReport, db: Session = Depends(get_db)):
    number = dialer_service.report_result(db, report)
    return {"id": number.id, "status": number.status}
