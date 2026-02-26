from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db import Base


class DialerBatchItem(Base):
    __tablename__ = "dialer_batch_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True, nullable=False)
    phone_number_id: Mapped[int] = mapped_column(ForeignKey("numbers.id"), index=True, nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    reported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    report_batch_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    report_call_result_id: Mapped[int | None] = mapped_column(ForeignKey("call_results.id"), index=True, nullable=True)
    report_attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    report_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    report_scenario_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    report_outbound_line_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    report_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company")
    phone_number = relationship("PhoneNumber")
    call_result = relationship("CallResult")
