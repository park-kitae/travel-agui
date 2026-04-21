"""
test_context_extraction.py — StateManager.apply_tool_call이
컨텍스트 추출 결과를 올바르게 state에 반영하는지 검증
(context_extractor.py 삭제 후 StateManager 기반으로 전면 재작성)
"""
import pytest
from ag_ui.core.events import StateDeltaEvent
from state.manager import StateManager


@pytest.fixture
def manager():
    return StateManager()


def _delta_by_path(event: StateDeltaEvent) -> dict[str, dict]:
    return {op["path"]: op for op in event.delta}


@pytest.mark.asyncio
async def test_apply_tool_call_search_hotels_extracts_context(manager):
    args = {
        "city": "도쿄",
        "check_in": "2026-06-10",
        "check_out": "2026-06-14",
        "guests": 2,
    }
    events = [e async for e in manager.apply_tool_call("t1", "search_hotels", args)]
    assert isinstance(events[0], StateDeltaEvent)
    delta = _delta_by_path(events[0])
    assert delta["/travel_context/destination"]["value"] == "도쿄"
    assert delta["/travel_context/check_in"]["value"] == "2026-06-10"
    assert delta["/travel_context/check_out"]["value"] == "2026-06-14"
    assert delta["/travel_context/guests"]["value"] == 2
    assert delta["/travel_context/nights"]["value"] == 4


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
    assert isinstance(events[0], StateDeltaEvent)
    delta = _delta_by_path(events[0])
    assert delta["/travel_context/origin"]["value"] == "서울"
    assert delta["/travel_context/destination"]["value"] == "오사카"
    assert delta["/travel_context/check_in"]["value"] == "2026-07-01"
    assert delta["/travel_context/guests"]["value"] == 1
    assert delta["/travel_context/trip_type"]["value"] == "round_trip"


@pytest.mark.asyncio
async def test_apply_tool_call_request_user_input_hotel(manager):
    args = {"input_type": "hotel_booking_details", "context": "제주"}
    events = [e async for e in manager.apply_tool_call("t3", "request_user_input", args)]
    assert isinstance(events[0], StateDeltaEvent)
    delta = _delta_by_path(events[0])
    assert delta["/agent_status/current_intent"]["value"] == "collecting_hotel_params"
    assert "check_in" in delta["/agent_status/missing_fields"]["value"]


@pytest.mark.asyncio
async def test_apply_tool_call_partial_args(manager):
    args = {"city": "부산"}
    events = [e async for e in manager.apply_tool_call("t4", "search_hotels", args)]
    assert isinstance(events[0], StateDeltaEvent)
    delta = _delta_by_path(events[0])
    assert delta["/travel_context/destination"]["value"] == "부산"
    state = manager.get("t4")
    assert state.travel_context.check_in is None
    assert state.travel_context.nights is None
