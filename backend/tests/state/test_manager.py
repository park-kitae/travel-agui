import pytest
from dataclasses import asdict
from state.manager import StateManager
from state.models import TravelState
from ag_ui.core.events import StateSnapshotEvent


@pytest.fixture
def manager():
    return StateManager()


@pytest.mark.asyncio
async def test_apply_client_state_updates_travel_context(manager):
    raw_state = {
        "travel_context": {
            "destination": "도쿄",
            "check_in": "2026-06-10",
            "check_out": "2026-06-14",
            "guests": 2,
        }
    }
    events = [e async for e in manager.apply_client_state("thread-1", raw_state)]
    assert len(events) == 1
    assert isinstance(events[0], StateSnapshotEvent)
    snap = events[0].snapshot
    assert snap["snapshot_type"] == "client_state"
    assert snap["travel_context"]["destination"] == "도쿄"
    assert snap["travel_context"]["guests"] == 2
    state = manager.get("thread-1")
    assert state.travel_context.destination == "도쿄"
    assert state.travel_context.guests == 2


@pytest.mark.asyncio
async def test_apply_client_state_updates_ui_context(manager):
    raw_state = {"ui_context": {"selected_hotel_code": "HTL-001"}}
    events = [e async for e in manager.apply_client_state("thread-2", raw_state)]
    assert len(events) == 1
    snap = events[0].snapshot
    assert snap["ui_context"]["selected_hotel_code"] == "HTL-001"
    state = manager.get("thread-2")
    assert state.ui_context.selected_hotel_code == "HTL-001"


@pytest.mark.asyncio
async def test_apply_client_state_empty_raw_state_yields_no_event(manager):
    events = [e async for e in manager.apply_client_state("thread-3", {})]
    assert events == []


def test_get_returns_empty_state_for_unknown_thread(manager):
    state = manager.get("unknown-thread")
    assert state == TravelState()


@pytest.mark.asyncio
async def test_apply_tool_call_search_hotels_updates_travel_context(manager):
    args = {"city": "오사카", "check_in": "2026-07-01", "check_out": "2026-07-04", "guests": 3}
    events = [e async for e in manager.apply_tool_call("thread-4", "search_hotels", args)]
    assert len(events) == 1
    snap = events[0].snapshot
    assert snap["snapshot_type"] == "agent_state"
    assert snap["travel_context"]["destination"] == "오사카"
    assert snap["travel_context"]["nights"] == 3
    assert snap["agent_status"]["current_intent"] == "searching"
    assert snap["agent_status"]["active_tool"] == "search_hotels"
    state = manager.get("thread-4")
    assert state.travel_context.destination == "오사카"
    assert state.agent_status.active_tool == "search_hotels"


@pytest.mark.asyncio
async def test_apply_tool_call_search_flights_updates_travel_context(manager):
    args = {
        "origin": "서울", "destination": "후쿠오카",
        "departure_date": "2026-08-10", "passengers": 2,
        "return_date": "2026-08-15",
    }
    events = [e async for e in manager.apply_tool_call("thread-5", "search_flights", args)]
    snap = events[0].snapshot
    assert snap["travel_context"]["origin"] == "서울"
    assert snap["travel_context"]["destination"] == "후쿠오카"
    assert snap["travel_context"]["trip_type"] == "round_trip"
    assert snap["agent_status"]["current_intent"] == "searching"


@pytest.mark.asyncio
async def test_apply_tool_call_search_flights_one_way(manager):
    args = {
        "origin": "서울", "destination": "도쿄",
        "departure_date": "2026-10-01", "passengers": 1,
        # no return_date
    }
    events = [e async for e in manager.apply_tool_call("thread-13", "search_flights", args)]
    snap = events[0].snapshot
    assert snap["travel_context"]["trip_type"] == "one_way"


@pytest.mark.asyncio
async def test_apply_tool_call_stores_tc_id(manager):
    args = {"city": "도쿄", "check_in": "2026-09-01", "check_out": "2026-09-03", "guests": 1}
    events = [e async for e in manager.apply_tool_call("thread-6", "search_hotels", args)]
    assert len(events) >= 1
    tc_id = manager.get_tc_id("thread-6", "search_hotels")
    assert isinstance(tc_id, str)
    assert len(tc_id) == 36


