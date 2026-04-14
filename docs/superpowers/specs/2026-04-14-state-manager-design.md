# State Manager 설계 스펙

**날짜:** 2026-04-14  
**브랜치:** claude/wizardly-greider  
**범위:** backend state 관련 코드 통합 및 `state/` 패키지 신설

---

## 배경

현재 state 관련 코드가 세 파일에 분산되어 있다:

| 파일 | 역할 |
|------|------|
| `main.py` (L98~132) | 클라이언트 `body["state"]` 파싱, 컨텍스트 주입 |
| `context_extractor.py` | 툴 호출 인수에서 travel_context, agent_status 추출 |
| `executor.py` (L104~122) | STATE_SNAPSHOT DataPart 직접 조립·발행 |

state 구조가 dict로만 관리되어 타입 안정성이 없고, 변경 시 여러 파일을 동시에 수정해야 한다.

---

## 목표

- `thread_id` 기준으로 세션별 state를 서버 메모리에서 통합 관리
- state 변경 시 `StateSnapshotEvent`를 이벤트 기반으로 yield
- `context_extractor.py` 제거 및 `state/` 패키지로 흡수
- 호출 측(`main.py`, `executor.py`)은 `apply_*` 메서드만 호출

---

## 아키텍처

### 파일 구성

```
backend/
  state/
    __init__.py       # StateManager 싱글톤 + 모델 export
    models.py         # 순수 frozen dataclass (TravelState, TravelContext, UIContext, AgentStatus)
    manager.py        # StateManager 클래스
  context_extractor.py  # 삭제
  main.py               # apply_client_state 호출로 교체
  executor.py           # apply_tool_call / apply_tool_result 호출로 교체
  converter.py          # 변경 없음
```

### 데이터 모델 (`state/models.py`)

모든 dataclass는 `frozen=True`를 사용해 불변성을 보장한다. 업데이트는 반드시 `dataclasses.replace()`로 처리한다.

```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class TravelContext:
    destination: str | None = None
    origin: str | None = None
    check_in: str | None = None
    check_out: str | None = None
    nights: int | None = None
    guests: int | None = None
    trip_type: str | None = None  # "round_trip" | "one_way"

@dataclass(frozen=True)
class UIContext:
    selected_hotel_code: str | None = None

@dataclass(frozen=True)
class AgentStatus:
    current_intent: str = "idle"
    missing_fields: tuple[str, ...] = ()   # frozen이므로 list 대신 tuple
    active_tool: str | None = None

@dataclass(frozen=True)
class TravelState:
    travel_context: TravelContext = field(default_factory=TravelContext)
    ui_context: UIContext = field(default_factory=UIContext)
    agent_status: AgentStatus = field(default_factory=AgentStatus)
```

### StateManager (`state/manager.py`)

**이벤트 타입 계층:**  
`apply_client_state`는 `ag_ui.core.events.StateSnapshotEvent`를 yield한다. `main.py`는 이를 `encoder.encode(event)`로 직접 SSE 직렬화한다.  
`apply_tool_call` / `apply_tool_result`도 동일하게 `ag_ui.core.events.StateSnapshotEvent`를 yield한다. 단, `executor.py`는 이를 직접 `event_queue.enqueue_event()`에 넣을 수 없다 — `event_queue`는 A2A 타입(`TaskArtifactUpdateEvent`)만 허용하기 때문이다. 따라서 `executor.py` caller는 yield된 `StateSnapshotEvent`의 `snapshot` dict를 꺼내 `TaskArtifactUpdateEvent(artifact=Artifact(parts=[Part(root=DataPart(data=snapshot))]))` 로 래핑한 후 enqueue한다.

