import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from svix.webhooks import Webhook

from scout_coordinator.main import create_app


class FakeTaskPublisher:
    def __init__(self) -> None:
        self.items = []
        self.target_urls = []

    async def enqueue(self, task, target_url=None) -> None:
        self.items.append(task)
        self.target_urls.append(target_url)


class FakeContainer:
    def __init__(self, secret: str, task_backend: str = "local", cloud_tasks_target_url: str = "") -> None:
        self.settings = type(
            "Settings",
            (),
            {
                "resend_webhook_secret": secret,
                "task_backend": task_backend,
                "cloud_tasks_target_url": cloud_tasks_target_url,
            },
        )()
        self.task_publisher = FakeTaskPublisher()
        self.email_processor = None


def _signed_headers(secret: str, payload: bytes) -> dict[str, str]:
    timestamp = datetime.now(timezone.utc)
    return {
        "svix-id": "msg_test",
        "svix-timestamp": str(int(timestamp.timestamp())),
        "svix-signature": Webhook(secret).sign("msg_test", timestamp, payload.decode()),
    }


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


def test_resend_webhook_schedules_email() -> None:
    secret = "whsec_test"
    container = FakeContainer(secret)
    payload = json.dumps(
        {
            "type": "email.received",
            "data": {
                "email_id": "email-1",
                "from": "sender@example.com",
                "to": ["jobs@example.com"],
                "subject": "Offer",
                "message_id": "<message@example.com>",
                "attachments": [],
            },
        }
    ).encode()

    with _client_with_container(container) as client:
        response = client.post(
            "/webhooks/resend",
            content=payload,
            headers={
                **_signed_headers(secret, payload),
                "content-type": "application/json",
            },
        )

    assert response.status_code == 202
    assert len(container.task_publisher.items) == 1
    assert container.task_publisher.items[0].email_id == "email-1"
    assert container.task_publisher.items[0].webhook_id == "msg_test"
    assert container.task_publisher.items[0].correlation_id == "email-1"
    assert container.task_publisher.target_urls == [None]


def test_resend_webhook_passes_request_derived_task_url_in_cloud_tasks_mode() -> None:
    secret = "whsec_test"
    container = FakeContainer(secret, task_backend="cloud_tasks")
    payload = json.dumps(
        {
            "type": "email.received",
            "data": {
                "email_id": "email-1",
                "from": "sender@example.com",
                "to": ["jobs@example.com"],
                "subject": "Offer",
                "message_id": "<message@example.com>",
                "attachments": [],
            },
        }
    ).encode()

    with _client_with_container(container) as client:
        response = client.post(
            "/webhooks/resend",
            content=payload,
            headers={
                **_signed_headers(secret, payload),
                "content-type": "application/json",
            },
        )

    assert response.status_code == 202
    assert container.task_publisher.target_urls == ["http://testserver/tasks/process-email"]


def test_resend_webhook_rejects_invalid_signature() -> None:
    secret = "whsec_test"
    container = FakeContainer(secret)
    payload = json.dumps(
        {
            "type": "email.received",
            "data": {
                "email_id": "email-1",
                "from": "sender@example.com",
            },
        }
    ).encode()

    with _client_with_container(container) as client:
        response = client.post(
            "/webhooks/resend",
            content=payload,
            headers={"svix-id": "msg_test", "svix-timestamp": "1", "svix-signature": "bad"},
        )

    assert response.status_code == 401
    assert container.task_publisher.items == []


def test_resend_webhook_rejects_missing_signature_headers() -> None:
    secret = "whsec_test"
    container = FakeContainer(secret)
    payload = json.dumps(
        {
            "type": "email.received",
            "data": {
                "email_id": "email-1",
                "from": "sender@example.com",
            },
        }
    ).encode()

    with _client_with_container(container) as client:
        response = client.post(
            "/webhooks/resend",
            content=payload,
            headers={"content-type": "application/json"},
        )

    assert response.status_code == 401
    assert container.task_publisher.items == []


def test_resend_webhook_rejects_invalid_payload() -> None:
    secret = "whsec_test"
    container = FakeContainer(secret)
    payload = json.dumps(
        {
            "type": "email.received",
            "data": {
                "from": "sender@example.com",
            },
        }
    ).encode()

    with _client_with_container(container) as client:
        response = client.post(
            "/webhooks/resend",
            content=payload,
            headers={
                **_signed_headers(secret, payload),
                "content-type": "application/json",
            },
        )

    assert response.status_code == 400
    assert container.task_publisher.items == []


def test_resend_webhook_ignores_unsupported_event_type() -> None:
    secret = "whsec_test"
    container = FakeContainer(secret)
    payload = json.dumps(
        {
            "type": "email.delivered",
            "data": {
                "email_id": "email-1",
                "from": "sender@example.com",
            },
        }
    ).encode()

    with _client_with_container(container) as client:
        response = client.post(
            "/webhooks/resend",
            content=payload,
            headers={
                **_signed_headers(secret, payload),
                "content-type": "application/json",
            },
        )

    assert response.status_code == 202
    assert container.task_publisher.items == []
