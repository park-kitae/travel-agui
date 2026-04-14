"""
test_context_extraction.py — StateManager.apply_tool_call이
컨텍스트 추출 결과를 올바르게 state에 반영하는지 검증
(context_extractor.py 삭제 후 StateManager 기반으로 전면 재작성)
"""
import pytest
from state.manager import StateManager


@pytest.fixture
def manager():
    return StateManager()


@pytest.mark.asyncio
async def test_apply_tool_call_search_hotels_extracts_context(manager):
    args = {
        "city": "도쿄",
        "check_in": "2026-06-10",
        "check_out": "2026-06-14",
        "guests": 2,
    }
    events = [e async for e in manager.apply_tool_call("t1", "search_hotels", args)]
    snap = events[0].snapshot
    tc = snap["travel_context"]
    assert tc["destination"] == "도쿄"
    assert tc["check_in"] == "2026-06-10"
    assert tc["check_out"] == "2026-06-14"
    assert tc["guests"] == 2
    assert tc["nights"] == 4


@pytest.mark.asyncio
async def test_apply_tool_call_search_flights_extracts_context(manager):
    args = {
        "origin": "서울",
        "destination": "오사카",
        "departure_date": "2026-07-01",
        "passengers": 1,
        "return_date": "2026-07-05",
    }
    events = [e async for e in manager.apply_tool_call("t2", "search_flights", args)]
    snap = events[0].snapshot
    tc = snap["travel_context"]
    assert tc["origin"] == "서울"
    assert tc["destination"] == "오사카"
    assert tc["check_in"] == "2026-07-01"
    assert tc["guests"] == 1
    assert tc["trip_type"] == "round_trip"


@pytest.mark.asyncio
async def test_apply_tool_call_request_user_input_hotel(manager):
    args = {"input_type": "hotel_booking_details", "context": "제주"}
    events = [e async for e in manager.apply_tool_call("t3", "request_user_input", args)]
    snap = events[0].snapshot
    assert snap["agent_status"]["current_intent"] == "collecting_hotel_params"
    assert "check_in" in snap["agent_status"]["missing_fields"]


@pytest.mark.asyncio
async def test_apply_tool_call_partial_args(manager):
    args = {"city": "부산"}
    events = [e async for e in manager.apply_tool_call("t4", "search_hotels", args)]
    snap = events[0].snapshot
    tc = snap["travel_context"]
    assert tc["destination"] == "부산"
    assert tc["check_in"] is None
    assert tc["nights"] is None
