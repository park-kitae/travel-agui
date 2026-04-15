# User Preference Collection Feature Design

**Date:** 2026-04-15  
**Status:** Approved  
**Approach:** New `USER_FAVORITE_REQUEST` event type (방식 1)

---

## Overview

호텔 또는 항공권 추천 요청 시, 상세 정보(날짜/인원) 수집 이전에 먼저 사용자 취향을 수집한다. 취향은 채팅 리스트가 아닌 입력창 위 슬라이드업 패널로 수집하며, 모든 항목은 선택 사항(optional)이다.

---

## 1. Data Layer

### `backend/data/preferences.py` (신규)

고정 취향 옵션 데이터를 정의한다.

**호텔 취향 (`hotel_preference`):**
- `hotel_grade` (radio): 2성, 3성, 4성, 5성
- `hotel_type` (radio): 비즈니스, 리조트, 부티크, 게스트하우스
- `amenities` (checkbox): 수영장, 조식포함, 주차, 피트니스, 반려동물 가능, 조기체크인

**항공 취향 (`flight_preference`):**
- `seat_class` (radio): 이코노미, 비즈니스, 퍼스트
- `seat_position` (radio): 창가, 복도, 무관
- `meal_preference` (radio): 일반식, 채식, 할랄, 무관
- `airline_preference` (checkbox): 대한항공, 아시아나, 저비용항공사 무관

---

## 2. Backend Tool

### `backend/tools/favorite_tools.py` (신규)

```python
def request_user_favorite(favorite_type: str, context: str = "") -> dict:
    """
    호텔 또는 항공편 취향 정보를 사용자에게 요청한다.
    favorite_type: "hotel_preference" | "flight_preference"
    반환값의 status: "user_favorite_required"
    """
```

- `favorite_type`에 따라 `preferences.py`에서 옵션 목록 로드
- `{status: "user_favorite_required", favorite_type: ..., options: {...}}` 반환
- executor가 `_agui_event: "USER_FAVORITE_REQUEST"`로 래핑하여 스트리밍

---

## 3. State Model

### `backend/state/models.py` 확장

```python
@dataclass(frozen=True)
class UserPreferences:
    # 호텔 취향
    hotel_grade: str | None = None
    hotel_type: str | None = None
    amenities: tuple[str, ...] = ()
    # 항공 취향
    seat_class: str | None = None
    seat_position: str | None = None
    meal_preference: str | None = None
    airline_preference: tuple[str, ...] = ()

@dataclass(frozen=True)
class TravelState:
    travel_context: TravelContext = field(default_factory=TravelContext)
    ui_context: UIContext = field(default_factory=UIContext)
    agent_status: AgentStatus = field(default_factory=AgentStatus)
    user_preferences: UserPreferences = field(default_factory=UserPreferences)  # 추가
```

---

## 4. Event Pipeline

### `backend/models.py` 확장

```python
class UserFavoriteRequestEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: str = "USER_FAVORITE_REQUEST"
    request_id: str = Field(alias="requestId")
    favorite_type: str = Field(alias="favoriteType")  # "hotel_preference" | "flight_preference"
    options: dict       # {field_name: {type: "radio"|"checkbox", label, choices: list[str]}}
```

- Pydantic `alias`를 통해 snake_case(Python) → camelCase(JSON/Frontend) 변환을 `models.py`에서 일괄 처리한다.
- `converter.py`는 변환 없이 `UserFavoriteRequestEvent` 인스턴스를 생성하고 `encoder.encode()`에 위임한다.
- `request_id`는 `converter.py`에서 `str(uuid.uuid4())`로 생성한다 (`USER_INPUT_REQUEST`와 동일한 패턴).

### `backend/converter.py` 확장

`_agui_event == "USER_FAVORITE_REQUEST"` 감지 → `UserFavoriteRequestEvent` emit

### 이벤트 구조 예시

```json
{
  "type": "USER_FAVORITE_REQUEST",
  "requestId": "uuid-1234",
  "favoriteType": "hotel_preference",
  "options": {
    "hotel_grade": {
      "type": "radio",
      "label": "호텔 등급",
      "choices": ["2성", "3성", "4성", "5성"]
    },
    "hotel_type": {
      "type": "radio",
      "label": "숙소 유형",
      "choices": ["비즈니스", "리조트", "부티크", "게스트하우스"]
    },
    "amenities": {
      "type": "checkbox",
      "label": "편의시설",
      "choices": ["수영장", "조식포함", "주차", "피트니스", "반려동물 가능", "조기체크인"]
    }
  }
}
```

---

## 5. Agent Prompt

### `backend/agent.py` 프롬프트 변경

**취향 수집 우선 규칙 추가:**

