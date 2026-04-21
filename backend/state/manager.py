"""
state/manager.py — thread_id 기준 세션별 TravelState 관리 및 이벤트 발행
"""
import uuid
import logging
from datetime import date
from collections.abc import AsyncGenerator
from dataclasses import replace, asdict

from ag_ui.core.events import StateSnapshotEvent, StateDeltaEvent, EventType

from .models import TravelState, TravelContext, UIContext, AgentStatus, UserPreferences

logger = logging.getLogger(__name__)


class StateManager:
    """thread_id 기준 세션별 TravelState를 메모리에서 관리한다."""

    def __init__(self) -> None:
        self._store: dict[str, TravelState] = {}
        self._tool_call_map: dict[str, dict[str, str]] = {}

    def get(self, thread_id: str) -> TravelState:
        """현재 state 조회. 없으면 빈 TravelState 반환."""
        return self._store.get(thread_id, TravelState())

    def _to_json_safe(self, value):
        if isinstance(value, dict):
            return {key: self._to_json_safe(item) for key, item in value.items()}
        if isinstance(value, tuple):
            return [self._to_json_safe(item) for item in value]
        if isinstance(value, list):
            return [self._to_json_safe(item) for item in value]
        return value

    def _diff_values(self, before, after, path: str) -> list[dict]:
        if isinstance(before, dict) and isinstance(after, dict):
            ops: list[dict] = []
            for key in before.keys() | after.keys():
                child_path = f"{path}/{key}"
                if key not in before:
                    ops.append({"op": "add", "path": child_path, "value": self._to_json_safe(after[key])})
                    continue
                if key not in after:
                    ops.append({"op": "remove", "path": child_path})
                    continue
                ops.extend(self._diff_values(before[key], after[key], child_path))
            return ops

        if before == after:
            return []

        return [{"op": "replace", "path": path, "value": self._to_json_safe(after)}]

    def _build_state_delta(self, before: TravelState, after: TravelState) -> StateDeltaEvent | None:
        before_dict = self._to_json_safe(asdict(before))
        after_dict = self._to_json_safe(asdict(after))
        delta = self._diff_values(before_dict, after_dict, "")
        if not delta:
            return None
        return StateDeltaEvent(type=EventType.STATE_DELTA, delta=delta)

    async def apply_client_state(
        self, thread_id: str, raw_state: dict
    ) -> AsyncGenerator[StateSnapshotEvent | StateDeltaEvent, None]:
        """
        main.py event_stream() 내부 상단(RUN_STARTED 직후)에서 호출.
        raw_state가 비어있으면 이벤트를 yield하지 않는다.
        caller(main.py)는 encoder.encode(event)로 SSE에 직접 forward한다.
        """
        if not raw_state:
            return

        current = self._store.get(thread_id, TravelState())

        raw_tc = raw_state.get("travel_context") or {}
        new_tc = replace(current.travel_context, **{
            k: v for k, v in raw_tc.items()
            if hasattr(current.travel_context, k)
        }) if raw_tc else current.travel_context

        raw_ui = raw_state.get("ui_context") or {}
        new_ui = replace(current.ui_context, **{
            k: v for k, v in raw_ui.items()
            if hasattr(current.ui_context, k)
        }) if raw_ui else current.ui_context

        raw_pref = raw_state.get("user_preferences") or {}
        new_pref = replace(current.user_preferences, **{
            k: tuple(v) if isinstance(v, list) else v
            for k, v in raw_pref.items()
            if hasattr(current.user_preferences, k) and v
        }) if raw_pref else current.user_preferences

        updated = replace(current, travel_context=new_tc, ui_context=new_ui, user_preferences=new_pref)
        self._store[thread_id] = updated

        delta_event = self._build_state_delta(current, updated)
        if delta_event is not None:
            yield delta_event

    async def apply_tool_call(
        self, thread_id: str, tool_name: str, args: dict
    ) -> AsyncGenerator[StateSnapshotEvent | StateDeltaEvent, None]:
        """
        executor.py에서 function_call 감지 시 호출 (TOOL_CALL_START 발행 전).
        caller(executor.py)는 event.snapshot을 DataPart로 래핑 후 event_queue에 enqueue한다.
        """
        current = self._store.get(thread_id, TravelState())
        tc = current.travel_context

        if tool_name == "search_hotels":
            check_in = args.get("check_in")
            check_out = args.get("check_out")
            nights = None
            if check_in and check_out:
                try:
                    nights = (date.fromisoformat(check_out) - date.fromisoformat(check_in)).days
                except Exception:
                    pass
            tc = replace(tc,
                destination=args.get("city") or tc.destination,
                check_in=check_in or tc.check_in,
                check_out=check_out or tc.check_out,
                guests=args.get("guests") or tc.guests,
                nights=nights or tc.nights,
            )
        elif tool_name == "search_flights":
            explicit_trip_type = args.get("trip_type")
            inferred_trip_type = "round_trip" if args.get("return_date") else "one_way"
            tc = replace(tc,
                origin=args.get("origin") or tc.origin,
                destination=args.get("destination") or tc.destination,
                check_in=args.get("departure_date") or tc.check_in,
                guests=args.get("passengers") or tc.guests,
                trip_type=explicit_trip_type or inferred_trip_type,
            )
        elif tool_name == "get_travel_tips":
            tc = replace(tc, destination=args.get("destination") or tc.destination)
        elif tool_name == "request_user_input":
            input_type = args.get("input_type", "")
            context_val = args.get("context", "")
            if input_type == "hotel_booking_details" and context_val:
                tc = replace(tc, destination=context_val)
            elif input_type == "flight_booking_details" and context_val:
                parts = context_val.split("|")
                if len(parts) >= 2:
                    tc = replace(tc, origin=parts[0].strip(), destination=parts[1].strip())

        intent_map = {
            "search_hotels": "searching",
            "search_flights": "searching",
            "get_hotel_detail": "presenting_results",
            "get_travel_tips": "presenting_results",
            "request_user_favorite": "awaiting_input",
        }
        missing_fields_map = {
            "hotel_booking_details": ("check_in", "check_out", "guests"),
            "flight_booking_details": ("origin", "destination", "departure_date", "passengers"),
        }
        intent = intent_map.get(tool_name, "idle")
        missing: tuple[str, ...] = ()
        if tool_name == "request_user_input":
            input_type = args.get("input_type", "")
            intent = "collecting_hotel_params" if "hotel" in input_type else "collecting_flight_params"
            missing = missing_fields_map.get(input_type, ())

        new_status = AgentStatus(
            current_intent=intent,
            missing_fields=missing,
            active_tool=tool_name,
        )

        tc_id = str(uuid.uuid4())
        self._tool_call_map.setdefault(thread_id, {})[tool_name] = tc_id

        updated = replace(current, travel_context=tc, agent_status=new_status)
        self._store[thread_id] = updated

        delta_event = self._build_state_delta(current, updated)
        if delta_event is not None:
            yield delta_event

    async def apply_tool_result(
        self, thread_id: str, tool_name: str, result: dict
    ) -> AsyncGenerator[StateSnapshotEvent, None]:
        """
        executor.py에서 function_response 수신 시 호출.
        request_user_input 특수 케이스는 user_input_request snapshot으로 발행한다.
        """
        if tool_name == "request_user_favorite" and result.get("status") == "user_favorite_required":
            yield StateSnapshotEvent(
                type=EventType.STATE_SNAPSHOT,
                snapshot={
                    "snapshot_type": "user_favorite_request",
                    "_agui_event": "USER_FAVORITE_REQUEST",
                    "request_id": str(uuid.uuid4()),
                    "favorite_type": result.get("favorite_type", ""),
                    "options": result.get("options", {}),
                },
            )
        elif tool_name == "request_user_input" and result.get("status") == "user_input_required":
            yield StateSnapshotEvent(
                type=EventType.STATE_SNAPSHOT,
                snapshot={
                    "snapshot_type": "user_input_request",
                    "_agui_event": "USER_INPUT_REQUEST",
                    "request_id": str(uuid.uuid4()),
                    "input_type": result.get("input_type", ""),
                    "fields": result.get("fields", []),
                },
            )
        else:
            yield StateSnapshotEvent(
                type=EventType.STATE_SNAPSHOT,
                snapshot={
                    "snapshot_type": "tool_result",
                    "tool": tool_name,
                    "result": result if isinstance(result, dict) else {"raw": str(result)},
                },
            )

    def get_tc_id(self, thread_id: str, tool_name: str) -> str:
        """
        tool_name에 해당하는 tc_id 조회.
        미등록 tool_name이면 warning 로그 후 새 uuid 반환 (TOOL_CALL 페어 불일치 가능).
        """
        tc_id = self._tool_call_map.get(thread_id, {}).get(tool_name)
        if tc_id is None:
            logger.warning(
                f"[{thread_id}] get_tc_id: '{tool_name}' 미등록 — 새 uuid 발행 (TOOL_CALL 페어 불일치 가능)"
            )
            return str(uuid.uuid4())
        return tc_id

    def clear(self, thread_id: str) -> None:
        self._store.pop(thread_id, None)
        self._tool_call_map.pop(thread_id, None)
