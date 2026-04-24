"""
tools/hotel_tools.py — 호텔 검색 및 상세 조회 툴
"""
from domains.travel.data import HOTEL_DB, HOTEL_DETAIL_DB
from domains.travel.knowledge import search_knowledge


def search_hotels(
    city: str,
    check_in: str,
    check_out: str,
    guests: int = 2,
    recommendation_query: str = "",
) -> dict:
    """
    도시와 날짜로 호텔을 검색합니다.

    Args:
        city: 여행 도시 (예: 도쿄, 오사카, 제주)
        check_in: 체크인 날짜 (YYYY-MM-DD)
        check_out: 체크아웃 날짜 (YYYY-MM-DD)
        guests: 투숙 인원 수
        recommendation_query: 조건 기반 추천/비교 질문. 값이 있으면 GraphRAG 근거로 호텔을 정렬합니다.

    Returns:
        호텔 검색 결과 목록 (각 호텔에 hotel_code 포함)
    """
    matched_city = next(
        (key for key in HOTEL_DB if key in city or city in key), None
    )
    if not matched_city:
        return {"status": "not_found", "message": f"{city}에 대한 호텔 정보를 찾을 수 없습니다.", "hotels": []}

    hotels = [
        {**h, "city": matched_city, "check_in": check_in, "check_out": check_out, "guests": guests}
        for h in HOTEL_DB[matched_city]
    ]

    recommendation = None
    if recommendation_query.strip():
        knowledge = search_knowledge(recommendation_query, city=matched_city, intent="hotel_recommendation")
        matched_codes = [
            str(item.get("hotel_code"))
            for item in knowledge.get("results", [])
            if item.get("type") == "hotel" and item.get("hotel_code")
        ]
        hotels = _rank_hotels_by_codes(hotels, matched_codes)
        recommendation = {
            "query": recommendation_query,
            "matched_hotel_codes": matched_codes,
            "answer_focus": knowledge.get("answer_focus", ""),
            "evidence": knowledge.get("evidence", []),
        }

    result = {
        "status": "success",
        "city": matched_city,
        "check_in": check_in,
        "check_out": check_out,
        "guests": guests,
        "count": len(hotels),
        "hotels": hotels,
    }
    if recommendation is not None:
        result["recommendation"] = recommendation
    return result


def get_hotel_detail(hotel_code: str) -> dict:
    """
    호텔 코드로 호텔 상세 정보를 조회합니다.
    사용자가 호텔 리스트에서 특정 호텔을 선택했을 때 호출합니다.

    Args:
        hotel_code: 호텔 코드 (예: HTL-SEO-001, HTL-TYO-002)

    Returns:
        호텔 상세 정보 (객실 타입, 편의시설, 정책 등)
    """
    if hotel_code not in HOTEL_DETAIL_DB:
        return {"status": "not_found", "message": f"호텔 코드 {hotel_code}에 해당하는 호텔을 찾을 수 없습니다."}
    return {**HOTEL_DETAIL_DB[hotel_code], "status": "success"}


def _rank_hotels_by_codes(hotels: list[dict], matched_codes: list[str]) -> list[dict]:
    if not matched_codes:
        return hotels
    rank = {code: index for index, code in enumerate(matched_codes)}
    return sorted(
        hotels,
        key=lambda hotel: (
            rank.get(str(hotel.get("hotel_code")), len(rank)),
            str(hotel.get("hotel_code", "")),
        ),
    )
