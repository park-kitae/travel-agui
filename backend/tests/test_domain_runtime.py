import sys
from types import ModuleType
from dataclasses import asdict, is_dataclass
from typing import Any, get_args

import pytest  # type: ignore[reportMissingImports]

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

from domain_runtime import (
    DomainRuntime,
    get_runtime,
    initialize_runtime_or_die,
    map_runtime_emission_to_payload,
    reset_runtime_for_tests,
)
from domains import (
    DomainPlugin,
    RuntimeDeltaPayload,
    RuntimeEmission,
    RuntimeSnapshotPayload,
    RuntimeUiRequestPayload,
)
from state.store import SerializedStateStore


class StubPlugin:
    def __init__(self) -> None:
        self.serialized_states: list[dict[str, Any]] = []
        self.deserialized_states: list[dict[str, Any]] = []

    def build_agent(self) -> LlmAgent:
        return _StubAgent()

    def agent_card(self) -> AgentCard:
        return _StubAgentCard()

    def empty_state(self) -> dict[str, Any]:
        return {"counter": 0, "nested": {"items": []}}

    def serialize_state(self, state: Any) -> dict[str, Any]:
        serialized = {"opaque": {"payload": state}}
        self.serialized_states.append(serialized)
        return serialized

    def deserialize_state(self, state: dict[str, Any]) -> Any:
        self.deserialized_states.append(state)
        return state["opaque"]["payload"]

    def merge_client_state(self, current_state: Any, client_state: dict[str, Any]) -> Any:
        return current_state

    def apply_tool_call(
        self,
        current_state: Any,
        tool_name: str,
        tool_args: dict[str, Any],
    ) -> tuple[Any, list[RuntimeEmission]]:
        return current_state, []

    def apply_tool_result(
        self,
        current_state: Any,
        tool_name: str,
        tool_result: Any,
    ) -> tuple[Any, list[RuntimeEmission]]:
        return current_state, []

    def build_context_block(self, state: Any, user_message: str) -> str:
        return user_message


class _StubAgent:
    pass


class _StubAgentCard:
    pass


def teardown_function() -> None:
    reset_runtime_for_tests()


def test_get_runtime_raises_before_initialization():
    reset_runtime_for_tests()

    with pytest.raises(RuntimeError, match="initialize_runtime_or_die"):
        get_runtime()


def test_serialized_state_store_round_trips_opaque_payload():
    store = SerializedStateStore()
    payload = {"opaque": {"nested": [1, {"two": 2}]}}

    store.set("thread-1", payload)

    assert store.get("thread-1") == payload

    store.clear("thread-1")

    assert store.get("thread-1") is None


def test_domain_runtime_round_trips_opaque_state_with_plugin():
    plugin = StubPlugin()
    runtime = DomainRuntime(plugin=plugin, state_store=SerializedStateStore())
    original_state = {"deep": {"nested": ["alpha", {"beta": 2}]}, "count": 7}

    runtime.set_state("thread-1", original_state)

    assert runtime.get_state("thread-1") == original_state
    assert runtime.get_serialized_state("thread-1") == {"opaque": {"payload": original_state}}
    assert plugin.serialized_states == [{"opaque": {"payload": original_state}}]
    assert plugin.deserialized_states == [{"opaque": {"payload": original_state}}]


def test_domain_runtime_exposes_startup_wrappers():
    plugin = StubPlugin()
    runtime = DomainRuntime(plugin=plugin)

    assert isinstance(runtime.build_agent(), _StubAgent)
    assert isinstance(runtime.agent_card(), _StubAgentCard)


def test_initialize_runtime_or_die_loads_plugin_once_and_returns_shared_singleton(monkeypatch: pytest.MonkeyPatch):
    reset_runtime_for_tests()
    load_calls = {"count": 0}

    module = ModuleType("stub_domain_plugin")

    def load_plugin() -> StubPlugin:
        load_calls["count"] += 1
        return StubPlugin()

    module.load_plugin = load_plugin  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "stub_domain_plugin", module)
    monkeypatch.setenv("DOMAIN_PLUGIN", "stub_domain_plugin:load_plugin")

    first = initialize_runtime_or_die()
    second = initialize_runtime_or_die()

    assert first is second
    assert get_runtime() is first
    assert load_calls["count"] == 1


