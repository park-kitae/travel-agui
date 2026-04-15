# User Preference Collection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 호텔/항공권 추천 요청 시 상세 정보 수집 전에 슬라이드업 패널로 취향을 먼저 수집하는 기능을 추가한다.

**Architecture:** 새 `USER_FAVORITE_REQUEST` AGUI 이벤트 타입을 추가하고, 백엔드의 `request_user_favorite` 툴이 이 이벤트를 발행한다. 프론트엔드는 이 이벤트를 수신하면 채팅 입력창 위 슬라이드업 패널을 노출하고, 사용자가 확인하면 마커 포함 메시지를 전송해 에이전트가 다음 단계(request_user_input → search)로 진행한다.

**Tech Stack:** Python (Google ADK, Pydantic, pytest), TypeScript (React, AG-UI)

---

## File Map

**신규 파일:**
- `backend/data/preferences.py` — 호텔/항공 취향 고정 옵션 데이터
- `backend/tools/favorite_tools.py` — `request_user_favorite` 툴 함수
- `frontend/src/components/FavoritePanel.tsx` — 슬라이드업 취향 수집 컴포넌트

**수정 파일:**
- `backend/models.py` — `UserFavoriteRequestEvent` 추가
- `backend/state/models.py` — `UserPreferences` dataclass 추가, `TravelState` 확장
- `backend/state/manager.py` — `request_user_favorite` 툴 결과 처리 추가
- `backend/converter.py` — `USER_FAVORITE_REQUEST` 이벤트 emit 추가
- `backend/agent.py` — `FunctionTool(request_user_favorite)` 추가, 프롬프트 업데이트
- `frontend/src/types/index.ts` — `FavoriteOptionDef`, `FavoriteRequest`, `UserPreferences` 타입 추가
- `frontend/src/hooks/useAGUIChat.ts` — `pendingFavoriteRequest` 상태, `submitFavorite` 함수 추가
- `frontend/src/App.tsx` — `FavoritePanel` 렌더링, `handleFavoriteSubmit` 추가
- `frontend/src/index.css` — 슬라이드업 애니메이션 CSS 추가

**테스트 파일:**
- `backend/tests/state/test_manager.py` — `request_user_favorite` 처리 테스트 추가
- `backend/tests/state/test_models.py` — `UserPreferences` 테스트 추가

---

## Task 1: 취향 옵션 데이터 파일 생성

**Files:**
- Create: `backend/data/preferences.py`

- [ ] **Step 1: 파일 생성**

```python
"""
data/preferences.py — 사용자 취향 수집을 위한 고정 옵션 데이터
"""
from typing import TypedDict


class OptionDef(TypedDict):
    type: str        # "radio" | "checkbox"
    label: str
    choices: list[str]


HOTEL_PREFERENCE_OPTIONS: dict[str, OptionDef] = {
    "hotel_grade": {
        "type": "radio",
        "label": "호텔 등급",
        "choices": ["2성", "3성", "4성", "5성"],
    },
    "hotel_type": {
        "type": "radio",
        "label": "숙소 유형",
        "choices": ["비즈니스", "리조트", "부티크", "게스트하우스"],
    },
    "amenities": {
        "type": "checkbox",
        "label": "편의시설",
        "choices": ["수영장", "조식포함", "주차", "피트니스", "반려동물 가능", "조기체크인"],
    },
}

FLIGHT_PREFERENCE_OPTIONS: dict[str, OptionDef] = {
    "seat_class": {
        "type": "radio",
        "label": "좌석 등급",
        "choices": ["이코노미", "비즈니스", "퍼스트"],
    },
    "seat_position": {
        "type": "radio",
        "label": "좌석 위치",
        "choices": ["창가", "복도", "무관"],
    },
    "meal_preference": {
        "type": "radio",
        "label": "기내식",
        "choices": ["일반식", "채식", "할랄", "무관"],
    },
    "airline_preference": {
        "type": "checkbox",
        "label": "선호 항공사",
        "choices": ["대한항공", "아시아나", "저비용항공사 무관"],
    },
}

PREFERENCE_OPTIONS: dict[str, dict[str, OptionDef]] = {
    "hotel_preference": HOTEL_PREFERENCE_OPTIONS,
    "flight_preference": FLIGHT_PREFERENCE_OPTIONS,
}
```

