import httpx

from scout_coordinator.models import ReceivedEmail


class ResendClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
            },
            timeout=timeout_seconds,
            transport=transport,
        )

    async def get_received_email(self, email_id: str) -> ReceivedEmail:
        response = await self._client.get(f"/emails/receiving/{email_id}")
        response.raise_for_status()
        return ReceivedEmail.model_validate(response.json())

    async def get_attachment_download_url(self, email_id: str, attachment_id: str) -> str:
        response = await self._client.get(f"/emails/receiving/{email_id}/attachments/{attachment_id}")
        response.raise_for_status()
        data = response.json()
        download_url = data.get("download_url") or data.get("raw", {}).get("download_url")
        if not download_url:
            raise ValueError(f"Attachment {attachment_id} response did not include a download_url")
        return download_url

    async def download_attachment(self, download_url: str) -> bytes:
        response = await self._client.get(download_url)
        response.raise_for_status()
        return response.content

    async def close(self) -> None:
        await self._client.aclose()
