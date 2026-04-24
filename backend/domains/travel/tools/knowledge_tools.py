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

    Args:
        query: 사용자의 자연어 질문
        city: 선택적 도시 필터
        hotel_code: 선택적 호텔 코드 필터
        intent: 선택적 의도 힌트

    Returns:
        구조화된 검색 결과와 답변 근거
    """
    return search_knowledge(query=query, city=city, hotel_code=hotel_code, intent=intent)
