import pytest
import uuid
from datetime import date
from context_extractor import _extract_travel_context, _extract_agent_status

def test_extract_travel_context_search_hotels():
    args = {
        "city": "도쿄",
        "check_in": "2026-06-10",
        "check_out": "2026-06-14",
        "guests": 2
    }
    ctx = _extract_travel_context("search_hotels", args)
    assert ctx["destination"] == "도쿄"
    assert ctx["check_in"] == "2026-06-10"
    assert ctx["check_out"] == "2026-06-14"
    assert ctx["guests"] == 2
    assert ctx["nights"] == 4

def test_extract_travel_context_search_flights():
    args = {
        "origin": "서울",
        "destination": "오사카",
        "departure_date": "2026-07-01",
        "passengers": 1,
        "return_date": "2026-07-05"
    }
    ctx = _extract_travel_context("search_flights", args)
    assert ctx["origin"] == "서울"
    assert ctx["destination"] == "오사카"
    assert ctx["check_in"] == "2026-07-01"
    assert ctx["guests"] == 1
    assert ctx["trip_type"] == "round_trip"

def test_extract_agent_status_request_user_input():
    args = {
        "input_type": "hotel_booking_details",
        "context": "제주"
    }
    status = _extract_agent_status("request_user_input", args)
    assert status["current_intent"] == "collecting_hotel_params"
    assert "check_in" in status["missing_fields"]
    assert status["active_tool"] == "request_user_input"

def test_extract_travel_context_partial():
    args = {"city": "부산"}
    ctx = _extract_travel_context("search_hotels", args)
    assert ctx["destination"] == "부산"
    assert ctx["check_in"] is None
    assert ctx["nights"] is None
