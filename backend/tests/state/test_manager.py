from collections.abc import Sequence

import pytest  # type: ignore[reportMissingImports]

from domains import RuntimeDeltaPayload, RuntimeSnapshotPayload, RuntimeUiRequestPayload
from domains.travel.plugin import TravelDomainPlugin, get_plugin
from domains.travel.state import UserPreferences, TravelState, apply_tool_call, apply_tool_result, merge_client_state


def _delta_by_path(emissions: Sequence[object]) -> dict[str, dict]:
    payload = next(emission for emission in emissions if isinstance(emission, RuntimeDeltaPayload))
    return {op["path"]: op for op in payload.ops}


def test_merge_client_state_updates_travel_context():
    current = TravelState()
    raw_state = {
        "travel_context": {
            "destination": "도쿄",
            "check_in": "2026-06-10",
            "check_out": "2026-06-14",
            "guests": 2,
        }
    }

    updated, emissions = merge_client_state(current, raw_state)

    assert current.travel_context.destination is None
    assert updated.travel_context.destination == "도쿄"
    assert updated.travel_context.guests == 2
    assert len(emissions) == 1
    delta = _delta_by_path(emissions)
    assert delta["/travel_context/destination"]["value"] == "도쿄"
    assert delta["/travel_context/guests"]["value"] == 2


def test_merge_client_state_updates_ui_context():
    raw_state = {"ui_context": {"selected_hotel_code": "HTL-001"}}
    updated, emissions = merge_client_state(TravelState(), raw_state)

    assert len(emissions) == 1
    delta = _delta_by_path(emissions)
    assert delta["/ui_context/selected_hotel_code"]["value"] == "HTL-001"
    assert updated.ui_context.selected_hotel_code == "HTL-001"


def test_merge_client_state_empty_raw_state_yields_no_emission():
    updated, emissions = merge_client_state(TravelState(), {})

    assert updated == TravelState()
    assert emissions == []


def test_merge_client_state_unchanged_state_yields_no_emission():
    raw_state = {"travel_context": {"destination": "도쿄"}}
    current, first_emissions = merge_client_state(TravelState(), raw_state)
    updated, second_emissions = merge_client_state(current, raw_state)

    assert len(first_emissions) == 1
    assert updated == current
    assert second_emissions == []


def test_merge_client_state_applies_falsey_present_preference_values():
    current = TravelState(
        user_preferences=UserPreferences(
            hotel_grade="5성",
            amenities=("수영장",),
            meal_preference="채식",
            airline_preference=("대한항공",),
        )
    )

    updated, emissions = merge_client_state(
        current,
        {
            "user_preferences": {
                "hotel_grade": "",
                "amenities": [],
                "meal_preference": "",
                "airline_preference": [],
            }
        },
    )

    delta = _delta_by_path(emissions)
    assert updated.user_preferences.hotel_grade == ""
    assert updated.user_preferences.amenities == ()
    assert updated.user_preferences.meal_preference == ""
    assert updated.user_preferences.airline_preference == ()
    assert delta["/user_preferences/hotel_grade"]["value"] == ""
    assert delta["/user_preferences/amenities"]["value"] == []
    assert delta["/user_preferences/meal_preference"]["value"] == ""
    assert delta["/user_preferences/airline_preference"]["value"] == []


def test_get_plugin_returns_travel_domain_plugin_instance():
    plugin = get_plugin()

    assert isinstance(plugin, TravelDomainPlugin)
    assert plugin.empty_state() == TravelState()


def test_plugin_merge_client_state_returns_travel_state_only():
    plugin = get_plugin()

    updated = plugin.merge_client_state(
        TravelState(),
        {"travel_context": {"destination": "도쿄", "guests": 2}},
    )

    assert isinstance(updated, TravelState)
    assert not isinstance(updated, tuple)
    assert updated.travel_context.destination == "도쿄"
    assert updated.travel_context.guests == 2


def test_plugin_serialize_deserialize_round_trip():
    plugin = get_plugin()
    state = TravelState(
        user_preferences=UserPreferences(
            hotel_grade="5성",
            amenities=("수영장",),
            airline_preference=("대한항공",),
        )
    )

    serialized = plugin.serialize_state(state)
    restored = plugin.deserialize_state(serialized)

    assert restored == state


def test_plugin_deserialize_state_tolerates_unknown_extra_keys():
    plugin = get_plugin()

    restored = plugin.deserialize_state(
        {
            "travel_context": {"destination": "도쿄", "unknown_key": "ignored"},
            "ui_context": {"selected_hotel_code": "HTL-001", "extra": True},
            "agent_status": {"current_intent": "searching", "missing_fields": ["check_in"], "other": "ignored"},
            "user_preferences": {"hotel_grade": "4성", "amenities": ["스파"], "ignored": "value"},
            "top_level_extra": {"ignored": True},
        }
    )

    assert restored.travel_context.destination == "도쿄"
    assert restored.ui_context.selected_hotel_code == "HTL-001"
    assert restored.agent_status.current_intent == "searching"
    assert restored.agent_status.missing_fields == ("check_in",)
    assert restored.user_preferences.hotel_grade == "4성"
    assert restored.user_preferences.amenities == ("스파",)


