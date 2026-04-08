"""
agent.py — Google ADK 기반 여행 에이전트
AG-UI 미들웨어에서 호출되는 핵심 에이전트 정의
"""
import asyncio
import json
from typing import Any
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool


# ──────────────────────────────────────────────
# MCP 스타일 Tool 함수들 (실제 환경에서는 MCP 서버 연결)
# ──────────────────────────────────────────────

def search_hotels(city: str, check_in: str, check_out: str, guests: int = 2) -> dict:
    """
    도시와 날짜로 호텔을 검색합니다.

    Args:
        city: 여행 도시 (예: 도쿄, 오사카, 제주)
        check_in: 체크인 날짜 (YYYY-MM-DD)
        check_out: 체크아웃 날짜 (YYYY-MM-DD)
        guests: 투숙 인원 수

    Returns:
        호텔 검색 결과 목록 (각 호텔에 hotel_code 포함)
    """
    hotel_db = {
        "서울": [
            {"hotel_code": "HTL-SEO-001", "name": "포시즌스 호텔 서울", "area": "광화문", "price": 450000, "rating": 4.9, "stars": 5},
            {"hotel_code": "HTL-SEO-002", "name": "조선팰리스", "area": "소공동", "price": 380000, "rating": 4.8, "stars": 5},
            {"hotel_code": "HTL-SEO-003", "name": "롯데호텔 서울", "area": "명동", "price": 320000, "rating": 4.6, "stars": 5},
            {"hotel_code": "HTL-SEO-004", "name": "그랜드 하얏트 서울", "area": "이태원", "price": 280000, "rating": 4.7, "stars": 5},
            {"hotel_code": "HTL-SEO-005", "name": "신라스테이 서울역", "area": "서울역", "price": 150000, "rating": 4.3, "stars": 4},
        ],
        "도쿄": [
            {"hotel_code": "HTL-TYO-001", "name": "파크 하얏트 도쿄", "area": "신주쿠", "price": 420000, "rating": 4.8, "stars": 5},
            {"hotel_code": "HTL-TYO-002", "name": "더 프린스 갤러리 도쿄", "area": "긴자", "price": 380000, "rating": 4.7, "stars": 5},
            {"hotel_code": "HTL-TYO-003", "name": "아파 호텔 신주쿠", "area": "신주쿠", "price": 120000, "rating": 4.2, "stars": 3},
        ],
        "오사카": [
            {"hotel_code": "HTL-OSA-001", "name": "콘래드 오사카", "area": "나카노시마", "price": 350000, "rating": 4.8, "stars": 5},
            {"hotel_code": "HTL-OSA-002", "name": "더블트리 힐튼 오사카", "area": "우메다", "price": 200000, "rating": 4.5, "stars": 4},
            {"hotel_code": "HTL-OSA-003", "name": "도미 인 난바", "area": "난바", "price": 95000, "rating": 4.3, "stars": 3},
        ],
        "제주": [
            {"hotel_code": "HTL-JEJ-001", "name": "롯데호텔 제주", "area": "중문", "price": 280000, "rating": 4.6, "stars": 5},
            {"hotel_code": "HTL-JEJ-002", "name": "신라스테이 제주", "area": "제주시", "price": 180000, "rating": 4.4, "stars": 4},
            {"hotel_code": "HTL-JEJ-003", "name": "라마다 제주 호텔", "area": "노형", "price": 130000, "rating": 4.1, "stars": 4},
        ],
        "방콕": [
            {"hotel_code": "HTL-BKK-001", "name": "만다린 오리엔탈 방콕", "area": "리버사이드", "price": 520000, "rating": 4.9, "stars": 5},
            {"hotel_code": "HTL-BKK-002", "name": "아난타라 시암", "area": "수쿰빗", "price": 310000, "rating": 4.7, "stars": 5},
            {"hotel_code": "HTL-BKK-003", "name": "이비스 방콕 나나", "area": "나나", "price": 85000, "rating": 4.2, "stars": 3},
        ],
    }

    matched_city = None
    for key in hotel_db:
        if key in city or city in key:
            matched_city = key
            break

    if not matched_city:
        return {
            "status": "not_found",
            "message": f"{city}에 대한 호텔 정보를 찾을 수 없습니다.",
            "hotels": []
        }

    hotels = hotel_db[matched_city]
    for h in hotels:
        h["city"] = matched_city
        h["check_in"] = check_in
        h["check_out"] = check_out
        h["guests"] = guests

    return {
        "status": "success",
        "city": matched_city,
        "check_in": check_in,
        "check_out": check_out,
        "guests": guests,
        "count": len(hotels),
        "hotels": hotels
    }


# ──────────────────────────────────────────────
# 호텔 상세 정보 DB
# ──────────────────────────────────────────────

