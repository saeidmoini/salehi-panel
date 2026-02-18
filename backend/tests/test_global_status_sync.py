from types import SimpleNamespace

from app.models.phone_number import CallStatus, GlobalStatus
from app.services import phone_service


def test_sync_global_status_sets_power_off():
    number = SimpleNamespace(global_status=GlobalStatus.ACTIVE)
    phone_service._sync_global_status_from_call_status(number, CallStatus.POWER_OFF)
    assert number.global_status == GlobalStatus.POWER_OFF


def test_sync_global_status_sets_complained():
    number = SimpleNamespace(global_status=GlobalStatus.ACTIVE)
    phone_service._sync_global_status_from_call_status(number, CallStatus.COMPLAINED)
    assert number.global_status == GlobalStatus.COMPLAINED


def test_sync_global_status_ignores_other_statuses():
    number = SimpleNamespace(global_status=GlobalStatus.COMPLAINED)
    phone_service._sync_global_status_from_call_status(number, CallStatus.MISSED)
    assert number.global_status == GlobalStatus.ACTIVE
