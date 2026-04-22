"""
data/preferences.py — 사용자 취향 수집을 위한 고정 옵션 데이터
"""
from typing import TypedDict


class OptionDef(TypedDict):
    type: str        # "radio" | "checkbox"
    label: str
    choices: list[str]


HOTEL_PREFERENCE_OPTIONS: dict[str, OptionDef] = {
    "hotel_grade": {
        "type": "radio",
        "label": "호텔 등급",
        "choices": ["2성", "3성", "4성", "5성"],
    },
    "hotel_type": {
        "type": "radio",
        "label": "숙소 유형",
        "choices": ["비즈니스", "리조트", "부티크", "게스트하우스"],
    },
    "amenities": {
        "type": "checkbox",
        "label": "편의시설",
        "choices": ["수영장", "조식포함", "주차", "피트니스", "반려동물 가능", "조기체크인"],
    },
}

FLIGHT_PREFERENCE_OPTIONS: dict[str, OptionDef] = {
    "seat_class": {
        "type": "radio",
        "label": "좌석 등급",
        "choices": ["이코노미", "비즈니스", "퍼스트"],
    },
    "seat_position": {
        "type": "radio",
        "label": "좌석 위치",
        "choices": ["창가", "복도", "무관"],
    },
    "meal_preference": {
        "type": "radio",
        "label": "기내식",
        "choices": ["일반식", "채식", "할랄", "무관"],
    },
    "airline_preference": {
        "type": "checkbox",
        "label": "선호 항공사",
        "choices": ["대한항공", "아시아나", "저비용항공사 무관"],
    },
}

PREFERENCE_OPTIONS: dict[str, dict[str, OptionDef]] = {
    "hotel_preference": HOTEL_PREFERENCE_OPTIONS,
    "flight_preference": FLIGHT_PREFERENCE_OPTIONS,
}
