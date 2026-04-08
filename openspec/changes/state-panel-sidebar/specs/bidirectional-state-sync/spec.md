## ADDED Requirements

### Requirement: Agent publishes travel context via STATE_SNAPSHOT
에이전트는 도구(search_hotels, search_flights, request_user_input, get_travel_tips, get_hotel_detail)를 호출하기 직전, `snapshot_type: "agent_state"`를 포함한 STATE_SNAPSHOT 이벤트를 발행해야 한다(SHALL). 이 스냅샷에는 현재까지 파악된 여행 컨텍스트와 에이전트 상태가 포함되어야 한다.

STATE_SNAPSHOT 페이로드 스키마:
```json
{
  "snapshot_type": "agent_state",
  "travel_context": {
    "destination": "string | null",
    "origin": "string | null",
    "check_in": "string | null",
    "check_out": "string | null",
    "nights": "number | null",
    "guests": "number | null",
    "trip_type": "round_trip | one_way | null"
  },
  "agent_status": {
    "current_intent": "collecting_hotel_params | collecting_flight_params | searching | presenting_results | awaiting_input | idle",
    "missing_fields": ["string"],
    "active_tool": "string | null"
  }
}
```

#### Scenario: Hotel search tool called with full params
- **WHEN** 에이전트가 `search_hotels(city="도쿄", check_in="2025-05-01", check_out="2025-05-04", guests=2)`를 호출하려 할 때
- **THEN** TOOL_CALL_START 이벤트 이전에 `{ snapshot_type: "agent_state", travel_context: { destination: "도쿄", check_in: "2025-05-01", check_out: "2025-05-04", guests: 2 }, agent_status: { current_intent: "searching", active_tool: "search_hotels", missing_fields: [] } }` STATE_SNAPSHOT이 발행되어야 한다

#### Scenario: User input requested with missing fields
- **WHEN** 에이전트가 `request_user_input(input_type="hotel_booking_details")`를 호출하려 할 때
- **THEN** `{ snapshot_type: "agent_state", agent_status: { current_intent: "collecting_hotel_params", missing_fields: ["check_in", "check_out", "guests"], active_tool: "request_user_input" } }` STATE_SNAPSHOT이 발행되어야 한다

#### Scenario: Partial context accumulation
- **WHEN** 대화에서 목적지만 파악되고 날짜/인원은 아직 모를 때
- **THEN** `travel_context.destination`은 파악된 값, 나머지 필드는 `null`로 STATE_SNAPSHOT이 발행되어야 한다

### Requirement: Existing tool result STATE_SNAPSHOT remains unchanged
기존 도구 결과 STATE_SNAPSHOT은 `snapshot_type: "tool_result"` 필드가 추가되어야 하며(SHALL), 기존 `tool`과 `result` 필드는 유지되어야 한다.

#### Scenario: Tool result snapshot includes type field
- **WHEN** `search_hotels` 도구 결과가 반환될 때
- **THEN** `{ snapshot_type: "tool_result", tool: "search_hotels", result: { ... } }` 형태로 STATE_SNAPSHOT이 발행되어야 한다

### Requirement: Client sends ui_context in RunAgentInput.state
클라이언트는 매 메시지 전송 시 `RunAgentInput.state` 필드에 현재 UI 컨텍스트를 포함해야 한다(SHALL).

`state` 필드 스키마:
```json
{
  "ui_context": {
    "selected_hotel_code": "string | null",
    "selected_flight_id": "string | null",
    "current_view": "chat | hotel_list | hotel_detail | flight_list"
  },
  "session_prefs": {
    "currency": "KRW | USD | JPY",
    "language": "ko | en | ja"
  }
}
```

#### Scenario: Hotel detail view state sent to agent
- **WHEN** 사용자가 호텔 카드를 클릭하여 호텔 상세 뷰를 보고 있을 때 새 메시지를 전송하면
- **THEN** RunAgentInput.state에 `{ ui_context: { selected_hotel_code: "HTL001", current_view: "hotel_detail" } }`가 포함되어야 한다

#### Scenario: Default state when no selection
- **WHEN** 사용자가 아무것도 선택하지 않은 상태에서 메시지를 전송하면
- **THEN** RunAgentInput.state에 `{ ui_context: { selected_hotel_code: null, selected_flight_id: null, current_view: "chat" } }`가 포함되어야 한다