_hotel_detail_db = {
    "HTL-SEO-001": {
        "hotel_code": "HTL-SEO-001",
        "name": "포시즌스 호텔 서울",
        "city": "서울", "area": "광화문", "stars": 5, "rating": 4.9,
        "address": "서울특별시 종로구 새문안로 97",
        "phone": "+82-2-6388-5000",
        "description": "광화문 광장 인근에 위치한 최고급 럭셔리 호텔로, 한국 전통미와 현대적 세련미가 조화를 이룹니다. 경복궁 뷰와 도심 야경을 동시에 즐길 수 있으며, 미슐랭 가이드 레스토랑을 보유하고 있습니다.",
        "amenities": ["야외 온수 수영장", "스파 & 웰니스 센터", "피트니스 센터", "미슐랭 레스토랑 2개", "루프탑 바", "비즈니스 센터", "컨시어지 서비스", "발렛 파킹", "공항 리무진"],
        "room_types": [
            {"type": "디럭스 룸", "size": "48m²", "price_per_night": 450000, "max_guests": 2, "bed": "킹베드"},
            {"type": "프리미어 룸", "size": "56m²", "price_per_night": 580000, "max_guests": 2, "bed": "킹베드"},
            {"type": "슈피리어 스위트", "size": "82m²", "price_per_night": 850000, "max_guests": 3, "bed": "킹베드 + 소파베드"},
            {"type": "그랜드 스위트", "size": "120m²", "price_per_night": 1200000, "max_guests": 4, "bed": "킹베드 2개"},
        ],
        "check_in_time": "15:00", "check_out_time": "12:00",
        "cancel_policy": "체크인 3일 전까지 무료 취소",
        "highlights": ["광화문 광장 도보 1분", "경복궁 뷰 객실", "미슐랭 레스토랑 운영", "전용 리무진 서비스"],
    },
    "HTL-SEO-002": {
        "hotel_code": "HTL-SEO-002",
        "name": "조선팰리스", "city": "서울", "area": "소공동", "stars": 5, "rating": 4.8,
        "address": "서울특별시 중구 소공로 119",
        "phone": "+82-2-6656-2222",
        "description": "1914년 개관한 역사적인 호텔로, 서울 중심부 명동·소공동에 위치합니다. 클래식한 품격과 현대적 편의시설이 조화를 이루며, 쇼핑·관광에 최적의 접근성을 자랑합니다.",
        "amenities": ["실내 수영장", "스파", "피트니스 센터", "레스토랑 4개", "바/라운지", "비즈니스 센터", "발렛 파킹"],
        "room_types": [
            {"type": "슈피리어 룸", "size": "36m²", "price_per_night": 380000, "max_guests": 2, "bed": "킹베드"},
            {"type": "디럭스 룸", "size": "44m²", "price_per_night": 480000, "max_guests": 2, "bed": "킹베드"},
            {"type": "주니어 스위트", "size": "65m²", "price_per_night": 720000, "max_guests": 3, "bed": "킹베드 + 소파베드"},
        ],
        "check_in_time": "15:00", "check_out_time": "11:00",
        "cancel_policy": "체크인 2일 전까지 무료 취소",
        "highlights": ["명동 쇼핑가 도보 5분", "110년 역사의 전통", "시티뷰 레스토랑", "지하철 직결"],
    },
    "HTL-SEO-003": {
        "hotel_code": "HTL-SEO-003",
        "name": "롯데호텔 서울", "city": "서울", "area": "명동", "stars": 5, "rating": 4.6,
        "address": "서울특별시 중구 을지로 30",
        "phone": "+82-2-771-1000",
        "description": "명동 중심에 위치한 대형 비즈니스·레저 호텔입니다. 롯데백화점과 직결되어 쇼핑이 편리하며, 다양한 F&B 시설과 넓은 회의 공간을 보유하고 있습니다.",
        "amenities": ["실내 수영장", "스파", "피트니스 센터", "레스토랑 6개", "면세점 연결", "비즈니스 센터", "주차장"],
        "room_types": [
            {"type": "스탠다드 룸", "size": "32m²", "price_per_night": 280000, "max_guests": 2, "bed": "더블베드"},
            {"type": "디럭스 룸", "size": "38m²", "price_per_night": 320000, "max_guests": 2, "bed": "킹베드"},
            {"type": "이그제큐티브 룸", "size": "42m²", "price_per_night": 420000, "max_guests": 2, "bed": "킹베드"},
        ],
        "check_in_time": "14:00", "check_out_time": "11:00",
        "cancel_policy": "체크인 1일 전까지 무료 취소",
        "highlights": ["명동 핵심 위치", "롯데백화점 직결", "면세점 이용 편리", "다양한 레스토랑"],
    },
    "HTL-SEO-004": {
        "hotel_code": "HTL-SEO-004",
        "name": "그랜드 하얏트 서울", "city": "서울", "area": "이태원", "stars": 5, "rating": 4.7,
        "address": "서울특별시 용산구 소월로 322",
        "phone": "+82-2-797-1234",
        "description": "남산 기슭에 위치하여 서울 전경과 한강 뷰를 자랑하는 럭셔리 호텔입니다. 이태원 문화지구와 인접하며, 대규모 컨벤션 시설로 비즈니스 행사에도 최적입니다.",
        "amenities": ["야외 수영장", "스파", "테니스 코트", "피트니스 센터", "레스토랑 5개", "볼링장", "비즈니스 센터", "발렛 파킹"],
        "room_types": [
            {"type": "스탠다드 룸", "size": "36m²", "price_per_night": 280000, "max_guests": 2, "bed": "킹베드"},
            {"type": "시티뷰 룸", "size": "40m²", "price_per_night": 340000, "max_guests": 2, "bed": "킹베드"},
            {"type": "파크뷰 스위트", "size": "78m²", "price_per_night": 680000, "max_guests": 3, "bed": "킹베드 + 소파베드"},
        ],
        "check_in_time": "15:00", "check_out_time": "12:00",
        "cancel_policy": "체크인 2일 전까지 무료 취소",
        "highlights": ["남산 & 한강 전망", "대규모 야외 수영장", "테니스 코트 보유", "이태원 인접"],
    },
    "HTL-SEO-005": {
        "hotel_code": "HTL-SEO-005",
        "name": "신라스테이 서울역", "city": "서울", "area": "서울역", "stars": 4, "rating": 4.3,
        "address": "서울특별시 중구 청파로 426",
        "phone": "+82-2-6953-5000",
        "description": "서울역 바로 앞에 위치한 비즈니스 호텔로, KTX·공항철도·지하철 모두 도보 이용 가능합니다. 합리적인 가격과 깔끔한 시설로 비즈니스 여행객에게 인기입니다.",
        "amenities": ["피트니스 센터", "레스토랑", "카페", "비즈니스 센터", "세탁 서비스"],
        "room_types": [
            {"type": "스탠다드 룸", "size": "22m²", "price_per_night": 130000, "max_guests": 2, "bed": "더블베드"},
            {"type": "슈피리어 룸", "size": "26m²", "price_per_night": 150000, "max_guests": 2, "bed": "킹베드"},
            {"type": "트윈 룸", "size": "26m²", "price_per_night": 155000, "max_guests": 2, "bed": "싱글베드 2개"},
        ],
        "check_in_time": "15:00", "check_out_time": "11:00",
        "cancel_policy": "체크인 당일 18시까지 무료 취소",
        "highlights": ["서울역 도보 1분", "KTX·공항철도 직결", "합리적인 가격", "깔끔한 현대식 시설"],
    },
    "HTL-TYO-001": {
        "hotel_code": "HTL-TYO-001",
        "name": "파크 하얏트 도쿄", "city": "도쿄", "area": "신주쿠", "stars": 5, "rating": 4.8,
        "address": "〒163-1055 東京都新宿区西新宿2-7-2",
        "phone": "+81-3-5322-1234",
        "description": "신주쿠 초고층 파크 타워 39~52층에 자리한 아이코닉한 럭셔리 호텔입니다. 영화 '사랑도 통역이 되나요?'의 촬영지로 유명하며, 도쿄 전경과 후지산 조망이 가능합니다.",
        "amenities": ["야외 수영장(47층)", "스파", "피트니스 센터", "레스토랑 3개", "재즈 바", "도서관 라운지", "컨시어지"],
        "room_types": [
            {"type": "파크 룸", "size": "50m²", "price_per_night": 420000, "max_guests": 2, "bed": "킹베드"},
            {"type": "시티 룸", "size": "55m²", "price_per_night": 500000, "max_guests": 2, "bed": "킹베드"},
            {"type": "파크 스위트", "size": "100m²", "price_per_night": 980000, "max_guests": 3, "bed": "킹베드 + 소파베드"},
        ],
        "check_in_time": "15:00", "check_out_time": "12:00",
        "cancel_policy": "체크인 3일 전까지 무료 취소",
        "highlights": ["영화 '사랑도 통역이 되나요?' 촬영지", "후지산 조망 가능", "47층 야외 수영장", "신주쿠역 도보 10분"],
    },
    "HTL-TYO-002": {
        "hotel_code": "HTL-TYO-002",
        "name": "더 프린스 갤러리 도쿄", "city": "도쿄", "area": "긴자", "stars": 5, "rating": 4.7,
        "address": "〒107-8666 東京都港区赤坂1-2-3",
        "phone": "+81-3-4333-1111",
        "description": "도쿄 도심 아카사카에 위치한 럭셔리 호텔로, 일본 현대 미술 작품으로 장식된 갤러리 컨셉을 자랑합니다. 긴자, 아카사카 등 도쿄 핵심 지구에 인접합니다.",
        "amenities": ["실내 수영장", "스파", "피트니스 센터", "레스토랑 4개", "아트 갤러리", "바", "비즈니스 센터"],
        "room_types": [
            {"type": "디럭스 룸", "size": "45m²", "price_per_night": 380000, "max_guests": 2, "bed": "킹베드"},
            {"type": "프리미엄 룸", "size": "52m²", "price_per_night": 460000, "max_guests": 2, "bed": "킹베드"},
            {"type": "스위트", "size": "90m²", "price_per_night": 850000, "max_guests": 3, "bed": "킹베드 + 소파베드"},
        ],
        "check_in_time": "15:00", "check_out_time": "12:00",
        "cancel_policy": "체크인 2일 전까지 무료 취소",
        "highlights": ["일본 현대 미술 갤러리 컨셉", "긴자 쇼핑 접근 용이", "도쿄 스카이트리 조망", "미슐랭 레스토랑 입점"],
    },
    "HTL-TYO-003": {
        "hotel_code": "HTL-TYO-003",
        "name": "아파 호텔 신주쿠", "city": "도쿄", "area": "신주쿠", "stars": 3, "rating": 4.2,
        "address": "〒160-0021 東京都新宿区歌舞伎町1-1-9",
        "phone": "+81-3-5291-6211",
        "description": "신주쿠 가부키초 바로 앞에 위치한 가성비 호텔입니다. 관광·쇼핑의 중심지에 있으면서 합리적인 가격을 제공하며, 깔끔하고 기능적인 객실이 특징입니다.",
        "amenities": ["피트니스 센터", "자판기 코너", "코인 세탁실", "편의점"],
        "room_types": [
            {"type": "싱글 룸", "size": "15m²", "price_per_night": 95000, "max_guests": 1, "bed": "싱글베드"},
            {"type": "더블 룸", "size": "18m²", "price_per_night": 120000, "max_guests": 2, "bed": "더블베드"},
            {"type": "트윈 룸", "size": "22m²", "price_per_night": 130000, "max_guests": 2, "bed": "싱글베드 2개"},
        ],
        "check_in_time": "16:00", "check_out_time": "11:00",
        "cancel_policy": "체크인 당일까지 무료 취소",
        "highlights": ["신주쿠역 도보 5분", "가부키초 인접", "합리적인 가격", "편의점 24시간 운영"],
    },
    "HTL-OSA-001": {
        "hotel_code": "HTL-OSA-001",
        "name": "콘래드 오사카", "city": "오사카", "area": "나카노시마", "stars": 5, "rating": 4.8,
        "address": "〒530-0005 大阪府大阪市北区中之島3-2-4",
        "phone": "+81-6-6222-0111",
        "description": "나카노시마 페스티벌 타워 웨스트 33~40층에 자리한 오사카 최고급 호텔입니다. 도지마강과 나카노시마 공원 전망을 보유하며, 아트 작품으로 가득한 인테리어가 인상적입니다.",
        "amenities": ["실내 수영장(40층)", "스파", "피트니스 센터", "레스토랑 3개", "바", "비즈니스 센터", "발렛 파킹"],
        "room_types": [
            {"type": "디럭스 룸", "size": "48m²", "price_per_night": 350000, "max_guests": 2, "bed": "킹베드"},
            {"type": "시티뷰 룸", "size": "52m²", "price_per_night": 420000, "max_guests": 2, "bed": "킹베드"},
            {"type": "이그제큐티브 스위트", "size": "95m²", "price_per_night": 880000, "max_guests": 3, "bed": "킹베드 + 소파베드"},
        ],
        "check_in_time": "15:00", "check_out_time": "12:00",
        "cancel_policy": "체크인 3일 전까지 무료 취소",
        "highlights": ["40층 실내 수영장", "나카노시마 강변 전망", "도보 우메다·도지마 접근", "세계적 수준의 스파"],
    },
    "HTL-OSA-002": {
        "hotel_code": "HTL-OSA-002",
        "name": "더블트리 힐튼 오사카", "city": "오사카", "area": "우메다", "stars": 4, "rating": 4.5,
        "address": "〒530-0011 大阪府大阪市北区大深町3-60",
        "phone": "+81-6-6376-5000",
        "description": "우메다 그랜드 프런트 오사카 내에 위치한 힐튼 계열 호텔입니다. 오사카역과 직결되어 이동이 매우 편리하며, 쇼핑몰과 레스토랑가에 바로 접근할 수 있습니다.",
        "amenities": ["피트니스 센터", "레스토랑", "바", "비즈니스 센터", "무료 주차"],
        "room_types": [
            {"type": "스탠다드 룸", "size": "30m²", "price_per_night": 180000, "max_guests": 2, "bed": "킹베드"},
            {"type": "디럭스 룸", "size": "36m²", "price_per_night": 220000, "max_guests": 2, "bed": "킹베드"},
            {"type": "스위트", "size": "65m²", "price_per_night": 450000, "max_guests": 3, "bed": "킹베드 + 소파베드"},
        ],
        "check_in_time": "15:00", "check_out_time": "11:00",
        "cancel_policy": "체크인 1일 전까지 무료 취소",
        "highlights": ["오사카역 직결", "그랜드 프런트 오사카 쇼핑몰 연결", "우메다 상권 인접", "체크인 시 쿠키 제공"],
    },
    "HTL-OSA-003": {
        "hotel_code": "HTL-OSA-003",
        "name": "도미 인 난바", "city": "오사카", "area": "난바", "stars": 3, "rating": 4.3,
        "address": "〒542-0086 大阪府大阪市中央区難波5-1-3",
        "phone": "+81-6-6634-5489",
        "description": "도톤보리·난바 맛집 거리 바로 인근에 위치한 가성비 비즈니스 호텔입니다. 일본식 온천(대욕장)을 무료로 이용할 수 있으며, 야식 라멘 서비스로 유명합니다.",
        "amenities": ["온천 대욕장", "사우나", "자판기 코너", "코인 세탁실", "야식 라멘 서비스(21:30~23:00)"],
        "room_types": [
            {"type": "싱글 룸", "size": "14m²", "price_per_night": 75000, "max_guests": 1, "bed": "싱글베드"},
            {"type": "더블 룸", "size": "18m²", "price_per_night": 95000, "max_guests": 2, "bed": "더블베드"},
            {"type": "트윈 룸", "size": "20m²", "price_per_night": 100000, "max_guests": 2, "bed": "싱글베드 2개"},
        ],
        "check_in_time": "16:00", "check_out_time": "11:00",
        "cancel_policy": "체크인 당일까지 무료 취소",
        "highlights": ["난바역 도보 2분", "무료 온천 대욕장", "야식 라멘 무료 제공", "도톤보리 도보 3분"],
    },
    "HTL-JEJ-001": {
        "hotel_code": "HTL-JEJ-001",
        "name": "롯데호텔 제주", "city": "제주", "area": "중문", "stars": 5, "rating": 4.6,
        "address": "제주특별자치도 서귀포시 중문관광로72번길 35",
        "phone": "+82-64-731-1000",
        "description": "제주 중문 관광단지 내에 위치한 제주 최고급 리조트 호텔입니다. 광대한 정원과 제주 바다 전망, 다양한 레저 시설을 갖추고 있어 가족 여행객에게 특히 인기입니다.",
        "amenities": ["야외 수영장", "실내 수영장", "스파", "골프장", "테니스 코트", "레스토랑 5개", "키즈 클럽", "피트니스"],
        "room_types": [
            {"type": "스탠다드 룸", "size": "36m²", "price_per_night": 250000, "max_guests": 2, "bed": "킹베드"},
            {"type": "오션뷰 룸", "size": "40m²", "price_per_night": 320000, "max_guests": 2, "bed": "킹베드"},
            {"type": "패밀리 룸", "size": "55m²", "price_per_night": 420000, "max_guests": 4, "bed": "킹베드 + 트윈베드"},
            {"type": "풀빌라 스위트", "size": "120m²", "price_per_night": 950000, "max_guests": 4, "bed": "킹베드 2개"},
        ],
        "check_in_time": "15:00", "check_out_time": "11:00",
        "cancel_policy": "체크인 3일 전까지 무료 취소",
        "highlights": ["중문 해변 도보 5분", "골프장 보유", "키즈 클럽 운영", "대규모 야외 수영장"],
    },
    "HTL-JEJ-002": {
        "hotel_code": "HTL-JEJ-002",
        "name": "신라스테이 제주", "city": "제주", "area": "제주시", "stars": 4, "rating": 4.4,
        "address": "제주특별자치도 제주시 노연로 80",
        "phone": "+82-64-741-1100",
        "description": "제주 시내 중심에 위치한 현대적 비즈니스 호텔입니다. 제주 국제공항에서 가깝고, 제주 올레길 및 주요 관광지 접근이 용이합니다.",
        "amenities": ["피트니스 센터", "레스토랑", "카페", "비즈니스 센터", "주차장"],
        "room_types": [
            {"type": "스탠다드 룸", "size": "25m²", "price_per_night": 160000, "max_guests": 2, "bed": "더블베드"},
            {"type": "슈피리어 룸", "size": "30m²", "price_per_night": 180000, "max_guests": 2, "bed": "킹베드"},
            {"type": "트윈 룸", "size": "30m²", "price_per_night": 185000, "max_guests": 2, "bed": "싱글베드 2개"},
        ],
        "check_in_time": "15:00", "check_out_time": "11:00",
        "cancel_policy": "체크인 당일 18시까지 무료 취소",
        "highlights": ["공항 차량 10분", "제주 시내 중심", "렌터카 픽업 편리", "합리적인 가격"],
    },
    "HTL-JEJ-003": {
        "hotel_code": "HTL-JEJ-003",
        "name": "라마다 제주 호텔", "city": "제주", "area": "노형", "stars": 4, "rating": 4.1,
        "address": "제주특별자치도 제주시 1100로 3031",
        "phone": "+82-64-720-7000",
        "description": "한라산 인근 제주시 노형동에 위치한 4성급 호텔입니다. 제주 자연을 즐기기 좋은 위치이며, 편안한 객실과 합리적인 가격으로 가족·커플 여행객이 즐겨 찾습니다.",
        "amenities": ["수영장", "피트니스 센터", "레스토랑", "주차장(무료)", "세탁 서비스"],
        "room_types": [
            {"type": "스탠다드 룸", "size": "28m²", "price_per_night": 115000, "max_guests": 2, "bed": "더블베드"},
            {"type": "디럭스 룸", "size": "33m²", "price_per_night": 130000, "max_guests": 2, "bed": "킹베드"},
            {"type": "패밀리 룸", "size": "48m²", "price_per_night": 200000, "max_guests": 4, "bed": "킹베드 + 싱글베드"},
        ],
        "check_in_time": "15:00", "check_out_time": "11:00",
        "cancel_policy": "체크인 당일까지 무료 취소",
        "highlights": ["한라산 드라이브 코스 인근", "무료 주차", "한라수목원 도보 15분", "합리적 가격"],
    },
    "HTL-BKK-001": {
        "hotel_code": "HTL-BKK-001",
        "name": "만다린 오리엔탈 방콕", "city": "방콕", "area": "리버사이드", "stars": 5, "rating": 4.9,
        "address": "48 Oriental Avenue, Bang Rak, Bangkok 10500",
        "phone": "+66-2-659-9000",
        "description": "1876년 개관한 아시아 최고의 럭셔리 호텔 중 하나입니다. 차오프라야 강변에 위치하며 150년 역사의 유산, 세계적 명성의 스파, 미슐랭 레스토랑을 보유합니다. 수많은 작가와 왕실이 머문 역사적 호텔입니다.",
        "amenities": ["강변 수영장", "더 스파(세계 최고 수준)", "테니스 코트", "쿠킹 스쿨", "레스토랑 5개", "리버 크루즈 전용 셔틀", "발렛 파킹"],
        "room_types": [
            {"type": "슈피리어 룸", "size": "38m²", "price_per_night": 480000, "max_guests": 2, "bed": "킹베드"},
            {"type": "디럭스 룸(리버뷰)", "size": "45m²", "price_per_night": 580000, "max_guests": 2, "bed": "킹베드"},
            {"type": "오리엔탈 스위트", "size": "100m²", "price_per_night": 1400000, "max_guests": 3, "bed": "킹베드 + 소파베드"},
        ],
        "check_in_time": "14:00", "check_out_time": "12:00",
        "cancel_policy": "체크인 3일 전까지 무료 취소",
        "highlights": ["150년 역사의 아이코닉 호텔", "세계 Top 3 스파", "차오프라야 강변 전망", "전용 리버 크루즈 서비스"],
    },
    "HTL-BKK-002": {
        "hotel_code": "HTL-BKK-002",
        "name": "아난타라 시암", "city": "방콕", "area": "수쿰빗", "stars": 5, "rating": 4.7,
        "address": "155 Rajadamri Road, Pathumwan, Bangkok 10330",
        "phone": "+66-2-126-8866",
        "description": "방콕 수쿰빗·쇼핑 지구 중심의 5성급 럭셔리 호텔입니다. 태국 전통 건축미와 현대적 세련미를 결합한 인테리어가 특징이며, 센트럴 월드 쇼핑몰과 도보 거리에 위치합니다.",
        "amenities": ["야외 수영장", "스파", "피트니스 센터", "레스토랑 4개", "루프탑 바", "발렛 파킹", "컨시어지"],
        "room_types": [
            {"type": "디럭스 룸", "size": "42m²", "price_per_night": 310000, "max_guests": 2, "bed": "킹베드"},
            {"type": "프리미엄 룸", "size": "50m²", "price_per_night": 380000, "max_guests": 2, "bed": "킹베드"},
            {"type": "시암 스위트", "size": "88m²", "price_per_night": 750000, "max_guests": 3, "bed": "킹베드 + 소파베드"},
        ],
        "check_in_time": "14:00", "check_out_time": "12:00",
        "cancel_policy": "체크인 2일 전까지 무료 취소",
        "highlights": ["BTS 라차담리역 도보 3분", "센트럴 월드 도보 5분", "루프탑 바 야경", "태국 전통 스파"],
    },
    "HTL-BKK-003": {
        "hotel_code": "HTL-BKK-003",
        "name": "이비스 방콕 나나", "city": "방콕", "area": "나나", "stars": 3, "rating": 4.2,
        "address": "1 Sukhumvit 4, Klongtoey, Bangkok 10110",
        "phone": "+66-2-659-2888",
        "description": "수쿰빗 나나 지역에 위치한 가성비 비즈니스 호텔입니다. BTS 나나역과 직결되어 방콕 전역으로의 이동이 편리하며, 깔끔하고 현대적인 시설을 합리적인 가격에 제공합니다.",
        "amenities": ["수영장", "피트니스 센터", "레스토랑", "바"],
        "room_types": [
            {"type": "스탠다드 룸", "size": "18m²", "price_per_night": 75000, "max_guests": 2, "bed": "더블베드"},
            {"type": "슈피리어 룸", "size": "22m²", "price_per_night": 85000, "max_guests": 2, "bed": "킹베드"},
            {"type": "트윈 룸", "size": "22m²", "price_per_night": 88000, "max_guests": 2, "bed": "싱글베드 2개"},
        ],
        "check_in_time": "14:00", "check_out_time": "12:00",
        "cancel_policy": "체크인 당일까지 무료 취소",
        "highlights": ["BTS 나나역 직결", "수쿰빗 상권 인접", "합리적인 가격", "수영장 보유"],
    },
}


