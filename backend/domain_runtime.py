"""Singleton runtime for shared domain plugin execution."""

from __future__ import annotations

import importlib
import inspect
import os
from dataclasses import dataclass
from typing import Any

from domains import (
    DomainPlugin,
    RuntimeDeltaPayload,
    RuntimeEmission,
    RuntimeSnapshotPayload,
    RuntimeUiRequestPayload,
)
from state.store import SerializedStateStore


_RUNTIME: DomainRuntime | None = None
_SUPPORTED_UI_EVENT_NAMES = frozenset({"USER_INPUT_REQUEST", "USER_FAVORITE_REQUEST"})


@dataclass(frozen=True, slots=True)
class PreparedRequest:
    """Runtime-prepared request payload for downstream transport."""

    state: Any
    user_message: str


class DomainRuntime:
    """Owns the shared plugin and its opaque state store."""

    def __init__(self, plugin: DomainPlugin, state_store: SerializedStateStore | None = None) -> None:
        self.plugin = plugin
        self.state_store = state_store or SerializedStateStore()

    def get_state(self, thread_id: str) -> Any:
        serialized = self.state_store.get(thread_id)
        if serialized is None:
            return self.plugin.empty_state()
        return self.plugin.deserialize_state(serialized)

    def set_state(self, thread_id: str, state: Any) -> None:
        self.state_store.set(thread_id, self.plugin.serialize_state(state))

    def prepare_request(self, thread_id: str, client_state: dict[str, Any], user_message: str) -> PreparedRequest:
        current_state = self.get_state(thread_id)
        merged_state = self.plugin.merge_client_state(current_state, client_state)
        self.set_state(thread_id, merged_state)
        enriched_message = self.plugin.build_context_block(merged_state, user_message)
        return PreparedRequest(state=merged_state, user_message=enriched_message)

    def build_agent(self) -> Any:
        return self.plugin.build_agent()

    def agent_card(self) -> Any:
        return self.plugin.agent_card()

    def app_name(self) -> str:
        card = self.agent_card()
        return getattr(card, "name", None) or "domain_runtime"

    def clear_state(self, thread_id: str) -> None:
        self.state_store.clear(thread_id)

    def get_serialized_state(self, thread_id: str) -> dict[str, Any] | None:
        return self.state_store.get(thread_id)


def map_runtime_emission_to_payload(emission: RuntimeEmission | Any) -> dict[str, Any]:
    """Convert typed runtime emissions into the current stream payload contract."""

    if isinstance(emission, RuntimeDeltaPayload):
        return {
            "_agui_event": "STATE_DELTA",
            "delta": emission.ops,
        }

    if isinstance(emission, RuntimeSnapshotPayload):
        return emission.snapshot

    if isinstance(emission, RuntimeUiRequestPayload):
        if emission.event_name not in _SUPPORTED_UI_EVENT_NAMES:
            raise ValueError(f"Unsupported UI event name: {emission.event_name}")
        return {
            "_agui_event": emission.event_name,
            **emission.payload,
        }

    raise TypeError(f"Unsupported runtime emission: {type(emission).__name__}")


def _load_plugin_from_env() -> DomainPlugin:
    plugin_spec = os.getenv("DOMAIN_PLUGIN")
    if not plugin_spec:
        raise RuntimeError("DOMAIN_PLUGIN is not configured")

    module_name, separator, attr_name = plugin_spec.partition(":")
    module = importlib.import_module(module_name)
    target: Any = getattr(module, attr_name) if separator else module

    if inspect.isclass(target):
        target = target()
    elif callable(target) and not isinstance(target, DomainPlugin):
        target = target()

    if not isinstance(target, DomainPlugin):
        raise TypeError(f"Loaded object from {plugin_spec!r} is not a DomainPlugin")

    return target


def initialize_runtime_or_die() -> DomainRuntime:
    global _RUNTIME

    if _RUNTIME is not None:
        return _RUNTIME

    plugin = _load_plugin_from_env()
    _RUNTIME = DomainRuntime(plugin=plugin)
    return _RUNTIME


def get_runtime() -> DomainRuntime:
    if _RUNTIME is None:
        raise RuntimeError("Domain runtime has not been initialized. Call initialize_runtime_or_die() first.")
    return _RUNTIME


def reset_runtime_for_tests() -> None:
    global _RUNTIME

    _RUNTIME = None


def get_runtime_app_name(runtime_or_runner: Any) -> str:
    """Resolve a stable app/session identity from runtime-backed objects."""

    if isinstance(runtime_or_runner, DomainRuntime):
        return runtime_or_runner.app_name()

    app_name = getattr(runtime_or_runner, "app_name", None)
    if app_name:
        return str(app_name)

    runtime = get_runtime()
    return runtime.app_name()
