from datetime import datetime
from pydantic import BaseModel, Field
from ..models.phone_number import CallStatus


class PhoneNumberCreate(BaseModel):
    phone_numbers: list[str] = Field(..., description="List of phone numbers to enqueue")


class PhoneNumberStatusUpdate(BaseModel):
    status: CallStatus
    note: str | None = None


class AssignedAgentOut(BaseModel):
    id: int
    username: str
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None

    class Config:
        from_attributes = True


class PhoneNumberOut(BaseModel):
    id: int
    phone_number: str
    status: CallStatus
    total_attempts: int
    last_attempt_at: datetime | None
    last_status_change_at: datetime | None
    assigned_at: datetime | None
    assigned_batch_id: str | None
    last_user_message: str | None = None
    assigned_agent_id: int | None = None
    assigned_agent: AssignedAgentOut | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


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
    search: str | None = None
    agent_id: int | None = None
    sort_by: str = Field(default="created_at", pattern="^(created_at|last_attempt_at|status)$")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")
    start_date: str | None = None
    end_date: str | None = None


class PhoneNumberBulkResult(BaseModel):
    updated: int = 0
    reset: int = 0
    deleted: int = 0


class PhoneNumberExportRequest(BaseModel):
    ids: list[int] = Field(default_factory=list)
    select_all: bool = False
    excluded_ids: list[int] = Field(default_factory=list)
    filter_status: CallStatus | None = None
    search: str | None = None
    agent_id: int | None = None
    sort_by: str = Field(default="created_at", pattern="^(created_at|last_attempt_at|status)$")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")
    start_date: str | None = None
    end_date: str | None = None
