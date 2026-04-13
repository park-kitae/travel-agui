"""
tools/input_tools.py — 사용자 입력 요청 툴
"""
import json as _json


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