def test_apply_tool_call_search_hotels_updates_travel_context():
    args = {"city": "오사카", "check_in": "2026-07-01", "check_out": "2026-07-04", "guests": 3}

    updated, emissions = apply_tool_call(TravelState(), "search_hotels", args)

    assert len(emissions) == 1
    delta = _delta_by_path(emissions)
    assert delta["/travel_context/destination"]["value"] == "오사카"
    assert delta["/travel_context/nights"]["value"] == 3
    assert delta["/agent_status/current_intent"]["value"] == "searching"
    assert delta["/agent_status/active_tool"]["value"] == "search_hotels"
    assert updated.travel_context.destination == "오사카"
    assert updated.agent_status.active_tool == "search_hotels"


def test_apply_tool_call_search_flights_updates_travel_context():
    args = {
        "origin": "서울", "destination": "후쿠오카",
        "departure_date": "2026-08-10", "passengers": 2,
        "return_date": "2026-08-15",
    }

    updated, emissions = apply_tool_call(TravelState(), "search_flights", args)

    delta = _delta_by_path(emissions)
    assert delta["/travel_context/origin"]["value"] == "서울"
    assert delta["/travel_context/destination"]["value"] == "후쿠오카"
    assert delta["/travel_context/check_out"]["value"] == "2026-08-15"
    assert delta["/travel_context/trip_type"]["value"] == "round_trip"
    assert delta["/agent_status/current_intent"]["value"] == "searching"
    assert updated.travel_context.trip_type == "round_trip"
    assert updated.travel_context.check_out == "2026-08-15"


def test_apply_tool_call_search_flights_one_way():
    args = {
        "origin": "서울", "destination": "도쿄",
        "departure_date": "2026-10-01", "passengers": 1,
        # no return_date
    }
    updated, emissions = apply_tool_call(TravelState(), "search_flights", args)

    assert isinstance(emissions[0], RuntimeDeltaPayload)
    assert updated.travel_context.trip_type == "one_way"


def test_apply_tool_call_preserves_previous_state_immutably():
    current = TravelState(travel_context=TravelState().travel_context)
    updated, _ = apply_tool_call(
        current,
        "search_hotels",
        {"city": "도쿄", "check_in": "2026-09-01", "check_out": "2026-09-03", "guests": 1},
    )

    assert current.travel_context.destination is None
    assert updated.travel_context.destination == "도쿄"


def test_apply_tool_call_request_user_input_collecting_hotel_params():
    args = {"input_type": "hotel_booking_details", "context": "제주"}
    updated, emissions = apply_tool_call(TravelState(), "request_user_input", args)

    delta = _delta_by_path(emissions)
    assert delta["/agent_status/current_intent"]["value"] == "collecting_hotel_params"
    assert "check_in" in delta["/agent_status/missing_fields"]["value"]
    assert updated.travel_context.destination == "제주"


def test_apply_tool_call_request_user_input_parses_hotel_context_json_string():
    args = {
        "input_type": "hotel_booking_details",
        "context": '{"city":"도쿄","check_in":"2026-06-10","check_out":"2026-06-14","guests":2}',
    }

    updated, emissions = apply_tool_call(TravelState(), "request_user_input", args)

    delta = _delta_by_path(emissions)
    assert delta["/travel_context/destination"]["value"] == "도쿄"
    assert delta["/travel_context/check_in"]["value"] == "2026-06-10"
    assert delta["/travel_context/check_out"]["value"] == "2026-06-14"
    assert delta["/travel_context/guests"]["value"] == 2
    assert updated.travel_context.destination == "도쿄"
    assert updated.travel_context.check_in == "2026-06-10"
    assert updated.travel_context.check_out == "2026-06-14"
    assert updated.travel_context.guests == 2


def test_apply_tool_call_request_user_input_parses_flight_context_json_string():
    args = {
        "input_type": "flight_booking_details",
        "context": '{"origin":"서울","destination":"오사카","departure_date":"2026-07-01","return_date":"2026-07-05","passengers":3}',
    }

    updated, emissions = apply_tool_call(TravelState(), "request_user_input", args)

    delta = _delta_by_path(emissions)
    assert delta["/travel_context/origin"]["value"] == "서울"
    assert delta["/travel_context/destination"]["value"] == "오사카"
    assert delta["/travel_context/check_in"]["value"] == "2026-07-01"
    assert delta["/travel_context/check_out"]["value"] == "2026-07-05"
    assert delta["/travel_context/guests"]["value"] == 3
    assert updated.travel_context.origin == "서울"
    assert updated.travel_context.destination == "오사카"
    assert updated.travel_context.check_in == "2026-07-01"
    assert updated.travel_context.check_out == "2026-07-05"
    assert updated.travel_context.guests == 3


