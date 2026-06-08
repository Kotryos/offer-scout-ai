import anyio
import httpx
from google.auth.transport.requests import Request
from google.oauth2 import id_token

from scout_coordinator.logging_context import get_correlation_id


class ScoutAgentClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        auth_mode: str = "none",
        audience: str = "",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._auth_mode = auth_mode
        self._audience = audience or self._base_url
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout_seconds,
            transport=transport,
        )

        if self._auth_mode not in {"none", "cloud_run_oidc"}:
            raise ValueError(f"Unsupported scout-agent auth mode: {self._auth_mode}")

    async def evaluate_offer(self, offer_text: str, profile_context: str) -> str:
        response = await self._client.post(
            "/offer/evaluation",
            json={
                "offerText": offer_text,
                "profileContext": profile_context,
            },
            headers=await self._request_headers(),
        )
        response.raise_for_status()
        evaluation = response.json().get("evaluation")
        if evaluation is None:
            raise ValueError("Scout agent response did not include an evaluation")
        return evaluation

    async def close(self) -> None:
        await self._client.aclose()

    async def _request_headers(self) -> dict[str, str]:
        headers = await self._auth_headers()
        correlation_id = get_correlation_id()
        if correlation_id != "-":
            headers["X-Correlation-Id"] = correlation_id
        return headers

    async def _auth_headers(self) -> dict[str, str]:
        if self._auth_mode == "none":
            return {}

        token = await anyio.to_thread.run_sync(
            id_token.fetch_id_token,
            Request(),
            self._audience,
        )
        return {"Authorization": f"Bearer {token}"}
