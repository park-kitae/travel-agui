"""
tools/favorite_tools.py — 사용자 취향 수집 요청 툴
"""
from domains.travel.data import PREFERENCE_OPTIONS


def request_user_favorite(favorite_type: str, context: str = "") -> dict:
    """
    호텔 또는 항공편 예약 전 사용자 취향을 수집하기 위한 폼을 요청합니다.

    사용 시기:
    - 호텔 추천 요청 시 hotel_preference 미수집 상태
    - 항공편 추천 요청 시 flight_preference 미수집 상태

    Args:
        favorite_type: "hotel_preference" 또는 "flight_preference"
        context: 미사용 (인터페이스 일관성 유지용)

    Returns:
        {status: "user_favorite_required", favorite_type: ..., options: {...}}
    """
    options = PREFERENCE_OPTIONS.get(favorite_type, {})
    return {
        "status": "user_favorite_required",
        "favorite_type": favorite_type,
        "options": options,
    }
