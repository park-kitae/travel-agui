import pytest
from dataclasses import replace, FrozenInstanceError
from state.models import TravelContext, UIContext, AgentStatus, TravelState


def test_travel_context_defaults():
    ctx = TravelContext()
    assert ctx.destination is None
    assert ctx.nights is None
    assert ctx.trip_type is None


def test_travel_context_frozen():
    ctx = TravelContext(destination="도쿄")
    with pytest.raises(FrozenInstanceError):
        ctx.destination = "오사카"  # type: ignore


def test_travel_context_replace():
    ctx = TravelContext(destination="도쿄", guests=2)
    updated = replace(ctx, destination="오사카")
    assert updated.destination == "오사카"
    assert updated.guests == 2
    assert ctx.destination == "도쿄"  # 원본 불변


def test_ui_context_frozen():
    ui = UIContext(selected_hotel_code="HTL001")
    with pytest.raises(FrozenInstanceError):
        ui.selected_hotel_code = "HTL002"  # type: ignore


def test_agent_status_defaults():
    status = AgentStatus()
    assert status.current_intent == "idle"
    assert status.missing_fields == ()
    assert status.active_tool is None


def test_agent_status_missing_fields_is_tuple():
    status = AgentStatus(missing_fields=("check_in", "guests"))
    assert isinstance(status.missing_fields, tuple)
    assert "check_in" in status.missing_fields


def test_travel_state_defaults():
    state = TravelState()
    assert isinstance(state.travel_context, TravelContext)
    assert isinstance(state.ui_context, UIContext)
    assert isinstance(state.agent_status, AgentStatus)


def test_travel_state_replace():
    state = TravelState()
    new_ctx = replace(state.travel_context, destination="제주")
    updated = replace(state, travel_context=new_ctx)
    assert updated.travel_context.destination == "제주"
    assert state.travel_context.destination is None  # 원본 불변


def test_user_preferences_defaults():
    from state.models import UserPreferences
    prefs = UserPreferences()
    assert prefs.hotel_grade is None
    assert prefs.hotel_type is None
    assert prefs.amenities == ()
    assert prefs.seat_class is None
    assert prefs.seat_position is None
    assert prefs.meal_preference is None
    assert prefs.airline_preference == ()


def test_user_preferences_is_frozen():
    from state.models import UserPreferences
    prefs = UserPreferences(hotel_grade="5성")
    with pytest.raises(FrozenInstanceError):
        prefs.hotel_grade = "3성"  # type: ignore


def test_travel_state_has_user_preferences():
    from state.models import UserPreferences
    state = TravelState()
    assert hasattr(state, "user_preferences")
    assert isinstance(state.user_preferences, UserPreferences)
