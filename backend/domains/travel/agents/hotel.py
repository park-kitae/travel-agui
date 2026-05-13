"""Hotel domain sub-agent factory."""

from __future__ import annotations

from google.adk.agents import LlmAgent

from ..tools import get_hotel_detail, request_user_input, search_hotels
from .shared import build_agent_instruction, create_domain_agent


HOTEL_INSTRUCTION = build_agent_instruction(
    "당신은 여행 AI의 호텔 전담 에이전트입니다.",
    [
        "호텔 관련 요청만 처리합니다.",
        '선택된 호텔 코드나 메시지 속 호텔 코드가 있으면 get_hotel_detail(hotel_code)을 호출합니다.',
        '도시, 체크인, 체크아웃, 인원이 충분하면 search_hotels(city, check_in, check_out, guests)를 호출합니다.',
        '정보가 부족하면 request_user_input("hotel_booking_details", "", context)로 필요한 값을 요청합니다.',
        "현재 여행 컨텍스트에 이미 있는 값은 우선 사용하고, 재사용한 값이 있으면 한 줄로만 안내합니다.",
        "호텔 외 요청은 코디네이터 에이전트로 이관합니다.",
    ],
)


def create_hotel_agent() -> LlmAgent:
    """호텔 전담 서브 에이전트를 생성합니다."""
    return create_domain_agent(
        name="hotel_agent",
        description="호텔 검색, 상세 정보, 예약 정보 수집 전담 에이전트",
        instruction=HOTEL_INSTRUCTION,
        tools=[search_hotels, get_hotel_detail, request_user_input],
    )
