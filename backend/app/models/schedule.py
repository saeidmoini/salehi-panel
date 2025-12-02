from datetime import datetime, time
from sqlalchemy import Integer, Boolean, DateTime, Time, func
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db import Base


class ScheduleConfig(Base):
    __tablename__ = "schedule_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    skip_holidays: Mapped[bool] = mapped_column(Boolean, default=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ScheduleWindow(Base):
    __tablename__ = "schedule_windows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day_of_week: Mapped[int] = mapped_column(Integer, index=True)  # 0 = Saturday, 6 = Friday
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