- [ ] **Step 2: `backend/data/__init__.py`에 export 추가**

`backend/data/__init__.py` 파일을 열거나 없으면 생성하고 다음을 추가한다:
```python
from .preferences import PREFERENCE_OPTIONS, HOTEL_PREFERENCE_OPTIONS, FLIGHT_PREFERENCE_OPTIONS
```

- [ ] **Step 3: 커밋**

```bash
cd backend
git add data/preferences.py data/__init__.py
git commit -m "feat: add preference options data for hotel and flight"
```

---

## Task 2: `UserPreferences` state 모델 추가

**Files:**
- Modify: `backend/state/models.py`
- Test: `backend/tests/state/test_models.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/state/test_models.py`를 열고 다음 테스트를 추가한다:

```python
from state.models import UserPreferences, TravelState


def test_user_preferences_defaults():
    prefs = UserPreferences()
    assert prefs.hotel_grade is None
    assert prefs.hotel_type is None
    assert prefs.amenities == ()
    assert prefs.seat_class is None
    assert prefs.seat_position is None
    assert prefs.meal_preference is None
    assert prefs.airline_preference == ()


def test_user_preferences_is_frozen():
    prefs = UserPreferences(hotel_grade="5성")
    try:
        prefs.hotel_grade = "3성"  # type: ignore
        assert False, "frozen dataclass should raise"
    except Exception:
        pass


def test_travel_state_has_user_preferences():
    state = TravelState()
    assert hasattr(state, "user_preferences")
    assert isinstance(state.user_preferences, UserPreferences)
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd backend
uv run pytest tests/state/test_models.py -v -k "user_preferences"
```

Expected: `AttributeError` 또는 `ImportError` (UserPreferences 미존재)

- [ ] **Step 3: `UserPreferences` 구현**

`backend/state/models.py`를 열고 기존 `TravelState` 위에 추가:

```python
@dataclass(frozen=True)
class UserPreferences:
    """사용자 서비스별 취향 (세션 내 1회 수집)."""
    # 호텔 취향
    hotel_grade: str | None = None
    hotel_type: str | None = None
    amenities: tuple[str, ...] = ()
    # 항공 취향
    seat_class: str | None = None
    seat_position: str | None = None
    meal_preference: str | None = None
    airline_preference: tuple[str, ...] = ()
```

그리고 `TravelState`에 필드 추가:

```python
@dataclass(frozen=True)
class TravelState:
    """thread_id 기준 세션 전체 state."""
    travel_context: TravelContext = field(default_factory=TravelContext)
    ui_context: UIContext = field(default_factory=UIContext)
    agent_status: AgentStatus = field(default_factory=AgentStatus)
    user_preferences: UserPreferences = field(default_factory=UserPreferences)
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd backend
uv run pytest tests/state/test_models.py -v -k "user_preferences"
```

Expected: PASSED (3 tests)

- [ ] **Step 5: 커밋**

```bash
git add backend/state/models.py backend/tests/state/test_models.py
git commit -m "feat: add UserPreferences dataclass to state models"
```

---

## Task 3: `UserFavoriteRequestEvent` 모델 추가

**Files:**
- Modify: `backend/models.py`

- [ ] **Step 1: `UserFavoriteRequestEvent` 추가**

`backend/models.py`를 열고 `UserInputRequestEvent` 아래에 추가:

```python
from pydantic import ConfigDict


class UserFavoriteRequestEvent(BaseModel):
    """사용자 취향 요청 이벤트 (AG-UI 확장)."""
    model_config = ConfigDict(populate_by_name=True)

    type: Literal["USER_FAVORITE_REQUEST"] = "USER_FAVORITE_REQUEST"
    request_id: str = Field(..., alias="requestId", description="요청 ID")
    favorite_type: str = Field(..., alias="favoriteType", description="취향 타입: hotel_preference | flight_preference")
    options: dict = Field(..., description="취향 옵션 정의 {field_name: {type, label, choices}}")
```

> **Note:** `ag_ui` encoder는 내부적으로 `model_dump_json(by_alias=True)`를 호출하므로 alias 직렬화가 지원된다. 별도 처리 없이 `encoder.encode(event)` 그대로 사용한다.

- [ ] **Step 2: import 확인 후 커밋**

