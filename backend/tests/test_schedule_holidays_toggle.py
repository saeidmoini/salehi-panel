from datetime import datetime, time
from types import SimpleNamespace

from app.services import schedule_service


class DummyDB:
    def commit(self):
        return None

    def refresh(self, _obj):
        return None


def test_skip_holidays_toggle_controls_holiday_block(monkeypatch):
    db = DummyDB()
    now = datetime.now(schedule_service.TEHRAN_TZ)
    day = schedule_service._iran_weekday(now)
    interval = SimpleNamespace(day_of_week=day, start_time=time(0, 0), end_time=time(23, 59))

    config = SimpleNamespace(
        wallet_balance=1000,
        enabled=True,
        skip_holidays=True,
        disabled_by_dialer=False,
        version=1,
    )
    monkeypatch.setattr(schedule_service, "ensure_config", lambda _db, company_id=None: config)
    monkeypatch.setattr(schedule_service, "list_intervals", lambda _db, company_id=None: [interval])
    monkeypatch.setattr(schedule_service, "is_holiday", lambda _now: True)

    allowed, reason, retry = schedule_service.is_call_allowed(now, db, company_id=None)
    assert allowed is False
    assert reason == "holiday"
    assert retry == 900

    config.skip_holidays = False
    allowed, reason, retry = schedule_service.is_call_allowed(now, db, company_id=None)
    assert allowed is True
    assert reason is None
    assert retry == 0
