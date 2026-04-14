# State Manager Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** state 관련 코드를 `state/` 패키지로 통합하여 타입 안전한 이벤트 기반 StateManager를 구축한다.

**Architecture:** `state/models.py`에 frozen dataclass 모델을 정의하고, `state/manager.py`의 `StateManager`가 thread_id 기준 세션별 state를 메모리에 보관하며 변경 시 `StateSnapshotEvent`를 yield한다. `main.py`와 `executor.py`는 `apply_*` 메서드 호출로 교체되고, `context_extractor.py`는 삭제된다.

**Tech Stack:** Python 3.11+, dataclasses (frozen=True), ag-ui-protocol (`ag_ui.core.events.StateSnapshotEvent`), a2a-sdk (`TaskArtifactUpdateEvent`, `Artifact`, `Part`, `DataPart`), pytest, pytest-asyncio, uv

---

## File Map

| 파일 | 변경 |
|------|------|
| `backend/state/__init__.py` | 신규 — 모델 export (Task 1), StateManager 싱글톤 추가 (Task 2) |
| `backend/state/models.py` | 신규 — frozen dataclass 모델 |
| `backend/state/manager.py` | 신규 — StateManager 클래스 |
| `backend/tests/state/__init__.py` | 신규 |
| `backend/tests/state/test_models.py` | 신규 |
| `backend/tests/state/test_manager.py` | 신규 |
| `backend/context_extractor.py` | **삭제** |
| `backend/main.py` | 수정 — apply_client_state 호출로 교체 |
| `backend/executor.py` | 수정 — apply_tool_call / apply_tool_result 호출로 교체 |
| `backend/tests/state-panel-sidebar/test_context_extraction.py` | **전면 재작성** |
| `backend/tests/state-panel-sidebar/test_snapshot_emission.py` | **전면 재작성** |
| `backend/tests/state-panel-sidebar/test_main_state_handling.py` | **전면 재작성** |

---

## Task 1: state/models.py — frozen dataclass 모델 정의

**Files:**
- Create: `backend/state/models.py`
- Create: `backend/state/__init__.py` (모델만 export, StateManager는 Task 2에서 추가)
- Create: `backend/tests/state/__init__.py`
- Create: `backend/tests/state/test_models.py`

- [ ] **Step 1: 테스트 작성**

`backend/tests/state/__init__.py`: (빈 파일)

`backend/tests/state/test_models.py`:

```python
import pytest
from dataclasses import replace, FrozenInstanceError
from state.models import TravelContext, UIContext, AgentStatus, TravelState


def test_travel_context_defaults():
    ctx = TravelContext()
    assert ctx.destination is None
    assert ctx.nights is None
    assert ctx.trip_type is None


def test_travel_context_frozen():
    ctx = TravelContext(destination="도쿄")
    with pytest.raises(FrozenInstanceError):
        ctx.destination = "오사카"  # type: ignore


def test_travel_context_replace():
    ctx = TravelContext(destination="도쿄", guests=2)
    updated = replace(ctx, destination="오사카")
    assert updated.destination == "오사카"
    assert updated.guests == 2
    assert ctx.destination == "도쿄"  # 원본 불변


def test_ui_context_frozen():
    ui = UIContext(selected_hotel_code="HTL001")
    with pytest.raises(FrozenInstanceError):
        ui.selected_hotel_code = "HTL002"  # type: ignore


def test_agent_status_defaults():
    status = AgentStatus()
    assert status.current_intent == "idle"
    assert status.missing_fields == ()
    assert status.active_tool is None


def test_agent_status_missing_fields_is_tuple():
    status = AgentStatus(missing_fields=("check_in", "guests"))
    assert isinstance(status.missing_fields, tuple)
    assert "check_in" in status.missing_fields


def test_travel_state_defaults():
    state = TravelState()
    assert isinstance(state.travel_context, TravelContext)
    assert isinstance(state.ui_context, UIContext)
    assert isinstance(state.agent_status, AgentStatus)


def test_travel_state_replace():
    state = TravelState()
    new_ctx = replace(state.travel_context, destination="제주")
    updated = replace(state, travel_context=new_ctx)
    assert updated.travel_context.destination == "제주"
    assert state.travel_context.destination is None  # 원본 불변
```

- [ ] **Step 2: 테스트 실패 확인 (아직 state/ 디렉터리 없음)**

> ⚠️ 이 단계에서 `state/` 디렉터리를 생성하거나 파일을 만들지 않는다.

```bash
cd backend && uv run pytest tests/state/test_models.py -v 2>&1 | tail -5
```
Expected: `ModuleNotFoundError: No module named 'state'`

- [ ] **Step 3: `state/` 패키지 생성 (모델만)**

