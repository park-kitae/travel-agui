"""Common domain contract for runtime plugins."""

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

try:  # pragma: no cover - runtime dependency may be absent in test env
    from a2a.types import AgentCard  # type: ignore[reportMissingImports]
except ModuleNotFoundError:  # pragma: no cover - fallback for isolated unit tests
    class AgentCard:  # type: ignore[no-redef]
        pass

try:  # pragma: no cover - runtime dependency may be absent in test env
    from google.adk.agents import LlmAgent  # type: ignore[reportMissingImports]
except ModuleNotFoundError:  # pragma: no cover - fallback for isolated unit tests
    class LlmAgent:  # type: ignore[no-redef]
        pass


@dataclass(frozen=True, slots=True)
class RuntimeDeltaPayload:
    """Runtime emission for incremental state updates."""

    ops: list[dict[str, Any]]


@dataclass(frozen=True, slots=True)
class RuntimeSnapshotPayload:
    """Runtime emission for full state snapshots."""

    snapshot: dict[str, Any]


@dataclass(frozen=True, slots=True)
class RuntimeUiRequestPayload:
    """Runtime emission for UI-driven requests."""

    event_name: str
    payload: dict[str, Any]


RuntimeEmission = (
    RuntimeDeltaPayload
    | RuntimeSnapshotPayload
    | RuntimeUiRequestPayload
)


@runtime_checkable
class DomainPlugin(Protocol):
    """Domain-specific plugin boundary for the shared chat runtime."""

    def build_agent(self) -> LlmAgent: ...

    def agent_card(self) -> AgentCard: ...

    def empty_state(self) -> Any: ...

    def serialize_state(self, state: Any) -> dict[str, Any]: ...

    def deserialize_state(self, state: dict[str, Any]) -> Any: ...

    def merge_client_state(self, current_state: Any, client_state: dict[str, Any]) -> Any: ...

    def apply_tool_call(
        self,
        current_state: Any,
        tool_name: str,
        tool_args: dict[str, Any],
    ) -> tuple[Any, list[RuntimeEmission]]: ...

    def apply_tool_result(
        self,
        current_state: Any,
        tool_name: str,
        tool_result: Any,
    ) -> tuple[Any, list[RuntimeEmission]]: ...

    def build_context_block(self, state: Any, user_message: str) -> str: ...
