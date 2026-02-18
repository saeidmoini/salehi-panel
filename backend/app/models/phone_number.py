from datetime import datetime
from enum import Enum
from sqlalchemy import String, Integer, DateTime, Enum as PgEnum, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db import Base


class CallStatus(str, Enum):
    IN_QUEUE = "IN_QUEUE"
    MISSED = "MISSED"
    CONNECTED = "CONNECTED"
    FAILED = "FAILED"
    NOT_INTERESTED = "NOT_INTERESTED"
    HANGUP = "HANGUP"
    DISCONNECTED = "DISCONNECTED"
    BUSY = "BUSY"
    POWER_OFF = "POWER_OFF"
    BANNED = "BANNED"
    UNKNOWN = "UNKNOWN"
    INBOUND_CALL = "INBOUND_CALL"  # تماس ورودی - not billable
    COMPLAINED = "COMPLAINED"  # شکایت - never call again


class GlobalStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLAINED = "COMPLAINED"  # شکایت ثبت شده - never call
    POWER_OFF = "POWER_OFF"    # خاموش - applies to all companies


class PhoneNumber(Base):
    __tablename__ = "numbers"  # Renamed from phone_numbers

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    phone_number: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    global_status: Mapped[GlobalStatus] = mapped_column(PgEnum(GlobalStatus), default=GlobalStatus.ACTIVE, nullable=False)
    last_called_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_called_company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_batch_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Relationships
    last_called_company = relationship("Company")