```bash
cd backend
uv run python -c "from models import UserFavoriteRequestEvent; print('OK')"
```

Expected: `OK`

```bash
git add backend/models.py
git commit -m "feat: add UserFavoriteRequestEvent model"
```

---

## Task 4: `request_user_favorite` 툴 구현

**Files:**
- Create: `backend/tools/favorite_tools.py`
- Modify: `backend/tools/__init__.py`

- [ ] **Step 1: 툴 파일 생성**

```python
"""
tools/favorite_tools.py — 사용자 취향 수집 요청 툴
"""
from data.preferences import PREFERENCE_OPTIONS


def request_user_favorite(favorite_type: str, context: str = "") -> dict:
    """
    호텔 또는 항공편 예약 전 사용자 취향을 수집하기 위한 폼을 요청합니다.

    사용 시기:
    - 호텔 추천 요청 시 hotel_preference 미수집 상태
    - 항공편 추천 요청 시 flight_preference 미수집 상태

    Args:
        favorite_type: "hotel_preference" 또는 "flight_preference"
        context: 미사용 (인터페이스 일관성 유지용)

    Returns:
        {status: "user_favorite_required", favorite_type: ..., options: {...}}
    """
    options = PREFERENCE_OPTIONS.get(favorite_type, {})
    return {
        "status": "user_favorite_required",
        "favorite_type": favorite_type,
        "options": options,
    }
```

- [ ] **Step 2: import 확인**

```bash
cd backend
uv run python -c "from tools.favorite_tools import request_user_favorite; r = request_user_favorite('hotel_preference'); print(r['status'])"
```

Expected: `user_favorite_required`

- [ ] **Step 3: 커밋**

```bash
git add backend/tools/favorite_tools.py
git commit -m "feat: add request_user_favorite tool"
```

---

## Task 5: StateManager — `request_user_favorite` 처리

**Files:**
- Modify: `backend/state/manager.py`
- Test: `backend/tests/state/test_manager.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/state/test_manager.py` 끝에 추가:

```python
@pytest.mark.asyncio
async def test_apply_tool_result_request_user_favorite_yields_favorite_request(manager):
    result = {
        "status": "user_favorite_required",
        "favorite_type": "hotel_preference",
        "options": {
            "hotel_grade": {"type": "radio", "label": "호텔 등급", "choices": ["2성", "3성", "4성", "5성"]},
        },
    }
    events = [e async for e in manager.apply_tool_result("thread-20", "request_user_favorite", result)]
    assert len(events) == 1
    snap = events[0].snapshot
    assert snap["snapshot_type"] == "user_favorite_request"
    assert snap["_agui_event"] == "USER_FAVORITE_REQUEST"
    assert snap["favorite_type"] == "hotel_preference"
    assert "hotel_grade" in snap["options"]


@pytest.mark.asyncio
async def test_apply_tool_call_request_user_favorite_sets_awaiting_intent(manager):
    args = {"favorite_type": "hotel_preference"}
    events = [e async for e in manager.apply_tool_call("thread-21", "request_user_favorite", args)]
    assert len(events) == 1
    snap = events[0].snapshot
    assert snap["agent_status"]["current_intent"] == "awaiting_input"
    assert snap["agent_status"]["active_tool"] == "request_user_favorite"
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd backend
uv run pytest tests/state/test_manager.py -v -k "favorite"
```

Expected: FAILED

- [ ] **Step 3: `apply_tool_result` 수정**

`backend/state/manager.py`의 `apply_tool_result` 메서드에서 기존 `if tool_name == "request_user_input"` 블록 앞에 추가:

```python
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
```

- [ ] **Step 4: `apply_tool_call` 수정**

`backend/state/manager.py`의 `intent_map` dict에 `"request_user_favorite": "awaiting_input"` 추가:

```python
intent_map = {
    "search_hotels": "searching",
    "search_flights": "searching",
    "get_hotel_detail": "presenting_results",
    "get_travel_tips": "presenting_results",
    "request_user_favorite": "awaiting_input",   # 추가
}
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
cd backend
uv run pytest tests/state/test_manager.py -v -k "favorite"
```

Expected: PASSED (2 tests)

- [ ] **Step 6: 전체 테스트 통과 확인**

```bash
cd backend
uv run pytest tests/state/ -v
```