`backend/state/models.py`:
```python
"""
state/models.py — 여행 state 데이터 모델 (frozen dataclass)
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class TravelContext:
    """여행 검색 파라미터 (목적지, 날짜, 인원 등)."""
    destination: str | None = None
    origin: str | None = None
    check_in: str | None = None
    check_out: str | None = None
    nights: int | None = None
    guests: int | None = None
    trip_type: str | None = None  # "round_trip" | "one_way"


@dataclass(frozen=True)
class UIContext:
    """UI에서 선택된 값 (호텔 코드 등)."""
    selected_hotel_code: str | None = None


@dataclass(frozen=True)
class AgentStatus:
    """에이전트 처리 상태."""
    current_intent: str = "idle"
    missing_fields: tuple[str, ...] = ()
    active_tool: str | None = None


@dataclass(frozen=True)
class TravelState:
    """thread_id 기준 세션 전체 state."""
    travel_context: TravelContext = field(default_factory=TravelContext)
    ui_context: UIContext = field(default_factory=UIContext)
    agent_status: AgentStatus = field(default_factory=AgentStatus)
```

`backend/state/__init__.py` (모델만 export — StateManager는 Task 2에서 추가):
```python
from .models import TravelState, TravelContext, UIContext, AgentStatus

__all__ = ["TravelState", "TravelContext", "UIContext", "AgentStatus"]
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd backend && uv run pytest tests/state/test_models.py -v 2>&1 | tail -15
```
Expected: 9개 PASSED

- [ ] **Step 5: 커밋**

```bash
git add backend/state/__init__.py backend/state/models.py backend/tests/state/__init__.py backend/tests/state/test_models.py
git commit -m "feat: state/models.py frozen dataclass 모델 정의"
```

---

## Task 2: state/manager.py — StateManager 구현

**Files:**
- Create: `backend/state/manager.py`
- Modify: `backend/state/__init__.py` (StateManager 싱글톤 추가)
- Create: `backend/tests/state/test_manager.py`

### 2-A: `apply_client_state`

- [ ] **Step 1: 테스트 작성**

`backend/tests/state/test_manager.py` (초기):

```python
import pytest
from dataclasses import asdict
from state.manager import StateManager
from state.models import TravelState
from ag_ui.core.events import StateSnapshotEvent


@pytest.fixture
def manager():
    return StateManager()


@pytest.mark.asyncio
async def test_apply_client_state_updates_travel_context(manager):
    raw_state = {
        "travel_context": {
            "destination": "도쿄",
            "check_in": "2026-06-10",
            "check_out": "2026-06-14",
            "guests": 2,
        }
    }
    events = [e async for e in manager.apply_client_state("thread-1", raw_state)]
    assert len(events) == 1
    assert isinstance(events[0], StateSnapshotEvent)
    snap = events[0].snapshot
    assert snap["snapshot_type"] == "client_state"
    assert snap["travel_context"]["destination"] == "도쿄"
    assert snap["travel_context"]["guests"] == 2

    state = manager.get("thread-1")
    assert state.travel_context.destination == "도쿄"
    assert state.travel_context.guests == 2


@pytest.mark.asyncio
async def test_apply_client_state_updates_ui_context(manager):
    raw_state = {
        "ui_context": {"selected_hotel_code": "HTL-001"}
    }
    events = [e async for e in manager.apply_client_state("thread-2", raw_state)]
    assert len(events) == 1
    snap = events[0].snapshot
    assert snap["ui_context"]["selected_hotel_code"] == "HTL-001"

    state = manager.get("thread-2")
    assert state.ui_context.selected_hotel_code == "HTL-001"


@pytest.mark.asyncio
async def test_apply_client_state_empty_raw_state_yields_no_event(manager):
    events = [e async for e in manager.apply_client_state("thread-3", {})]
    assert events == []


@pytest.mark.asyncio
async def test_get_returns_empty_state_for_unknown_thread(manager):
    state = manager.get("unknown-thread")
    assert state == TravelState()
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd backend && uv run pytest tests/state/test_manager.py -v 2>&1 | tail -10
```
Expected: `ImportError: cannot import name 'StateManager' from 'state.manager'` 또는 `ModuleNotFoundError`

- [ ] **Step 3: `state/manager.py` 생성 + `__init__.py` 업데이트**

`backend/state/manager.py`:

```python
"""
state/manager.py — thread_id 기준 세션별 TravelState 관리 및 이벤트 발행
"""
import uuid
import logging
from collections.abc import AsyncGenerator
from dataclasses import replace, asdict

from ag_ui.core.events import StateSnapshotEvent, EventType

from .models import TravelState, TravelContext, UIContext, AgentStatus

logger = logging.getLogger(__name__)


class StateManager:
    """thread_id 기준 세션별 TravelState를 메모리에서 관리한다."""

    def __init__(self) -> None:
        self._store: dict[str, TravelState] = {}
        self._tool_call_map: dict[str, dict[str, str]] = {}

    def get(self, thread_id: str) -> TravelState:
        """현재 state 조회. 없으면 빈 TravelState 반환."""
        return self._store.get(thread_id, TravelState())

    async def apply_client_state(
        self, thread_id: str, raw_state: dict
    ) -> AsyncGenerator[StateSnapshotEvent, None]:
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

        updated = replace(current, travel_context=new_tc, ui_context=new_ui)
        self._store[thread_id] = updated

        yield StateSnapshotEvent(
            type=EventType.STATE_SNAPSHOT,
            snapshot={
                "snapshot_type": "client_state",
                "travel_context": asdict(updated.travel_context),
                "ui_context": asdict(updated.ui_context),
            },
        )

    async def apply_tool_call(
        self, thread_id: str, tool_name: str, args: dict
    ) -> AsyncGenerator[StateSnapshotEvent, None]:
        raise NotImplementedError

    async def apply_tool_result(
        self, thread_id: str, tool_name: str, result: dict
    ) -> AsyncGenerator[StateSnapshotEvent, None]:
        raise NotImplementedError

    def get_tc_id(self, thread_id: str, tool_name: str) -> str:
        raise NotImplementedError

    def clear(self, thread_id: str) -> None:
        self._store.pop(thread_id, None)
        self._tool_call_map.pop(thread_id, None)
```