```
취향 수집 우선 규칙:
- 호텔 추천 요청 시:
  → state 메시지에 "[호텔 취향 수집 완료]" 마커가 없으면 request_user_favorite("hotel_preference") 먼저 호출
  → 마커가 있으면 (취향 내용 불문) 재수집 없이 바로 request_user_input 또는 search로 진행
- 항공편 추천 요청 시:
  → state 메시지에 "[항공 취향 수집 완료]" 마커가 없으면 request_user_favorite("flight_preference") 먼저 호출
  → 마커가 있으면 재수집 없이 다음 단계로 진행
- 취향 수집 후 → "OO 취향을 바탕으로 검색하겠습니다" 안내 후 다음 단계 진행
```

**"수집 완료" 판단 기준:**
- 사용자가 FavoritePanel에서 "확인" 버튼을 클릭하면 프론트엔드가 아래 형식의 메시지를 sendMessage로 전송:
  - 선택 있음: "호텔 취향: 5성, 리조트, 수영장·조식포함 [호텔 취향 수집 완료]"
  - 선택 없음: "취향 없이 진행합니다 [호텔 취향 수집 완료]"
- 에이전트는 메시지에 마커가 포함되어 있으면 해당 서비스의 취향을 "수집 완료"로 간주한다.
- 이 방식으로 빈 제출(all-None)과 미수집을 명확히 구분한다.

**플로우:**
1. 호텔/항공편 추천 요청
2. 수집 완료 마커 없음 → `request_user_favorite` 호출 → 슬라이드업 패널 노출
3. 사용자가 확인 버튼 클릭 (선택 여부 무관) → 마커 포함 메시지 전송 → 패널 닫힘
4. `request_user_input` 호출 → 날짜/인원 폼 노출 (기존 흐름)
5. `search_hotels` / `search_flights` 호출

---

## 6. Frontend

### `frontend/src/types/index.ts` 확장

```typescript
// 이벤트 타입 추가
type AGUIEventType = ... | 'USER_FAVORITE_REQUEST'

// 취향 옵션
interface FavoriteOptionDef {
  type: 'radio' | 'checkbox'
  label: string
  choices: string[]
}

// 취향 요청 상태
interface FavoriteRequest {
  requestId: string
  favoriteType: 'hotel_preference' | 'flight_preference'
  options: Record<string, FavoriteOptionDef>
  submitted: boolean
}

// 사용자 취향 state
interface UserPreferences {
  hotel_grade?: string
  hotel_type?: string
  amenities?: string[]
  seat_class?: string
  seat_position?: string
  meal_preference?: string
  airline_preference?: string[]
}

// AgentState에 추가
interface AgentState {
  travel_context: TravelContext
  agent_status: AgentStatus
  user_preferences: UserPreferences  // 추가
  last_updated: number
}
```

### `frontend/src/hooks/useAGUIChat.ts` 확장

- `pendingFavoriteRequest: FavoriteRequest | null` state 추가
- `handleEvent`에 `USER_FAVORITE_REQUEST` case 추가
- `submitFavorite(data: Record<string, string | string[]>)` 함수:
  - 선택 내용을 자연어 문장으로 조합
  - `sendMessage` 호출
  - `pendingFavoriteRequest` 초기화
- `clearMessages` 시 `pendingFavoriteRequest` 리셋

### `frontend/src/components/FavoritePanel.tsx` (신규)

- 위치: `<footer>` 위에 렌더링
- 애니메이션: `transform: translateY(100%) → translateY(0)`, `transition: 0.3s ease`
- radio 항목: 버튼 그룹 단일 선택 UI
- checkbox 항목: 칩(chip) 형태 다중 선택 UI
- 확인 버튼: 선택 없어도 항상 활성화 (optional)
- 확인 클릭 시 전송 메시지 형식:
  - 선택 있음: `"호텔 취향: {grade}, {type}, {amenities 목록} [호텔 취향 수집 완료]"`
  - 선택 없음: `"취향 없이 진행합니다 [호텔 취향 수집 완료]"` (항공은 `[항공 취향 수집 완료]`)
- 패널에는 별도 닫기/건너뛰기 버튼 없음 — "확인" 버튼이 유일한 탈출구 (선택 없이 눌러도 됨)

### `frontend/src/App.tsx` 수정

- `pendingFavoriteRequest` 있으면 `<FavoritePanel>` 렌더링 (footer 위)
- `handleFavoriteSubmit` 핸들러 추가
- 패널 열린 동안 textarea & 전송 버튼 `disabled`

---

## 7. Constraints & Non-Goals

- 취향은 세션 내 서비스별 1회만 수집 (호텔 취향, 항공 취향 각각)
- 취향 항목은 모두 optional — 아무것도 선택 안 해도 진행 가능
- 실제 검색 필터링에 취향을 적용하는 것은 이번 범위 외 (에이전트 응답 시 참고 안내 용도)
- 기존 `USER_INPUT_REQUEST` 플로우 변경 없음
