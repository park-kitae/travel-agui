## Backend Compatibility Cleanup Design

### Goal

런타임 코드와 테스트 코드에서 더 이상 필요하지 않은 backend 호환용 re-export 레이어를 제거한다. 문서 예제는 유지하고, 실제 실행 경로와 테스트 import 만 현재 도메인 구조에 맞게 정리한다.

### Current State

현재 backend 에는 실제 구현이 `domains.travel.*` 아래로 이동한 뒤 남겨둔 호환용 wrapper 가 있다.

- `backend/agent.py`
- `backend/tools/*`
- `backend/data/*` 중 순수 re-export 파일
- `backend/state/{__init__.py, manager.py, models.py, context_builder.py}`

이 파일들은 대부분 구현 없이 import 만 다시 노출한다. 반면 `backend/state/store.py` 는 실제 구현을 가지고 있으며 런타임과 테스트에서 직접 사용 중이다.

### Scope

포함:

- 런타임 코드 import 를 실제 구현 경로로 전환
- 테스트 코드 import 를 실제 구현 경로로 전환
- 더 이상 참조되지 않는 순수 compatibility wrapper 삭제

제외:

- `docs/superpowers/*` 문서 내 예전 import 예시 수정
- 도메인 로직 변경
- `state.store` 정리 또는 이동

### Approach

가장 작은 변경으로 정리한다.

1. 먼저 런타임 코드와 테스트 코드에서 compatibility 경로를 직접 구현 경로로 교체한다.
2. `backend/state/store.py` 처럼 실제 구현을 가진 모듈은 유지한다.
3. 더 이상 참조되지 않는 순수 re-export 파일만 삭제한다.

이 방식은 공개 API 호환을 유지할 필요가 없다는 현재 요구를 충족하면서도, 런타임에 실제로 쓰이는 모듈까지 과하게 건드리지 않는다.

### Import Mapping

다음 규칙으로 import 를 교체한다.

- `from agent import create_travel_agent` -> `from domains.travel.agent import create_travel_agent`
- `from tools...` -> `from domains.travel.tools...`
- `from data...` -> `from domains.travel.data...`
- `from state.manager...` -> `from domains.travel.state_manager...`
- `from state.models...` -> `from domains.travel.state...`
- `from state.context_builder...` -> `from domains.travel.context...`
- `from state import ...` 형태 중 state store 와 무관한 호환 export 는 실제 도메인 모듈로 치환
- `from state.store import SerializedStateStore` 는 유지

### Deletion Rules

삭제 대상은 아래 조건을 모두 만족하는 파일로 제한한다.

- 자체 로직이 없음
- 다른 구현 모듈을 그대로 re-export 함
- 런타임/테스트 코드에서 더 이상 참조되지 않음

예상 삭제 대상:

- `backend/agent.py`
- `backend/tools/__init__.py`
- `backend/tools/favorite_tools.py`
- `backend/tools/flight_tools.py`
- `backend/tools/hotel_tools.py`
- `backend/tools/input_tools.py`
- `backend/tools/tips_tools.py`
- `backend/data/__init__.py`
- `backend/data/flights.py`
- `backend/data/hotels.py`
- `backend/data/preferences.py`
- `backend/data/tips.py`
- `backend/state/__init__.py`
- `backend/state/manager.py`
- `backend/state/models.py`
- `backend/state/context_builder.py`

유지 대상:

- `backend/state/store.py`

### Error Handling

이번 작업은 구조 정리이므로 런타임 동작 변경이 없어야 한다. import 교체 후 테스트에서 `ModuleNotFoundError` 또는 잘못된 심볼 import 가 발생하면, 삭제보다 import 경로 수정이 먼저라는 원칙으로 되돌아가 해당 참조를 직접 경로로 맞춘다.

### Testing

TDD 원칙에 따라 먼저 관련 테스트 또는 import 검증이 실패하는 상태를 만든 뒤 수정한다. 검증은 아래 순서로 진행한다.

1. compatibility 경로 제거를 전제로 한 테스트/런타임 import 수정
2. 관련 테스트 실행으로 실패 지점 확인
3. 필요한 최소 코드 수정
4. 관련 테스트 재실행
5. backend 테스트 전체 재실행 또는 충분히 넓은 회귀 테스트 실행

최소 확인 대상은 다음을 포함한다.

- `backend/tests/test_a2a_stream.py`
- `backend/tests/test_domain_runtime.py`
- `backend/tests/state-panel-sidebar/*`
- `backend/tests/state/*`

### Risks

- 일부 테스트나 진입점이 아직 호환 경로를 암묵적으로 기대할 수 있다.
- `state` 디렉터리는 `store.py` 때문에 완전히 사라지지 않는다.
- 문서 예시는 구 경로를 계속 보여주지만, 이번 범위에서는 의도적으로 유지한다.

### Success Criteria

- 런타임/테스트 코드에서 compatibility wrapper import 가 사라진다.
- 순수 re-export wrapper 파일이 제거된다.
- `backend/state/store.py` 기반 동작은 유지된다.
- 관련 테스트가 통과한다.
