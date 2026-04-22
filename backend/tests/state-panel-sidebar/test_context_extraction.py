"""
test_context_extraction.py — runtime plugin apply_tool_call이
컨텍스트 추출 결과를 올바르게 state에 반영하는지 검증
"""
from typing import Sequence

import pytest  # type: ignore[reportMissingImports]

from domain_runtime import DomainRuntime, map_runtime_emission_to_payload
from domains import RuntimeDeltaPayload, RuntimeEmission
from domains.travel.plugin import get_plugin
from state.store import SerializedStateStore


@pytest.fixture
def runtime() -> DomainRuntime:
    return DomainRuntime(plugin=get_plugin(), state_store=SerializedStateStore())


def _apply_tool_call(runtime: DomainRuntime, thread_id: str, tool_name: str, args: dict):
    current_state = runtime.get_state(thread_id)
    updated_state, emissions = runtime.plugin.apply_tool_call(current_state, tool_name, args)
    runtime.set_state(thread_id, updated_state)
    return emissions


def _delta_by_path(emissions: Sequence[RuntimeEmission]) -> dict[str, dict]:
    assert len(emissions) == 1
    assert isinstance(emissions[0], RuntimeDeltaPayload)
    payload = map_runtime_emission_to_payload(emissions[0])
    return {op["path"]: op for op in payload["delta"]}


def test_apply_tool_call_search_hotels_extracts_context(runtime: DomainRuntime):
    args = {
        "city": "도쿄",
        "check_in": "2026-06-10",
        "check_out": "2026-06-14",
        "guests": 2,
    }
    emissions = _apply_tool_call(runtime, "t1", "search_hotels", args)
    delta = _delta_by_path(emissions)
    assert delta["/travel_context/destination"]["value"] == "도쿄"
    assert delta["/travel_context/check_in"]["value"] == "2026-06-10"
    assert delta["/travel_context/check_out"]["value"] == "2026-06-14"
    assert delta["/travel_context/guests"]["value"] == 2
    assert delta["/travel_context/nights"]["value"] == 4


def test_apply_tool_call_search_flights_extracts_context(runtime: DomainRuntime):
    args = {
        "origin": "서울",
        "destination": "오사카",
        "departure_date": "2026-07-01",
        "passengers": 1,
        "return_date": "2026-07-05",
    }
    emissions = _apply_tool_call(runtime, "t2", "search_flights", args)
    delta = _delta_by_path(emissions)
    assert delta["/travel_context/origin"]["value"] == "서울"
    assert delta["/travel_context/destination"]["value"] == "오사카"
    assert delta["/travel_context/check_in"]["value"] == "2026-07-01"
    assert delta["/travel_context/guests"]["value"] == 1
    assert delta["/travel_context/trip_type"]["value"] == "round_trip"


def test_apply_tool_call_request_user_input_hotel(runtime: DomainRuntime):
    args = {"input_type": "hotel_booking_details", "context": "제주"}
    emissions = _apply_tool_call(runtime, "t3", "request_user_input", args)
    delta = _delta_by_path(emissions)
    assert delta["/agent_status/current_intent"]["value"] == "collecting_hotel_params"
    assert "check_in" in delta["/agent_status/missing_fields"]["value"]


def test_apply_tool_call_partial_args(runtime: DomainRuntime):
    args = {"city": "부산"}
    emissions = _apply_tool_call(runtime, "t4", "search_hotels", args)
    delta = _delta_by_path(emissions)
    assert delta["/travel_context/destination"]["value"] == "부산"
    state = runtime.get_state("t4")
    assert state.travel_context.check_in is None
    assert state.travel_context.nights is None
