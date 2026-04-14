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
    models.py         # 순수 dataclass (TravelState, TravelContext, UIContext, AgentStatus)
    manager.py        # StateManager 클래스
  context_extractor.py  # 삭제
  main.py               # apply_client_state 호출로 교체
  executor.py           # apply_tool_call / apply_tool_result 호출로 교체
  converter.py          # 변경 없음
```

### 데이터 모델 (`state/models.py`)

```python
from dataclasses import dataclass, field

@dataclass
class TravelContext:
    destination: str | None = None
    origin: str | None = None
    check_in: str | None = None
    check_out: str | None = None
    nights: int | None = None
    guests: int | None = None
    trip_type: str | None = None  # "round_trip" | "one_way"

@dataclass
class UIContext:
    selected_hotel_code: str | None = None

@dataclass
class AgentStatus:
    current_intent: str = "idle"
    missing_fields: list[str] = field(default_factory=list)
    active_tool: str | None = None

@dataclass
class TravelState:
    travel_context: TravelContext = field(default_factory=TravelContext)
    ui_context: UIContext = field(default_factory=UIContext)
    agent_status: AgentStatus = field(default_factory=AgentStatus)
```

모든 state 업데이트는 `dataclasses.replace()`를 사용한 immutable update 방식으로 처리한다.

### StateManager (`state/manager.py`)

```python
class StateManager:
    def __init__(self):
        self._store: dict[str, TravelState] = {}

    def get(self, thread_id: str) -> TravelState:
        """현재 state 조회. 없으면 빈 TravelState 반환."""

    async def apply_client_state(
        self, thread_id: str, raw_state: dict
    ) -> AsyncGenerator[StateSnapshotEvent, None]:
        """
        main.py에서 body['state'] 수신 시 호출.
        - ui_context 업데이트 (selected_hotel_code 등)
        - travel_context 업데이트
        - 변경된 state를 StateSnapshotEvent로 yield
        """

    async def apply_tool_call(
        self, thread_id: str, tool_name: str, args: dict
    ) -> AsyncGenerator[StateSnapshotEvent, None]:
        """
        executor.py에서 function_call 감지 시 호출.
        - context_extractor 로직 내부 수행
        - travel_context + agent_status 업데이트
        - agent_state 타입 StateSnapshotEvent yield
        """

    async def apply_tool_result(
        self, thread_id: str, tool_name: str, result: dict
    ) -> AsyncGenerator[StateSnapshotEvent, None]:
        """
        executor.py에서 function_response 수신 시 호출.
        - tool_result 타입 StateSnapshotEvent yield
        """

    def clear(self, thread_id: str) -> None:
        """세션 종료 시 메모리 정리."""
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
    → main.py: async for event in state_manager.apply_client_state(thread_id, raw_state)
        → SSE yield (StateSnapshotEvent)

[ADK function_call]
    → executor.py: async for event in state_manager.apply_tool_call(thread_id, tool_name, args)
        → event_queue.enqueue_event(StateSnapshotEvent)  # agent_state

[ADK function_response]
    → executor.py: async for event in state_manager.apply_tool_result(thread_id, tool_name, result)
        → event_queue.enqueue_event(StateSnapshotEvent)  # tool_result

[컨텍스트 주입 (main.py)]
    → state = state_manager.get(thread_id)
    → state.travel_context, state.ui_context로 프롬프트 조립
```

---

## 기존 파일 변경 요약

| 파일 | 변경 내용 |
|------|-----------|
| `context_extractor.py` | **삭제** — `state/manager.py` 내부로 흡수 |
| `main.py` | state 파싱·주입 블록 → `apply_client_state` + `state_manager.get` 호출로 교체 |
| `executor.py` | DataPart 직접 조립 → `apply_tool_call` / `apply_tool_result` 호출로 교체 |
| `converter.py` | 변경 없음 |
| `models.py` | 변경 없음 (`UserInputRequestEvent` 그대로 유지) |

---

## 테스트 전략

- `state/models.py`: dataclass 생성 및 immutable replace 단위 테스트
- `state/manager.py`: 각 `apply_*` 메서드별 단위 테스트
  - `apply_client_state`: `ui_context`, `travel_context` 반영 확인
  - `apply_tool_call`: `agent_status`, `travel_context` 업데이트 + event yield 확인
  - `apply_tool_result`: `tool_result` snapshot event yield 확인
- 기존 `tests/state-panel-sidebar/` 테스트를 새 인터페이스에 맞게 업데이트
- `context_extractor` 관련 테스트는 `state/manager` 테스트로 이전

---

## 생명주기

- state는 `thread_id` 기준으로 서버 메모리에 보관
- 서버 재시작 시 초기화 (ADK 세션과 동일)
- `clear(thread_id)` 는 명시적 정리용으로 제공하되, 현재는 자동 호출 없음
