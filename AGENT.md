# Travel AG-UI

Google ADK 기반 여행 AI 에이전트 + AG-UI 프로토콜 프론트엔드.

## 아키텍처

```
사용자 → React Frontend (5173)
       → AG-UI Gateway / main.py + converter.py (8000) → SSE 스트리밍
       → A2A Server / a2a_server.py + executor.py (8001)
       → LlmAgent (Gemini) → FunctionTools
```

프론트엔드는 `frontend/src/hooks/useAGUIChat.ts` + `frontend/src/hooks/useAgentState.ts`에서 `STATE_DELTA`(JSON Patch)와 `STATE_SNAPSHOT`을 모두 처리합니다.

## 개발 명령어

```bash
python start.py                     # 전체 서버 시작 (백엔드 + 프론트)

cd backend && uv run pytest          # 백엔드 단위 테스트
cd frontend && npm run build         # 프론트 빌드 검증
cd frontend && npm test              # Playwright E2E 테스트
```

## 핵심 파일

| 파일 | 역할 |
|------|------|
| `backend/agent.py` | LlmAgent 정의, FunctionTool 조립, instruction |
| `backend/tools/*.py` | 호텔/항공편/입력/취향/팁 FunctionTool 구현 |
| `backend/a2a_server.py` | A2A 프로토콜 서버 엔트리 |
| `backend/executor.py` | tool-call state를 `STATE_DELTA` DataPart로 enqueue |
| `backend/converter.py` | A2A DataPart를 `STATE_DELTA` / `STATE_SNAPSHOT` / 커스텀 이벤트로 변환 |
| `backend/main.py` | AG-UI Gateway, `/agui/run` 엔드포인트 |
| `backend/state/models.py` | 여행 상태 frozen dataclass 정의 (TravelState, TravelContext, UIContext, AgentStatus, UserPreferences) |
| `backend/state/manager.py` | StateManager — state 변경 시 `StateDeltaEvent`, tool result/request 시 `StateSnapshotEvent` 생성 |
| `frontend/src/components/ToolResultCard.tsx` | 도구 결과 UI 렌더링 |
| `frontend/src/components/ChatMessageBubble.tsx` | 채팅 메시지 렌더링 |
| `frontend/src/components/FavoritePanel.tsx` | 취향 수집 슬라이드업 패널 |
| `frontend/src/hooks/useAGUIChat.ts` | SSE 스트림 처리 + `STATE_DELTA` / `STATE_SNAPSHOT` 라우팅 |
| `frontend/src/hooks/useAgentState.ts` | snapshot merge + JSON Patch(delta) 적용 |
| `frontend/src/types/index.ts` | AG-UI 이벤트 타입 (`STATE_DELTA`, `STATE_SNAPSHOT`, request events) 정의 |

## FunctionTool 목록

- `search_hotels(city, check_in, check_out, guests)` — 호텔 검색
- `search_flights(origin, destination, departure_date, passengers, return_date)` — 항공편 검색
- `request_user_input(input_type, fields, context)` — 정보 부족 시 입력 폼 요청
- `request_user_favorite(favorite_type, context)` — 호텔/항공 취향 수집 요청
- `get_travel_tips(destination, travel_type)` — 여행지 정보
- `get_hotel_detail(hotel_code)` — 호텔 상세 (HTL-XXX-000 형식)

## 주요 규칙

- 호텔/항공편 필수 정보 누락 시 → 텍스트 질문 ❌, `request_user_input` 호출 ✅
- **취향 수집 우선**: 호텔/항공 추천 요청 시 먼저 `request_user_favorite` 호출 → 사용자 확인 후 `request_user_input` 또는 검색 진행
- 마커 기반 완료 추적: `[호텔 취향 수집 완료]`, `[항공 취향 수집 완료]` 마커로 수집 여부 판단
- 크로스 서비스 날짜 재사용: 호텔↔항공편 일정이 있으면 자동으로 날짜·인원 매핑
- `context` 파라미터는 반드시 유효한 JSON 문자열
- tool-call에 의해 `TravelState`가 바뀌면 backend는 `STATE_DELTA`(RFC 6902 JSON Patch)를 우선 전송한다
- `tool_result`, `USER_INPUT_REQUEST`, `USER_FAVORITE_REQUEST`는 snapshot/custom event 경로를 유지한다
- frontend는 `STATE_DELTA`와 `STATE_SNAPSHOT(snapshot_type="agent_state")`를 모두 지원해야 한다
- instruction 또는 tool schema 수정 시 → E2E 테스트 필수

## 새 FunctionTool 추가 시

1. `backend/tools/`에 Python 함수 정의 (타입 힌트 + docstring 필수)
2. `backend/agent.py`에서 해당 함수를 import하고 `create_travel_agent()`의 `tools` 리스트에 `FunctionTool(func)` 추가
3. `instruction`에 도구 사용 조건과 예시 추가
4. `ToolResultCard.tsx`에 결과 렌더링 추가 (UI 필요 시)
5. `python start.py`로 재시작 후 `cd backend && uv run pytest`, `cd frontend && npm run build && npm test` 검증