def test_initialize_runtime_or_die_raises_on_plugin_load_failure(monkeypatch: pytest.MonkeyPatch):
    reset_runtime_for_tests()
    monkeypatch.setenv("DOMAIN_PLUGIN", "missing_plugin_module:load_plugin")

    with pytest.raises(ImportError):
        initialize_runtime_or_die()


def test_runtime_delta_payload_shape():
    payload = RuntimeDeltaPayload(ops=[{"op": "replace", "path": "/agent_status/current_intent", "value": "idle"}])

    assert is_dataclass(payload)
    assert asdict(payload) == {"ops": [{"op": "replace", "path": "/agent_status/current_intent", "value": "idle"}]}


def test_runtime_snapshot_payload_shape():
    payload = RuntimeSnapshotPayload(snapshot={"snapshot_type": "tool_result", "tool": "search_hotels"})

    assert is_dataclass(payload)
    assert asdict(payload) == {"snapshot": {"snapshot_type": "tool_result", "tool": "search_hotels"}}


def test_runtime_ui_request_payload_shape():
    payload = RuntimeUiRequestPayload(event_name="USER_INPUT_REQUEST", payload={"fields": ["check_in", "check_out"]})

    assert is_dataclass(payload)
    assert asdict(payload) == {"event_name": "USER_INPUT_REQUEST", "payload": {"fields": ["check_in", "check_out"]}}


def test_runtime_emission_alias_accepts_all_runtime_payloads():
    alias_types = get_args(RuntimeEmission)
    assert alias_types == (RuntimeDeltaPayload, RuntimeSnapshotPayload, RuntimeUiRequestPayload)

    samples = [
        RuntimeDeltaPayload(ops=[]),
        RuntimeSnapshotPayload(snapshot={}),
        RuntimeUiRequestPayload(event_name="USER_FAVORITE_REQUEST", payload={}),
    ]
    assert all(isinstance(sample, alias_types) for sample in samples)


def test_runtime_delta_payload_maps_to_current_stream_contract():
    payload = map_runtime_emission_to_payload(
        RuntimeDeltaPayload(
            ops=[{"op": "replace", "path": "/agent_status/current_intent", "value": "searching"}]
        )
    )

    assert payload == {
        "_agui_event": "STATE_DELTA",
        "delta": [{"op": "replace", "path": "/agent_status/current_intent", "value": "searching"}],
    }


def test_runtime_snapshot_payload_maps_to_current_stream_contract():
    payload = map_runtime_emission_to_payload(
        RuntimeSnapshotPayload(snapshot={"snapshot_type": "tool_result", "tool": "search_hotels"})
    )

    assert payload == {"snapshot_type": "tool_result", "tool": "search_hotels"}


def test_runtime_ui_request_payload_maps_to_current_stream_contract():
    payload = map_runtime_emission_to_payload(
        RuntimeUiRequestPayload(
            event_name="USER_INPUT_REQUEST",
            payload={"request_id": "req-1", "input_type": "hotel_booking_details", "fields": []},
        )
    )

    assert payload == {
        "_agui_event": "USER_INPUT_REQUEST",
        "request_id": "req-1",
        "input_type": "hotel_booking_details",
        "fields": [],
    }


def test_runtime_ui_request_payload_rejects_unsupported_event_name():
    with pytest.raises(ValueError, match="Unsupported UI event name"):
        map_runtime_emission_to_payload(
            RuntimeUiRequestPayload(event_name="STATE_SNAPSHOT", payload={})
        )


def test_runtime_mapping_rejects_unknown_emission_object():
    with pytest.raises(TypeError, match="Unsupported runtime emission"):
        map_runtime_emission_to_payload(object())  # type: ignore[arg-type]


def test_domain_plugin_is_importable_and_declares_required_methods():
    required_methods = {
        "build_agent",
        "agent_card",
        "empty_state",
        "serialize_state",
        "deserialize_state",
        "merge_client_state",
        "apply_tool_call",
        "apply_tool_result",
        "build_context_block",
    }

    assert DomainPlugin.__name__ == "DomainPlugin"
    assert required_methods.issubset(set(dir(DomainPlugin)))
    assert isinstance(StubPlugin(), DomainPlugin)