Expected: 모두 PASSED

- [ ] **Step 7: 커밋**

```bash
git add backend/state/manager.py backend/tests/state/test_manager.py
git commit -m "feat: handle request_user_favorite in StateManager"
```

---

## Task 6: Converter — `USER_FAVORITE_REQUEST` 이벤트 emit

**Files:**
- Modify: `backend/converter.py`

- [ ] **Step 1: import 추가**

`backend/converter.py` 상단 import에 추가:

```python
from models import UserInputRequestEvent, UserFavoriteRequestEvent
```

- [ ] **Step 2: `elif agui_event == "USER_FAVORITE_REQUEST":` 케이스 추가**

`backend/converter.py`의 `elif agui_event == "USER_INPUT_REQUEST":` 블록 아래에 추가:

```python
elif agui_event == "USER_FAVORITE_REQUEST":
    # 사용자 취향 요청 이벤트
    try:
        event_data = UserFavoriteRequestEvent(
            request_id=data.get("request_id", str(uuid.uuid4())),
            favorite_type=data.get("favorite_type", ""),
            options=data.get("options", {}),
        )
        yield encoder.encode(event_data)
    except Exception as e:
        logger.warning(f"UserFavoriteRequest 직렬화 실패: {e}")
```

> **Note:** 필드명은 snake_case(Python 필드명)를 사용한다. `UserInputRequestEvent` 패턴과 동일하다. `ag_ui` encoder는 `model_dump_json(by_alias=True)`를 호출하므로 JSON 출력은 자동으로 camelCase로 직렬화된다.

- [ ] **Step 3: Python import 오류 없음 확인**

```bash
cd backend
uv run python -c "from converter import a2a_to_agui_stream; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: 커밋**

```bash
git add backend/converter.py
git commit -m "feat: emit USER_FAVORITE_REQUEST event in converter"
```

---

## Task 7: Agent 프롬프트 & 툴 등록

**Files:**
- Modify: `backend/agent.py`

- [ ] **Step 1: import 추가**

`backend/agent.py` 상단에 추가:

```python
from tools.favorite_tools import request_user_favorite
```

- [ ] **Step 2: 취향 수집 규칙 프롬프트 추가**

`backend/agent.py`의 `instruction` 문자열에서 `━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n도구 사용 가이드` 섹션 **위에** 다음 섹션을 추가한다:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
취향 수집 우선 규칙 (최우선 적용)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
호텔 또는 항공편 추천/검색 요청이 들어오면 반드시 아래 순서를 따릅니다:

STEP 1 — 취향 수집 여부 확인:
- 대화 이력에 "[호텔 취향 수집 완료]" 마커가 없으면
  → request_user_favorite("hotel_preference") 호출 후 다음 단계 대기
- 대화 이력에 "[항공 취향 수집 완료]" 마커가 없으면
  → request_user_favorite("flight_preference") 호출 후 다음 단계 대기
- 마커가 이미 있으면 → STEP 2로 바로 진행 (재수집 절대 금지)

STEP 2 — 상세 정보 수집 및 검색:
- 취향 수집 완료 후 기존 도구 사용 가이드에 따라 request_user_input 또는 search 진행
- 취향 수집 후 "OO 취향을 바탕으로 검색하겠습니다" 안내 메시지 출력

취향 수집 완료 판단:
- 사용자 메시지에 "[호텔 취향 수집 완료]" 또는 "[항공 취향 수집 완료]" 마커 포함 시 완료 처리
- 마커가 있으면 선택 내용(비어있어도)에 관계없이 완료로 간주

시나리오 예시:
- "도쿄 호텔 추천해줘" (마커 없음)
  → request_user_favorite("hotel_preference")
  → (사용자 확인) → "도쿄 호텔 5성, 리조트, 수영장 [호텔 취향 수집 완료]"
  → request_user_input("hotel_booking_details", ...) 또는 search_hotels(...)

- "도쿄 호텔 추천해줘" (이미 "[호텔 취향 수집 완료]" 있음)
  → 즉시 request_user_input("hotel_booking_details", ...) 진행
```

- [ ] **Step 3: `FunctionTool(request_user_favorite)` 등록**

`backend/agent.py`의 `tools=[...]` 리스트에 추가:

