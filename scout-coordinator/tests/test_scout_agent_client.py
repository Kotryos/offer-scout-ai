import json

import httpx
import pytest

from scout_coordinator.integrations import scout_agent
from scout_coordinator.integrations.scout_agent import ScoutAgentClient


async def test_scout_agent_client_calls_agent_without_auth_header_in_none_auth_mode() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"evaluation": "Worth pursuing."})

    client = ScoutAgentClient(
        base_url="https://agent.example.com",
        timeout_seconds=120.0,
        transport=httpx.MockTransport(handler),
    )

    try:
        evaluation = await client.evaluate_offer("offer", "profile")
    finally:
        await client.close()

    assert evaluation == "Worth pursuing."
    assert requests[0].url == "https://agent.example.com/offer/evaluation"
    assert requests[0].headers.get("authorization") is None
    assert json.loads(requests[0].read()) == {
        "offerText": "offer",
        "profileContext": "profile",
    }


async def test_scout_agent_client_calls_agent_with_bearer_token_in_cloud_run_oidc_auth_mode(monkeypatch) -> None:
    def fake_fetch_id_token(request, audience: str) -> str:
        assert audience == "https://agent.example.com"
        return "test-token"

    monkeypatch.setattr(scout_agent.id_token, "fetch_id_token", fake_fetch_id_token)
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"evaluation": "Worth pursuing."})

    client = ScoutAgentClient(
        base_url="https://agent.example.com",
        timeout_seconds=120.0,
        auth_mode="cloud_run_oidc",
        transport=httpx.MockTransport(handler),
    )

    try:
        evaluation = await client.evaluate_offer("offer", "profile")
    finally:
        await client.close()

    assert evaluation == "Worth pursuing."
    assert requests[0].headers["authorization"] == "Bearer test-token"
    assert json.loads(requests[0].read()) == {
        "offerText": "offer",
        "profileContext": "profile",
    }


async def test_scout_agent_client_raises_for_agent_http_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, request=request)

    client = ScoutAgentClient(
        base_url="https://agent.example.com",
        timeout_seconds=120.0,
        transport=httpx.MockTransport(handler),
    )

    try:
        with pytest.raises(httpx.HTTPStatusError):
            await client.evaluate_offer("offer", "profile")
    finally:
        await client.close()


async def test_scout_agent_client_raises_when_agent_response_has_no_evaluation() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    client = ScoutAgentClient(
        base_url="https://agent.example.com",
        timeout_seconds=120.0,
        transport=httpx.MockTransport(handler),
    )

    try:
        with pytest.raises(ValueError, match="did not include an evaluation"):
            await client.evaluate_offer("offer", "profile")
    finally:
        await client.close()
