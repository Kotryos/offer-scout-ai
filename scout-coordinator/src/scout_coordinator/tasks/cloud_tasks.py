import logging

from google.api_core.exceptions import AlreadyExists
from google.cloud import tasks_v2

from scout_coordinator.models import EmailProcessingTask
from scout_coordinator.tasks.publisher import TaskPublisher

log = logging.getLogger(__name__)


class CloudTasksPublisher(TaskPublisher):
    def __init__(
        self,
        project: str,
        location: str,
        queue: str,
        target_url: str,
        service_account_email: str,
        dispatch_deadline_seconds: int,
        oidc_audience: str = "",
        client: tasks_v2.CloudTasksAsyncClient | None = None,
    ) -> None:
        self._client = client or tasks_v2.CloudTasksAsyncClient()
        self._parent = self._client.queue_path(project, location, queue)
        self._target_url = target_url
        self._service_account_email = service_account_email
        self._oidc_audience = oidc_audience or target_url
        self._dispatch_deadline_seconds = dispatch_deadline_seconds

    async def enqueue(self, task: EmailProcessingTask) -> None:
        cloud_task = self._build_task(task)
        try:
            await self._client.create_task(parent=self._parent, task=cloud_task)
        except AlreadyExists:
            log.info("Cloud Task already exists for email %s", task.email_id)

    async def stop(self) -> None:
        return None

    def _build_task(self, task: EmailProcessingTask) -> tasks_v2.Task:
        payload = task.model_dump_json(exclude_none=True).encode("utf-8")
        return tasks_v2.Task(
            {
                "name": self._client.task_path(
                    *self._parent.split("/")[1::2],
                    f"email-{task.email_id}",
                ),
                "http_request": {
                    "http_method": tasks_v2.HttpMethod.POST,
                    "url": self._target_url,
                    "headers": {"Content-Type": "application/json"},
                    "body": payload,
                    "oidc_token": {
                        "service_account_email": self._service_account_email,
                        "audience": self._oidc_audience,
                    },
                },
                "dispatch_deadline": {"seconds": self._dispatch_deadline_seconds},
            }
        )
