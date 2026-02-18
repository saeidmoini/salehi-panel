from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.deps import get_company_user
from app.models.phone_number import CallStatus
from app.services import phone_service


def test_get_company_user_allows_superuser():
    user = SimpleNamespace(is_superuser=True, company_id=None)
    company = SimpleNamespace(id=2)
    assert get_company_user(user, company) is user


def test_get_company_user_blocks_wrong_company_user():
    user = SimpleNamespace(is_superuser=False, company_id=1)
    company = SimpleNamespace(id=2)
    with pytest.raises(HTTPException) as exc:
        get_company_user(user, company)
    assert exc.value.status_code == 403


def test_resolve_company_id_blocks_non_superuser_cross_company(monkeypatch):
    class FakeQuery:
        def __init__(self, company):
            self.company = company

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return self.company

    class FakeDB:
        def query(self, _model):
            return FakeQuery(SimpleNamespace(id=2, name="saeid"))

    user = SimpleNamespace(is_superuser=False, company_id=1)
    with pytest.raises(HTTPException) as exc:
        phone_service._resolve_company_id(FakeDB(), user, "saeid")
    assert exc.value.status_code == 403


def test_mutable_guard_blocks_immutable_for_non_superuser(monkeypatch):
    monkeypatch.setattr(phone_service, "_latest_status_for_company", lambda *args, **kwargs: CallStatus.CONNECTED)
    with pytest.raises(HTTPException) as exc:
        phone_service._ensure_mutable_for_user(
            db=SimpleNamespace(),
            number_id=1,
            company_id=1,
            current_user=SimpleNamespace(is_superuser=False),
        )
    assert exc.value.status_code == 400


def test_mutable_guard_allows_superuser(monkeypatch):
    monkeypatch.setattr(phone_service, "_latest_status_for_company", lambda *args, **kwargs: CallStatus.CONNECTED)
    phone_service._ensure_mutable_for_user(
        db=SimpleNamespace(),
        number_id=1,
        company_id=1,
        current_user=SimpleNamespace(is_superuser=True),
    )
