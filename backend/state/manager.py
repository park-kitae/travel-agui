"""Backward-compatible state manager re-exports."""

from domains.travel.state_manager import (
    AgentStatus,
    StateManager,
    TravelContext,
    TravelState,
    UIContext,
    UserPreferences,
    apply_tool_call,
    apply_tool_result,
    merge_client_state,
)


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
