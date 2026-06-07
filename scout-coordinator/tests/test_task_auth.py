from typing import cast

import pytest
from fastapi import HTTPException, Request
from starlette.datastructures import Headers

from scout_coordinator.config import Settings
from scout_coordinator.tasks import auth


class FakeRequest:
    def __init__(self, headers: dict[str, str]) -> None:
        self.headers = Headers(headers)


def _settings() -> Settings:
    return Settings(
        cloud_tasks_target_url="https://coordinator.example.com/tasks/process-email",
        cloud_tasks_service_account_email="tasks@example.iam.gserviceaccount.com",
    )


async def test_verify_task_request_accepts_expected_service_account(monkeypatch) -> None:
    def fake_verify_oauth2_token(token, request, audience):
        assert token == "test-token"
        assert audience == "https://coordinator.example.com/tasks/process-email"
        return {"email": "tasks@example.iam.gserviceaccount.com"}

    monkeypatch.setattr(auth.id_token, "verify_oauth2_token", fake_verify_oauth2_token)

    request = cast(Request, FakeRequest({"Authorization": "Bearer test-token"}))

    await auth.verify_task_request(request, _settings())


async def test_verify_task_request_rejects_wrong_service_account(monkeypatch) -> None:
    def fake_verify_oauth2_token(token, request, audience):
        return {"email": "other@example.iam.gserviceaccount.com"}

    monkeypatch.setattr(auth.id_token, "verify_oauth2_token", fake_verify_oauth2_token)

    with pytest.raises(HTTPException) as exc_info:
        request = cast(Request, FakeRequest({"Authorization": "Bearer test-token"}))
        await auth.verify_task_request(request, _settings())

    assert exc_info.value.status_code == 403


async def test_verify_task_request_rejects_invalid_token(monkeypatch) -> None:
    def fake_verify_oauth2_token(token, request, audience):
        raise ValueError("bad token")

    monkeypatch.setattr(auth.id_token, "verify_oauth2_token", fake_verify_oauth2_token)

    with pytest.raises(HTTPException) as exc_info:
        request = cast(Request, FakeRequest({"Authorization": "Bearer test-token"}))
        await auth.verify_task_request(request, _settings())

    assert exc_info.value.status_code == 401


async def test_verify_task_request_rejects_missing_authorization_header() -> None:
    with pytest.raises(HTTPException) as exc_info:
        request = cast(Request, FakeRequest({}))
        await auth.verify_task_request(request, _settings())

    assert exc_info.value.status_code == 401
