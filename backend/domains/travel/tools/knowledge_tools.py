"""Knowledge retrieval tool for broader travel consultation."""

from __future__ import annotations

from typing import Any

from domains.travel.knowledge import search_knowledge


def search_travel_knowledge(
    query: str,
    city: str = "",
    hotel_code: str = "",
    intent: str = "",
) -> dict[str, Any]:
    """
    여행 지식 그래프에서 추천, 비교, 조건형 질문에 필요한 근거를 검색합니다.

    이 도구는 날짜, 인원, 출발지, 목적지 등 request_user_input으로 받아야 하는
    상세 정보 수집이 완료된 뒤에만 사용합니다. 상세 정보 수집이 필요한 턴에서는
    request_user_input만 호출하고, 이 도구를 같은 턴에 함께 호출하지 않습니다.
    이 도구를 호출한 응답 턴에서는 search_hotels, search_flights, get_travel_tips를
    이어서 호출하지 말고, 반환된 results/evidence만으로 답변합니다.

    Args:
        query: 사용자의 자연어 질문
        city: 선택적 도시 필터
        hotel_code: 선택적 호텔 코드 필터
        intent: 선택적 의도 힌트

    Returns:
        구조화된 검색 결과와 답변 근거
    """
    return search_knowledge(query=query, city=city, hotel_code=hotel_code, intent=intent)
