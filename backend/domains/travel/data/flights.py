"""
data/flights.py — 항공편 검색 정적 데이터
"""
from typing import Final

OUTBOUND_DB: Final[dict[tuple[str, str], list[dict]]] = {
    ("서울", "도쿄"): [
        {"airline": "대한항공", "flight": "KE703", "depart": "09:00", "arrive": "11:25", "duration": "2h25m", "price": 380000, "class": "이코노미"},
        {"airline": "아시아나", "flight": "OZ101", "depart": "11:30", "arrive": "13:55", "duration": "2h25m", "price": 350000, "class": "이코노미"},
        {"airline": "진에어", "flight": "LJ205", "depart": "14:00", "arrive": "16:20", "duration": "2h20m", "price": 220000, "class": "이코노미"},
    ],
    ("서울", "오사카"): [
        {"airline": "대한항공", "flight": "KE723", "depart": "08:30", "arrive": "10:40", "duration": "2h10m", "price": 320000, "class": "이코노미"},
        {"airline": "제주항공", "flight": "7C1101", "depart": "12:00", "arrive": "14:05", "duration": "2h05m", "price": 185000, "class": "이코노미"},
    ],
    ("서울", "방콕"): [
        {"airline": "대한항공", "flight": "KE657", "depart": "10:15", "arrive": "14:30", "duration": "5h45m", "price": 650000, "class": "이코노미"},
        {"airline": "타이항공", "flight": "TG659", "depart": "23:55", "arrive": "04:20+1", "duration": "5h55m", "price": 580000, "class": "이코노미"},
    ],
}

INBOUND_DB: Final[dict[tuple[str, str], list[dict]]] = {
    ("도쿄", "서울"): [
        {"airline": "대한항공", "flight": "KE704", "depart": "13:00", "arrive": "15:10", "duration": "2h10m", "price": 380000, "class": "이코노미"},
        {"airline": "아시아나", "flight": "OZ102", "depart": "15:30", "arrive": "17:40", "duration": "2h10m", "price": 350000, "class": "이코노미"},
        {"airline": "진에어", "flight": "LJ206", "depart": "18:00", "arrive": "20:05", "duration": "2h05m", "price": 220000, "class": "이코노미"},
    ],
    ("오사카", "서울"): [
        {"airline": "대한항공", "flight": "KE724", "depart": "12:00", "arrive": "13:55", "duration": "1h55m", "price": 320000, "class": "이코노미"},
        {"airline": "제주항공", "flight": "7C1102", "depart": "15:30", "arrive": "17:20", "duration": "1h50m", "price": 185000, "class": "이코노미"},
    ],
    ("방콕", "서울"): [
        {"airline": "대한항공", "flight": "KE658", "depart": "00:30", "arrive": "08:15", "duration": "5h45m", "price": 650000, "class": "이코노미"},
        {"airline": "타이항공", "flight": "TG656", "depart": "17:50", "arrive": "01:30+1", "duration": "5h40m", "price": 580000, "class": "이코노미"},
    ],
}