`backend/state/__init__.py` 업데이트 (StateManager 싱글톤 추가):
```python
from .models import TravelState, TravelContext, UIContext, AgentStatus
from .manager import StateManager

state_manager = StateManager()

__all__ = [
    "state_manager",
    "StateManager",
    "TravelState",
    "TravelContext",
    "UIContext",
    "AgentStatus",
]
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd backend && uv run pytest tests/state/test_manager.py::test_apply_client_state_updates_travel_context tests/state/test_manager.py::test_apply_client_state_updates_ui_context tests/state/test_manager.py::test_apply_client_state_empty_raw_state_yields_no_event tests/state/test_manager.py::test_get_returns_empty_state_for_unknown_thread -v 2>&1 | tail -15
```
Expected: 4개 PASSED

### 2-B: `apply_tool_call`

- [ ] **Step 5: 테스트 추가**

`tests/state/test_manager.py`에 아래 테스트들을 추가:

```python
@pytest.mark.asyncio
async def test_apply_tool_call_search_hotels_updates_travel_context(manager):
    args = {"city": "오사카", "check_in": "2026-07-01", "check_out": "2026-07-04", "guests": 3}
    events = [e async for e in manager.apply_tool_call("thread-4", "search_hotels", args)]
    assert len(events) == 1
    snap = events[0].snapshot
    assert snap["snapshot_type"] == "agent_state"
    assert snap["travel_context"]["destination"] == "오사카"
    assert snap["travel_context"]["nights"] == 3
    assert snap["agent_status"]["current_intent"] == "searching"
    assert snap["agent_status"]["active_tool"] == "search_hotels"

    state = manager.get("thread-4")
    assert state.travel_context.destination == "오사카"
    assert state.agent_status.active_tool == "search_hotels"


@pytest.mark.asyncio
async def test_apply_tool_call_search_flights_updates_travel_context(manager):
    args = {
        "origin": "서울", "destination": "후쿠오카",
        "departure_date": "2026-08-10", "passengers": 2,
        "return_date": "2026-08-15",
    }
    events = [e async for e in manager.apply_tool_call("thread-5", "search_flights", args)]
    snap = events[0].snapshot
    assert snap["travel_context"]["origin"] == "서울"
    assert snap["travel_context"]["destination"] == "후쿠오카"
    assert snap["travel_context"]["trip_type"] == "round_trip"
    assert snap["agent_status"]["current_intent"] == "searching"


@pytest.mark.asyncio
async def test_apply_tool_call_stores_tc_id(manager):
    args = {"city": "도쿄", "check_in": "2026-09-01", "check_out": "2026-09-03", "guests": 1}
    events = [e async for e in manager.apply_tool_call("thread-6", "search_hotels", args)]
    assert len(events) >= 1
    tc_id = manager.get_tc_id("thread-6", "search_hotels")
    assert isinstance(tc_id, str)
    assert len(tc_id) == 36  # UUID 형식


@pytest.mark.asyncio
async def test_apply_tool_call_request_user_input_collecting_hotel_params(manager):
    args = {"input_type": "hotel_booking_details", "context": "제주"}
    events = [e async for e in manager.apply_tool_call("thread-7", "request_user_input", args)]
    snap = events[0].snapshot
    assert snap["agent_status"]["current_intent"] == "collecting_hotel_params"
    assert "check_in" in snap["agent_status"]["missing_fields"]
```

- [ ] **Step 6: 테스트 실패 확인**

```bash
cd backend && uv run pytest tests/state/test_manager.py -k "tool_call" -v 2>&1 | tail -10
```
Expected: `NotImplementedError`

- [ ] **Step 7: `apply_tool_call` 구현**

`state/manager.py`의 `apply_tool_call` `raise NotImplementedError` 를 아래로 교체:

