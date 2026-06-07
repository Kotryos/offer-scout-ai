import anyio
from fastapi import HTTPException, Request, status
from google.auth.transport import requests
from google.oauth2 import id_token

from scout_coordinator.config import Settings


async def verify_task_request(request: Request, settings: Settings) -> None:
    authorization = request.headers.get("authorization", "")
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    bearer_token = authorization.split(" ", 1)[1]
    audience = settings.cloud_tasks_oidc_audience or settings.cloud_tasks_target_url

    try:
        claims = await anyio.to_thread.run_sync(
            id_token.verify_oauth2_token,
            bearer_token,
            requests.Request(),
            audience,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid task bearer token") from exc

    expected_email = settings.cloud_tasks_service_account_email
    if expected_email and claims.get("email") != expected_email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unexpected task service account")
