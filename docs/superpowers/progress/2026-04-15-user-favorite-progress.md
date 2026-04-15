# User Preference Collection Feature — Progress Report

**Date:** 2026-04-15  
**Branch:** `claude/cool-torvalds`  
**Status:** Tasks 1–9 Complete ✅ | Tasks 10–12 Pending

---

## Overview

사용자 취향(호텔/항공) 수집 기능 구현 중. 슬라이드업 패널로 선택 사항 취향을 수집한 후 상세 정보(날짜/인원) 폼으로 진행하는 UX.

**Architecture:**
- Backend: `request_user_favorite` 툴 → `USER_FAVORITE_REQUEST` AG-UI 이벤트 emit
- Frontend: 슬라이드업 `FavoritePanel` 컴포넌트 → 마커 메시지로 취향 제출
- State: `UserPreferences` 데이터클래스 + marker-based completion tracking

---

## Completed Tasks (1–9)

### ✅ Task 1: Preference Options Data

**Files:** `backend/data/preferences.py` (생성)

**내용:**
- `HOTEL_PREFERENCE_OPTIONS`: 호텔 등급(radio), 숙소 유형(radio), 편의시설(checkbox)
- `FLIGHT_PREFERENCE_OPTIONS`: 좌석 등급(radio), 좌석 위치(radio), 식사 선호(radio), 항공사(checkbox)
- `PREFERENCE_OPTIONS` dict로 통합

**Commit:** `e6e4c02 feat: add preference options data for hotel and flight`

---

### ✅ Task 2: `UserPreferences` State Model

**Files:** `backend/state/models.py` (수정)

**내용:**
```python
@dataclass(frozen=True)
class UserPreferences:
    hotel_grade: str | None = None
    hotel_type: str | None = None
    amenities: tuple[str, ...] = ()
    seat_class: str | None = None
    seat_position: str | None = None
    meal_preference: str | None = None
    airline_preference: tuple[str, ...] = ()

# TravelState에 user_preferences 필드 추가
```

**Commit:** `2b98f30 feat: add UserPreferences dataclass to state models`

---

### ✅ Task 3: `UserFavoriteRequestEvent` Pydantic Model

**Files:** `backend/models.py` (수정)

**내용:**
```python
class UserFavoriteRequestEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    type: Literal["USER_FAVORITE_REQUEST"] = "USER_FAVORITE_REQUEST"
    request_id: str = Field(..., alias="requestId")
    favorite_type: str = Field(..., alias="favoriteType")
    options: dict = Field(...)
```

**Key Point:** Pydantic `Field(alias=...)` + `ag_ui` encoder의 `model_dump_json(by_alias=True)` 자동 처리

**Commit:** `e179cf1 feat: add UserFavoriteRequestEvent model`

---

### ✅ Task 4: `request_user_favorite` Tool

**Files:** `backend/tools/favorite_tools.py` (생성)

**내용:**
```python
def request_user_favorite(favorite_type: str, context: str = "") -> dict:
    options = PREFERENCE_OPTIONS.get(favorite_type, {})
    return {
        "status": "user_favorite_required",
        "favorite_type": favorite_type,
        "options": options,
    }
```

**Commit:** `0d5b76c feat: add request_user_favorite tool`

---

### ✅ Task 5: StateManager — Tool Result & Call Handling

**Files:** `backend/state/manager.py` (수정)

**내용:**
- `apply_tool_result()`: `request_user_favorite` 감지 → `USER_FAVORITE_REQUEST` snapshot emit
- `apply_tool_call()`: `intent_map`에 `"request_user_favorite": "awaiting_input"` 추가

**Commit:** `92bf0c5 feat: handle request_user_favorite in StateManager`

---

### ✅ Task 6: Converter — AG-UI Event Emission

**Files:** `backend/converter.py` (수정)

