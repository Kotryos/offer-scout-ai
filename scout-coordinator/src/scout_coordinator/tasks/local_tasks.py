import asyncio
import logging

from scout_coordinator.models import EmailProcessingTask
from scout_coordinator.logging_context import correlation_id_scope
from scout_coordinator.processing.email_processor import EmailProcessor
from scout_coordinator.tasks.publisher import TaskPublisher

log = logging.getLogger(__name__)


class LocalTaskPublisher(TaskPublisher):
    def __init__(self, processor: EmailProcessor, retry_attempts: int = 3) -> None:
        self._processor = processor
        self._retry_attempts = retry_attempts
        self._background_tasks: set[asyncio.Task[None]] = set()

    async def enqueue(self, task: EmailProcessingTask, target_url: str | None = None) -> None:
        background_task = asyncio.create_task(
            self._process_email_with_retries(task),
            name=f"local-email-task-{task.email_id}",
        )
        self._track_background_task(background_task)

    async def stop(self) -> None:
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

    def _track_background_task(self, task: asyncio.Task[None]) -> None:
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def _process_email_with_retries(self, task: EmailProcessingTask) -> None:
        with correlation_id_scope(task.correlation_id):
            for attempt in range(1, self._retry_attempts + 1):
                try:
                    await self._processor.process_email(task.email_id)
                    log.info("Processed email %s", task.email_id)
                    return
                except Exception:
                    log.exception(
                        "Failed to process email %s on attempt %s/%s",
                        task.email_id,
                        attempt,
                        self._retry_attempts,
                    )
                    if attempt < self._retry_attempts:
                        await asyncio.sleep(attempt * 2)