def test_apply_tool_result_yields_tool_result_snapshot():
    result = {"status": "success", "hotels": [{"code": "HTL001", "name": "신주쿠 호텔"}]}

    updated, emissions = apply_tool_result(TravelState(), "search_hotels", result)

    assert updated == TravelState()
    assert len(emissions) == 1
    assert isinstance(emissions[0], RuntimeSnapshotPayload)
    snap = emissions[0].snapshot
    assert snap["snapshot_type"] == "tool_result"
    assert snap["tool"] == "search_hotels"
    assert snap["result"] == result


def test_apply_tool_result_request_user_input_yields_user_input_request():
    result = {
        "status": "user_input_required",
        "input_type": "hotel_booking_details",
        "fields": [{"name": "check_in", "type": "date"}],
    }

    _, emissions = apply_tool_result(TravelState(), "request_user_input", result)
    _, repeated_emissions = apply_tool_result(TravelState(), "request_user_input", result)

    assert len(emissions) == 1
    first_payload = emissions[0]
    repeated_payload = repeated_emissions[0]
    assert isinstance(first_payload, RuntimeUiRequestPayload)
    assert isinstance(repeated_payload, RuntimeUiRequestPayload)
    assert first_payload.event_name == "USER_INPUT_REQUEST"
    assert first_payload.payload == {
        "request_id": first_payload.payload["request_id"],
        "input_type": "hotel_booking_details",
        "fields": result["fields"],
    }
    assert first_payload.payload["request_id"]
    assert repeated_payload.payload["request_id"] == first_payload.payload["request_id"]
    assert first_payload.payload["input_type"] == "hotel_booking_details"
    assert first_payload.payload["fields"] == result["fields"]


def test_apply_tool_result_request_user_favorite_yields_favorite_request():
    result = {
        "status": "user_favorite_required",
        "favorite_type": "hotel_preference",
        "options": {
            "hotel_grade": {"type": "radio", "label": "호텔 등급", "choices": ["2성", "3성", "4성", "5성"]},
        },
    }

    _, emissions = apply_tool_result(TravelState(), "request_user_favorite", result)
    _, repeated_emissions = apply_tool_result(TravelState(), "request_user_favorite", result)

    assert len(emissions) == 1
    first_payload = emissions[0]
    repeated_payload = repeated_emissions[0]
    assert isinstance(first_payload, RuntimeUiRequestPayload)
    assert isinstance(repeated_payload, RuntimeUiRequestPayload)
    assert first_payload.event_name == "USER_FAVORITE_REQUEST"
    assert first_payload.payload == {
        "request_id": first_payload.payload["request_id"],
        "favorite_type": "hotel_preference",
        "options": result["options"],
    }
    assert first_payload.payload["request_id"]
    assert repeated_payload.payload["request_id"] == first_payload.payload["request_id"]
    assert first_payload.payload["favorite_type"] == "hotel_preference"
    assert "hotel_grade" in first_payload.payload["options"]


def test_apply_tool_call_request_user_favorite_sets_awaiting_intent():
    updated, emissions = apply_tool_call(
        TravelState(),
        "request_user_favorite",
        {"favorite_type": "hotel_preference"},
    )

    delta = _delta_by_path(emissions)
    assert delta["/agent_status/current_intent"]["value"] == "awaiting_input"
    assert delta["/agent_status/active_tool"]["value"] == "request_user_favorite"
    assert updated.agent_status.active_tool == "request_user_favorite"


def test_apply_tool_call_unchanged_state_yields_no_emission():
    args = {"city": "오사카", "check_in": "2026-07-01", "check_out": "2026-07-04", "guests": 3}
    current, first_emissions = apply_tool_call(TravelState(), "search_hotels", args)
    updated, second_emissions = apply_tool_call(current, "search_hotels", args)

    assert len(first_emissions) == 1
    assert updated == current
    assert second_emissions == []


def test_travel_domain_plugin_agent_card_exposes_full_metadata_contract():
    plugin = get_plugin()

    card = plugin.agent_card()

    assert getattr(card, "name", None) == "travel_agent"
    assert getattr(card, "description", None)
    assert getattr(card, "url", None) == "http://localhost:8001/"
    assert getattr(card, "version", None) == "1.0.0"
    assert getattr(card, "default_input_modes", None) == ["text/plain"]
    assert getattr(card, "default_output_modes", None) == ["text/plain"]
    assert getattr(getattr(card, "capabilities", None), "streaming", None) is True
    assert len(getattr(card, "skills", [])) == 3