```python
async def apply_tool_call(
    self, thread_id: str, tool_name: str, args: dict
) -> AsyncGenerator[StateSnapshotEvent, None]:
    """
    executor.py에서 function_call 감지 시 호출 (TOOL_CALL_START 발행 전).
    caller(executor.py)는 event.snapshot을 DataPart로 래핑 후 event_queue에 enqueue한다.
    """
    from datetime import date

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
        tc = replace(tc,
            origin=args.get("origin") or tc.origin,
            destination=args.get("destination") or tc.destination,
            check_in=args.get("departure_date") or tc.check_in,
            guests=args.get("passengers") or tc.guests,
            trip_type="round_trip" if args.get("return_date") else "one_way",
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

    yield StateSnapshotEvent(
        type=EventType.STATE_SNAPSHOT,
        snapshot={
            "snapshot_type": "agent_state",
            "travel_context": asdict(updated.travel_context),
            "agent_status": {
                "current_intent": new_status.current_intent,
                "missing_fields": list(new_status.missing_fields),
                "active_tool": new_status.active_tool,
            },
        },
    )
```

- [ ] **Step 8: 테스트 통과 확인**

```bash
cd backend && uv run pytest tests/state/test_manager.py -k "tool_call" -v 2>&1 | tail -15
```
Expected: 5개 PASSED

### 2-C: `apply_tool_result` + `get_tc_id` + `clear`

- [ ] **Step 9: 테스트 추가**

`tests/state/test_manager.py`에 아래 테스트들을 추가:

```python
@pytest.mark.asyncio
async def test_apply_tool_result_yields_tool_result_snapshot(manager):
    result = {"status": "success", "hotels": [{"code": "HTL001", "name": "신주쿠 호텔"}]}
    events = [e async for e in manager.apply_tool_result("thread-8", "search_hotels", result)]
    assert len(events) == 1
    snap = events[0].snapshot
    assert snap["snapshot_type"] == "tool_result"
    assert snap["tool"] == "search_hotels"
    assert snap["result"] == result


@pytest.mark.asyncio
async def test_apply_tool_result_request_user_input_yields_user_input_request(manager):
    result = {
        "status": "user_input_required",
        "input_type": "hotel_booking_details",
        "fields": [{"name": "check_in", "type": "date"}],
    }
    events = [e async for e in manager.apply_tool_result("thread-9", "request_user_input", result)]
    assert len(events) == 1
    snap = events[0].snapshot
    assert snap["snapshot_type"] == "user_input_request"
    assert snap["_agui_event"] == "USER_INPUT_REQUEST"
    assert snap["input_type"] == "hotel_booking_details"
    assert snap["fields"] == result["fields"]


@pytest.mark.asyncio
async def test_get_tc_id_returns_stored_id(manager):
    args = {"city": "도쿄", "check_in": "2026-09-01", "check_out": "2026-09-03", "guests": 1}
    events = [e async for e in manager.apply_tool_call("thread-10", "search_hotels", args)]
    assert len(events) >= 1
    tc_id = manager.get_tc_id("thread-10", "search_hotels")
    assert len(tc_id) == 36


@pytest.mark.asyncio
async def test_get_tc_id_unknown_tool_returns_new_uuid_with_warning(manager, caplog):
    import logging
    with caplog.at_level(logging.WARNING):
        tc_id = manager.get_tc_id("thread-11", "unknown_tool")
    assert len(tc_id) == 36
    assert "미등록" in caplog.text


def test_clear_removes_state_and_tool_call_map(manager):
    manager._store["thread-12"] = TravelState()  # type: ignore
    manager._tool_call_map["thread-12"] = {"search_hotels": "some-id"}  # type: ignore
    manager.clear("thread-12")
    assert "thread-12" not in manager._store
    assert "thread-12" not in manager._tool_call_map
```

- [ ] **Step 10: 테스트 실패 확인**

```bash
cd backend && uv run pytest tests/state/test_manager.py -k "tool_result or tc_id or clear" -v 2>&1 | tail -10
```
Expected: `NotImplementedError`

- [ ] **Step 11: `apply_tool_result`, `get_tc_id` 구현**

`state/manager.py`의 `apply_tool_result`와 `get_tc_id` `raise NotImplementedError`를 아래로 교체:

```python
async def apply_tool_result(
    self, thread_id: str, tool_name: str, result: dict
) -> AsyncGenerator[StateSnapshotEvent, None]:
    """
    executor.py에서 function_response 수신 시 호출.
    request_user_input 특수 케이스는 user_input_request snapshot으로 발행한다.
    caller(executor.py)는 event.snapshot을 DataPart로 래핑 후 event_queue에 enqueue한다.
    """
    if tool_name == "request_user_input" and result.get("status") == "user_input_required":
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
```

- [ ] **Step 12: 전체 manager 테스트 통과 확인**

```bash
cd backend && uv run pytest tests/state/ -v 2>&1 | tail -20
```
Expected: 전체 PASSED

- [ ] **Step 13: 커밋**

```bash
git add backend/state/__init__.py backend/state/manager.py backend/tests/state/test_manager.py
git commit -m "feat: state/manager.py StateManager 구현 (apply_client_state, apply_tool_call, apply_tool_result)"
```

---

## Task 3: executor.py 교체

**Files:**
- Modify: `backend/executor.py`
- Rewrite: `backend/tests/state-panel-sidebar/test_snapshot_emission.py`

- [ ] **Step 1: 기존 테스트 전면 재작성**

