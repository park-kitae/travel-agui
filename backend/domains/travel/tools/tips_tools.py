"""
tools/tips_tools.py — 여행 팁 조회 툴
"""
from domains.travel.data import TIPS_DB


def get_travel_tips(destination: str, travel_type: str = "일반") -> dict:
    """
    목적지의 여행 팁과 주요 관광지 정보를 조회합니다.

    Args:
        destination: 여행 목적지
        travel_type: 여행 유형 (일반, 음식, 문화, 쇼핑, 자연)

    Returns:
        여행 팁 및 관광지 정보
    """
    matched = next((key for key in TIPS_DB if key in destination or destination in key), None)
    if not matched:
        return {"status": "not_found", "message": f"{destination}의 여행 정보를 찾을 수 없습니다."}
    return {"status": "success", "destination": matched, "travel_type": travel_type, **TIPS_DB[matched]}
