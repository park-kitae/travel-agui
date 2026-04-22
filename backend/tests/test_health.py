"""/health 엔드포인트 테스트."""

from __future__ import annotations

import importlib
import sys
from dataclasses import dataclass

from domain_runtime import get_runtime, reset_runtime_for_tests
from domains.travel.plugin import get_plugin

try:  # pragma: no cover - runtime dependency may be absent in test env
    from a2a.types import AgentCapabilities, AgentCard, AgentSkill  # type: ignore[reportMissingImports]
except ModuleNotFoundError:  # pragma: no cover - fallback for isolated unit tests
    @dataclass
    class AgentCapabilities:  # type: ignore[no-redef]
        streaming: bool = False

    @dataclass
    class AgentSkill:  # type: ignore[no-redef]
        id: str
        name: str
        description: str
        tags: list[str]

    @dataclass
    class AgentCard:  # type: ignore[no-redef]
        name: str
        description: str
        url: str
        version: str
        default_input_modes: list[str]
        default_output_modes: list[str]
        capabilities: AgentCapabilities
        skills: list[AgentSkill]


async def test_health(client):
    response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["mode"] == "a2a-client"
    assert "a2a_server" in data


def test_a2a_server_uses_runtime_plugin_for_agent_and_agent_card(monkeypatch):
    reset_runtime_for_tests()
    plugin = get_plugin()
    build_agent_calls = {"count": 0}
    original_build_agent = plugin.build_agent
    sentinel_card = AgentCard(
        name="runtime-backed-agent",
        description="Sentinel runtime-backed agent card",
        url="http://localhost:8001/",
        version="9.9.9",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(streaming=True),
        skills=[
            AgentSkill(
                id="runtime-skill",
                name="Runtime skill",
                description="Exposes runtime wiring",
                tags=["runtime"],
            )
        ],
    )

    monkeypatch.setenv("DOMAIN_PLUGIN", "domains.travel.plugin:get_plugin")
    monkeypatch.setattr(plugin, "agent_card", lambda: sentinel_card)

    def instrumented_build_agent():
        build_agent_calls["count"] += 1
        return original_build_agent()

    monkeypatch.setattr(plugin, "build_agent", instrumented_build_agent)
    sys.modules.pop("a2a_server", None)

    a2a_server = importlib.import_module("a2a_server")

    assert get_runtime().plugin is plugin
    assert build_agent_calls["count"] == 1
    assert a2a_server.agent_card == sentinel_card