`backend/tests/state-panel-sidebar/test_snapshot_emission.py`:

```python
"""
test_snapshot_emission.py — executor.py가 StateManager를 통해
agent_state snapshot을 TOOL_CALL_START 전에 발행하는지 검증
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from executor import ADKAgentExecutor


def _make_function_call_event(tool_name: str, args: dict):
    fc = MagicMock()
    fc.name = tool_name
    fc.args = args

    part = MagicMock()
    part.text = None
    part.function_call = fc
    part.function_response = None

    content = MagicMock()
    content.parts = [part]

    event = MagicMock()
    event.content = content
    event.is_final_response.return_value = False
    return event


async def _async_gen(*items):
    for item in items:
        yield item


@pytest.mark.asyncio
async def test_agent_state_snapshot_enqueued_before_tool_call_start():
    """apply_tool_call이 반환한 snapshot이 TOOL_CALL_START DataPart보다 먼저 enqueue된다."""
    from ag_ui.core.events import StateSnapshotEvent, EventType

    mock_snapshot_event = StateSnapshotEvent(
        type=EventType.STATE_SNAPSHOT,
        snapshot={"snapshot_type": "agent_state", "travel_context": {}, "agent_status": {}},
    )

    mock_runner = MagicMock()
    mock_runner.run_async.return_value = _async_gen(
        _make_function_call_event("search_hotels", {"city": "도쿄"})
    )
    mock_session_service = AsyncMock()
    mock_session_service.get_session.return_value = MagicMock()

    mock_state_manager = MagicMock()

    async def mock_apply_tool_call(*args, **kwargs):
        yield mock_snapshot_event

    mock_state_manager.apply_tool_call = mock_apply_tool_call
    mock_state_manager.get_tc_id.return_value = "test-tc-id"

    async def mock_apply_tool_result(*args, **kwargs):
        return
        yield  # async generator

    mock_state_manager.apply_tool_result = mock_apply_tool_result

    with patch("executor.state_manager", mock_state_manager):
        executor = ADKAgentExecutor(mock_runner, mock_session_service)
        mock_queue = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.task_id = "t1"
        mock_ctx.context_id = "c1"
        mock_ctx.get_user_input.return_value = "도쿄 호텔"

        await executor.execute(mock_ctx, mock_queue)

    calls = mock_queue.enqueue_event.call_args_list
    data_list = []
    for call in calls:
        event = call[0][0]
        if hasattr(event, "artifact") and event.artifact and event.artifact.parts:
            for p in event.artifact.parts:
                root = p.root if hasattr(p, "root") else p
                if hasattr(root, "data") and isinstance(root.data, dict):
                    data_list.append(root.data)

    keys = [d.get("snapshot_type") or d.get("_agui_event") for d in data_list]
    assert "agent_state" in keys
    assert "TOOL_CALL_START" in keys
    assert keys.index("agent_state") < keys.index("TOOL_CALL_START")


@pytest.mark.asyncio
async def test_tool_result_snapshot_enqueued_after_tool_call_end():
    """apply_tool_result이 반환한 snapshot이 TOOL_CALL_END DataPart 이후에 enqueue된다."""
    from ag_ui.core.events import StateSnapshotEvent, EventType

    mock_snapshot_event = StateSnapshotEvent(
        type=EventType.STATE_SNAPSHOT,
        snapshot={"snapshot_type": "tool_result", "tool": "search_hotels", "result": {}},
    )

    fr = MagicMock()
    fr.name = "search_hotels"
    fr.response = {"status": "success", "hotels": []}

    part = MagicMock()
    part.text = None
    part.function_call = None
    part.function_response = fr

    content = MagicMock()
    content.parts = [part]

    adk_event = MagicMock()
    adk_event.content = content
    adk_event.is_final_response.return_value = False

    mock_runner = MagicMock()
    mock_runner.run_async.return_value = _async_gen(adk_event)
    mock_session_service = AsyncMock()
    mock_session_service.get_session.return_value = MagicMock()

    mock_state_manager = MagicMock()

    async def mock_apply_tool_call(*args, **kwargs):
        return
        yield

    mock_state_manager.apply_tool_call = mock_apply_tool_call

    async def mock_apply_tool_result(*args, **kwargs):
        yield mock_snapshot_event

    mock_state_manager.apply_tool_result = mock_apply_tool_result
    mock_state_manager.get_tc_id.return_value = "tc-id-999"

    with patch("executor.state_manager", mock_state_manager):
        executor = ADKAgentExecutor(mock_runner, mock_session_service)
        mock_queue = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.task_id = "t2"
        mock_ctx.context_id = "c2"
        mock_ctx.get_user_input.return_value = "test"

        await executor.execute(mock_ctx, mock_queue)

    calls = mock_queue.enqueue_event.call_args_list
    data_list = []
    for call in calls:
        event = call[0][0]
        if hasattr(event, "artifact") and event.artifact and event.artifact.parts:
            for p in event.artifact.parts:
                root = p.root if hasattr(p, "root") else p
                if hasattr(root, "data") and isinstance(root.data, dict):
                    data_list.append(root.data)

    keys = [d.get("snapshot_type") or d.get("_agui_event") for d in data_list]
    assert "TOOL_CALL_END" in keys
    assert "tool_result" in keys
    assert keys.index("TOOL_CALL_END") < keys.index("tool_result")
```

