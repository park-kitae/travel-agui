"""Travel domain ADK agent assembly."""

from .agents.coordinator import create_coordinator_agent as create_travel_agent

__all__ = ["create_travel_agent"]
