from datetime import datetime
from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db import Base


class DialerBatch(Base):
    __tablename__ = "dialer_batches"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    requested_size: Mapped[int] = mapped_column(Integer, nullable=False)
    returned_size: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
