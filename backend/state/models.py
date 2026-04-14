"""
state/models.py — 여행 state 데이터 모델 (frozen dataclass)
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class TravelContext:
    """여행 검색 파라미터 (목적지, 날짜, 인원 등)."""
    destination: str | None = None
    origin: str | None = None
    check_in: str | None = None
    check_out: str | None = None
    nights: int | None = None
    guests: int | None = None
    trip_type: str | None = None  # "round_trip" | "one_way"


@dataclass(frozen=True)
class UIContext:
    """UI에서 선택된 값 (호텔 코드 등)."""
    selected_hotel_code: str | None = None


@dataclass(frozen=True)
class AgentStatus:
    """에이전트 처리 상태."""
    current_intent: str = "idle"
    missing_fields: tuple[str, ...] = ()
    active_tool: str | None = None


@dataclass(frozen=True)
class TravelState:
    """thread_id 기준 세션 전체 state."""
    travel_context: TravelContext = field(default_factory=TravelContext)
    ui_context: UIContext = field(default_factory=UIContext)
    agent_status: AgentStatus = field(default_factory=AgentStatus)
