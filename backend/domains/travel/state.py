"""Travel domain state models and pure transition helpers."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field, replace
from datetime import date
from typing import Any

from domains import RuntimeDeltaPayload, RuntimeEmission, RuntimeSnapshotPayload, RuntimeUiRequestPayload


@dataclass(frozen=True)
class TravelContext:
    """여행 검색 파라미터 (목적지, 날짜, 인원 등)."""

    destination: str | None = None
    origin: str | None = None
    check_in: str | None = None
    check_out: str | None = None
    nights: int | None = None
    guests: int | None = None
    rooms: int | None = None
    trip_type: str | None = None
    budget_range: str | None = None
    travel_purpose: str | None = None


@dataclass(frozen=True)
class UIContext:
    """UI에서 선택된 값 (호텔 코드, 항공편 ID 등)."""

    selected_hotel_code: str | None = None
    selected_flight_id: str | None = None


@dataclass(frozen=True)
class AgentStatus:
    """에이전트 처리 상태."""

    current_intent: str = "idle"
    missing_fields: tuple[str, ...] = ()
    active_tool: str | None = None


@dataclass(frozen=True)
class UserPreferences:
    """사용자 서비스별 취향 (세션 내 1회 수집)."""

    hotel_grade: str | None = None
    hotel_type: str | None = None
    amenities: tuple[str, ...] = ()
    seat_class: str | None = None
    seat_position: str | None = None
    meal_preference: str | None = None
    airline_preference: tuple[str, ...] = ()


@dataclass(frozen=True)
class TravelState:
    """세션 전체 travel domain 상태."""

    travel_context: TravelContext = field(default_factory=TravelContext)
    ui_context: UIContext = field(default_factory=UIContext)
    agent_status: AgentStatus = field(default_factory=AgentStatus)
    user_preferences: UserPreferences = field(default_factory=UserPreferences)


def merge_client_state(
    current_state: TravelState,
    client_state: dict[str, Any],
) -> tuple[TravelState, list[RuntimeEmission]]:
    """Merge client-provided state into a new immutable travel state."""

    if not client_state:
        return current_state, []

    raw_travel_context = client_state.get("travel_context") or {}
    next_travel_context = (
        replace(
            current_state.travel_context,
            **{
                key: value
                for key, value in raw_travel_context.items()
                if hasattr(current_state.travel_context, key)
            },
        )
        if raw_travel_context
        else current_state.travel_context
    )

    raw_ui_context = client_state.get("ui_context") or {}
    next_ui_context = (
        replace(
            current_state.ui_context,
            **{
                key: value
                for key, value in raw_ui_context.items()
                if hasattr(current_state.ui_context, key)
            },
        )
        if raw_ui_context
        else current_state.ui_context
    )

    raw_preferences = client_state.get("user_preferences") or {}
    next_preferences = (
        replace(
            current_state.user_preferences,
            **_normalize_preference_updates(current_state.user_preferences, raw_preferences),
        )
        if raw_preferences
        else current_state.user_preferences
    )

    next_state = replace(
        current_state,
        travel_context=next_travel_context,
        ui_context=next_ui_context,
        user_preferences=next_preferences,
    )
    return next_state, _build_delta_emissions(current_state, next_state)


def apply_tool_call(
    current_state: TravelState,
    tool_name: str,
    tool_args: dict[str, Any],
) -> tuple[TravelState, list[RuntimeEmission]]:
    """Apply a tool-call side effect to immutable state and emit runtime deltas."""

    next_travel_context = current_state.travel_context

    if tool_name == "search_hotels":
        check_in = tool_args.get("check_in")
        check_out = tool_args.get("check_out")
        nights = _calculate_nights(check_in, check_out)
        next_travel_context = replace(
            next_travel_context,
            destination=tool_args.get("city") or next_travel_context.destination,
            check_in=check_in or next_travel_context.check_in,
            check_out=check_out or next_travel_context.check_out,
            guests=tool_args.get("guests") or next_travel_context.guests,
            nights=nights or next_travel_context.nights,
        )
    elif tool_name == "search_flights":
        explicit_trip_type = tool_args.get("trip_type")
        inferred_trip_type = "round_trip" if tool_args.get("return_date") else "one_way"
        next_travel_context = replace(
            next_travel_context,
            origin=tool_args.get("origin") or next_travel_context.origin,
            destination=tool_args.get("destination") or next_travel_context.destination,
            check_in=tool_args.get("departure_date") or next_travel_context.check_in,
            check_out=tool_args.get("return_date") or next_travel_context.check_out,
            guests=tool_args.get("passengers") or next_travel_context.guests,
            trip_type=explicit_trip_type or inferred_trip_type,
        )
    elif tool_name == "get_travel_tips":
        next_travel_context = replace(
            next_travel_context,
            destination=tool_args.get("destination") or next_travel_context.destination,
        )
    elif tool_name == "request_user_input":
        input_type = tool_args.get("input_type", "")
        context_value = tool_args.get("context", "")
        parsed_context = _parse_request_context(context_value)
        if input_type == "hotel_booking_details":
            next_travel_context = _apply_hotel_request_context(next_travel_context, context_value, parsed_context)
        elif input_type == "flight_booking_details":
            next_travel_context = _apply_flight_request_context(next_travel_context, context_value, parsed_context)

    next_status = AgentStatus(
        current_intent=_resolve_intent(tool_name, tool_args),
        missing_fields=_resolve_missing_fields(tool_name, tool_args),
        active_tool=tool_name,
    )
    next_state = replace(
        current_state,
        travel_context=next_travel_context,
        agent_status=next_status,
    )
    return next_state, _build_delta_emissions(current_state, next_state)


def apply_tool_result(
    current_state: TravelState,
    tool_name: str,
    tool_result: Any,
) -> tuple[TravelState, list[RuntimeEmission]]:
    """Convert a tool result into runtime emissions without mutating state."""

    result_payload = tool_result if isinstance(tool_result, dict) else {"raw": str(tool_result)}

    if tool_name == "request_user_favorite" and result_payload.get("status") == "user_favorite_required":
        ui_payload = {
            "favorite_type": result_payload.get("favorite_type", ""),
            "options": result_payload.get("options", {}),
        }
        return current_state, [
            RuntimeUiRequestPayload(
                event_name="USER_FAVORITE_REQUEST",
                payload={
                    "request_id": _build_request_id(tool_name, ui_payload),
                    **ui_payload,
                },
            )
        ]

    if tool_name == "request_user_input" and result_payload.get("status") == "user_input_required":
        ui_payload = {
            "input_type": result_payload.get("input_type", ""),
            "fields": result_payload.get("fields", []),
        }
        return current_state, [
            RuntimeUiRequestPayload(
                event_name="USER_INPUT_REQUEST",
                payload={
                    "request_id": _build_request_id(tool_name, ui_payload),
                    **ui_payload,
                },
            )
        ]

    return current_state, [
        RuntimeSnapshotPayload(
            snapshot={
                "snapshot_type": "tool_result",
                "tool": tool_name,
                "result": result_payload,
            }
        )
    ]


def _calculate_nights(check_in: str | None, check_out: str | None) -> int | None:
    if not (check_in and check_out):
        return None
    try:
        return (date.fromisoformat(check_out) - date.fromisoformat(check_in)).days
    except ValueError:
        return None


def _build_request_id(tool_name: str, payload: dict[str, Any]) -> str:
    canonical_payload = json.dumps(
        _to_json_safe(payload),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{tool_name}:{canonical_payload}"))


def _normalize_preference_updates(current_preferences: UserPreferences, raw_preferences: dict[str, Any]) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    for key, value in raw_preferences.items():
        if not hasattr(current_preferences, key):
            continue
        updates[key] = tuple(value) if isinstance(value, list) else value
    return updates


def _parse_request_context(context_value: Any) -> dict[str, Any]:
    if isinstance(context_value, dict):
        return context_value
    if not isinstance(context_value, str) or not context_value.strip():
        return {}

    try:
        parsed = json.loads(context_value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _apply_hotel_request_context(
    current_context: TravelContext,
    raw_context: Any,
    parsed_context: dict[str, Any],
) -> TravelContext:
    if parsed_context:
        check_in = parsed_context.get("check_in") or current_context.check_in
        check_out = parsed_context.get("check_out") or current_context.check_out
        return replace(
            current_context,
            destination=parsed_context.get("city") or parsed_context.get("destination") or current_context.destination,
            check_in=check_in,
            check_out=check_out,
            guests=parsed_context.get("guests") or current_context.guests,
            rooms=parsed_context.get("rooms") or current_context.rooms,
            nights=_calculate_nights(check_in, check_out) or current_context.nights,
        )

    if isinstance(raw_context, str) and raw_context:
        return replace(current_context, destination=raw_context)
    return current_context


def _apply_flight_request_context(
    current_context: TravelContext,
    raw_context: Any,
    parsed_context: dict[str, Any],
) -> TravelContext:
    if parsed_context:
        return replace(
            current_context,
            origin=parsed_context.get("origin") or current_context.origin,
            destination=parsed_context.get("destination") or current_context.destination,
            check_in=parsed_context.get("departure_date") or current_context.check_in,
            check_out=parsed_context.get("return_date") or current_context.check_out,
            guests=parsed_context.get("passengers") or current_context.guests,
            trip_type=(parsed_context.get("trip_type") or ("round_trip" if parsed_context.get("return_date") else "one_way"))
            if (parsed_context.get("departure_date") or parsed_context.get("return_date") or parsed_context.get("trip_type"))
            else current_context.trip_type,
        )

    if isinstance(raw_context, str):
        parts = raw_context.split("|")
        if len(parts) >= 2:
            return replace(
                current_context,
                origin=parts[0].strip(),
                destination=parts[1].strip(),
            )
    return current_context


def _resolve_intent(tool_name: str, tool_args: dict[str, Any]) -> str:
    intent_map = {
        "search_hotels": "searching",
        "search_flights": "searching",
        "get_hotel_detail": "presenting_results",
        "get_travel_tips": "presenting_results",
        "request_user_favorite": "awaiting_input",
    }
    if tool_name != "request_user_input":
        return intent_map.get(tool_name, "idle")

    input_type = tool_args.get("input_type", "")
    return "collecting_hotel_params" if "hotel" in input_type else "collecting_flight_params"


def _resolve_missing_fields(tool_name: str, tool_args: dict[str, Any]) -> tuple[str, ...]:
    if tool_name != "request_user_input":
        return ()

    missing_fields_map = {
        "hotel_booking_details": ("check_in", "check_out", "guests"),
        "flight_booking_details": ("origin", "destination", "departure_date", "passengers"),
    }
    return missing_fields_map.get(tool_args.get("input_type", ""), ())


def _build_delta_emissions(before: TravelState, after: TravelState) -> list[RuntimeEmission]:
    delta_ops = _diff_values(_to_json_safe(asdict(before)), _to_json_safe(asdict(after)), "")
    if not delta_ops:
        return []
    return [RuntimeDeltaPayload(ops=delta_ops)]


def _diff_values(before: Any, after: Any, path: str) -> list[dict[str, Any]]:
    if isinstance(before, dict) and isinstance(after, dict):
        ops: list[dict[str, Any]] = []
        for key in before.keys() | after.keys():
            child_path = f"{path}/{key}"
            if key not in before:
                ops.append({"op": "add", "path": child_path, "value": _to_json_safe(after[key])})
                continue
            if key not in after:
                ops.append({"op": "remove", "path": child_path})
                continue
            ops.extend(_diff_values(before[key], after[key], child_path))
        return ops

    if before == after:
        return []

    return [{"op": "replace", "path": path, "value": _to_json_safe(after)}]


def _to_json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _to_json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_to_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_to_json_safe(item) for item in value]
    return value
