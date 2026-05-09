"""Verify the travel agent sub-agent hierarchy structure."""

import pytest

from domains.travel.agent import create_travel_agent


def test_travel_agent_is_coordinator():
    agent = create_travel_agent()
    assert agent.name == "travel_agent"
    assert agent.model == "gemini-3-flash-preview"


def test_travel_agent_has_two_sub_agents():
    agent = create_travel_agent()
    sub_names = [sa.name for sa in agent.sub_agents]
    assert "hotel_agent" in sub_names
    assert "flight_agent" in sub_names
    assert len(agent.sub_agents) == 2


def test_coordinator_owns_preference_and_tips_tools():
    agent = create_travel_agent()
    tool_names = [t.name for t in agent.tools]
    assert "request_user_favorite" in tool_names
    assert "get_travel_tips" in tool_names


def test_hotel_agent_owns_hotel_tools():
    agent = create_travel_agent()
    hotel_agent = next(sa for sa in agent.sub_agents if sa.name == "hotel_agent")
    tool_names = [t.name for t in hotel_agent.tools]
    assert "search_hotels" in tool_names
    assert "get_hotel_detail" in tool_names
    assert "request_user_input" in tool_names


def test_flight_agent_owns_flight_tools():
    agent = create_travel_agent()
    flight_agent = next(sa for sa in agent.sub_agents if sa.name == "flight_agent")
    tool_names = [t.name for t in flight_agent.tools]
    assert "search_flights" in tool_names
    assert "request_user_input" in tool_names


def test_sub_agents_allow_transfer_back():
    agent = create_travel_agent()
    for sa in agent.sub_agents:
        assert sa.disallow_transfer_to_parent is False
        assert sa.disallow_transfer_to_peers is False