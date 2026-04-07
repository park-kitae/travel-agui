## Why

현재 에이전트와 클라이언트 간 상태 교환이 없어, 에이전트가 대화에서 파악한 여행 컨텍스트(목적지, 날짜, 인원 등)가 UI에 전혀 노출되지 않는다. 반대로 클라이언트의 UI 컨텍스트(선택된 호텔 등)도 에이전트에 전달되지 않아 상태 불일치가 발생한다. 양방향 상태 동기화와 이를 시각화하는 사이드 패널을 추가해 에이전트-클라이언트 간 상태 흐름을 실시간으로 파악할 수 있게 한다.

## What Changes

- **SERVER → CLIENT**: AG-UI `STATE_SNAPSHOT` 이벤트에 `travel_context` + `agent_status` 필드 추가
  - `travel_context`: 에이전트가 대화에서 추출한 여행 엔티티 (destination, origin, check_in, check_out, guests, trip_type)
  - `agent_status`: 현재 에이전트 상태 (current_intent, missing_fields, active_tool)
- **CLIENT → SERVER**: `RunAgentInput.state` 필드에 `ui_context` + `session_prefs` 추가
  - `ui_context`: 현재 선택된 호텔 코드, 현재 뷰
  - `session_prefs`: 통화, 언어 설정
- **UI**: 채팅 우측에 상태 패널(StatePanel) 사이드바 추가
  - 서버에서 받은 `travel_context`, `agent_status` 실시간 표시
  - 클라이언트가 서버로 보내는 `ui_context` 표시
  - 상태값이 변경될 때 애니메이션으로 흐름 시각화
- **백엔드**: `a2a_server.py`에서 ADK 도구 호출 전 대화 분석 후 `travel_context` STATE_SNAPSHOT 발행
- **백엔드**: `main.py`에서 `RunAgentInput.state`를 A2A RequestContext로 전달

## Capabilities

### New Capabilities

- `bidirectional-state-sync`: 에이전트-클라이언트 간 양방향 상태 스키마 및 전송 프로토콜 (STATE_SNAPSHOT 확장, RunAgentInput.state 활용)
- `state-panel-ui`: 상태값 실시간 시각화 사이드 패널 UI 컴포넌트

### Modified Capabilities

- `ag-ui-gateway`: RunAgentInput.state 수신 및 A2A context 전달 로직 추가

## Impact

- `backend/main.py`: RunAgentInput에서 state 필드 파싱 및 A2A 요청에 context로 전달
- `backend/a2a_server.py`: ADK 실행 전 travel_context 추출 및 STATE_SNAPSHOT 이벤트 발행 추가
- `frontend/src/hooks/useAGUIChat.ts`: RunAgentInput에 state 필드 추가, STATE_SNAPSHOT에서 agent state 파싱
- `frontend/src/types/index.ts`: AgentState, TravelContext, AgentStatus, UIContext 타입 추가
- `frontend/src/components/StatePanel.tsx`: 신규 컴포넌트 (상태 사이드 패널)
- `frontend/src/App.tsx`: StatePanel 레이아웃 통합
