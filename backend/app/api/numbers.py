import csv
import io
from fastapi import APIRouter, Depends, UploadFile, File, Query
from sqlalchemy.orm import Session

from ..api.deps import get_active_admin
from ..core.db import get_db
from ..models.phone_number import CallStatus
from ..schemas.phone_number import PhoneNumberCreate, PhoneNumberOut, PhoneNumberStatusUpdate, PhoneNumberImportResponse
from ..services import phone_service

router = APIRouter(dependencies=[Depends(get_active_admin)])


@router.get("/", response_model=list[PhoneNumberOut])
def list_numbers(
    status: CallStatus | None = Query(default=None),
    search: str | None = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    numbers = phone_service.list_numbers(db, status=status, search=search, skip=skip, limit=limit)
    return numbers


@router.post("/", response_model=PhoneNumberImportResponse)
def add_numbers(payload: PhoneNumberCreate, db: Session = Depends(get_db)):
    result = phone_service.add_numbers(db, payload)
    return PhoneNumberImportResponse(**result)


@router.post("/upload", response_model=PhoneNumberImportResponse)
def upload_numbers(file: UploadFile = File(...), db: Session = Depends(get_db)):
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
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True)
        sheet = wb.active
        numbers = [str(cell.value) for cell in sheet["A"] if cell.value]
    result = phone_service.add_numbers(db, PhoneNumberCreate(phone_numbers=numbers))
    return PhoneNumberImportResponse(**result)


@router.put("/{number_id}/status", response_model=PhoneNumberOut)
def update_status(number_id: int, payload: PhoneNumberStatusUpdate, db: Session = Depends(get_db)):
    number = phone_service.update_number_status(db, number_id, payload)
    return number


@router.delete("/{number_id}")
def delete_number(number_id: int, db: Session = Depends(get_db)):
    phone_service.delete_number(db, number_id)
    return {"deleted": True, "id": number_id}


@router.post("/{number_id}/reset", response_model=PhoneNumberOut)
def reset_number(number_id: int, db: Session = Depends(get_db)):
    number = phone_service.reset_number(db, number_id)
    return number
