# Travel AG-UI

Google ADK 기반 여행 AI 에이전트 + AG-UI 프로토콜 프론트엔드.

## 아키텍처

```
사용자 → React Frontend (5173)
       → AG-UI Gateway / main.py (8000) → SSE 스트리밍
       → A2A Server / a2a_server.py (8001)
       → LlmAgent (Gemini) → FunctionTools
```

## 개발 명령어

```bash
./start.sh        # 전체 서버 시작 (백엔드 + 프론트)
./stop.sh         # 전체 서버 종료

cd backend && uv run pytest          # 백엔드 단위 테스트
cd frontend && npx playwright test   # E2E 테스트
```

## 핵심 파일

| 파일 | 역할 |
|------|------|
| `backend/agent.py` | LlmAgent 정의, FunctionTool 목록, instruction |
| `backend/a2a_server.py` | A2A 프로토콜 서버, SSE 이벤트 변환 |
| `backend/main.py` | AG-UI Gateway, `/agui/run` 엔드포인트 |
| `backend/state/models.py` | 여행 상태 frozen dataclass 정의 (TravelState, TravelContext, UIContext, AgentStatus) |
| `backend/state/manager.py` | StateManager — thread_id 기준 state 통합 관리, StateSnapshotEvent yield |
| `frontend/src/components/ToolResultCard.tsx` | 도구 결과 UI 렌더링 |
| `frontend/src/components/ChatMessageBubble.tsx` | 채팅 메시지 렌더링 |
| `frontend/src/components/FavoritePanel.tsx` | 취향 수집 슬라이드업 패널 |
| `frontend/src/hooks/useAGUIChat.ts` | SSE 스트림 처리 |

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
- instruction 또는 tool schema 수정 시 → E2E 테스트 필수

## 새 FunctionTool 추가 시

1. `backend/agent.py`에 Python 함수 정의 (타입 힌트 + docstring 필수)
2. `create_travel_agent()`의 `tools` 리스트에 `FunctionTool(func)` 추가
3. `instruction`에 도구 사용 조건과 예시 추가
4. `ToolResultCard.tsx`에 결과 렌더링 추가 (UI 필요 시)
5. `./stop.sh && ./start.sh` 로 재시작
