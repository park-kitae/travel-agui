"""Flight domain sub-agent factory."""

from __future__ import annotations

from google.adk.agents import LlmAgent

from ..tools import request_user_input, search_flights
from .shared import build_agent_instruction, create_domain_agent


FLIGHT_INSTRUCTION = build_agent_instruction(
    "당신은 여행 AI의 항공 전담 에이전트입니다.",
    [
        "항공 관련 요청만 처리합니다.",
        '출발지, 목적지, 출발일, 인원이 충분하면 search_flights(origin, destination, departure_date, passengers, return_date)를 호출합니다.',
        '정보가 부족하면 request_user_input("flight_booking_details", "", context)로 필요한 값을 요청합니다.',
        "현재 여행 컨텍스트에 이미 있는 값은 우선 사용하고, 재사용한 값이 있으면 한 줄로만 안내합니다.",
        "항공 외 요청은 코디네이터 에이전트로 이관합니다.",
    ],
)


def create_flight_agent() -> LlmAgent:
    """항공편 전담 서브 에이전트를 생성합니다."""
    return create_domain_agent(
        name="flight_agent",
        description="항공편 검색, 예약 정보 수집 전담 에이전트",
        instruction=FLIGHT_INSTRUCTION,
        tools=[search_flights, request_user_input],
    )
