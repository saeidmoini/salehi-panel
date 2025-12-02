from datetime import datetime, timezone
from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db import Base
from .phone_number import CallStatus


class CallAttempt(Base):
    __tablename__ = "call_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone_number_id: Mapped[int] = mapped_column(ForeignKey("phone_numbers.id"), index=True)
    status: Mapped[CallStatus] = mapped_column(String(32))
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    phone_number = relationship("PhoneNumber")
