import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response, status
from pydantic import ValidationError
from svix.webhooks import Webhook, WebhookVerificationError

from scout_coordinator.config import Settings, get_settings
from scout_coordinator.integrations.gmail import GmailSmtpSender
from scout_coordinator.integrations.resend import ResendClient
from scout_coordinator.integrations.scout_agent import ScoutAgentClient
from scout_coordinator.models import EmailProcessingTask, ResendWebhookEvent
from scout_coordinator.processing.email_processor import EmailProcessor
from scout_coordinator.tasks.auth import verify_task_request
from scout_coordinator.tasks.cloud_tasks import CloudTasksPublisher
from scout_coordinator.tasks.local_tasks import LocalTaskPublisher
from scout_coordinator.tasks.publisher import TaskPublisher

log = logging.getLogger(__name__)


class AppContainer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.resend_client = ResendClient(
            api_key=settings.resend_api_key,
            base_url=settings.resend_base_url,
            timeout_seconds=settings.resend_timeout_seconds,
        )
        self.scout_agent_client = ScoutAgentClient(
            base_url=settings.scout_agent_base_url,
            timeout_seconds=settings.scout_agent_timeout_seconds,
            auth_mode=settings.scout_agent_auth_mode,
            audience=settings.scout_agent_audience,
        )
        self.gmail_sender = GmailSmtpSender(
            username=settings.gmail_smtp_username,
            app_password=settings.gmail_smtp_app_password,
            host=settings.gmail_smtp_host,
            port=settings.gmail_smtp_port,
        )
        self.email_processor = EmailProcessor(
            resend_client=self.resend_client,
            scout_agent_client=self.scout_agent_client,
            gmail_sender=self.gmail_sender,
            profile_context=settings.profile_context,
            max_attachment_bytes=settings.max_attachment_bytes,
            max_offer_text_chars=settings.max_offer_text_chars,
        )
        self.task_publisher: TaskPublisher = self._create_task_publisher(settings)

    async def stop(self) -> None:
        await self.task_publisher.stop()
        await self.resend_client.close()
        await self.scout_agent_client.close()

    def _create_task_publisher(self, settings: Settings) -> TaskPublisher:
        if settings.task_backend == "local":
            return LocalTaskPublisher(
                processor=self.email_processor,
                retry_attempts=settings.local_task_retry_attempts,
            )

        if settings.task_backend == "cloud_tasks":
            missing = [
                name
                for name, value in {
                    "CLOUD_TASKS_PROJECT": settings.cloud_tasks_project,
                    "CLOUD_TASKS_LOCATION": settings.cloud_tasks_location,
                    "CLOUD_TASKS_QUEUE": settings.cloud_tasks_queue,
                    "CLOUD_TASKS_TARGET_URL": settings.cloud_tasks_target_url,
                    "CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL": settings.cloud_tasks_service_account_email,
                }.items()
                if not value
            ]
            if missing:
                raise RuntimeError(f"Missing Cloud Tasks configuration: {', '.join(missing)}")

            return CloudTasksPublisher(
                project=settings.cloud_tasks_project,
                location=settings.cloud_tasks_location,
                queue=settings.cloud_tasks_queue,
                target_url=settings.cloud_tasks_target_url,
                service_account_email=settings.cloud_tasks_service_account_email,
                oidc_audience=settings.cloud_tasks_oidc_audience,
                dispatch_deadline_seconds=settings.cloud_tasks_dispatch_deadline_seconds,
            )

        raise RuntimeError(f"Unsupported TASK_BACKEND={settings.task_backend}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(level=settings.log_level.upper())
    container = AppContainer(settings)
    app.state.container = container
    yield
    await container.stop()


def create_app() -> FastAPI:
    app = FastAPI(title="Scout Coordinator", lifespan=lifespan)

    @app.post("/webhooks/resend", status_code=status.HTTP_202_ACCEPTED)
    async def handle_resend_webhook(request: Request) -> Response:
        container: AppContainer = request.app.state.container
        payload = await request.body()

        try:
            Webhook(container.settings.resend_webhook_secret).verify(payload, request.headers)
        except WebhookVerificationError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature") from exc

        try:
            event = ResendWebhookEvent.model_validate_json(payload)
        except ValidationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook payload") from exc

        if event.type != "email.received":
            log.info("Ignoring Resend event type %s", event.type)
            return Response(status_code=status.HTTP_202_ACCEPTED)

        webhook_id = request.headers.get("svix-id")
        await container.task_publisher.enqueue(
            EmailProcessingTask(email_id=event.data.email_id, webhook_id=webhook_id)
        )
        log.info("Scheduled email %s from webhook %s", event.data.email_id, webhook_id)
        return Response(status_code=status.HTTP_202_ACCEPTED)

    @app.post("/tasks/process-email")
    async def process_email_task(request: Request, task: EmailProcessingTask) -> dict[str, str]:
        container: AppContainer = request.app.state.container
        if container.settings.task_backend != "cloud_tasks":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task endpoint is disabled")

        await verify_task_request(request, container.settings)
        await container.email_processor.process_email(task.email_id)
        return {"status": "processed"}

    return app


app = create_app()
