"""Travel-domain compatibility state manager implementation."""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncGenerator
from dataclasses import asdict

from ag_ui.core.events import EventType, StateDeltaEvent, StateSnapshotEvent  # type: ignore[reportMissingImports]

from .state import (
    AgentStatus,
    TravelContext,
    TravelState,
    UIContext,
    UserPreferences,
    apply_tool_call as _apply_tool_call,
    apply_tool_result as _apply_tool_result,
    merge_client_state as _merge_client_state,
)

logger = logging.getLogger(__name__)


class StateManager:
    """Backward-compatible thread-scoped travel state manager."""

    def __init__(self) -> None:
        self._store: dict[str, TravelState] = {}
        self._tool_call_map: dict[str, dict[str, str]] = {}

    def get(self, thread_id: str) -> TravelState:
        return self._store.get(thread_id, TravelState())

    async def apply_client_state(self, thread_id: str, raw_state: dict) -> AsyncGenerator[StateSnapshotEvent | StateDeltaEvent, None]:
        if not raw_state:
            return

        current = self.get(thread_id)
        updated, emissions = _merge_client_state(current, raw_state)
        self._store[thread_id] = updated

        for emission in emissions:
            yield _runtime_emission_to_agui_event(emission)

    async def apply_tool_call(self, thread_id: str, tool_name: str, args: dict) -> AsyncGenerator[StateSnapshotEvent | StateDeltaEvent, None]:
        current = self.get(thread_id)
        updated, emissions = _apply_tool_call(current, tool_name, args)
        tc_id = str(uuid.uuid4())
        self._tool_call_map.setdefault(thread_id, {})[tool_name] = tc_id
        self._store[thread_id] = updated

        for emission in emissions:
            yield _runtime_emission_to_agui_event(emission)

    async def apply_tool_result(self, thread_id: str, tool_name: str, result: dict) -> AsyncGenerator[StateSnapshotEvent, None]:
        current = self.get(thread_id)
        updated, emissions = _apply_tool_result(current, tool_name, result)
        self._store[thread_id] = updated

        for emission in emissions:
            yield _runtime_emission_to_agui_event(emission)

    def get_tc_id(self, thread_id: str, tool_name: str) -> str:
        tc_id = self._tool_call_map.get(thread_id, {}).get(tool_name)
        if tc_id is None:
            logger.warning(f"[{thread_id}] get_tc_id: '{tool_name}' 미등록 — 새 uuid 발행 (TOOL_CALL 페어 불일치 가능)")
            return str(uuid.uuid4())
        return tc_id

    def clear(self, thread_id: str) -> None:
        self._store.pop(thread_id, None)
        self._tool_call_map.pop(thread_id, None)


merge_client_state = _merge_client_state
apply_tool_call = _apply_tool_call
apply_tool_result = _apply_tool_result


def _runtime_emission_to_agui_event(emission):
    payload = asdict(emission)
    if "ops" in payload:
        return StateDeltaEvent(type=EventType.STATE_DELTA, delta=payload["ops"])
    snapshot = payload.get("snapshot") or {}
    if payload.get("event_name") == "USER_FAVORITE_REQUEST":
        snapshot = {
            "snapshot_type": "user_favorite_request",
            "_agui_event": "USER_FAVORITE_REQUEST",
            **payload.get("payload", {}),
        }
    elif payload.get("event_name") == "USER_INPUT_REQUEST":
        snapshot = {
            "snapshot_type": "user_input_request",
            "_agui_event": "USER_INPUT_REQUEST",
            **payload.get("payload", {}),
        }
    return StateSnapshotEvent(type=EventType.STATE_SNAPSHOT, snapshot=snapshot)


__all__ = [
    "StateManager",
    "TravelState",
    "TravelContext",
    "UIContext",
    "AgentStatus",
    "UserPreferences",
    "merge_client_state",
    "apply_tool_call",
    "apply_tool_result",
]
