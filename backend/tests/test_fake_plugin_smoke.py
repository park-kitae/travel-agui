import importlib
import json
import sys

import httpx  # type: ignore[reportMissingImports]
import pytest  # type: ignore[reportMissingImports]

import main
from domain_runtime import reset_runtime_for_tests
from domains import DomainPlugin


REAL_HTTPX_ASYNC_CLIENT = httpx.AsyncClient


def parse_sse_events(raw: str) -> list[dict]:
    events: list[dict] = []
    for line in raw.splitlines():
        if not line.startswith("data:"):
            continue
        payload = line[len("data:"):].strip()
        if payload:
            events.append(json.loads(payload))
    return events


async def _empty_adk_stream(*_args, **_kwargs):
    if False:
        yield None


@pytest.fixture(autouse=True)
def _reset_runtime_and_modules():
    reset_runtime_for_tests()
    yield
    reset_runtime_for_tests()
    sys.modules.pop("a2a_server", None)


def _import_a2a_server_with_fake_plugin(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DOMAIN_PLUGIN", "domains.fake.plugin:get_plugin")
    reset_runtime_for_tests()
    sys.modules.pop("a2a_server", None)
    return importlib.import_module("a2a_server")


def test_fake_plugin_implements_shared_contract_and_generic_context(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DOMAIN_PLUGIN", "domains.fake.plugin:get_plugin")

    from domains.fake.plugin import FakeState, get_plugin

    plugin = get_plugin()
    merged_state = plugin.merge_client_state(plugin.empty_state(), {"notes": ["minimal"]})
    serialized = plugin.serialize_state(merged_state)
    restored_state = plugin.deserialize_state(serialized)
    context = plugin.build_context_block(restored_state, "ping")

    assert isinstance(plugin, DomainPlugin)
    assert isinstance(restored_state, FakeState)
    assert serialized == {"notes": ["minimal"], "turn_count": 1}
    assert context == "[fake-domain]\nnotes=minimal\nuser=ping"
    assert "destination" not in context
    assert "travel_context" not in context


@pytest.mark.asyncio
async def test_fake_plugin_smoke_request_returns_standard_lifecycle(client, monkeypatch: pytest.MonkeyPatch):
    a2a_server = _import_a2a_server_with_fake_plugin(monkeypatch)
    a2a_server.runner.run_async = _empty_adk_stream

    transport = httpx.ASGITransport(app=a2a_server.app)

    def build_a2a_http_client(*_args, **_kwargs) -> httpx.AsyncClient:
        return REAL_HTTPX_ASYNC_CLIENT(transport=transport, base_url=main.A2A_SERVER_URL)

    monkeypatch.setattr(main.httpx, "AsyncClient", build_a2a_http_client)

    response = await client.post(
        "/agui/run",
        json={
            "thread_id": "fake-thread-001",
            "run_id": "fake-run-001",
            "messages": [{"id": "msg-001", "role": "user", "content": "ping fake plugin"}],
            "state": {"notes": ["smoke"]},
            "tools": [],
            "context": [],
            "forwardedProps": {},
        },
    )

    assert response.status_code == 200
    assert a2a_server.agent_card.name == "fake_agent"

    events = parse_sse_events(response.text)
    assert [event["type"] for event in events] == [
        "RUN_STARTED",
        "STEP_STARTED",
        "STEP_FINISHED",
        "RUN_FINISHED",
    ]
