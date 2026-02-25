from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..api.deps import get_company, get_company_user, get_active_admin
from ..schemas.scenario import ScenarioCreate, ScenarioUpdate, ScenarioOut
from ..models.scenario import Scenario
from ..models.company import Company
from ..models.user import AdminUser
from ..services import schedule_service

router = APIRouter()


@router.get("/{company_name}/scenarios", response_model=list[ScenarioOut])
def list_scenarios(
    company: Company = Depends(get_company),
    user: AdminUser = Depends(get_company_user),
    db: Session = Depends(get_db),
):
    """List all scenarios for a company"""
    cfg = schedule_service.ensure_config(db, company_id=company.id)
    default_cost = cfg.cost_per_connected or 0
    updated = db.query(Scenario).filter(
        Scenario.company_id == company.id,
        Scenario.cost_per_connected.is_(None),
    ).update({Scenario.cost_per_connected: default_cost}, synchronize_session=False)
    if updated:
        db.commit()
    return (
        db.query(Scenario)
        .filter(Scenario.company_id == company.id)
        .order_by(Scenario.id.asc())
        .all()
    )


@router.post("/{company_name}/scenarios", response_model=ScenarioOut)
def create_scenario(
    payload: ScenarioCreate,
    company: Company = Depends(get_company),
    user: AdminUser = Depends(get_active_admin),
    db: Session = Depends(get_db),
):
    """Create a new scenario (admin only)"""
    cfg = schedule_service.ensure_config(db, company_id=company.id)

    # Verify company_id matches the path parameter
    if payload.company_id != company.id:
        raise HTTPException(status_code=400, detail="Company ID mismatch")

    # Check if scenario name already exists for this company
    existing = db.query(Scenario).filter(
        Scenario.company_id == company.id,
        Scenario.name == payload.name
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Scenario name already exists for this company")

    scenario = Scenario(
        company_id=payload.company_id,
        name=payload.name,
        display_name=payload.display_name,
        cost_per_connected=payload.cost_per_connected if payload.cost_per_connected is not None else (cfg.cost_per_connected or 0),
        is_active=payload.is_active,
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    return scenario


@router.put("/{company_name}/scenarios/{scenario_id}", response_model=ScenarioOut)
def update_scenario(
    scenario_id: int,
    payload: ScenarioUpdate,
    company: Company = Depends(get_company),
    user: AdminUser = Depends(get_active_admin),
    db: Session = Depends(get_db),
):
    """Update scenario (admin only)"""
    schedule_service.ensure_config(db, company_id=company.id)
    scenario = db.query(Scenario).filter(
        Scenario.id == scenario_id,
        Scenario.company_id == company.id
    ).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    if payload.display_name is not None:
        scenario.display_name = payload.display_name
    if payload.cost_per_connected is not None:
        scenario.cost_per_connected = payload.cost_per_connected
    if payload.is_active is not None:
        scenario.is_active = payload.is_active

    db.commit()
    db.refresh(scenario)
    return scenario


@router.delete("/{company_name}/scenarios/{scenario_id}")
def delete_scenario(
    scenario_id: int,
    company: Company = Depends(get_company),
    user: AdminUser = Depends(get_active_admin),
    db: Session = Depends(get_db),
):
    """Delete scenario (admin only)"""
    scenario = db.query(Scenario).filter(
        Scenario.id == scenario_id,
        Scenario.company_id == company.id
    ).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    db.delete(scenario)
    db.commit()
    return {"deleted": True, "id": scenario_id}
