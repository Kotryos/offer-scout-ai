from scout_coordinator.models import EmailProcessingTask
from scout_coordinator.logging_context import get_correlation_id
from scout_coordinator.tasks.local_tasks import LocalTaskPublisher


class FakeProcessor:
    def __init__(self) -> None:
        self.email_ids: list[str] = []
        self.correlation_ids: list[str | None] = []

    async def process_email(self, email_id: str) -> None:
        self.email_ids.append(email_id)
        self.correlation_ids.append(get_correlation_id())


class FailOnceProcessor:
    def __init__(self) -> None:
        self.calls = 0

    async def process_email(self, email_id: str) -> None:
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("temporary failure")


async def test_local_task_publisher_processes_enqueued_task() -> None:
    processor = FakeProcessor()
    publisher = LocalTaskPublisher(processor=processor, retry_attempts=2)  # type: ignore[arg-type]

    await publisher.enqueue(EmailProcessingTask(email_id="email-1", webhook_id="webhook-1", correlation_id="email-1"))
    await publisher.stop()

    assert processor.email_ids == ["email-1"]
    assert processor.correlation_ids == ["email-1"]


async def test_local_task_publisher_retries_failed_processing() -> None:
    processor = FailOnceProcessor()
    publisher = LocalTaskPublisher(processor=processor, retry_attempts=2)  # type: ignore[arg-type]

    await publisher.enqueue(EmailProcessingTask(email_id="email-1", webhook_id="webhook-1", correlation_id="email-1"))
    await publisher.stop()

    assert processor.calls == 2