```python
from typing import AsyncIterator
from ag_ui.core.events import StateSnapshotEvent

class StateManager:
    def __init__(self):
        self._store: dict[str, TravelState] = {}
        # thread_id → {tool_name: tc_id} 맵 (TOOL_CALL_END 발행에 필요)
        self._tool_call_map: dict[str, dict[str, str]] = {}

    def get(self, thread_id: str) -> TravelState:
        """현재 state 조회. 없으면 빈 TravelState 반환."""
        return self._store.get(thread_id, TravelState())

    async def apply_client_state(
        self, thread_id: str, raw_state: dict
    ) -> AsyncIterator[StateSnapshotEvent]:
        """
        main.py의 event_stream() 내부 상단(RUN_STARTED 직후)에서 호출.
        body['state']를 수신해 ui_context + travel_context를 업데이트하고
        ag_ui.core.events.StateSnapshotEvent를 yield한다.
        caller(main.py)는 encoder.encode(event)로 SSE에 직접 forward한다.

        snapshot 페이로드 예시:
        {
            "snapshot_type": "client_state",
            "travel_context": {"destination": "도쿄", "check_in": "2026-05-01", ...},
            "ui_context": {"selected_hotel_code": "HTL001"}
        }
        """

    async def apply_tool_call(
        self, thread_id: str, tool_name: str, args: dict
    ) -> AsyncIterator[StateSnapshotEvent]:
        """
        executor.py에서 function_call 감지 시 호출 (TOOL_CALL_START DataPart 발행 전).
        - context_extractor 로직 내부 수행
        - travel_context + agent_status 업데이트
        - tc_id 생성 후 self._tool_call_map[thread_id][tool_name] 에 저장
        - ag_ui.core.events.StateSnapshotEvent yield

        caller(executor.py)는 yield된 event.snapshot dict를 꺼내
        TaskArtifactUpdateEvent(DataPart)로 래핑 후 event_queue.enqueue_event()에 전달한다.

        snapshot 페이로드 예시:
        {
            "snapshot_type": "agent_state",
            "travel_context": {"destination": "도쿄", "check_in": "2026-05-01", ...},
            "agent_status": {"current_intent": "searching", "missing_fields": [], "active_tool": "search_hotels"}
        }
        """

    async def apply_tool_result(
        self, thread_id: str, tool_name: str, result: dict
    ) -> AsyncIterator[StateSnapshotEvent]:
        """
        executor.py에서 function_response 수신 시 호출.
        - tool_name == "request_user_input" 이고 result["status"] == "user_input_required" 인 경우:
            snapshot_type: "user_input_request" StateSnapshotEvent yield
        - 그 외: snapshot_type: "tool_result" StateSnapshotEvent yield

        caller(executor.py)는 yield된 event.snapshot dict를 꺼내
        TaskArtifactUpdateEvent(DataPart)로 래핑 후 event_queue.enqueue_event()에 전달한다.

        tool_result snapshot 페이로드 예시:
        {
            "snapshot_type": "tool_result",
            "tool": "search_hotels",
            "result": { ... }
        }

        user_input_request snapshot 페이로드 예시:
        {
            "snapshot_type": "user_input_request",
            "_agui_event": "USER_INPUT_REQUEST",
            "request_id": "<uuid>",
            "input_type": "hotel_booking_details",
            "fields": [...]
        }

        tc_id는 caller가 get_tc_id(thread_id, tool_name)으로 별도 조회해 TOOL_CALL_END DataPart에 사용한다.
        """

    def get_tc_id(self, thread_id: str, tool_name: str) -> str:
        """
        tool_name에 해당하는 tc_id 조회.
        apply_tool_call이 호출되지 않은 경우(미등록 tool_name) 새 uuid를 반환하며
        logger.warning을 발행한다 — TOOL_CALL_START/END 페어가 깨지는 알려진 실패 모드.
        """
        tc_id = self._tool_call_map.get(thread_id, {}).get(tool_name)
        if tc_id is None:
            logger.warning(f"[{thread_id}] get_tc_id: '{tool_name}' 미등록 — 새 uuid 발행 (TOOL_CALL 페어 불일치 가능)")
            return str(uuid.uuid4())
        return tc_id

    def clear(self, thread_id: str) -> None:
        """세션 종료 시 _store + _tool_call_map 정리."""
        self._store.pop(thread_id, None)
        self._tool_call_map.pop(thread_id, None)
```

### 싱글톤 (`state/__init__.py`)

```python
from .manager import StateManager
from .models import TravelState, TravelContext, UIContext, AgentStatus

state_manager = StateManager()
```

`main.py`와 `executor.py`가 `from state import state_manager`로 공유 인스턴스를 import한다.

---

## 데이터 흐름

