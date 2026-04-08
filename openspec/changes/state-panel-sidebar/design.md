## Context

현재 travel-agui는 A2A → AG-UI → React 3계층 이벤트 스트리밍 아키텍처다. AG-UI의 `STATE_SNAPSHOT` 이벤트는 도구 결과 컨테이너로만 사용되고, `RunAgentInput`의 `state` 필드는 전혀 활용되지 않는다. 에이전트가 Gemini를 통해 추출한 여행 컨텍스트(목적지, 날짜 등)는 ADK 세션 내부에만 존재하며 클라이언트는 도구 호출 결과가 도달하기 전까지 이를 알 수 없다.

현재 `STATE_SNAPSHOT` 구조:
```json
{ "tool": "search_hotels", "result": { ... } }
```

현재 `RunAgentInput` 전송 구조: messages + threadId + runId만 포함, state 없음.

## Goals / Non-Goals

**Goals:**
- `STATE_SNAPSHOT` 이벤트를 두 종류로 구분: tool result vs agent state
- 에이전트가 매 도구 호출 전 travel_context + agent_status를 STATE_SNAPSHOT으로 발행
- 클라이언트가 매 sendMessage 시 ui_context를 RunAgentInput.state에 포함
- 우측 사이드 패널(StatePanel)에서 양방향 상태를 실시간 시각화
- 상태값 변경 시 하이라이트 애니메이션으로 흐름 표시

**Non-Goals:**
- 서버 측 상태 영속화 (DB, Redis 등)
- 다중 사용자 세션 관리
- STATE_DELTA (partial patch) 구현 — SNAPSHOT만 사용

## Decisions

### 1. STATE_SNAPSHOT 구분: `snapshot_type` 필드로 식별

**결정**: 동일한 `STATE_SNAPSHOT` 이벤트 타입을 유지하되, `snapshot.snapshot_type` 필드로 구분한다.

```
snapshot_type: "tool_result"  → 기존 도구 결과
snapshot_type: "agent_state"  → 새로운 에이전트 상태
```

**이유**: 이벤트 타입을 새로 추가하면 프론트엔드 핸들러, 백엔드 변환기, 타입 정의 전체를 수정해야 한다. 필드 추가로 기존 코드와 하위 호환성 유지.

**대안 고려**: `AGENT_STATE_UPDATE` 신규 이벤트 타입 — 명확하지만 변경 범위 큼, 채택 안 함.

### 2. travel_context 추출 시점: 도구 호출 직전 발행

**결정**: `a2a_server.py`의 `on_event` 핸들러에서 `function_call` 이벤트 감지 시, tool result STATE_SNAPSHOT 전에 agent_state STATE_SNAPSHOT을 먼저 발행한다.

```
function_call 감지
  → agent_state STATE_SNAPSHOT 발행 (travel_context + agent_status)
  → 기존 TOOL_CALL_START DataPart 발행
```

**이유**: ADK가 Gemini에게 도구를 호출하기로 결정한 시점 = 여행 컨텍스트가 파악된 시점. 별도 NLP 추출 로직 불필요.

**travel_context 추출 방법**: function_call의 args에서 직접 파싱.
- `search_hotels(city, check_in, check_out, guests)` → destination, check_in, check_out, guests 추출
- `search_flights(origin, destination, departure_date, ...)` → origin, destination, trip_type 추출
- `request_user_input(input_type, context)` → input_type에서 intent 파악

### 3. RunAgentInput.state → A2A context 전달

**결정**: `main.py`에서 `RunAgentInput`의 `state` 필드를 파싱하여 A2A `send_message` 요청의 `metadata`로 전달한다.

**이유**: A2A SDK의 `RequestContext`가 metadata를 지원하며, `context.get_metadata()`로 접근 가능. 에이전트 코드(agent.py) 수정 불필요.

### 4. StatePanel UI 구조

**결정**: 채팅 우측에 고정 너비(320px) 사이드 패널. 반응형으로 작은 화면에서는 접을 수 있는 토글 버튼 제공.

```
┌─────────────────────┬─────────────────────┐
│                     │   STATE PANEL       │
│   Chat Area         │   ─────────────     │
│                     │   CLIENT → SERVER   │
│                     │   [ui_context]      │
│                     │                     │
│                     │   SERVER → CLIENT   │
│                     │   [travel_context]  │
│                     │   [agent_status]    │
└─────────────────────┴─────────────────────┘
```

상태 변경 시: 해당 필드에 1.5초 황색 하이라이트 + 방향 표시(↑↓) 애니메이션.

### 5. useAGUIChat 상태 확장

**결정**: 기존 `messages` 상태 외에 `agentState: AgentState | null` 상태를 추가. STATE_SNAPSHOT(agent_state) 수신 시 갱신.

```typescript
interface AgentState {
  travel_context: TravelContext
  agent_status: AgentStatus
  last_updated: number  // timestamp for animation trigger
}
```

## Risks / Trade-offs

- **[Risk] travel_context 추출 정확도**: function_call args 파싱이 ADK 내부 구조에 의존 → Mitigation: args가 없거나 파싱 실패 시 해당 필드를 null로 유지, 패널에 "-" 표시로 graceful degradation.
- **[Risk] STATE_SNAPSHOT 이벤트 빈도 증가**: 매 도구 호출마다 agent_state snapshot 추가 → Mitigation: 필드 변경이 있을 때만 발행 (이전 state와 비교).
- **[Trade-off] snapshot_type 필드 추가**: 기존 tool result 코드가 이 필드를 무시하므로 하위 호환은 되지만, 명시적이지 않음 → 타입 가드로 프론트엔드에서 안전하게 처리.

## Open Questions

- `travel_context`를 대화 시작 시 초기화할지, 누적할지? (현재 설계: 누적, 새 정보가 들어오면 덮어씀)
- StatePanel 너비를 사용자가 조절 가능하게 할지? (현재 설계: 고정 320px, 추후 확장 가능)
