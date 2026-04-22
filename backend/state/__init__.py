"""Backward-compatible state package exports."""

from .context_builder import ContextBuilder
from .manager import StateManager, apply_tool_call, apply_tool_result, merge_client_state
from .models import AgentStatus, TravelContext, TravelState, UIContext, UserPreferences

state_manager = StateManager()

__all__ = [
    "state_manager",
    "StateManager",
    "ContextBuilder",
    "TravelState",
    "TravelContext",
    "UIContext",
    "AgentStatus",
    "UserPreferences",
    "merge_client_state",
    "apply_tool_call",
    "apply_tool_result",
]
