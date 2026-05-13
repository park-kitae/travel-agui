"""Travel coordinator agent factory."""

from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from .flight import create_flight_agent
from .hotel import create_hotel_agent
from .shared import COMMON_RESPONSE_POLICY
from ..tools import get_travel_tips, request_user_favorite


def build_coordinator_instruction() -> str:
    """라우팅 중심의 간결한 코디네이터 instruction을 생성합니다."""
    return f"""당신은 여행 AI의 코디네이터입니다.

규칙:
- 호텔 관련 요청은 hotel_agent로 이관합니다.
- 항공 관련 요청은 flight_agent로 이관합니다.
- 여행지 정보, 관광지, 맛집, 일정, 날씨 요청은 get_travel_tips(destination)로 직접 처리합니다.
- 호텔 추천/검색 요청인데 호텔 취향 수집 완료 마커가 없으면 request_user_favorite("hotel_preference")를 먼저 호출합니다.
- 항공 추천/검색 요청인데 항공 취향 수집 완료 마커가 없으면 request_user_favorite("flight_preference")를 먼저 호출합니다.
- 메시지 앞의 현재 여행 컨텍스트 블록과 취향 마커가 있으면 그 값을 우선 사용하고 불필요한 재질문을 하지 않습니다.
- 복합 요청은 필요한 취향 수집 후 호텔/항공 에이전트로 순서대로 이관합니다.

{COMMON_RESPONSE_POLICY}"""


def create_coordinator_agent() -> LlmAgent:
    """여행 상담 코디네이터 에이전트를 생성합니다."""
    return LlmAgent(
        name="travel_agent",
        model="gemini-3-flash-preview",
        description="여행 AI 여행 상담 코디네이터 — 라우팅, 취향 수집, 여행 팁 안내",
        instruction=build_coordinator_instruction(),
        tools=[
            FunctionTool(request_user_favorite),
            FunctionTool(get_travel_tips),
        ],
        sub_agents=[
            create_hotel_agent(),
            create_flight_agent(),
        ],
    )
