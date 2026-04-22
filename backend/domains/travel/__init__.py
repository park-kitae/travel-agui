"""Travel domain package."""

from . import data
from .agent import create_travel_agent
from .context import ContextBuilder
from .plugin import TravelDomainPlugin, get_plugin
from .state import (
    AgentStatus,
    TravelContext,
    TravelState,
    UIContext,
    UserPreferences,
    apply_tool_call,
    apply_tool_result,
    merge_client_state,
)

__all__ = [
    "data",
    "AgentStatus",
    "ContextBuilder",
    "TravelContext",
    "TravelDomainPlugin",
    "TravelState",
    "UIContext",
    "UserPreferences",
    "apply_tool_call",
    "apply_tool_result",
    "create_travel_agent",
    "get_plugin",
    "merge_client_state",
]