```
[React] body["state"]
    → main.py event_stream() 내부 상단 (RUN_STARTED 직후):
        async for event in state_manager.apply_client_state(thread_id, raw_state):
            yield encoder.encode(event)   # SSE forward

    (이후 컨텍스트 주입)
    state = state_manager.get(thread_id)
    → state.travel_context, state.ui_context로 프롬프트 조립 후 A2A 전송

[ADK function_call]
    → executor.py:
        async for event in state_manager.apply_tool_call(thread_id, tool_name, args):
            # StateSnapshotEvent를 A2A TaskArtifactUpdateEvent로 래핑 후 enqueue
            await event_queue.enqueue_event(
                TaskArtifactUpdateEvent(
                    artifact=Artifact(parts=[Part(root=DataPart(data=event.snapshot))])
                )
            )
        tc_id = state_manager.get_tc_id(thread_id, tool_name)
        → TOOL_CALL_START DataPart 발행 (tc_id 사용)

[ADK function_response]
    → executor.py:
        tc_id = state_manager.get_tc_id(thread_id, tool_name)
        → TOOL_CALL_END DataPart 발행 (tc_id 사용)
        async for event in state_manager.apply_tool_result(thread_id, tool_name, result):
            # StateSnapshotEvent를 A2A TaskArtifactUpdateEvent로 래핑 후 enqueue
            await event_queue.enqueue_event(
                TaskArtifactUpdateEvent(
                    artifact=Artifact(parts=[Part(root=DataPart(data=event.snapshot))])
                )
            )
```

---

## 기존 파일 변경 요약

| 파일 | 변경 내용 |
|------|-----------|
| `context_extractor.py` | **삭제** — `state/manager.py` 내부로 흡수 |
| `main.py` | state 파싱·주입 블록 → `apply_client_state` + `state_manager.get` 호출로 교체 |
| `executor.py` | DataPart 직접 조립 → `apply_tool_call` / `apply_tool_result` + `get_tc_id` 호출로 교체 |
| `converter.py` | 변경 없음 |
| `models.py` | 변경 없음 (`UserInputRequestEvent` 그대로 유지) |

---

## 동시성 모델

현재 아키텍처에서 각 `thread_id`는 단일 `/agui/run` 요청에 대응하며, A2A 스트리밍은 해당 요청 내에서 순차 처리된다. 따라서 동일 `thread_id`에 대한 동시 코루틴 접근은 현재 발생하지 않는다. `asyncio.Lock`은 현재 범위에서는 불필요하다. 향후 동일 thread_id로 병렬 요청이 가능해지면 thread_id 키 기반 Lock을 추가해야 한다.

---

## 생명주기 및 메모리 관리

state는 `thread_id` 기준으로 서버 메모리에 보관되며 서버 재시작 시 초기화된다 (ADK 세션과 동일). `_store`와 `_tool_call_map`은 현재 자동 eviction 없이 프로세스 수명 동안 누적된다. 현재 단일 프로세스·개발용 서버 환경에서는 세션 수가 제한적이므로 허용 가능한 트레이드오프다. 프로덕션 배포 시에는 TTL 기반 eviction 또는 요청 완료 훅(`clear` 자동 호출)을 추가해야 한다.

---

## 테스트 전략

### 신규 테스트 (`tests/state/`)

- `test_models.py`: frozen dataclass 생성, `replace()` immutable update 단위 테스트
- `test_manager.py`:
  - `apply_client_state`: `ui_context`, `travel_context` 반영 확인, yield된 snapshot 페이로드 검증
  - `apply_tool_call`: `agent_status`, `travel_context` 업데이트 + event yield 확인, `tc_id` 저장 확인
  - `apply_tool_result` (일반): `tool_result` snapshot event yield 확인
  - `apply_tool_result` (request_user_input): `user_input_request` snapshot event yield 확인
  - `get_tc_id`: 저장된 tc_id 반환, 없을 때 warning 로그 + 새 uuid 반환 확인
  - `clear`: `_store` + `_tool_call_map` 양쪽 모두 정리 확인

### 기존 테스트 변경

| 파일 | 변경 수준 |
|------|-----------|
| `tests/state-panel-sidebar/test_context_extraction.py` | **전면 재작성** — `context_extractor` 직접 import 불가, `StateManager.apply_tool_call` 기반으로 교체 |
| `tests/state-panel-sidebar/test_snapshot_emission.py` | **전면 재작성** — `ADKAgentExecutor`의 DataPart 직접 조립 로직이 사라지므로 `StateManager` mock 기반으로 교체 |
| `tests/state-panel-sidebar/test_main_state_handling.py` | **전면 재작성** — 기존 tautological assertion(`assert payload["state"] == payload["state"]`) 제거, `apply_client_state` yield 이벤트 내용 검증으로 교체 |