```python
tools=[
    FunctionTool(request_user_favorite),   # 추가
    FunctionTool(request_user_input),
    FunctionTool(search_hotels),
    FunctionTool(get_hotel_detail),
    FunctionTool(search_flights),
    FunctionTool(get_travel_tips),
],
```

- [ ] **Step 4: import 오류 없음 확인**

```bash
cd backend
uv run python -c "from agent import create_travel_agent; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: 커밋**

```bash
git add backend/agent.py
git commit -m "feat: add request_user_favorite tool and preference collection prompt"
```

---

## Task 8: Frontend 타입 정의 추가

**Files:**
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: `AgentStatus` 타입에 `"awaiting_input"` 추가**

`frontend/src/types/index.ts`에서 `AgentStatus` 인터페이스를 찾아 `current_intent` 리터럴 유니언에 추가:

```typescript
export interface AgentStatus {
  current_intent: 'collecting_hotel_params' | 'collecting_flight_params' | 'searching' | 'presenting_results' | 'awaiting_input' | 'idle'
  missing_fields: string[]
  active_tool: string | null
}
```

- [ ] **Step 2: AGUIEventType에 `USER_FAVORITE_REQUEST` 추가**

`frontend/src/types/index.ts`에서 `AGUIEventType`을 찾아 `'USER_FAVORITE_REQUEST'`를 추가:

```typescript
export type AGUIEventType =
  | 'RUN_STARTED'
  | 'RUN_FINISHED'
  | 'RUN_ERROR'
  | 'STEP_STARTED'
  | 'STEP_FINISHED'
  | 'TEXT_MESSAGE_START'
  | 'TEXT_MESSAGE_CHUNK'
  | 'TEXT_MESSAGE_END'
  | 'TOOL_CALL_START'
  | 'TOOL_CALL_ARGS'
  | 'TOOL_CALL_END'
  | 'STATE_SNAPSHOT'
  | 'USER_INPUT_REQUEST'
  | 'USER_FAVORITE_REQUEST'   // 추가
```

- [ ] **Step 2: 취향 관련 타입 추가**

`UserInputRequestEvent` 인터페이스 아래에 추가:

```typescript
// 취향 옵션 정의
export interface FavoriteOptionDef {
  type: 'radio' | 'checkbox'
  label: string
  choices: string[]
}

// 취향 요청 이벤트
export interface UserFavoriteRequestEvent extends AGUIEvent {
  type: 'USER_FAVORITE_REQUEST'
  requestId: string
  favoriteType: 'hotel_preference' | 'flight_preference'
  options: Record<string, FavoriteOptionDef>
}

// 취향 요청 상태 (훅에서 관리)
export interface FavoriteRequest {
  requestId: string
  favoriteType: 'hotel_preference' | 'flight_preference'
  options: Record<string, FavoriteOptionDef>
  submitted: boolean
}

// 사용자 취향 (AgentState 일부)
export interface UserPreferences {
  hotel_grade?: string
  hotel_type?: string
  amenities?: string[]
  seat_class?: string
  seat_position?: string
  meal_preference?: string
  airline_preference?: string[]
}
```

- [ ] **Step 3: `AgentState`에 `user_preferences` 추가**

기존 `AgentState` 인터페이스를 찾아 `user_preferences` 필드 추가:

```typescript
export interface AgentState {
  travel_context: TravelContext
  agent_status: AgentStatus
  user_preferences: UserPreferences   // 추가
  last_updated: number
}
```

- [ ] **Step 4: TypeScript 타입 오류 없음 확인**

```bash
cd frontend
npm run build 2>&1 | head -30
```

Expected: 오류 없이 빌드 성공 (또는 타입 오류 없음)

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/types/index.ts
git commit -m "feat: add USER_FAVORITE_REQUEST types to frontend"
```

---

## Task 9: `useAGUIChat` 훅 확장

**Files:**
- Modify: `frontend/src/hooks/useAGUIChat.ts`

- [ ] **Step 1: `pendingFavoriteRequest` 상태 추가**

`useAGUIChat.ts`에서 기존 `useState` 선언들 아래에 추가:

```typescript
const [pendingFavoriteRequest, setPendingFavoriteRequest] = useState<FavoriteRequest | null>(null)
```

그리고 import에 `FavoriteRequest` 추가:

