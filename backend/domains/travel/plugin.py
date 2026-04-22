"""Travel domain plugin implementation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any

from domains import DomainPlugin

from .agent import create_travel_agent
from .context import ContextBuilder
from .state import (
    AgentStatus,
    TravelContext,
    TravelState,
    UIContext,
    UserPreferences,
    apply_tool_call,
    apply_tool_result,
    merge_client_state,
)

try:  # pragma: no cover - runtime dependency may be absent in test env
    from a2a.types import AgentCapabilities, AgentCard, AgentSkill  # type: ignore[reportMissingImports]
except ModuleNotFoundError:  # pragma: no cover - fallback for isolated unit tests
    @dataclass
    class AgentCapabilities:  # type: ignore[no-redef]
        streaming: bool = False

    @dataclass
    class AgentSkill:  # type: ignore[no-redef]
        id: str
        name: str
        description: str
        tags: list[str]

    @dataclass
    class AgentCard:  # type: ignore[no-redef]
        name: str
        description: str
        url: str
        version: str
        default_input_modes: list[str]
        default_output_modes: list[str]
        capabilities: AgentCapabilities
        skills: list[AgentSkill]


class TravelDomainPlugin(DomainPlugin):
    """Authoritative travel-domain runtime plugin."""

    def build_agent(self):
        return create_travel_agent()

    def agent_card(self) -> AgentCard:
        return AgentCard(
            name="travel_agent",
            description="여행 AI 여행 상담 에이전트 — 호텔, 항공, 관광 정보 안내",
            url="http://localhost:8001/",
            version="1.0.0",
            default_input_modes=["text/plain"],
            default_output_modes=["text/plain"],
            capabilities=AgentCapabilities(streaming=True),
            skills=[
                AgentSkill(
                    id="hotel_search",
                    name="호텔 검색",
                    description="도시와 날짜로 호텔을 검색합니다",
                    tags=["hotel", "search"],
                ),
                AgentSkill(
                    id="flight_search",
                    name="항공편 검색",
                    description="출발지/목적지 항공편을 검색합니다",
                    tags=["flight", "search"],
                ),
                AgentSkill(
                    id="travel_tips",
                    name="여행 팁",
                    description="목적지 관광 정보 및 팁을 제공합니다",
                    tags=["travel", "tips"],
                ),
            ],
        )

    def empty_state(self) -> TravelState:
        return TravelState()

    def serialize_state(self, state: Any) -> dict[str, Any]:
        travel_state = state if isinstance(state, TravelState) else self.deserialize_state(state)
        return _to_json_safe(asdict(travel_state))

    def deserialize_state(self, state: dict[str, Any]) -> TravelState:
        travel_context = _filter_dataclass_kwargs(TravelContext, state.get("travel_context") or {})
        ui_context = _filter_dataclass_kwargs(UIContext, state.get("ui_context") or {})
        agent_status = _filter_dataclass_kwargs(AgentStatus, state.get("agent_status") or {})
        user_preferences = _filter_dataclass_kwargs(UserPreferences, state.get("user_preferences") or {})
        return TravelState(
            travel_context=TravelContext(**travel_context),
            ui_context=UIContext(**ui_context),
            agent_status=AgentStatus(
                current_intent=agent_status.get("current_intent", "idle"),
                missing_fields=tuple(agent_status.get("missing_fields", ())),
                active_tool=agent_status.get("active_tool"),
            ),
            user_preferences=UserPreferences(
                hotel_grade=user_preferences.get("hotel_grade"),
                hotel_type=user_preferences.get("hotel_type"),
                amenities=tuple(user_preferences.get("amenities", ())),
                seat_class=user_preferences.get("seat_class"),
                seat_position=user_preferences.get("seat_position"),
                meal_preference=user_preferences.get("meal_preference"),
                airline_preference=tuple(user_preferences.get("airline_preference", ())),
            ),
        )

    def merge_client_state(self, current_state: Any, client_state: dict[str, Any]) -> Any:
        state = current_state if isinstance(current_state, TravelState) else self.deserialize_state(current_state)
        next_state, _ = merge_client_state(state, client_state)
        return next_state

    def apply_tool_call(
        self,
        current_state: Any,
        tool_name: str,
        tool_args: dict[str, Any],
    ):
        state = current_state if isinstance(current_state, TravelState) else self.deserialize_state(current_state)
        return apply_tool_call(state, tool_name, tool_args)

    def apply_tool_result(
        self,
        current_state: Any,
        tool_name: str,
        tool_result: Any,
    ):
        state = current_state if isinstance(current_state, TravelState) else self.deserialize_state(current_state)
        return apply_tool_result(state, tool_name, tool_result)

    def build_context_block(self, state: Any, user_message: str) -> str:
        travel_state = state if isinstance(state, TravelState) else self.deserialize_state(state)
        return ContextBuilder(travel_state).build_context_block(user_message)


def _to_json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _to_json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_to_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_to_json_safe(item) for item in value]
    return value


def _filter_dataclass_kwargs(model: type[Any], raw_values: dict[str, Any]) -> dict[str, Any]:
    allowed_fields = {field.name for field in fields(model)}
    return {key: value for key, value in raw_values.items() if key in allowed_fields}


_PLUGIN = TravelDomainPlugin()


def get_plugin() -> TravelDomainPlugin:
    return _PLUGIN
