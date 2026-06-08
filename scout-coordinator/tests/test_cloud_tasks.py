import json

from google.api_core.exceptions import AlreadyExists
from google.cloud import tasks_v2

from scout_coordinator.models import EmailProcessingTask
from scout_coordinator.tasks.cloud_tasks import CloudTasksPublisher


class FakeCloudTasksClient:
    def __init__(self) -> None:
        self.created = None

    def queue_path(self, project: str, location: str, queue: str) -> str:
        return f"projects/{project}/locations/{location}/queues/{queue}"

    def task_path(self, project: str, location: str, queue: str, task: str) -> str:
        return f"projects/{project}/locations/{location}/queues/{queue}/tasks/{task}"

    async def create_task(self, parent, task):
        self.created = {"parent": parent, "task": task}


class AlreadyExistsCloudTasksClient(FakeCloudTasksClient):
    async def create_task(self, parent, task):
        raise AlreadyExists("Task already exists")


async def test_cloud_tasks_publisher_creates_http_task() -> None:
    client = FakeCloudTasksClient()
    publisher = CloudTasksPublisher(
        project="project-1",
        location="europe-west1",
        queue="email-processing",
        target_url="https://coordinator.example.com/tasks/process-email",
        service_account_email="tasks@example.iam.gserviceaccount.com",
        dispatch_deadline_seconds=600,
        client=client,  # type: ignore[arg-type]
    )

    await publisher.enqueue(EmailProcessingTask(email_id="email-1", webhook_id="webhook-1", correlation_id="email-1"))

    assert client.created is not None
    assert client.created["parent"] == "projects/project-1/locations/europe-west1/queues/email-processing"
    cloud_task = client.created["task"]
    assert cloud_task.name.endswith("/tasks/email-email-1")
    assert cloud_task.http_request.http_method == tasks_v2.HttpMethod.POST
    assert cloud_task.http_request.url == "https://coordinator.example.com/tasks/process-email"
    assert cloud_task.http_request.headers["Content-Type"] == "application/json"
    assert cloud_task.http_request.oidc_token.service_account_email == "tasks@example.iam.gserviceaccount.com"
    assert cloud_task.http_request.oidc_token.audience == "https://coordinator.example.com/tasks/process-email"
    assert json.loads(cloud_task.http_request.body) == {
        "email_id": "email-1",
        "webhook_id": "webhook-1",
        "correlation_id": "email-1",
    }
    assert cloud_task.dispatch_deadline.seconds == 600


async def test_cloud_tasks_publisher_uses_enqueue_target_url_when_not_configured() -> None:
    client = FakeCloudTasksClient()
    publisher = CloudTasksPublisher(
        project="project-1",
        location="europe-west1",
        queue="email-processing",
        target_url="",
        service_account_email="tasks@example.iam.gserviceaccount.com",
        dispatch_deadline_seconds=600,
        client=client,  # type: ignore[arg-type]
    )

    await publisher.enqueue(
        EmailProcessingTask(email_id="email-1", webhook_id="webhook-1", correlation_id="email-1"),
        target_url="https://coordinator.example.com/tasks/process-email",
    )

    assert client.created is not None
    cloud_task = client.created["task"]
    assert cloud_task.http_request.url == "https://coordinator.example.com/tasks/process-email"
    assert cloud_task.http_request.oidc_token.audience == "https://coordinator.example.com/tasks/process-email"


async def test_cloud_tasks_publisher_requires_target_url() -> None:
    publisher = CloudTasksPublisher(
        project="project-1",
        location="europe-west1",
        queue="email-processing",
        target_url="",
        service_account_email="tasks@example.iam.gserviceaccount.com",
        dispatch_deadline_seconds=600,
        client=FakeCloudTasksClient(),  # type: ignore[arg-type]
    )

    try:
        await publisher.enqueue(EmailProcessingTask(email_id="email-1", webhook_id="webhook-1", correlation_id="email-1"))
    except ValueError as exc:
        assert str(exc) == "Cloud Task target URL is required"
    else:
        raise AssertionError("Expected ValueError")


async def test_cloud_tasks_publisher_ignores_existing_task() -> None:
    publisher = CloudTasksPublisher(
        project="project-1",
        location="europe-west1",
        queue="email-processing",
        target_url="https://coordinator.example.com/tasks/process-email",
        service_account_email="tasks@example.iam.gserviceaccount.com",
        dispatch_deadline_seconds=600,
        client=AlreadyExistsCloudTasksClient(),  # type: ignore[arg-type]
    )

    await publisher.enqueue(EmailProcessingTask(email_id="email-1", webhook_id="webhook-1", correlation_id="email-1"))