def get_hotel_detail(hotel_code: str) -> dict:
    """
    호텔 코드로 호텔 상세 정보를 조회합니다.
    사용자가 호텔 리스트에서 특정 호텔을 선택했을 때 호출합니다.

    Args:
        hotel_code: 호텔 코드 (예: HTL-SEO-001, HTL-TYO-002)

    Returns:
        호텔 상세 정보 (객실 타입, 편의시설, 정책 등)
    """
    if hotel_code not in _hotel_detail_db:
        return {
            "status": "not_found",
            "message": f"호텔 코드 {hotel_code}에 해당하는 호텔을 찾을 수 없습니다."
        }

    detail = _hotel_detail_db[hotel_code].copy()
    detail["status"] = "success"
    return detail


def search_flights(origin: str, destination: str, departure_date: str, passengers: int = 1, return_date: str = "") -> dict:
    """
    출발지/목적지와 날짜로 항공편을 검색합니다.

    Args:
        origin: 출발 도시 또는 공항 코드 (예: 서울, ICN)
        destination: 도착 도시 또는 공항 코드 (예: 도쿄, NRT)
        departure_date: 출발 날짜 (YYYY-MM-DD)
        passengers: 승객 수
        return_date: 귀국 날짜 (YYYY-MM-DD), 빈 문자열이면 편도

    Returns:
        항공편 검색 결과 (편도 또는 왕복)
    """
    outbound_db = {
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

    inbound_db = {
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

    outbound_key = None
    for (orig, dest) in outbound_db:
        if (orig in origin or origin in orig) and (dest in destination or destination in dest):
            outbound_key = (orig, dest)
            break

    if not outbound_key:
        return {
            "status": "not_found",
            "message": f"{origin}→{destination} 구간 항공편을 찾을 수 없습니다.",
            "flights": []
        }

    outbound_flights = outbound_db[outbound_key]
    for f in outbound_flights:
        f["departure_date"] = departure_date
        f["passengers"] = passengers
        f["total_price"] = f["price"] * passengers
        f["direction"] = "outbound"

    is_round_trip = bool(return_date)
    inbound_flights = []

    if is_round_trip:
        inbound_key = (outbound_key[1], outbound_key[0])
        if inbound_key in inbound_db:
            inbound_flights = inbound_db[inbound_key]
            for f in inbound_flights:
                f["departure_date"] = return_date
                f["passengers"] = passengers
                f["total_price"] = f["price"] * passengers
                f["direction"] = "inbound"

    result = {
        "status": "success",
        "origin": outbound_key[0],
        "destination": outbound_key[1],
        "departure_date": departure_date,
        "passengers": passengers,
        "trip_type": "round_trip" if is_round_trip else "one_way",
    }

    if is_round_trip:
        result["return_date"] = return_date
        result["outbound_flights"] = outbound_flights
        result["inbound_flights"] = inbound_flights
        result["outbound_count"] = len(outbound_flights)
        result["inbound_count"] = len(inbound_flights)
    else:
        result["flights"] = outbound_flights
        result["count"] = len(outbound_flights)

    return result


def request_user_input(input_type: str, fields: str = "", context: str = "") -> dict:
    """
    호텔이나 항공편 검색에 필요한 정보가 부족할 때 사용자에게 입력 폼을 요청합니다.

    사용 시기:
    - 호텔 검색: 도시, 체크인 날짜, 체크아웃 날짜, 인원수 중 하나라도 없을 때
    - 항공편 검색: 출발지, 목적지, 출발 날짜, 인원수 중 하나라도 없을 때

    Args:
        input_type: "hotel_booking_details" 또는 "flight_booking_details"
        fields: 사용하지 않음 (자동 생성됨)
        context: 기존 여행 컨텍스트를 JSON 문자열로 전달 (기본값 채우기용)
            - hotel_booking_details 예시:
              '{"city":"도쿄","check_in":"2026-06-10","check_out":"2026-06-14","guests":2}'
            - flight_booking_details 예시:
              '{"origin":"서울","destination":"도쿄","departure_date":"2026-06-10","return_date":"2026-06-14","passengers":2}'
            - 알 수 없는 값은 해당 키를 생략하거나 빈 문자열로 전달

    Returns:
        사용자 입력 요청 정보 (기존 컨텍스트 값이 default로 채워진 필드 포함)
    """
    import json as _json

    # context를 JSON으로 파싱 (실패하면 빈 dict)
    ctx: dict = {}
    if context:
        try:
            ctx = _json.loads(context)
        except Exception:
            # 하위 호환: 구형 "city" 또는 "origin|destination" 형식 처리
            if "|" in context:
                parts = context.split("|", 1)
                ctx = {"origin": parts[0].strip(), "destination": parts[1].strip()}
            else:
                ctx = {"city": context.strip()}

    if input_type == "hotel_booking_details":
        field_list = [
            {
                "name": "city",
                "type": "text",
                "label": "도시",
                "required": True,
                "default": ctx.get("city", ""),
            },
            {
                "name": "check_in",
                "type": "date",
                "label": "체크인",
                "required": True,
                "default": ctx.get("check_in", ""),
            },
            {
                "name": "check_out",
                "type": "date",
                "label": "체크아웃",
                "required": True,
                "default": ctx.get("check_out", ""),
            },
            {
                "name": "guests",
                "type": "number",
                "label": "인원수",
                "required": True,
                "default": str(ctx.get("guests", "")),
            },
        ]

    elif input_type == "flight_booking_details":
        field_list = [
            {
                "name": "origin",
                "type": "text",
                "label": "출발지",
                "required": True,
                "default": ctx.get("origin", ""),
            },
            {
                "name": "destination",
                "type": "text",
                "label": "목적지",
                "required": True,
                "default": ctx.get("destination", ""),
            },
            {
                "name": "trip_type",
                "type": "select",
                "label": "여행 유형",
                "required": True,
                "options": ["편도", "왕복"],
                "default": ctx.get("trip_type", "왕복"),
            },
            {
                "name": "departure_date",
                "type": "date",
                "label": "출발 날짜",
                "required": True,
                "default": ctx.get("departure_date", ""),
            },
            {
                "name": "return_date",
                "type": "date",
                "label": "귀국 날짜",
                "required": False,
                "default": ctx.get("return_date", ""),
            },
            {
                "name": "passengers",
                "type": "number",
                "label": "승객 수",
                "required": True,
                "default": str(ctx.get("passengers", "")),
            },
        ]
    else:
        field_list = []

    return {
        "status": "user_input_required",
        "input_type": input_type,
        "fields": field_list,
    }


def get_travel_tips(destination: str, travel_type: str = "일반") -> dict:
    """
    목적지의 여행 팁과 주요 관광지 정보를 조회합니다.

    Args:
        destination: 여행 목적지
        travel_type: 여행 유형 (일반, 음식, 문화, 쇼핑, 자연)

    Returns:
        여행 팁 및 관광지 정보
    """
    tips_db = {
        "도쿄": {
            "overview": "일본의 수도로 최첨단 문화와 전통이 공존하는 도시",
            "best_season": "3-4월(벚꽃), 10-11월(단풍)",
            "currency": "JPY (엔화)",
            "language": "일본어",
            "spots": ["시부야 스크램블 교차로", "아사쿠사 센소지", "하라주쿠 타케시타 거리", "신주쿠 골든가이", "팀랩 플래닛"],
            "food": ["스시", "라멘", "야키토리", "모찌", "타마고야키"],
            "tips": ["IC카드(스이카) 구매 필수", "지하철 노선도 미리 확인", "현금 사용 빈도 높음"]
        },
        "오사카": {
            "overview": "일본의 부엌이라 불리는 미식의 도시",
            "best_season": "3-4월, 9-11월",
            "currency": "JPY (엔화)",
            "language": "일본어",
            "spots": ["도톤보리", "오사카성", "유니버설 스튜디오 재팬", "나카노시마", "아메리카무라"],
            "food": ["타코야키", "오코노미야키", "구시카츠", "이치란 라멘", "551 호라이 만두"],
            "tips": ["오사카 주유패스 활용", "도톤보리 야경 필수", "신칸센으로 도쿄 당일치기 가능"]
        },
        "제주": {
            "overview": "한국의 보물섬, 화산 지형과 아름다운 자연의 섬",
            "best_season": "4-6월, 9-11월",
            "currency": "KRW (원화)",
            "language": "한국어",
            "spots": ["한라산", "성산일출봉", "협재해수욕장", "만장굴", "제주 올레길"],
            "food": ["흑돼지 구이", "갈치조림", "해물라면", "한라봉 주스", "오메기떡"],
            "tips": ["렌터카 필수", "올레길 트레킹 추천", "돌하르방 기념품 쇼핑"]
        },
        "방콕": {
            "overview": "사원과 현대 문화가 조화를 이루는 태국의 수도",
            "best_season": "11-2월(건기)",
            "currency": "THB (바트화)",
            "language": "태국어",
            "spots": ["왓 프라깨우(에메랄드 불상)", "왓 아룬", "차오프라야 강 크루즈", "짜뚜짝 시장", "카오산 로드"],
            "food": ["팟타이", "똠얌꿍", "카오팟", "마사만 커리", "망고 찹쌀밥"],
            "tips": ["그랩 택시 앱 필수", "사원 방문 시 긴 옷 착용", "우기(6-10월) 스콜 주의"]
        },
    }

    matched = None
    for key in tips_db:
        if key in destination or destination in key:
            matched = key
            break

    if not matched:
        return {
            "status": "not_found",
            "message": f"{destination}의 여행 정보를 찾을 수 없습니다."
        }

    return {
        "status": "success",
        "destination": matched,
        "travel_type": travel_type,
        **tips_db[matched]
    }


# ──────────────────────────────────────────────
# ADK 에이전트 생성
# ──────────────────────────────────────────────

def create_travel_agent() -> LlmAgent:
    """여행 상담 ADK 에이전트를 생성합니다."""

    agent = LlmAgent(
        name="travel_agent",
        model="gemini-3-flash-preview",
        description="여행 AI 여행 상담 에이전트 — 호텔, 항공, 관광 정보 안내",
        instruction="""당신은 여행 AI의 AI 여행 상담 전문가입니다.

역할:
- 고객의 여행 계획을 돕고 최적의 호텔, 항공편, 관광 정보를 제공합니다
- 친절하고 전문적인 톤으로 한국어로 응답합니다
- 정확한 정보를 제공하기 위해 항상 도구를 활용합니다

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[현재 여행 컨텍스트] 활용 규칙 (최우선 적용)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
메시지 앞에 "[현재 여행 컨텍스트 - 이미 확인된 정보]" 블록이 있으면:
- 해당 정보를 대화의 기준 값으로 사용합니다
- 사용자가 명시적으로 다른 값을 말하지 않는 한 기존 값을 그대로 유지합니다

날짜·인원 자동 재사용 (크로스 서비스 편의성):
- 호텔 조회 이력이 있고 항공편을 문의하는 경우:
  → 체크인 날짜를 departure_date로, 체크아웃 날짜를 return_date로 자동 사용
  → "기존 일정(체크인: X일, 체크아웃: Y일)을 항공편에도 적용하겠습니다 ✈️" 형식으로 안내
  → 인원수도 passengers에 그대로 적용
- 항공편 조회 이력이 있고 호텔을 문의하는 경우:
  → departure_date를 check_in으로, return_date를 check_out으로 자동 사용
  → "기존 항공 일정(출발: X일, 귀국: Y일)을 호텔 예약에도 적용하겠습니다 🏨" 형식으로 안내
  → 탑승객 수도 guests에 그대로 적용
- 목적지가 이미 설정된 경우 도시 재확인 없이 바로 검색 진행

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
도구 사용 가이드
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 호텔 문의 시:
  1) 날짜·인원 정보가 없고 기존 컨텍스트도 없음
     → request_user_input("hotel_booking_details", "", '{"city":"도시명"}')
     (도시도 모르면 context를 "" 또는 '{}' 로 전달)
  2) 날짜·인원 정보가 없지만 기존 컨텍스트에 날짜·인원이 있음
     → request_user_input("hotel_booking_details", "", '{"city":"도시명","check_in":"YYYY-MM-DD","check_out":"YYYY-MM-DD","guests":N}')
     (기존 값을 context JSON에 그대로 담아서 전달 → 폼 필드에 자동 pre-fill)
  3) 모든 정보 있음 → search_hotels(city, check_in, check_out, guests)

- 항공편 문의 시:
  1) 날짜·인원 정보가 없고 기존 컨텍스트도 없음
     → request_user_input("flight_booking_details", "", '{"origin":"출발지","destination":"목적지"}')
  2) 날짜·인원 정보가 없지만 기존 컨텍스트에 날짜·인원이 있음 (호텔 검색 이후 등)
     → request_user_input("flight_booking_details", "", '{"origin":"서울","destination":"도시명","departure_date":"YYYY-MM-DD","return_date":"YYYY-MM-DD","passengers":N}')
     (체크인→departure_date, 체크아웃→return_date, guests→passengers 로 변환해서 전달)
  3) 모든 정보 있음 → search_flights(origin, destination, departure_date, passengers, return_date)

  ※ context JSON은 반드시 유효한 JSON 문자열이어야 합니다
  ※ 기존 컨텍스트 값을 재사용할 때는 사용자에게 "기존 일정을 적용했습니다"라고 안내

- 여행지 정보 → get_travel_tips(destination)
- 호텔 상세 정보 문의 시 (호텔 코드 형식: HTL-XXX-000) → get_hotel_detail(hotel_code)

호텔 상세 조회 예시:
- "HTL-SEO-001 호텔 상세 정보 알려줘" → get_hotel_detail("HTL-SEO-001")
- 사용자가 호텔 코드를 언급하면 반드시 get_hotel_detail을 호출합니다

시나리오 예시:
- "서울 호텔 알려줘" (컨텍스트 없음)
  → request_user_input("hotel_booking_details", "", '{"city":"서울"}')

- "도쿄 6월 10일~14일 2명 호텔" (정보 완전)
  → search_hotels("도쿄", "2026-06-10", "2026-06-14", 2)

- 기존 컨텍스트(체크인 2026-06-10, 체크아웃 2026-06-14, 인원 2) + "항공편도 알려줘"
  → search_flights("서울", "도쿄", "2026-06-10", 2, "2026-06-14")  (정보 완전)
  또는 목적지만 모를 경우:
  → request_user_input("flight_booking_details", "", '{"origin":"서울","departure_date":"2026-06-10","return_date":"2026-06-14","passengers":2}')

- 기존 컨텍스트(출발 2026-07-01, 귀국 2026-07-08, 탑승 2명) + "호텔도 찾아줘"
  → request_user_input("hotel_booking_details", "", '{"city":"목적지","check_in":"2026-07-01","check_out":"2026-07-08","guests":2}')

응답 형식:
- 검색 결과는 간결하고 보기 좋게 정리해서 제공
- 가격은 항상 원화(원)로 표시
- 기존 컨텍스트 값을 재사용했을 때는 어떤 값을 적용했는지 한 줄로 안내
- 추가 문의가 있으면 편하게 질문하도록 안내
- 이모지를 적절히 활용하여 가독성 향상

제약사항:
- 실제 예약 처리는 불가능하며, 정보 제공만 가능합니다
""",
        tools=[
            FunctionTool(request_user_input),
            FunctionTool(search_hotels),
            FunctionTool(get_hotel_detail),
            FunctionTool(search_flights),
            FunctionTool(get_travel_tips),
        ],
    )

    return agent
