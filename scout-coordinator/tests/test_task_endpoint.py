from fastapi.testclient import TestClient

from scout_coordinator.logging_context import get_correlation_id
from scout_coordinator.main import create_app


class FakeProcessor:
    def __init__(self) -> None:
        self.email_ids = []
        self.correlation_ids = []

    async def process_email(self, email_id: str) -> None:
        self.email_ids.append(email_id)
        self.correlation_ids.append(get_correlation_id())


class FakeContainer:
    def __init__(self, task_backend: str = "local") -> None:
        self.settings = type(
            "Settings",
            (),
            {
                "resend_webhook_secret": "whsec_test",
                "task_backend": task_backend,
                "cloud_tasks_oidc_audience": "",
                "cloud_tasks_target_url": "",
                "cloud_tasks_service_account_email": "",
            },
        )()
        self.email_processor = FakeProcessor()


def _client_with_container(container: FakeContainer) -> TestClient:
    app = create_app()
    app.router.lifespan_context = _fake_lifespan(container)
    return TestClient(app)


def _fake_lifespan(container: FakeContainer):
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(app):
        app.state.container = container
        yield

    return lifespan


def test_task_endpoint_processes_email_after_cloud_tasks_auth(monkeypatch) -> None:
    async def fake_verify_task_request(request, settings) -> None:
        return None

    monkeypatch.setattr("scout_coordinator.main.verify_task_request", fake_verify_task_request)
    container = FakeContainer(task_backend="cloud_tasks")

    with _client_with_container(container) as client:
        response = client.post(
            "/tasks/process-email",
            json={"email_id": "email-1", "webhook_id": "webhook-1", "correlation_id": "email-1"},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "processed"}
    assert container.email_processor.email_ids == ["email-1"]
    assert container.email_processor.correlation_ids == ["email-1"]


def test_task_endpoint_is_disabled_in_local_mode() -> None:
    container = FakeContainer()

    with _client_with_container(container) as client:
        response = client.post(
            "/tasks/process-email",
            json={"email_id": "email-1", "webhook_id": "webhook-1", "correlation_id": "email-1"},
        )

    assert response.status_code == 404
    assert container.email_processor.email_ids == []


def test_task_endpoint_rejects_cloud_tasks_request_without_bearer_token() -> None:
    container = FakeContainer(task_backend="cloud_tasks")

    with _client_with_container(container) as client:
        response = client.post(
            "/tasks/process-email",
            json={"email_id": "email-1", "correlation_id": "email-1"},
        )

    assert response.status_code == 401
    assert container.email_processor.email_ids == []
