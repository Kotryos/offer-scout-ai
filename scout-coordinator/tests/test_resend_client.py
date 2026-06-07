import httpx
import pytest

from scout_coordinator.integrations.resend import ResendClient


def _received_email_response() -> dict:
    return {
        "id": "email-1",
        "from": "sender@example.com",
        "to": ["jobs@example.com"],
        "subject": "Test offer",
        "text": "Please check this offer.",
        "attachments": [],
    }


async def test_resend_client_fetches_received_email_with_authorization_header() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=_received_email_response())

    client = ResendClient(
        api_key="test-key",
        base_url="https://resend.example.com/",
        timeout_seconds=30.0,
        transport=httpx.MockTransport(handler),
    )

    try:
        email = await client.get_received_email("email-1")
    finally:
        await client.close()

    assert email.id == "email-1"
    assert email.from_email == "sender@example.com"
    assert requests[0].url == "https://resend.example.com/emails/receiving/email-1"
    assert requests[0].headers["authorization"] == "Bearer test-key"


async def test_resend_client_gets_attachment_download_url() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://resend.example.com/emails/receiving/email-1/attachments/att-1"
        return httpx.Response(200, json={"download_url": "https://cdn.example.com/att-1"})

    client = ResendClient(
        api_key="test-key",
        base_url="https://resend.example.com",
        timeout_seconds=30.0,
        transport=httpx.MockTransport(handler),
    )

    try:
        download_url = await client.get_attachment_download_url("email-1", "att-1")
    finally:
        await client.close()

    assert download_url == "https://cdn.example.com/att-1"


async def test_resend_client_downloads_attachment_bytes() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://cdn.example.com/att-1"
        return httpx.Response(200, content=b"attachment bytes")

    client = ResendClient(
        api_key="test-key",
        base_url="https://resend.example.com",
        timeout_seconds=30.0,
        transport=httpx.MockTransport(handler),
    )

    try:
        data = await client.download_attachment("https://cdn.example.com/att-1")
    finally:
        await client.close()

    assert data == b"attachment bytes"


async def test_resend_client_rejects_attachment_response_without_download_url() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    client = ResendClient(
        api_key="test-key",
        base_url="https://resend.example.com",
        timeout_seconds=30.0,
        transport=httpx.MockTransport(handler),
    )

    try:
        with pytest.raises(ValueError, match="did not include a download_url"):
            await client.get_attachment_download_url("email-1", "att-1")
    finally:
        await client.close()


@pytest.mark.parametrize("status_code", [404, 500])
async def test_resend_client_raises_for_received_email_http_error(status_code: int) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, request=request)

    client = ResendClient(
        api_key="test-key",
        base_url="https://resend.example.com",
        timeout_seconds=30.0,
        transport=httpx.MockTransport(handler),
    )

    try:
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_received_email("email-1")
    finally:
        await client.close()


@pytest.mark.parametrize("status_code", [404, 500])
async def test_resend_client_raises_for_attachment_download_url_http_error(status_code: int) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, request=request)

    client = ResendClient(
        api_key="test-key",
        base_url="https://resend.example.com",
        timeout_seconds=30.0,
        transport=httpx.MockTransport(handler),
    )

    try:
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_attachment_download_url("email-1", "att-1")
    finally:
        await client.close()
