## 1. 타입 정의 (Frontend)

- [x] 1.1 `frontend/src/types/index.ts`에 `TravelContext`, `AgentStatus`, `AgentState` 인터페이스 추가
- [x] 1.2 `frontend/src/types/index.ts`에 `UIContext`, `SessionPrefs`, `ClientState` 인터페이스 추가
- [x] 1.3 `STATE_SNAPSHOT` 이벤트 타입에 `snapshot_type: "agent_state" | "tool_result"` 구분 필드 추가
- [x] 1.4 `RunAgentInput`에 `state?: ClientState` 옵션 필드 추가

## 2. 백엔드 — 에이전트 상태 발행 (a2a_server.py)

- [x] 2.1 `function_call` 이벤트에서 tool name과 args를 파싱하여 `TravelContext` 추출하는 헬퍼 함수 구현
- [x] 2.2 `function_call` 이벤트 감지 시 TOOL_CALL_START DataPart 발행 전에 `snapshot_type: "agent_state"` STATE_SNAPSHOT DataPart 발행
- [x] 2.3 `function_response` 이벤트의 기존 tool result DataPart에 `snapshot_type: "tool_result"` 필드 추가
- [x] 2.4 `search_hotels` args에서 destination, check_in, check_out, guests 추출 로직 구현
- [x] 2.5 `search_flights` args에서 origin, destination, departure_date, trip_type 추출 로직 구현
- [x] 2.6 `request_user_input` args에서 input_type → current_intent, missing_fields 매핑 로직 구현

## 3. 백엔드 — RunAgentInput.state 처리 (main.py)

- [x] 3.1 `RunAgentInput` 파싱 시 `state` 필드 추출
- [x] 3.2 A2A `send_message` 요청 시 `metadata: { "client_state": state }` 포함하도록 수정
- [x] 3.3 `state` 필드가 없을 때 graceful fallback 처리 (빈 dict or 생략)

## 4. 프론트엔드 — useAGUIChat 상태 확장

- [x] 4.1 `useAGUIChat` hook에 `agentState: AgentState | null` 상태 추가
- [x] 4.2 `handleEvent`에서 `STATE_SNAPSHOT(snapshot_type: "agent_state")` 처리 분기 추가 → agentState 업데이트
- [x] 4.3 `sendMessage`에서 `RunAgentInput.state`에 현재 `uiContext` 포함하도록 수정
- [x] 4.4 `uiContext` 상태 추적: `selected_hotel_code`, `current_view` 관리
- [x] 4.5 호텔 카드 클릭 시 `uiContext.selected_hotel_code` 업데이트 연동 (App.tsx → useAGUIChat)

## 5. 프론트엔드 — StatePanel 컴포넌트

- [x] 5.1 `frontend/src/components/StatePanel.tsx` 컴포넌트 생성
- [x] 5.2 "CLIENT → SERVER" 섹션 구현: ui_context 필드들 표시 (selected_hotel_code, current_view, currency, language)
- [x] 5.3 "SERVER → CLIENT" 섹션 구현: travel_context 필드들 표시 (destination, origin, check_in, check_out, nights, guests, trip_type)
- [x] 5.4 agent_status 서브섹션 구현: current_intent, missing_fields, active_tool 표시
- [x] 5.5 방향 화살표 아이콘(↑↓) 및 섹션 헤더 구현
- [x] 5.6 상태값 변경 시 하이라이트 애니메이션 구현 (서버→클라이언트: 녹색, 클라이언트→서버: 파란색, 1.5초)
- [x] 5.7 화살표 pulse 애니메이션 구현 (상태 업데이트 시 1초간 강조)
- [x] 5.8 1024px 미만 뷰포트에서 토글 버튼으로 접기/펼치기 구현
- [x] 5.9 `index.css`에 하이라이트 및 pulse 애니메이션 CSS keyframes 추가

## 6. 프론트엔드 — App.tsx 레이아웃 통합

- [x] 6.1 `App.tsx`에 `StatePanel` import 및 레이아웃에 추가 (채팅 우측 320px)
- [x] 6.2 `useAGUIChat`에서 `agentState`, `uiContext`를 StatePanel props로 전달
- [x] 6.3 전체 레이아웃을 flex row로 변경: `[ChatArea 1fr] [StatePanel 320px]`
- [x] 6.4 반응형 breakpoint 처리 (1024px 미만 시 StatePanel hidden + toggle button 표시)
