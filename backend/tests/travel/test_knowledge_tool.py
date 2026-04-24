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

    assert "search_travel_knowledge" not in tool_names
    assert "search_hotels" in tool_names


def test_travel_agent_instruction_prioritizes_input_collection_before_graphrag():
    agent = create_travel_agent()

    assert "request_user_input 이 1순위" in agent.instruction
    assert "같은 응답 턴에서 search_hotels를 함께 호출하지 않습니다" in agent.instruction
    assert "상세 정보 수집이 완료된 다음 턴부터 search_hotels" in agent.instruction


def test_travel_agent_instruction_keeps_graphrag_exclusive_from_search_tools():
    agent = create_travel_agent()

    assert "호텔 조건 추천의 최종 도구는 search_hotels입니다" in agent.instruction
    assert "recommendation_query" in agent.instruction
    assert "search_travel_knowledge는 직접 호출하지 않습니다" in agent.instruction