- [ ] **Step 2: 테스트 실패 확인 (executor가 아직 state_manager를 사용하지 않음)**

```bash
cd backend && uv run pytest tests/state-panel-sidebar/test_snapshot_emission.py -v 2>&1 | tail -10
```
Expected: FAIL 또는 ImportError

- [ ] **Step 3: executor.py 수정**

아래 변경을 순서대로 적용한다:

**1) import 변경** — 파일 상단에서:
- `from context_extractor import extract_travel_context, extract_agent_status` 제거
- `from state import state_manager` 추가

**2) `tool_call_map` 로컬 변수 제거** — `execute()` 함수 내부 line 65 (`tool_call_map: dict[str, str] = {}`) 삭제

**3) function_call 블록 교체** — `elif hasattr(part, "function_call") and part.function_call:` 블록 전체를 아래로 교체:

```python
# 함수 호출 (Tool Call 시작) → agent_state STATE_SNAPSHOT 먼저 발행 후 TOOL_CALL_START
elif hasattr(part, "function_call") and part.function_call:
    fc = part.function_call
    args_dict = dict(fc.args) if fc.args else {}

    # agent_state STATE_SNAPSHOT 먼저 발행 (TOOL_CALL_START 전)
    async for snap_event in state_manager.apply_tool_call(context_id, fc.name, args_dict):
        await event_queue.enqueue_event(
            TaskArtifactUpdateEvent(
                task_id=task_id,
                context_id=context_id,
                artifact=Artifact(
                    artifact_id=str(uuid.uuid4()),
                    parts=[Part(root=DataPart(data=snap_event.snapshot))],
                ),
                append=False,
                last_chunk=False,
            )
        )

    tc_id = state_manager.get_tc_id(context_id, fc.name)
    await event_queue.enqueue_event(
        TaskArtifactUpdateEvent(
            task_id=task_id,
            context_id=context_id,
            artifact=Artifact(
                artifact_id=str(uuid.uuid4()),
                parts=[Part(root=DataPart(data={
                    "_agui_event": "TOOL_CALL_START",
                    "id": tc_id,
                    "name": fc.name,
                    "args": args_dict,
                }))],
            ),
            append=False,
            last_chunk=False,
        )
    )
```

**4) function_response 블록 교체** — `elif hasattr(part, "function_response") and part.function_response:` 블록 전체를 아래로 교체:

```python
# 함수 응답 (Tool Call 종료 + 결과)
elif hasattr(part, "function_response") and part.function_response:
    fr = part.function_response
    tc_id = state_manager.get_tc_id(context_id, fr.name)

    # TOOL_CALL_END 신호
    await event_queue.enqueue_event(
        TaskArtifactUpdateEvent(
            task_id=task_id,
            context_id=context_id,
            artifact=Artifact(
                artifact_id=str(uuid.uuid4()),
                parts=[Part(root=DataPart(data={
                    "_agui_event": "TOOL_CALL_END",
                    "id": tc_id,
                }))],
            ),
            append=False,
            last_chunk=False,
        )
    )

    if fr.response:
        logger.info(f"[DEBUG] {fr.name} response type={type(fr.response).__name__}")
        response_data = fr.response if isinstance(fr.response, dict) else {"raw": str(fr.response)}
        async for snap_event in state_manager.apply_tool_result(context_id, fr.name, response_data):
            await event_queue.enqueue_event(
                TaskArtifactUpdateEvent(
                    task_id=task_id,
                    context_id=context_id,
                    artifact=Artifact(
                        artifact_id=str(uuid.uuid4()),
                        parts=[Part(root=DataPart(data=snap_event.snapshot))],
                    ),
                    append=False,
                    last_chunk=False,
                )
            )
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd backend && uv run pytest tests/state-panel-sidebar/test_snapshot_emission.py -v 2>&1 | tail -15
```
Expected: 2개 PASSED

- [ ] **Step 5: 커밋**

```bash
git add backend/executor.py backend/tests/state-panel-sidebar/test_snapshot_emission.py
git commit -m "refactor: executor.py에서 StateManager 호출로 교체"
```

---

## Task 4: main.py 교체

**Files:**
- Modify: `backend/main.py`
- Rewrite: `backend/tests/state-panel-sidebar/test_main_state_handling.py`

- [ ] **Step 1: 기존 테스트 전면 재작성**

`backend/tests/state-panel-sidebar/test_main_state_handling.py`:

