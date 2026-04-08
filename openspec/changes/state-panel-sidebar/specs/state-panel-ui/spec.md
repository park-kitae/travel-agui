## ADDED Requirements

### Requirement: StatePanel displays bidirectional state in sidebar
채팅 UI 우측에 StatePanel 컴포넌트가 고정 너비(320px)로 표시되어야 한다(SHALL). StatePanel은 두 섹션으로 구성된다: "CLIENT → SERVER" (클라이언트가 보내는 상태)와 "SERVER → CLIENT" (에이전트에서 받은 상태).

#### Scenario: Panel renders on initial load
- **WHEN** 애플리케이션이 로드될 때
- **THEN** 채팅 영역 우측에 StatePanel이 표시되며, 모든 필드는 "-" (빈 상태)로 표시되어야 한다

#### Scenario: Panel shows client-to-server state
- **WHEN** 사용자가 호텔 카드를 클릭하면
- **THEN** StatePanel의 "CLIENT → SERVER" 섹션에 `selected_hotel_code`, `current_view` 값이 업데이트되어야 한다

#### Scenario: Panel shows server-to-client travel context
- **WHEN** 에이전트로부터 `snapshot_type: "agent_state"` STATE_SNAPSHOT이 수신되면
- **THEN** StatePanel의 "SERVER → CLIENT" 섹션에 `destination`, `check_in`, `check_out`, `guests`, `current_intent`, `missing_fields` 값이 업데이트되어야 한다

### Requirement: State change triggers highlight animation
상태값이 변경될 때 해당 필드에 시각적 하이라이트 애니메이션이 1.5초간 표시되어야 한다(SHALL). 서버에서 오는 상태와 클라이언트에서 보내는 상태는 각각 다른 색상으로 구분된다.

#### Scenario: Server state update highlights green
- **WHEN** `travel_context.destination`이 새 값으로 업데이트되면
- **THEN** 해당 필드 배경이 녹색으로 1.5초간 하이라이트된 후 원래 색으로 돌아가야 한다

#### Scenario: Client state update highlights blue
- **WHEN** `ui_context.selected_hotel_code`가 변경되면
- **THEN** 해당 필드 배경이 파란색으로 1.5초간 하이라이트된 후 원래 색으로 돌아가야 한다

### Requirement: StatePanel is collapsible on small screens
StatePanel은 뷰포트 너비가 1024px 미만일 때 토글 버튼으로 접고 펼 수 있어야 한다(SHALL). 기본 상태는 접힌 상태다.

#### Scenario: Toggle button collapses panel
- **WHEN** 뷰포트가 1024px 미만이고 사용자가 토글 버튼을 클릭하면
- **THEN** StatePanel이 슬라이드 애니메이션으로 숨겨지고 채팅 영역이 전체 너비를 차지해야 한다

#### Scenario: Panel auto-hides on mobile
- **WHEN** 애플리케이션이 1024px 미만 뷰포트에서 로드되면
- **THEN** StatePanel은 기본적으로 숨겨진 상태여야 한다

### Requirement: StatePanel shows state flow direction indicator
각 섹션 헤더에 방향을 나타내는 화살표 아이콘(↑ 또는 ↓)과 레이블이 표시되어야 한다(SHALL). 상태 업데이트 시 화살표가 1초간 강조 표시되어야 한다.

#### Scenario: Direction indicators visible at all times
- **WHEN** StatePanel이 렌더링될 때
- **THEN** "↑ CLIENT → SERVER"와 "↓ SERVER → CLIENT" 헤더가 각 섹션 상단에 표시되어야 한다

#### Scenario: Arrow pulses on state update
- **WHEN** 어느 방향으로든 상태가 업데이트되면
- **THEN** 해당 방향 화살표가 1초간 pulse 애니메이션으로 강조되어야 한다
