from datetime import datetime
from pydantic import BaseModel, Field
from ..models.phone_number import CallStatus, GlobalStatus


class PhoneNumberCreate(BaseModel):
    phone_numbers: list[str] = Field(..., description="List of phone numbers to enqueue")


class PhoneNumberStatusUpdate(BaseModel):
    status: CallStatus
    note: str | None = None


class PhoneNumberOut(BaseModel):
    # New multi-company architecture: minimal fields
    id: int
    phone_number: str
    global_status: GlobalStatus
    last_called_at: datetime | None = None
    last_called_company_id: int | None = None
    assigned_at: datetime | None = None
    assigned_batch_id: str | None = None

    # Legacy fields for frontend compatibility (will be populated from call_results)
    status: str | None = None  # Per-company status from call_results
    total_attempts: int = 0  # Per-company attempt count from call_results
    last_attempt_at: datetime | None = None  # Deprecated: use last_called_at
    last_status_change_at: datetime | None = None  # Deprecated
    last_user_message: str | None = None  # From most recent call_result
    assigned_agent_id: int | None = None  # From most recent call_result
    assigned_agent: dict | None = None  # From most recent call_result
    scenario_display_name: str | None = None  # From most recent call_result
    outbound_line_display_name: str | None = None  # From most recent call_result

    class Config:
        from_attributes = True


class PhoneNumberHistoryOut(BaseModel):
    call_result_id: int
    number_id: int
    phone_number: str
    global_status: GlobalStatus
    status: str
    total_attempts: int
    last_attempt_at: datetime
    last_user_message: str | None = None
    assigned_agent_id: int | None = None
    assigned_agent: dict | None = None
    scenario_display_name: str | None = None
    outbound_line_display_name: str | None = None
    sent_batch_id: str | None = None
    reported_batch_id: str | None = None


class PhoneNumberImportResponse(BaseModel):
    inserted: int
    duplicates: int
    invalid: int
    invalid_samples: list[str] = []


class PhoneNumberStatsResponse(BaseModel):
    total: int


class PhoneNumberBulkAction(BaseModel):
    action: str = Field(..., pattern="^(update_status|reset|delete)$")
    status: CallStatus | None = None
    note: str | None = None
    ids: list[int] = Field(default_factory=list)
    select_all: bool = False
    excluded_ids: list[int] = Field(default_factory=list)
    filter_status: CallStatus | None = None
    filter_global_status: GlobalStatus | None = None
    search: str | None = None
    agent_id: int | None = None
    sort_by: str = Field(default="created_at", pattern="^(created_at|last_attempt_at|status)$")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")
    start_date: str | None = None
    end_date: str | None = None
    company_name: str | None = None


class PhoneNumberBulkResult(BaseModel):
    updated: int = 0
    reset: int = 0
    deleted: int = 0


class PhoneNumberExportRequest(BaseModel):
    ids: list[int] = Field(default_factory=list)
    select_all: bool = False
    excluded_ids: list[int] = Field(default_factory=list)
    filter_status: CallStatus | None = None
    filter_global_status: GlobalStatus | None = None
    search: str | None = None
    agent_id: int | None = None
    sort_by: str = Field(default="created_at", pattern="^(created_at|last_attempt_at|status)$")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")
    start_date: str | None = None
    end_date: str | None = None
    company_name: str | None = None
