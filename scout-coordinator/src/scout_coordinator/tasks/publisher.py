from typing import Protocol

from scout_coordinator.models import EmailProcessingTask


class TaskPublisher(Protocol):
    async def enqueue(self, task: EmailProcessingTask) -> None:
        """Schedule email processing."""

    async def stop(self) -> None:
        """Release publisher resources or wait for local background work."""
