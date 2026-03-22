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
        호텔 검색 결과 목록
    """
    # 실제 환경에서는 hotel_search API 호출
    hotel_db = {
        "도쿄": [
            {"name": "파크 하얏트 도쿄", "area": "신주쿠", "price": 420000, "rating": 4.8, "stars": 5},
            {"name": "더 프린스 갤러리 도쿄", "area": "긴자", "price": 380000, "rating": 4.7, "stars": 5},
            {"name": "아파 호텔 신주쿠", "area": "신주쿠", "price": 120000, "rating": 4.2, "stars": 3},
        ],
        "오사카": [
            {"name": "콘래드 오사카", "area": "나카노시마", "price": 350000, "rating": 4.8, "stars": 5},
            {"name": "더블트리 힐튼 오사카", "area": "우메다", "price": 200000, "rating": 4.5, "stars": 4},
            {"name": "도미 인 난바", "area": "난바", "price": 95000, "rating": 4.3, "stars": 3},
        ],
        "제주": [
            {"name": "롯데호텔 제주", "area": "중문", "price": 280000, "rating": 4.6, "stars": 5},
            {"name": "신라스테이 제주", "area": "제주시", "price": 180000, "rating": 4.4, "stars": 4},
            {"name": "라마다 제주 호텔", "area": "노형", "price": 130000, "rating": 4.1, "stars": 4},
        ],
        "방콕": [
            {"name": "만다린 오리엔탈 방콕", "area": "리버사이드", "price": 520000, "rating": 4.9, "stars": 5},
            {"name": "아난타라 시암", "area": "수쿰빗", "price": 310000, "rating": 4.7, "stars": 5},
            {"name": "이비스 방콕 나나", "area": "나나", "price": 85000, "rating": 4.2, "stars": 3},
        ],
    }

    # 도시 키워드 매칭
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


def search_flights(origin: str, destination: str, departure_date: str, passengers: int = 1) -> dict:
    """
    출발지/목적지와 날짜로 항공편을 검색합니다.

    Args:
        origin: 출발 도시 또는 공항 코드 (예: 서울, ICN)
        destination: 도착 도시 또는 공항 코드 (예: 도쿄, NRT)
        departure_date: 출발 날짜 (YYYY-MM-DD)
        passengers: 승객 수

    Returns:
        항공편 검색 결과
    """
    flight_db = {
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

    key = None
    for (orig, dest) in flight_db:
        if (orig in origin or origin in orig) and (dest in destination or destination in dest):
            key = (orig, dest)
            break

    if not key:
        return {
            "status": "not_found",
            "message": f"{origin}→{destination} 구간 항공편을 찾을 수 없습니다.",
            "flights": []
        }

    flights = flight_db[key]
    for f in flights:
        f["departure_date"] = departure_date
        f["passengers"] = passengers
        f["total_price"] = f["price"] * passengers

    return {
        "status": "success",
        "origin": key[0],
        "destination": key[1],
        "departure_date": departure_date,
        "passengers": passengers,
        "count": len(flights),
        "flights": flights
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
        model="gemini-2.0-flash",
        description="여행 AI 여행 상담 에이전트 — 호텔, 항공, 관광 정보 안내",
        instruction="""당신은 여행 AI의 AI 여행 상담 전문가입니다.

역할:
- 고객의 여행 계획을 돕고 최적의 호텔, 항공편, 관광 정보를 제공합니다
- 친절하고 전문적인 톤으로 한국어로 응답합니다
- 정확한 정보를 제공하기 위해 항상 도구를 활용합니다

도구 사용 가이드:
- 호텔 추천 요청 → search_hotels 도구 사용
- 항공편 문의 → search_flights 도구 사용  
- 여행지 정보/팁 → get_travel_tips 도구 사용
- 복합 요청은 여러 도구를 순서대로 사용

응답 형식:
- 검색 결과는 간결하고 보기 좋게 정리해서 제공
- 가격은 항상 원화(원)로 표시
- 추가 문의가 있으면 편하게 질문하도록 안내
- 이모지를 적절히 활용하여 가독성 향상

제약사항:
- 실제 예약 처리는 불가능하며, 정보 제공만 가능합니다
- 모르는 정보는 솔직하게 모른다고 안내합니다""",
        tools=[
            FunctionTool(search_hotels),
            FunctionTool(search_flights),
            FunctionTool(get_travel_tips),
        ],
    )

    return agent
