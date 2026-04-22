"""Minimal fake runtime plugin used for smoke tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from domains import DomainPlugin

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

try:  # pragma: no cover - runtime dependency may be absent in test env
    from google.adk.agents import LlmAgent  # type: ignore[reportMissingImports]
except ModuleNotFoundError:  # pragma: no cover - fallback for isolated unit tests
    @dataclass
    class LlmAgent:  # type: ignore[no-redef]
        name: str
        model: str
        description: str
        instruction: str


@dataclass(frozen=True, slots=True)
class FakeState:
    notes: tuple[str, ...] = ()
    turn_count: int = 0


class FakeDomainPlugin(DomainPlugin):
    """Tiny non-travel plugin proving the runtime can swap domains."""

    def build_agent(self) -> LlmAgent:
        return LlmAgent(
            name="fake_agent",
            model="gemini-3-flash-preview",
            description="Minimal fake domain agent used for runtime smoke tests.",
            instruction="Respond briefly. Do not assume any travel-specific state.",
        )

    def agent_card(self) -> AgentCard:
        return AgentCard(
            name="fake_agent",
            description="Minimal fake domain agent used for runtime smoke tests.",
            url="http://localhost:8001/",
            version="1.0.0",
            default_input_modes=["text/plain"],
            default_output_modes=["text/plain"],
            capabilities=AgentCapabilities(streaming=True),
            skills=[
                AgentSkill(
                    id="fake_smoke",
                    name="Fake smoke",
                    description="Minimal smoke-test skill for runtime plugin swapping.",
                    tags=["fake", "smoke"],
                )
            ],
        )

    def empty_state(self) -> FakeState:
        return FakeState()

    def serialize_state(self, state: Any) -> dict[str, Any]:
        fake_state = state if isinstance(state, FakeState) else self.deserialize_state(state)
        return {
            "notes": list(fake_state.notes),
            "turn_count": fake_state.turn_count,
        }

    def deserialize_state(self, state: dict[str, Any]) -> FakeState:
        raw_notes = state.get("notes") or []
        notes = tuple(str(note) for note in raw_notes)
        return FakeState(notes=notes, turn_count=int(state.get("turn_count", 0)))

    def merge_client_state(self, current_state: Any, client_state: dict[str, Any]) -> FakeState:
        state = current_state if isinstance(current_state, FakeState) else self.deserialize_state(current_state)
        raw_notes = client_state.get("notes")
        notes = tuple(str(note) for note in raw_notes) if isinstance(raw_notes, list | tuple) else state.notes
        return FakeState(notes=notes, turn_count=state.turn_count + 1)

    def apply_tool_call(
        self,
        current_state: Any,
        tool_name: str,
        tool_args: dict[str, Any],
    ) -> tuple[FakeState, list[Any]]:
        state = current_state if isinstance(current_state, FakeState) else self.deserialize_state(current_state)
        return state, []

    def apply_tool_result(
        self,
        current_state: Any,
        tool_name: str,
        tool_result: Any,
    ) -> tuple[FakeState, list[Any]]:
        state = current_state if isinstance(current_state, FakeState) else self.deserialize_state(current_state)
        return state, []

    def build_context_block(self, state: Any, user_message: str) -> str:
        fake_state = state if isinstance(state, FakeState) else self.deserialize_state(state)
        notes_line = ",".join(fake_state.notes) if fake_state.notes else "none"
        return f"[fake-domain]\nnotes={notes_line}\nuser={user_message}"


_PLUGIN = FakeDomainPlugin()


def get_plugin() -> FakeDomainPlugin:
    return _PLUGIN
