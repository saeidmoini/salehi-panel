import csv
import io
from datetime import datetime, date
from fastapi import APIRouter, Depends, UploadFile, File, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..core.security import get_current_active_user
from ..models.phone_number import CallStatus, GlobalStatus
from ..schemas.phone_number import (
    PhoneNumberCreate,
    PhoneNumberOut,
    PhoneNumberHistoryOut,
    PhoneNumberStatusUpdate,
    PhoneNumberImportResponse,
    PhoneNumberStatsResponse,
    PhoneNumberBulkAction,
    PhoneNumberBulkResult,
    PhoneNumberExportRequest,
)
from ..services import phone_service

router = APIRouter()


@router.get("/", response_model=list[PhoneNumberOut])
def list_numbers(
    company: str | None = Query(default=None, description="Company name to filter data"),
    status: CallStatus | None = Query(default=None),
    global_status: GlobalStatus | None = Query(default=None),
    search: str | None = None,
    start_date: str | None = Query(default=None, description="ISO date (YYYY-MM-DD)"),
    end_date: str | None = Query(default=None, description="ISO date (YYYY-MM-DD)"),
    skip: int = 0,
    limit: int = 50,
    sort_by: str = Query(default="created_at", pattern="^(created_at|last_attempt_at|status|total_attempts)$"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    agent_id: int | None = Query(default=None, description="Admin-only: filter numbers assigned to an agent"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    start = _parse_date_param(start_date, "start_date")
    end = _parse_date_param(end_date, "end_date")
    numbers = phone_service.list_numbers(
        db,
        current_user=current_user,
        company_name=company,
        status=status,
        global_status=global_status,
        search=search,
        start_date=start,
        end_date=end,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
        agent_id=agent_id,
    )
    return numbers


@router.get("/stats", response_model=PhoneNumberStatsResponse)
def numbers_stats(
    company: str | None = Query(default=None, description="Company name to filter data"),
    status: CallStatus | None = Query(default=None),
    global_status: GlobalStatus | None = Query(default=None),
    search: str | None = None,
    start_date: str | None = Query(default=None, description="ISO date (YYYY-MM-DD)"),
    end_date: str | None = Query(default=None, description="ISO date (YYYY-MM-DD)"),
    agent_id: int | None = Query(default=None, description="Admin-only: filter numbers assigned to an agent"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    start = _parse_date_param(start_date, "start_date")
    end = _parse_date_param(end_date, "end_date")
    total = phone_service.count_numbers(
        db,
        current_user=current_user,
        company_name=company,
        status=status,
        global_status=global_status,
        search=search,
        agent_id=agent_id,
        start_date=start,
        end_date=end,
    )
    return PhoneNumberStatsResponse(total=total)


@router.post("/", response_model=PhoneNumberImportResponse)
def add_numbers(payload: PhoneNumberCreate, db: Session = Depends(get_db), current_user=Depends(get_current_active_user)):
    result = phone_service.add_numbers(db, payload, current_user=current_user)
    return PhoneNumberImportResponse(**result)


@router.post("/upload", response_model=PhoneNumberImportResponse)
def upload_numbers(file: UploadFile = File(...), db: Session = Depends(get_db), current_user=Depends(get_current_active_user)):
    content = file.file.read()
    file.file.close()
    if file.filename.endswith(".csv"):
        decoded = content.decode("utf-8")
        reader = csv.reader(io.StringIO(decoded))
        numbers = [row[0] for row in reader if row]
    else:
        try:
            import openpyxl
        except ImportError:  # pragma: no cover
            raise RuntimeError("openpyxl not installed")
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        sheet = wb.active
        numbers = []
        for row in sheet.iter_rows(min_row=1, max_col=1, values_only=True):
            val = row[0]
            if val:
                numbers.append(str(val))
    result = phone_service.add_numbers(db, PhoneNumberCreate(phone_numbers=numbers), current_user=current_user)
    return PhoneNumberImportResponse(**result)


@router.put("/{number_id}/status", response_model=PhoneNumberOut)
def update_status(
    number_id: int,
    payload: PhoneNumberStatusUpdate,
    company: str | None = Query(default=None, description="Company slug"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    number = phone_service.update_number_status(db, number_id, payload, current_user=current_user, company_name=company)
    return number


@router.delete("/{number_id}")
def delete_number(
    number_id: int,
    company: str | None = Query(default=None, description="Company slug"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    phone_service.delete_number(db, number_id, current_user=current_user, company_name=company)
    return {"deleted": True, "id": number_id}


@router.post("/{number_id}/reset", response_model=PhoneNumberOut)
def reset_number(
    number_id: int,
    company: str | None = Query(default=None, description="Company slug"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    number = phone_service.reset_number(db, number_id, current_user=current_user, company_name=company)
    return number


@router.get("/{number_id}/history", response_model=list[PhoneNumberHistoryOut])
def number_history(
    number_id: int,
    company: str | None = Query(default=None, description="Company slug"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return phone_service.list_number_history(
        db,
        current_user=current_user,
        number_id=number_id,
        company_name=company,
    )


@router.post("/bulk", response_model=PhoneNumberBulkResult)
def bulk_numbers_action(payload: PhoneNumberBulkAction, db: Session = Depends(get_db), current_user=Depends(get_current_active_user)):
    return phone_service.bulk_action(db, payload, current_user=current_user)


@router.post("/export")
def export_numbers(payload: PhoneNumberExportRequest, db: Session = Depends(get_db), current_user=Depends(get_current_active_user)):
    stream = phone_service.export_numbers(db, payload, current_user=current_user)
    filename = "numbers_export.xlsx"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


def _parse_date_param(value: str | None, field: str) -> date | None:
    if not value:
        return None
    normalized = _normalize_digits(value)
    try:
        return datetime.fromisoformat(normalized).date()
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid {field}")


def _normalize_digits(value: str) -> str:
    # Convert Persian/Arabic digits to ASCII
    mapping = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    return value.translate(mapping)