**내용:**
```python
elif agui_event == "USER_FAVORITE_REQUEST":
    event_data = UserFavoriteRequestEvent(
        request_id=data.get("request_id", str(uuid.uuid4())),
        favorite_type=data.get("favorite_type", ""),
        options=data.get("options", {}),
    )
    yield encoder.encode(event_data)
```

**Commit:** `1947635 feat: emit USER_FAVORITE_REQUEST event in converter`

---

### ✅ Task 7: Agent Prompt & Tool Registration

**Files:** `backend/agent.py` (수정)

**내용:**
- Import: `from tools.favorite_tools import request_user_favorite`
- Tool 등록: `tools=[FunctionTool(request_user_favorite), ...]`
- 프롬프트 추가: "취향 수집 우선 규칙" 섹션
  - `request_user_favorite("hotel_preference")` / `request_user_favorite("flight_preference")`
  - 마커 기반 완료 추적: `[호텔 취향 수집 완료]` / `[항공 취향 수집 완료]`

**Commit:** `f1c8e05 feat: add request_user_favorite tool and preference collection prompt`

---

### ✅ Task 8: Frontend Type Definitions

**Files:** `frontend/src/types/index.ts` (수정)

**내용:**
- `AGUIEventType`에 `'USER_FAVORITE_REQUEST'` 추가
- `AgentStatus.current_intent`에 `'awaiting_input'` 추가
- `FavoriteOptionDef`, `UserFavoriteRequestEvent`, `FavoriteRequest`, `UserPreferences` 인터페이스 정의
- `AgentState`에 `user_preferences: UserPreferences` 추가

**Commit:** `dc78933 feat: add USER_FAVORITE_REQUEST types to frontend`

---

### ✅ Task 9: `useAGUIChat` Hook Extension

**Files:** `frontend/src/hooks/useAGUIChat.ts` (수정)

**내용:**
- State: `pendingFavoriteRequest: FavoriteRequest | null`
- Function: `submitFavorite(favoriteType, selections)` — 마커 메시지 생성 & 전송
- Handler: `handleEvent` switch에 `'USER_FAVORITE_REQUEST'` case 추가
- Return: `pendingFavoriteRequest`, `submitFavorite` export

**마커 메시지 형식:**
- 선택 있음: `"호텔 취향: 5성, 리조트, 수영장 [호텔 취향 수집 완료]"`
- 선택 없음: `"취향 없이 진행합니다 [호텔 취향 수집 완료]"`

**Commit:** `c521050 feat: add pendingFavoriteRequest state and submitFavorite to useAGUIChat`

---

## Pending Tasks (10–12)

### ⏳ Task 10: `FavoritePanel` 컴포넌트 & CSS

**Files:**
- Create: `frontend/src/components/FavoritePanel.tsx`
- Modify: `frontend/src/index.css`

**Deliverables:**
- React 컴포넌트: radio button groups (단일 선택) + chip-style checkboxes (다중 선택)
- "확인" 버튼: 항상 활성화 (optional 필드이므로)
- CSS: slide-up 애니메이션 (`translateY(100%) → 0`), 0.3s ease

**Status:** 준비됨 (계획 상세함)

---

### ⏳ Task 11: `App.tsx` 연결

**Files:**
- Modify: `frontend/src/App.tsx`

**Deliverables:**
- `FavoritePanel` import & 렌더링 (`<footer>` 위에)
- `handleFavoriteSubmit` 핸들러 추가
- `<textarea>` & send button disabled 조건 수정: `Boolean(pendingFavoriteRequest && !pendingFavoriteRequest.submitted)`

**Status:** 준비됨

---

### ⏳ Task 12: 전체 테스트 & 최종 검증

