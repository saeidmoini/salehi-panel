from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db import Base
from .phone_number import CallStatus


class CallDirection(str, Enum):
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"


class CallResult(Base):
    __tablename__ = "call_results"  # Renamed from call_attempts

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone_number_id: Mapped[int] = mapped_column(ForeignKey("numbers.id"), index=True)  # Updated FK reference
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), index=True, nullable=True)
    scenario_id: Mapped[int | None] = mapped_column(ForeignKey("scenarios.id"), nullable=True)
    outbound_line_id: Mapped[int | None] = mapped_column(ForeignKey("outbound_lines.id"), nullable=True)
    call_direction: Mapped[CallDirection] = mapped_column(String(16), nullable=False, default=CallDirection.OUTBOUND)
    status: Mapped[CallStatus] = mapped_column(String(32))
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    user_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    agent_id: Mapped[int | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    # Relationships
    phone_number = relationship("PhoneNumber")
    company = relationship("Company")
    scenario = relationship("Scenario")
    outbound_line = relationship("OutboundLine")
    agent = relationship("AdminUser")