```typescript
import {
  ChatMessage,
  RunAgentInput,
  AGUIEvent,
  ToolSnapshot,
  FormField,
  AgentState,
  UIContext,
  ClientState,
  AgentStateSnapshot,
  FavoriteRequest,   // 추가
} from '../types'
```

- [ ] **Step 2: `submitFavorite` 함수 추가**

`markFormSubmitted` 함수 아래에 추가:

```typescript
const submitFavorite = useCallback((
  favoriteType: 'hotel_preference' | 'flight_preference',
  selections: Record<string, string | string[]>
) => {
  // 선택 내용을 자연어 메시지로 조합
  const hasSelections = Object.values(selections).some(v =>
    Array.isArray(v) ? v.length > 0 : Boolean(v)
  )

  const marker = favoriteType === 'hotel_preference'
    ? '[호텔 취향 수집 완료]'
    : '[항공 취향 수집 완료]'

  let message: string
  if (!hasSelections) {
    message = `취향 없이 진행합니다 ${marker}`
  } else {
    const parts: string[] = []
    Object.entries(selections).forEach(([_key, value]) => {
      if (Array.isArray(value) && value.length > 0) {
        parts.push(value.join('·'))
      } else if (typeof value === 'string' && value) {
        parts.push(value)
      }
    })
    const serviceLabel = favoriteType === 'hotel_preference' ? '호텔' : '항공'
    message = `${serviceLabel} 취향: ${parts.join(', ')} ${marker}`
  }

  setPendingFavoriteRequest(null)
  sendMessage(message)
}, [sendMessage])
```

- [ ] **Step 3: `clearMessages`에 `setPendingFavoriteRequest(null)` 추가**

기존 `clearMessages` 내부에 추가:

```typescript
const clearMessages = useCallback(() => {
  threadIdRef.current = generateId()
  setMessages([])
  setError(null)
  setAgentState(null)
  setUiContext(DEFAULT_UI_CONTEXT)
  setPendingFavoriteRequest(null)   // 추가
}, [])
```

- [ ] **Step 4: `handleEvent`에 `USER_FAVORITE_REQUEST` case 추가**

`handleEvent` 함수의 switch 문에 추가 (파라미터에 `setPendingFavoriteRequest` 추가):

`handleEvent` 함수 시그니처 수정:
```typescript
function handleEvent(
  event: AGUIEvent,
  assistantId: string,
  toolArgsBuffer: Record<string, string>,
  updateMessage: (id: string, fn: (m: ChatMessage) => ChatMessage) => void,
  setAgentState: (fn: (prev: AgentState | null) => AgentState) => void,
  setPendingFavoriteRequest: (req: FavoriteRequest | null) => void,   // 추가
) {
```

switch 문 끝에 case 추가:
```typescript
case 'USER_FAVORITE_REQUEST': {
  const requestId = event.requestId as string
  const favoriteType = event.favoriteType as 'hotel_preference' | 'flight_preference'
  const options = event.options as Record<string, import('../types').FavoriteOptionDef>
  setPendingFavoriteRequest({
    requestId,
    favoriteType,
    options,
    submitted: false,
  })
  break
}
```

**기존 `handleEvent` 호출부(약 line 136)를 찾아 6번째 인자를 추가한다:**
```typescript
// 변경 전:
handleEvent(event, assistantId, toolArgsBuffer, updateMessage, setAgentState)
// 변경 후:
handleEvent(event, assistantId, toolArgsBuffer, updateMessage, setAgentState, setPendingFavoriteRequest)
```

- [ ] **Step 5: `return` 객체에 추가**

```typescript
return {
  messages,
  isRunning,
  error,
  agentState,
  uiContext,
  updateUiContext,
  pendingFavoriteRequest,   // 추가
  sendMessage,
  interruptAndSend,
  stopStreaming,
  clearMessages,
  markFormSubmitted,
  submitFavorite,           // 추가
}
```

- [ ] **Step 6: TypeScript 오류 없음 확인**

```bash
cd frontend
npm run build 2>&1 | head -30
```

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/hooks/useAGUIChat.ts
git commit -m "feat: add pendingFavoriteRequest state and submitFavorite to useAGUIChat"
```

---

## Task 10: `FavoritePanel` 컴포넌트 & CSS

**Files:**
- Create: `frontend/src/components/FavoritePanel.tsx`
- Modify: `frontend/src/index.css`

- [ ] **Step 1: `FavoritePanel.tsx` 생성**

```tsx
import { useState } from 'react'
import { FavoriteRequest, FavoriteOptionDef } from '../types'