```python
"""
test_main_state_handling.py — main.py의 event_stream()에서
StateManager.apply_client_state가 올바르게 호출되는지 검증
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from ag_ui.core.events import StateSnapshotEvent, EventType


@pytest.mark.asyncio
async def test_apply_client_state_called_with_body_state():
    """event_stream 내에서 body['state']가 apply_client_state에 전달된다."""
    from main import app
    from httpx import AsyncClient, ASGITransport

    raw_state = {
        "travel_context": {"destination": "도쿄"},
        "ui_context": {"selected_hotel_code": "HTL-001"},
    }

    mock_snapshot = StateSnapshotEvent(
        type=EventType.STATE_SNAPSHOT,
        snapshot={"snapshot_type": "client_state", "travel_context": {}, "ui_context": {}},
    )

    captured_args: dict = {}

    async def mock_apply_client_state(thread_id, raw):
        captured_args["thread_id"] = thread_id
        captured_args["raw_state"] = raw
        yield mock_snapshot

    mock_state_mgr = MagicMock()
    mock_state_mgr.apply_client_state = mock_apply_client_state
    mock_state_mgr.get.return_value = MagicMock(
        travel_context=MagicMock(
            destination=None, origin=None, check_in=None,
            check_out=None, nights=None, guests=None, trip_type=None,
        ),
        ui_context=MagicMock(selected_hotel_code=None),
    )

    # A2A 호출을 완전히 mock — 빈 스트림 반환
    async def empty_stream():
        return
        yield  # async generator

    with patch("main.state_manager", mock_state_mgr), \
         patch("main.httpx.AsyncClient") as mock_http:
        mock_http_instance = AsyncMock()
        mock_http.return_value.__aenter__.return_value = mock_http_instance
        mock_http_instance.get.return_value = MagicMock(
            json=lambda: {
                "name": "test", "url": "http://localhost:8001",
                "version": "1.0", "capabilities": {},
            },
            raise_for_status=lambda: None,
        )

        # A2AClient mock
        with patch("main.A2AClient") as mock_a2a_cls:
            mock_a2a_instance = MagicMock()
            mock_a2a_cls.return_value = mock_a2a_instance
            mock_a2a_instance.send_message_streaming.return_value = empty_stream()

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                payload = {
                    "threadId": "test-thread",
                    "runId": "test-run",
                    "messages": [{"id": "m1", "role": "user", "content": "테스트"}],
                    "tools": [],
                    "context": [],
                    "forwardedProps": {},
                    "state": raw_state,
                }
                # SSE 스트림을 소비해야 generator가 실행됨
                response = await ac.post("/agui/run", json=payload)
                # StreamingResponse 본문을 일부라도 소비
                _ = response.content

    assert captured_args.get("raw_state") == raw_state
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd backend && uv run pytest tests/state-panel-sidebar/test_main_state_handling.py -v 2>&1 | tail -10
```
Expected: FAIL (main.py가 아직 state_manager를 사용하지 않음)

- [ ] **Step 3: main.py 수정**

아래 변경을 순서대로 적용한다:

**1) import 추가** — 파일 상단 import 블록에 추가:
```python
from state import state_manager
```

**2) `client_state` 파싱 블록 제거** — 아래 블록(L98~102) 삭제:
```python
# client_state 추출 (RunAgentInput.state 필드, 없으면 빈 dict)
client_state: dict = {}
raw_state = body.get("state")
if isinstance(raw_state, dict) and raw_state:
    client_state = raw_state
```

**3) 컨텍스트 추출·주입 블록 제거** — 아래 블록(L104~132) 삭제:
```python
# travel_context가 있으면 에이전트 메시지 앞에 컨텍스트 블록을 주입
travel_context: dict = client_state.get("travel_context") or {}
ui_context: dict = client_state.get("ui_context") or {}
ctx_lines = []
...
if ctx_lines:
    ...
    logger.info(f"[{thread_id}] 여행 컨텍스트 주입: {ctx_lines}")
```

**4) `event_stream()` 내부 교체** — `RUN_STARTED` yield 직후에 아래 블록 삽입:

```python
# 2. 클라이언트 state 반영 (ui_context, travel_context)
raw_state = body.get("state") or {}
async for snap_event in state_manager.apply_client_state(thread_id, raw_state):
    yield encoder.encode(snap_event)

# 3. 컨텍스트 주입 (최신 state 조회)
state = state_manager.get(thread_id)
tc = state.travel_context
ui = state.ui_context
ctx_lines = []
if ui.selected_hotel_code:
    ctx_lines.append(f"- 선택된 호텔 코드: {ui.selected_hotel_code}")
if tc.destination:
    ctx_lines.append(f"- 목적지: {tc.destination}")
if tc.origin:
    ctx_lines.append(f"- 출발지: {tc.origin}")
if tc.check_in:
    ctx_lines.append(f"- 체크인/출발일: {tc.check_in}")
if tc.check_out:
    ctx_lines.append(f"- 체크아웃/귀국일: {tc.check_out}")
if tc.nights:
    ctx_lines.append(f"- 숙박: {tc.nights}박")
if tc.guests:
    ctx_lines.append(f"- 인원: {tc.guests}명")
if tc.trip_type:
    ctx_lines.append(f"- 여행 유형: {tc.trip_type}")
if ctx_lines:
    context_block = "[현재 여행 컨텍스트 - 이미 확인된 정보]\n" + "\n".join(ctx_lines)
    user_message = f"{context_block}\n\n사용자 요청: {user_message}"
    logger.info(f"[{thread_id}] 여행 컨텍스트 주입: {ctx_lines}")
```

