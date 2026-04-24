from domains.travel.agent import create_travel_agent
from domains.travel.tools import search_travel_knowledge


def test_search_travel_knowledge_tool_returns_structured_evidence():
    result = search_travel_knowledge("수영장 있는 서울 5성 호텔", city="서울")

    assert result["status"] == "success"
    assert result["query"] == "수영장 있는 서울 5성 호텔"
    assert result["results"]
    assert result["evidence"]


def test_travel_agent_registers_knowledge_tool():
    agent = create_travel_agent()

    tool_names = {
        getattr(getattr(tool, "func", None), "__name__", getattr(tool, "name", ""))
        for tool in agent.tools
    }

    assert "search_travel_knowledge" in tool_names
