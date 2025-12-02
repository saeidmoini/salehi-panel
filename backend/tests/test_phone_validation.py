from datetime import time, datetime
from zoneinfo import ZoneInfo

from app.services.phone_service import normalize_phone
from app.services.schedule_service import _next_start, TEHRAN_TZ
from app.models.schedule import ScheduleWindow


def test_normalize_phone_accepts_common_formats():
    assert normalize_phone("09123456789") == "09123456789"
    assert normalize_phone("+989123456789") == "09123456789"
    assert normalize_phone("00989123456789") == "09123456789"
    assert normalize_phone("9123456789") == "09123456789"


def test_normalize_phone_rejects_invalid_numbers():
    assert normalize_phone("12345") is None
    assert normalize_phone("071234567890") is None


def test_next_start_rolls_over_week():
    now = datetime(2024, 1, 1, 23, 0, tzinfo=TEHRAN_TZ)
    intervals = [ScheduleWindow(day_of_week=1, start_time=time(9, 0), end_time=time(10, 0))]
    nxt = _next_start(now, intervals)
    assert nxt.tzinfo == TEHRAN_TZ
    assert nxt.date() >= now.date()
