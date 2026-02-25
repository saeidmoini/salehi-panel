from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..api.deps import get_company, get_company_admin
from ..schemas.outbound_line import OutboundLineCreate, OutboundLineUpdate, OutboundLineOut
from ..models.outbound_line import OutboundLine
from ..models.company import Company
from ..models.user import AdminUser

router = APIRouter()


@router.get("/{company_name}/outbound-lines", response_model=list[OutboundLineOut])
def list_outbound_lines(
    company: Company = Depends(get_company),
    user: AdminUser = Depends(get_company_admin),
    db: Session = Depends(get_db),
):
    """List all outbound lines for a company"""
    return (
        db.query(OutboundLine)
        .filter(OutboundLine.company_id == company.id)
        .order_by(OutboundLine.id.asc())
        .all()
    )


@router.post("/{company_name}/outbound-lines", response_model=OutboundLineOut)
def create_outbound_line(
    payload: OutboundLineCreate,
    company: Company = Depends(get_company),
    user: AdminUser = Depends(get_company_admin),
    db: Session = Depends(get_db),
):
    """Create a new outbound line (admin only)"""
    # Verify company_id matches the path parameter
    if payload.company_id != company.id:
        raise HTTPException(status_code=400, detail="Company ID mismatch")

    # Check if phone number already exists for this company
    existing = db.query(OutboundLine).filter(
        OutboundLine.company_id == company.id,
        OutboundLine.phone_number == payload.phone_number
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Phone number already exists for this company")

    line = OutboundLine(
        company_id=payload.company_id,
        phone_number=payload.phone_number,
        display_name=payload.display_name,
        is_active=payload.is_active,
    )
    db.add(line)
    db.commit()
    db.refresh(line)
    return line


@router.put("/{company_name}/outbound-lines/{line_id}", response_model=OutboundLineOut)
def update_outbound_line(
    line_id: int,
    payload: OutboundLineUpdate,
    company: Company = Depends(get_company),
    user: AdminUser = Depends(get_company_admin),
    db: Session = Depends(get_db),
):
    """Update outbound line (admin only)"""
    line = db.query(OutboundLine).filter(
        OutboundLine.id == line_id,
        OutboundLine.company_id == company.id
    ).first()
    if not line:
        raise HTTPException(status_code=404, detail="Outbound line not found")

    if payload.display_name is not None:
        line.display_name = payload.display_name
    if payload.is_active is not None:
        line.is_active = payload.is_active

    db.commit()
    db.refresh(line)
    return line


@router.delete("/{company_name}/outbound-lines/{line_id}")
def delete_outbound_line(
    line_id: int,
    company: Company = Depends(get_company),
    user: AdminUser = Depends(get_company_admin),
    db: Session = Depends(get_db),
):
    """Outbound line deletion is disabled from panel."""
    raise HTTPException(status_code=405, detail="Deleting outbound lines is disabled")