interface Props {
  request: FavoriteRequest
  onSubmit: (favoriteType: 'hotel_preference' | 'flight_preference', selections: Record<string, string | string[]>) => void
  disabled?: boolean
}

export function FavoritePanel({ request, onSubmit, disabled }: Props) {
  const [selections, setSelections] = useState<Record<string, string | string[]>>({})

  const handleRadioChange = (fieldName: string, value: string) => {
    setSelections(prev => ({ ...prev, [fieldName]: value }))
  }

  const handleCheckboxToggle = (fieldName: string, choice: string) => {
    setSelections(prev => {
      const current = (prev[fieldName] as string[] | undefined) ?? []
      const next = current.includes(choice)
        ? current.filter(c => c !== choice)
        : [...current, choice]
      return { ...prev, [fieldName]: next }
    })
  }

  const handleConfirm = () => {
    if (!disabled) {
      onSubmit(request.favoriteType, selections)
    }
  }

  const title = request.favoriteType === 'hotel_preference' ? '호텔 취향' : '항공 취향'

  return (
    <div className="favorite-panel">
      <div className="favorite-panel-header">
        <span className="favorite-panel-title">{title} 선택</span>
        <span className="favorite-panel-hint">선택 사항 · 원하는 항목만 골라주세요</span>
      </div>
      <div className="favorite-panel-body">
        {Object.entries(request.options).map(([fieldName, optDef]: [string, FavoriteOptionDef]) => (
          <div key={fieldName} className="favorite-field">
            <div className="favorite-field-label">{optDef.label}</div>
            <div className="favorite-choices">
              {optDef.type === 'radio' && optDef.choices.map(choice => {
                const selected = selections[fieldName] === choice
                return (
                  <button
                    key={choice}
                    type="button"
                    className={`favorite-chip ${selected ? 'selected' : ''}`}
                    onClick={() => handleRadioChange(fieldName, selected ? '' : choice)}
                    disabled={disabled}
                  >
                    {choice}
                  </button>
                )
              })}
              {optDef.type === 'checkbox' && optDef.choices.map(choice => {
                const current = (selections[fieldName] as string[] | undefined) ?? []
                const selected = current.includes(choice)
                return (
                  <button
                    key={choice}
                    type="button"
                    className={`favorite-chip ${selected ? 'selected' : ''}`}
                    onClick={() => handleCheckboxToggle(fieldName, choice)}
                    disabled={disabled}
                  >
                    {choice}
                  </button>
                )
              })}
            </div>
          </div>
        ))}
      </div>
      <div className="favorite-panel-footer">
        <button
          type="button"
          className="favorite-confirm-btn"
          onClick={handleConfirm}
          disabled={disabled}
        >
          확인
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: `index.css`에 스타일 추가**

`frontend/src/index.css` 끝에 추가:

```css
/* ── FavoritePanel (슬라이드업) ─────────────── */
.favorite-panel {
  background: var(--white);
  border-top: 2px solid var(--gold);
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
  box-shadow: 0 -4px 24px rgba(0,0,0,0.12);
  padding: 20px 20px 12px;
  animation: slide-up 0.3s ease;
  max-height: 55vh;
  overflow-y: auto;
}

@keyframes slide-up {
  from { transform: translateY(100%); opacity: 0; }
  to   { transform: translateY(0);   opacity: 1; }
}

.favorite-panel-header {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 16px;
}
.favorite-panel-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--navy);
}
.favorite-panel-hint {
  font-size: 12px;
  color: var(--text-muted);
}

.favorite-panel-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.favorite-field {}
.favorite-field-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 8px;
}
.favorite-choices {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.favorite-chip {
  padding: 6px 14px;
  border-radius: 20px;
  border: 1.5px solid var(--gray-200);
  background: var(--white);
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
}
.favorite-chip:hover:not(:disabled) {
  border-color: var(--gold);
  color: var(--navy);
}
.favorite-chip.selected {
  background: var(--navy);
  border-color: var(--navy);
  color: var(--white);
}
.favorite-chip:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.favorite-panel-footer {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.favorite-confirm-btn {
  background: var(--gold);
  color: var(--navy);
  border: none;
  border-radius: var(--radius-md);
  padding: 10px 28px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.2s;
}
.favorite-confirm-btn:hover:not(:disabled) {
  background: var(--gold-light);
}
.favorite-confirm-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
```

- [ ] **Step 3: TypeScript 오류 없음 확인**

```bash
cd frontend
npm run build 2>&1 | head -30
```

- [ ] **Step 4: 커밋**

```bash
git add frontend/src/components/FavoritePanel.tsx frontend/src/index.css
git commit -m "feat: add FavoritePanel slide-up component with CSS animation"
```

---

## Task 11: `App.tsx` 연결

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: import 추가**

`App.tsx` 상단에 추가:

```typescript
import { FavoritePanel } from './components/FavoritePanel'
```

- [ ] **Step 2: `useAGUIChat`에서 신규 값 구조분해**

기존:
```typescript
const { messages, isRunning, error, agentState, uiContext, updateUiContext, sendMessage, interruptAndSend, stopStreaming, clearMessages, markFormSubmitted } = useAGUIChat()
```

변경:
```typescript
const {
  messages, isRunning, error, agentState, uiContext, updateUiContext,
  pendingFavoriteRequest,
  sendMessage, interruptAndSend, stopStreaming, clearMessages,
  markFormSubmitted, submitFavorite,
} = useAGUIChat()
```

- [ ] **Step 3: `handleFavoriteSubmit` 핸들러 추가**

`handleFormSubmit` 함수 아래에 추가:

```typescript
const handleFavoriteSubmit = (selections: Record<string, string | string[]>) => {
  if (!pendingFavoriteRequest || isRunning) return
  submitFavorite(pendingFavoriteRequest.favoriteType, selections)
}
```

- [ ] **Step 4: JSX에 `FavoritePanel` 렌더링 추가**

`<footer className="input-area">` 바로 위에 추가:

```tsx
{/* 취향 수집 슬라이드업 패널 */}
{pendingFavoriteRequest && !pendingFavoriteRequest.submitted && (
  <FavoritePanel
    request={pendingFavoriteRequest}
    onSubmit={handleFavoriteSubmit}
    disabled={isRunning}
  />
)}
```

- [ ] **Step 5: 패널 열린 동안 textarea & 전송 버튼 비활성화**

`<textarea>` 의 `disabled` prop 수정:

```tsx
disabled={isRunning || Boolean(pendingFavoriteRequest && !pendingFavoriteRequest.submitted)}
```

`<button className={...send-btn...}>` 의 `disabled` prop 수정:

```tsx
disabled={(!isRunning && !input.trim()) || Boolean(pendingFavoriteRequest && !pendingFavoriteRequest.submitted)}
```

- [ ] **Step 6: TypeScript 오류 없음 확인**

```bash
cd frontend
npm run build 2>&1 | head -30
```

Expected: 오류 없이 빌드 성공

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/App.tsx
git commit -m "feat: wire FavoritePanel into App — slide-up on USER_FAVORITE_REQUEST"
```

---

## Task 12: 전체 테스트 & 최종 검증

- [ ] **Step 1: 백엔드 전체 테스트**

```bash
cd backend
uv run pytest tests/ -v
```

Expected: 모두 PASSED

- [ ] **Step 2: 프론트엔드 타입 체크**

```bash
cd frontend
npx tsc --noEmit
```

Expected: 오류 없음

- [ ] **Step 3: 서버 기동 확인**

```bash
# 프로젝트 루트에서
./start.sh
```

브라우저에서 `http://localhost:5173` 열고:
1. "도쿄 호텔 추천해줘" 입력
2. 슬라이드업 패널 등장 확인 (호텔 취향 선택)
3. 아무것도 선택하지 않고 "확인" 클릭 → 패널 닫히고 취향 마커 메시지 전송 확인
4. 이어서 날짜/인원 폼(request_user_input) 등장 확인
5. 두 번째로 "도쿄 호텔 추천해줘" 입력 → 취향 패널 미노출, 바로 폼으로 진행 확인

- [ ] **Step 4: 최종 커밋 (필요 시)**

```bash
git add -A
git commit -m "chore: final integration — user preference collection feature complete"
```