**5) `client_state` metadata 전달 코드 제거** — `msg_kwargs` 조립 블록에서:
```python
if client_state:
    msg_kwargs["metadata"] = {"client_state": client_state}
```
이 부분을 제거한다 (client_state 변수가 더 이상 존재하지 않음).

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd backend && uv run pytest tests/state-panel-sidebar/test_main_state_handling.py -v 2>&1 | tail -10
```
Expected: PASSED

- [ ] **Step 5: 커밋**

```bash
git add backend/main.py backend/tests/state-panel-sidebar/test_main_state_handling.py
git commit -m "refactor: main.py에서 StateManager.apply_client_state 호출로 교체"
```

---

## Task 5: context_extractor.py 삭제 + 테스트 재작성

**Files:**
- Delete: `backend/context_extractor.py`
- Rewrite: `backend/tests/state-panel-sidebar/test_context_extraction.py`

- [ ] **Step 1: 기존 테스트 전면 재작성**

`backend/tests/state-panel-sidebar/test_context_extraction.py`:

```python
"""
test_context_extraction.py — StateManager.apply_tool_call이
컨텍스트 추출 결과를 올바르게 state에 반영하는지 검증
(context_extractor.py 삭제 후 StateManager 기반으로 전면 재작성)
"""
import pytest
from state.manager import StateManager


@pytest.fixture
def manager():
    return StateManager()


@pytest.mark.asyncio
async def test_apply_tool_call_search_hotels_extracts_context(manager):
    args = {
        "city": "도쿄",
        "check_in": "2026-06-10",
        "check_out": "2026-06-14",
        "guests": 2,
    }
    events = [e async for e in manager.apply_tool_call("t1", "search_hotels", args)]
    snap = events[0].snapshot
    tc = snap["travel_context"]
    assert tc["destination"] == "도쿄"
    assert tc["check_in"] == "2026-06-10"
    assert tc["check_out"] == "2026-06-14"
    assert tc["guests"] == 2
    assert tc["nights"] == 4


@pytest.mark.asyncio
async def test_apply_tool_call_search_flights_extracts_context(manager):
    args = {
        "origin": "서울",
        "destination": "오사카",
        "departure_date": "2026-07-01",
        "passengers": 1,
        "return_date": "2026-07-05",
    }
    events = [e async for e in manager.apply_tool_call("t2", "search_flights", args)]
    snap = events[0].snapshot
    tc = snap["travel_context"]
    assert tc["origin"] == "서울"
    assert tc["destination"] == "오사카"
    assert tc["check_in"] == "2026-07-01"
    assert tc["guests"] == 1
    assert tc["trip_type"] == "round_trip"


@pytest.mark.asyncio
async def test_apply_tool_call_request_user_input_hotel(manager):
    args = {"input_type": "hotel_booking_details", "context": "제주"}
    events = [e async for e in manager.apply_tool_call("t3", "request_user_input", args)]
    snap = events[0].snapshot
    assert snap["agent_status"]["current_intent"] == "collecting_hotel_params"
    assert "check_in" in snap["agent_status"]["missing_fields"]


@pytest.mark.asyncio
async def test_apply_tool_call_partial_args(manager):
    args = {"city": "부산"}
    events = [e async for e in manager.apply_tool_call("t4", "search_hotels", args)]
    snap = events[0].snapshot
    tc = snap["travel_context"]
    assert tc["destination"] == "부산"
    assert tc["check_in"] is None
    assert tc["nights"] is None
```

- [ ] **Step 2: 테스트 통과 확인 (StateManager 구현 완료)**

```bash
cd backend && uv run pytest tests/state-panel-sidebar/test_context_extraction.py -v 2>&1 | tail -10
```
Expected: 4개 PASSED

- [ ] **Step 3: context_extractor.py 삭제**

```bash
rm backend/context_extractor.py
```

- [ ] **Step 4: 삭제 후 전체 테스트 통과 확인**

```bash
cd backend && uv run pytest tests/ -v 2>&1 | tail -20
```
Expected: 전체 PASSED

- [ ] **Step 5: 커밋**

```bash
git add backend/tests/state-panel-sidebar/test_context_extraction.py
git add -u backend/context_extractor.py
git commit -m "refactor: context_extractor.py 삭제, 테스트 StateManager 기반으로 전면 재작성"
```

---

## Task 6: 최종 검증

- [ ] **Step 1: 전체 테스트 실행**

```bash
cd backend && uv run pytest tests/ -v 2>&1 | tail -30
```
Expected: 전체 PASSED, 실패 없음

- [ ] **Step 2: import 오류 없음 확인**

```bash
cd backend && uv run python3 -c "from state import state_manager; from main import app; from executor import ADKAgentExecutor; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: 워킹 트리 클린 확인**

```bash
git status
```
Expected: `nothing to commit, working tree clean`
