## ADDED Requirements

### Requirement: AG-UI gateway forwards RunAgentInput.state to A2A context
AG-UI 게이트웨이(`main.py`)는 `RunAgentInput.state` 필드가 존재할 경우 이를 A2A `send_message` 요청의 metadata로 포함시켜야 한다(SHALL).

#### Scenario: State forwarded in A2A request
- **WHEN** 클라이언트가 `{ state: { ui_context: { selected_hotel_code: "HTL001" } } }`를 포함한 RunAgentInput을 POST /agui/run에 전송하면
- **THEN** A2A 서버로의 send_message 요청에 `metadata: { "client_state": { ... } }`가 포함되어야 한다

#### Scenario: Missing state field handled gracefully
- **WHEN** 클라이언트가 `state` 필드 없이 RunAgentInput을 전송하면
- **THEN** 게이트웨이는 오류 없이 처리하며 A2A 요청에 빈 metadata 또는 metadata 미포함으로 처리해야 한다
