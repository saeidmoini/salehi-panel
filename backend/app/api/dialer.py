from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from ..api.deps import get_dialer_auth
from ..core.db import get_db
from ..schemas.dialer import NextBatchResponse, DialerReport
from ..schemas.scenario import RegisterScenariosRequest
from ..schemas.outbound_line import RegisterOutboundLinesRequest
from ..services import dialer_service
from ..models.company import Company
from ..models.scenario import Scenario
from ..models.outbound_line import OutboundLine

router = APIRouter(dependencies=[Depends(get_dialer_auth)])


@router.get("/next-batch", response_model=NextBatchResponse)
def next_batch(
    company: str = Query(..., description="Company slug"),
    size: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
):
    """Fetch next batch of numbers for a company"""
    company_obj = db.query(Company).filter(Company.name == company, Company.is_active == True).first()
    if not company_obj:
        raise HTTPException(status_code=404, detail="Company not found")

    payload = dialer_service.fetch_next_batch(db, company=company_obj, size=size)
    return payload


@router.post("/report-result")
def report_result(report: DialerReport, db: Session = Depends(get_db)):
    """Report call result for a company"""
    company_obj = db.query(Company).filter(Company.name == report.company, Company.is_active == True).first()
    if not company_obj:
        raise HTTPException(status_code=404, detail="Company not found")

    result = dialer_service.report_result(db, report, company=company_obj)
    return result


@router.post("/register-scenarios")
def register_scenarios(
    payload: RegisterScenariosRequest,
    db: Session = Depends(get_db),
):
    """Dialer app registers available scenarios on startup"""
    company_obj = db.query(Company).filter(Company.name == payload.company, Company.is_active == True).first()
    if not company_obj:
        raise HTTPException(status_code=404, detail="Company not found")

    incoming = {item.name: item for item in payload.scenarios}
    existing_rows = db.query(Scenario).filter(Scenario.company_id == company_obj.id).all()
    existing_by_name = {row.name: row for row in existing_rows}

    created = 0
    updated = 0
    deactivated = 0

    for name, item in incoming.items():
        existing = existing_by_name.get(name)
        if existing:
            if existing.display_name != item.display_name:
                existing.display_name = item.display_name
                updated += 1
        else:
            db.add(Scenario(
                company_id=company_obj.id,
                name=name,
                display_name=item.display_name,
                is_active=True,
            ))
            created += 1

    incoming_names = set(incoming.keys())
    for row in existing_rows:
        if row.name not in incoming_names and row.is_active:
            row.is_active = False
            deactivated += 1

    # Dialer registration is authoritative for existence; panel controls active toggle afterward.
    db.commit()
    return {
        "registered": len(incoming),
        "created": created,
        "updated": updated,
        "deactivated": deactivated,
    }


@router.post("/register-outbound-lines")
def register_outbound_lines(
    payload: RegisterOutboundLinesRequest,
    db: Session = Depends(get_db),
):
    """Dialer app registers available outbound lines on startup."""
    company_obj = db.query(Company).filter(Company.name == payload.company, Company.is_active == True).first()
    if not company_obj:
        raise HTTPException(status_code=404, detail="Company not found")

    incoming = {item.phone_number: item for item in payload.outbound_lines}
    existing_rows = db.query(OutboundLine).filter(OutboundLine.company_id == company_obj.id).all()
    existing_by_phone = {row.phone_number: row for row in existing_rows}

    created = 0
    updated = 0
    deactivated = 0

    for phone, item in incoming.items():
        existing = existing_by_phone.get(phone)
        if existing:
            if existing.display_name != item.display_name:
                existing.display_name = item.display_name
                updated += 1
        else:
            db.add(OutboundLine(
                company_id=company_obj.id,
                phone_number=phone,
                display_name=item.display_name,
                is_active=True,
            ))
            created += 1

    # Dialer registration updates/creates known lines only.
    # Active/inactive state is controlled from panel and must remain untouched here.
    db.commit()
    return {
        "registered": len(incoming),
        "created": created,
        "updated": updated,
        "deactivated": deactivated,
    }