@pytest.mark.asyncio
async def test_apply_tool_call_request_user_input_collecting_hotel_params(manager):
    args = {"input_type": "hotel_booking_details", "context": "제주"}
    events = [e async for e in manager.apply_tool_call("thread-7", "request_user_input", args)]
    snap = events[0].snapshot
    assert snap["agent_status"]["current_intent"] == "collecting_hotel_params"
    assert "check_in" in snap["agent_status"]["missing_fields"]


@pytest.mark.asyncio
async def test_apply_tool_result_yields_tool_result_snapshot(manager):
    result = {"status": "success", "hotels": [{"code": "HTL001", "name": "신주쿠 호텔"}]}
    events = [e async for e in manager.apply_tool_result("thread-8", "search_hotels", result)]
    assert len(events) == 1
    snap = events[0].snapshot
    assert snap["snapshot_type"] == "tool_result"
    assert snap["tool"] == "search_hotels"
    assert snap["result"] == result


@pytest.mark.asyncio
async def test_apply_tool_result_request_user_input_yields_user_input_request(manager):
    result = {
        "status": "user_input_required",
        "input_type": "hotel_booking_details",
        "fields": [{"name": "check_in", "type": "date"}],
    }
    events = [e async for e in manager.apply_tool_result("thread-9", "request_user_input", result)]
    assert len(events) == 1
    snap = events[0].snapshot
    assert snap["snapshot_type"] == "user_input_request"
    assert snap["_agui_event"] == "USER_INPUT_REQUEST"
    assert snap["input_type"] == "hotel_booking_details"
    assert snap["fields"] == result["fields"]


@pytest.mark.asyncio
async def test_get_tc_id_returns_stored_id(manager):
    args = {"city": "도쿄", "check_in": "2026-09-01", "check_out": "2026-09-03", "guests": 1}
    events = [e async for e in manager.apply_tool_call("thread-10", "search_hotels", args)]
    assert len(events) >= 1
    tc_id = manager.get_tc_id("thread-10", "search_hotels")
    assert len(tc_id) == 36


@pytest.mark.asyncio
async def test_get_tc_id_unknown_tool_returns_new_uuid_with_warning(manager, caplog):
    import logging
    with caplog.at_level(logging.WARNING):
        tc_id = manager.get_tc_id("thread-11", "unknown_tool")
    assert len(tc_id) == 36
    assert "미등록" in caplog.text


def test_clear_removes_state_and_tool_call_map(manager):
    manager._store["thread-12"] = TravelState()  # type: ignore
    manager._tool_call_map["thread-12"] = {"search_hotels": "some-id"}  # type: ignore
    manager.clear("thread-12")
    assert "thread-12" not in manager._store
    assert "thread-12" not in manager._tool_call_map


@pytest.mark.asyncio
async def test_apply_tool_result_request_user_favorite_yields_favorite_request(manager):
    result = {
        "status": "user_favorite_required",
        "favorite_type": "hotel_preference",
        "options": {
            "hotel_grade": {"type": "radio", "label": "호텔 등급", "choices": ["2성", "3성", "4성", "5성"]},
        },
    }
    events = [e async for e in manager.apply_tool_result("thread-20", "request_user_favorite", result)]
    assert len(events) == 1
    snap = events[0].snapshot
    assert snap["snapshot_type"] == "user_favorite_request"
    assert snap["_agui_event"] == "USER_FAVORITE_REQUEST"
    assert snap["favorite_type"] == "hotel_preference"
    assert "hotel_grade" in snap["options"]


@pytest.mark.asyncio
async def test_apply_tool_call_request_user_favorite_sets_awaiting_intent(manager):
    args = {"favorite_type": "hotel_preference"}
    events = [e async for e in manager.apply_tool_call("thread-21", "request_user_favorite", args)]
    assert len(events) == 1
    snap = events[0].snapshot
    assert snap["agent_status"]["current_intent"] == "awaiting_input"
    assert snap["agent_status"]["active_tool"] == "request_user_favorite"
