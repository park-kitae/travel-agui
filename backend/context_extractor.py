"""
context_extractor.py — 툴 호출 인수에서 여행 컨텍스트 및 에이전트 상태 추출
"""
from datetime import date


def extract_travel_context(tool_name: str, args: dict) -> dict:
    """function_call args에서 TravelContext를 추출합니다."""
    ctx: dict = {
        "destination": None,
        "origin": None,
        "check_in": None,
        "check_out": None,
        "nights": None,
        "guests": None,
        "trip_type": None,
    }

    if tool_name == "search_hotels":
        ctx["destination"] = args.get("city")
        ctx["check_in"] = args.get("check_in")
        ctx["check_out"] = args.get("check_out")
        ctx["guests"] = args.get("guests")
        if ctx["check_in"] and ctx["check_out"]:
            try:
                ci = date.fromisoformat(ctx["check_in"])
                co = date.fromisoformat(ctx["check_out"])
                ctx["nights"] = (co - ci).days
            except Exception:
                pass

    elif tool_name == "search_flights":
        ctx["origin"] = args.get("origin")
        ctx["destination"] = args.get("destination")
        ctx["check_in"] = args.get("departure_date")
        ctx["guests"] = args.get("passengers")
        ctx["trip_type"] = "round_trip" if args.get("return_date") else "one_way"

    elif tool_name == "get_hotel_detail":
        pass  # hotel_code만 있음, travel context 없음

    elif tool_name == "get_travel_tips":
        ctx["destination"] = args.get("destination")

    elif tool_name == "request_user_input":
        input_type = args.get("input_type", "")
        context_val = args.get("context", "")
        if input_type == "hotel_booking_details" and context_val:
            ctx["destination"] = context_val
        elif input_type == "flight_booking_details" and context_val:
            parts = context_val.split("|")
            if len(parts) >= 2:
                ctx["origin"] = parts[0].strip()
                ctx["destination"] = parts[1].strip()

    return ctx


def extract_agent_status(tool_name: str, args: dict) -> dict:
    """tool_name으로부터 agent_status를 추출합니다."""
    intent_map = {
        "search_hotels": "searching",
        "search_flights": "searching",
        "get_hotel_detail": "presenting_results",
        "get_travel_tips": "presenting_results",
        "request_user_input": None,  # input_type으로 결정
    }

    missing_fields_map = {
        "hotel_booking_details": ["check_in", "check_out", "guests"],
        "flight_booking_details": ["origin", "destination", "departure_date", "passengers"],
    }

    intent = intent_map.get(tool_name, "idle")
    missing: list = []

    if tool_name == "request_user_input":
        input_type = args.get("input_type", "")
        if "hotel" in input_type:
            intent = "collecting_hotel_params"
        else:
            intent = "collecting_flight_params"
        missing = missing_fields_map.get(input_type, [])

    return {
        "current_intent": intent or "idle",
        "missing_fields": missing,
        "active_tool": tool_name,
    }


# 하위 호환 alias
_extract_travel_context = extract_travel_context
_extract_agent_status = extract_agent_status