**Checklist:**
- [ ] Backend pytest: `uv run pytest tests/ -v`
- [ ] Frontend tsc: `npx tsc --noEmit`
- [ ] Manual browser test:
  1. "도쿄 호텔 추천해줘" → 슬라이드업 패널 노출 ✓
  2. 선택 없이 "확인" → 마커 메시지 전송 ✓
  3. 날짜/인원 폼 등장 ✓
  4. 두 번째 "도쿄 호텔 추천해줘" → 패널 스킵, 바로 폼 ✓
- [ ] Final commit: `chore: final integration — user preference collection feature complete`

**Status:** 준비됨

---

## Key Implementation Details

### 마커 기반 취향 완료 추적

**Why:** 상태 동기화 복잡도 ↓, 명확한 명시적 완료 신호 ↑

**Flow:**
```
1. "도쿄 호텔 추천" (마커 없음)
   ↓
2. Agent: request_user_favorite("hotel_preference")
   ↓
3. Frontend: USER_FAVORITE_REQUEST 수신 → FavoritePanel 렌더
   ↓
4. User: 선택 후 "확인" 클릭
   ↓
5. Frontend: "호텔 취향: ... [호텔 취향 수집 완료]" 전송
   ↓
6. Agent: 메시지 내 마커 감지 → 재수집 금지, 다음 단계 진행
```

### Pydantic Alias 처리

- Python: snake_case (`request_id`, `favorite_type`)
- JSON: camelCase (`requestId`, `favoriteType`)
- 처리 위치: `UserFavoriteRequestEvent` 모델의 `Field(alias=...)`
- 직렬화: `ag_ui` encoder가 내부적으로 `model_dump_json(by_alias=True)` 호출

---

## Test Coverage

**Backend (모두 PASSED):**
- Task 2: `UserPreferences` dataclass (3 tests)
- Task 5: StateManager `request_user_favorite` (2 tests)
- Task 6–7: Tool & Agent integration (automatic via existing test suite)

**Frontend:**
- Task 8: TypeScript build `npm run build` (타입 오류 없음)
- Task 9: useAGUIChat hook TypeScript check (완료)

**End-to-End (Task 12에서 수행):**
- Browser: Favorite panel 슬라이드업, 선택, 제출, 마커 메시지 확인
- Flow: Hotel → Favorite → Input → Search 완전 순환 테스트

---

## Git History

```
c521050 feat: add pendingFavoriteRequest state and submitFavorite to useAGUIChat
dc78933 feat: add USER_FAVORITE_REQUEST types to frontend
f1c8e05 feat: add request_user_favorite tool and preference collection prompt
1947635 feat: emit USER_FAVORITE_REQUEST event in converter
92bf0c5 feat: handle request_user_favorite in StateManager
0d5b76c feat: add request_user_favorite tool
e179cf1 feat: add UserFavoriteRequestEvent model
2b98f30 feat: add UserPreferences dataclass to state models
e6e4c02 feat: add preference options data for hotel and flight
0c9461a docs: add user-favorite implementation plan
```

---

## Design Decisions & Trade-offs

| 항목 | 결정 | 이유 |
|------|------|------|
| 취향 필드 | Optional (모두 선택 사항) | 사용자 자유도 ↑, 빠른 진행 가능 |
| UI 위치 | 슬라이드업 (chat 위) | Chat 기록 깔끔함, UX 명확성 |
| 완료 신호 | 마커 메시지 | 상태 불일치 방지, 명시적 의도 |
| 수집 횟수 | 1회/service | 세션 중 재수집 금지 (패턴 명확) |
| Radio UI | Toggle-off 가능 | 사용자가 선택 해제 가능 |

---

## Next Steps

1. **Task 10 dispatch:** `FavoritePanel.tsx` & CSS 구현 (subagent)
2. **Task 11 dispatch:** `App.tsx` 연결 (subagent)
3. **Task 12 verify:** E2E 테스트 & 최종 검증 (수동)
4. **PR 준비:** 스펙/계획/진행률 문서 정리 후 PR 생성

---

**Last Updated:** 2026-04-15  
**Next Review:** Task 10 완료 후
