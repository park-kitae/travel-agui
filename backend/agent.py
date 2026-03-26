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
        "서울": [
            {"name": "포시즌스 호텔 서울", "area": "광화문", "price": 450000, "rating": 4.9, "stars": 5},
            {"name": "조선팰리스", "area": "소공동", "price": 380000, "rating": 4.8, "stars": 5},
            {"name": "롯데호텔 서울", "area": "명동", "price": 320000, "rating": 4.6, "stars": 5},
            {"name": "그랜드 하얏트 서울", "area": "이태원", "price": 280000, "rating": 4.7, "stars": 5},
            {"name": "신라스테이 서울역", "area": "서울역", "price": 150000, "rating": 4.3, "stars": 4},
        ],
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
    # 편도 항공편 데이터
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

    # 귀국편 데이터 (역방향)
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

    # 출발편 검색
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

    # 왕복인 경우 귀국편도 검색
    is_round_trip = bool(return_date)
    inbound_flights = []

    if is_round_trip:
        inbound_key = (outbound_key[1], outbound_key[0])  # 역방향
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
        context: 호텔의 경우 도시명, 항공편의 경우 "출발지|목적지" 형식

    Returns:
        사용자 입력 요청 정보
    """
    from datetime import datetime, timedelta
    import json

    # 호텔 예약 폼 필드 생성
    if input_type == "hotel_booking_details":
        # 3주 후 날짜 계산
        check_in_date = datetime.now() + timedelta(weeks=3)
        check_out_date = check_in_date + timedelta(days=1)  # 1박

        field_list = [
            {
                "name": "city",
                "type": "text",
                "label": "도시",
                "required": True,
                "default": context if context else ""
            },
            {
                "name": "check_in",
                "type": "date",
                "label": "체크인",
                "required": True,
                "default": check_in_date.strftime("%Y-%m-%d")
            },
            {
                "name": "check_out",
                "type": "date",
                "label": "체크아웃",
                "required": True,
                "default": check_out_date.strftime("%Y-%m-%d")
            },
            {
                "name": "guests",
                "type": "number",
                "label": "인원수",
                "required": True,
                "default": "2"
            }
        ]
    elif input_type == "flight_booking_details":
        # 1개월 후 날짜 계산
        departure_date = datetime.now() + timedelta(days=30)
        return_date = departure_date + timedelta(days=7)  # 7일 후 귀국

        # context에서 출발지/목적지 파싱 (예: "서울|도쿄" 또는 "")
        origin = ""
        destination = ""
        if context and "|" in context:
            parts = context.split("|")
            origin = parts[0] if len(parts) > 0 else ""
            destination = parts[1] if len(parts) > 1 else ""

        field_list = [
            {
                "name": "origin",
                "type": "text",
                "label": "출발지",
                "required": True,
                "default": origin
            },
            {
                "name": "destination",
                "type": "text",
                "label": "목적지",
                "required": True,
                "default": destination
            },
            {
                "name": "trip_type",
                "type": "select",
                "label": "여행 유형",
                "required": True,
                "options": ["편도", "왕복"],
                "default": "왕복"
            },
            {
                "name": "departure_date",
                "type": "date",
                "label": "출발 날짜",
                "required": True,
                "default": departure_date.strftime("%Y-%m-%d")
            },
            {
                "name": "return_date",
                "type": "date",
                "label": "귀국 날짜",
                "required": False,
                "default": return_date.strftime("%Y-%m-%d")
            },
            {
                "name": "passengers",
                "type": "number",
                "label": "승객 수",
                "required": True,
                "default": "1"
            }
        ]
    else:
        # 다른 타입의 폼
        field_list = []

    return {
        "status": "user_input_required",
        "input_type": input_type,
        "fields": field_list
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

도구 사용 가이드:
- 호텔 문의 시:
  1) 도시만 언급됨 → request_user_input("hotel_booking_details", "", "도시명")
  2) 모든 정보 있음 → search_hotels(city, check_in, check_out, guests)
- 항공편 문의 시:
  1) 출발지나 목적지만 언급됨 → request_user_input("flight_booking_details", "", "출발지|목적지")
  2) 모든 정보 있음 → search_flights(origin, destination, departure_date, passengers, return_date)
- 여행지 정보 → get_travel_tips(destination)

예시:
"서울 호텔 알려줘" → request_user_input("hotel_booking_details", "", "서울")
"도쿄 6월 10일부터 14일까지 2명" → search_hotels("도쿄", "2026-06-10", "2026-06-14", 2)

응답 형식:
- 검색 결과는 간결하고 보기 좋게 정리해서 제공
- 가격은 항상 원화(원)로 표시
- 추가 문의가 있으면 편하게 질문하도록 안내
- 이모지를 적절히 활용하여 가독성 향상

제약사항:
- 실제 예약 처리는 불가능하며, 정보 제공만 가능합니다
""",
        tools=[
            FunctionTool(request_user_input),
            FunctionTool(search_hotels),
            FunctionTool(search_flights),
            FunctionTool(get_travel_tips),
        ],
    )

    return agent
