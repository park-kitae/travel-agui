# Domain Plugin Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract the current travel-specific backend behavior behind a startup-selected `DomainPlugin` boundary while keeping the AG-UI/A2A chat pipeline common.

**Architecture:** Introduce a singleton common runtime that loads one plugin at startup, owns opaque serialized per-thread state, validates typed plugin emissions, and supplies the active ADK agent and agent card to the shared engine. Move travel-specific prompt rules, tools, data, state schema, context rendering, and tool lifecycle interpretation into `backend/domains/travel/`, then prove the boundary by booting the same engine with a fake plugin and running smoke requests through the normal lifecycle.

**Tech Stack:** Python 3.11+, FastAPI, Google ADK, a2a-sdk, ag-ui-protocol, dataclasses, pytest, uv

---

## Implementation Notes

- Follow @python-patterns for protocol/dataclass boundaries and focused module design.
- Follow @python-testing for pytest structure, fixtures, and regression coverage.
- Preserve the current request/response contract; this plan refactors backend boundaries, not frontend behavior.
- Treat `backend/main.py`, `backend/a2a_server.py`, `backend/executor.py`, and `backend/converter.py` as the stable engine surface.
- Do not let shared modules interpret travel field names such as `destination`, `check_in`, `check_out`, `hotel`, or `flight`.

---

## File Map

### Create

- `backend/domains/__init__.py` — plugin package marker and exports
- `backend/domains/base.py` — `DomainPlugin` protocol and typed runtime emission dataclasses
- `backend/domain_runtime.py` — singleton runtime loader, plugin/store access, emission validation
- `backend/state/store.py` — opaque serialized state storage keyed by thread/session id
- `backend/domains/travel/__init__.py` — travel domain exports
- `backend/domains/travel/plugin.py` — `DomainPlugin` implementation for travel
- `backend/domains/travel/agent.py` — travel ADK agent construction
- `backend/domains/travel/state.py` — travel-specific state dataclasses and pure lifecycle helpers
- `backend/domains/travel/context.py` — travel-specific context builder
- `backend/domains/travel/tools/__init__.py` — travel tool exports
- `backend/domains/travel/tools/favorite_tools.py`
- `backend/domains/travel/tools/flight_tools.py`
- `backend/domains/travel/tools/hotel_tools.py`
- `backend/domains/travel/tools/input_tools.py`
- `backend/domains/travel/tools/tips_tools.py`
- `backend/domains/travel/data/__init__.py` — travel data exports
- `backend/domains/travel/data/flights.py`
- `backend/domains/travel/data/hotels.py`
- `backend/domains/travel/data/preferences.py`
- `backend/domains/travel/data/tips.py`
- `backend/domains/fake/__init__.py` — fake plugin package marker
- `backend/domains/fake/plugin.py` — minimal fake plugin for swappability proof
- `backend/tests/test_domain_runtime.py` — runtime contract, singleton, emission validation tests
- `backend/tests/test_fake_plugin_smoke.py` — fake plugin boot and smoke-request tests

### Modify

- `backend/main.py` — replace direct travel state/context usage with runtime calls
- `backend/a2a_server.py` — build ADK agent and agent card from the active plugin runtime
- `backend/executor.py` — replace direct travel state hooks with plugin runtime hooks and typed emission mapping
- `backend/agent.py` — compatibility re-export or retire after callers are updated
- `backend/state/__init__.py` — export common store/runtime helpers or compatibility aliases only
- `backend/state/manager.py` — compatibility wrapper or delete after migration
- `backend/state/models.py` — compatibility wrapper or delete after migration
- `backend/state/context_builder.py` — compatibility wrapper or delete after migration
- `backend/data/__init__.py` — compatibility re-export or retire callers
- `backend/tools/__init__.py` — compatibility re-export or retire callers
- `backend/tests/conftest.py` — add runtime fixture reset helpers if needed
- `backend/tests/test_agui_run.py` — update for runtime-backed request flow
- `backend/tests/test_a2a_stream.py` — update for typed runtime emissions
- `backend/tests/test_health.py` — update for plugin-backed agent card / startup wiring
- `backend/tests/state/test_context_builder.py` — retarget to `domains.travel.context`
- `backend/tests/state/test_manager.py` — retarget to travel plugin lifecycle helpers
- `backend/tests/state/test_models.py` — retarget to `domains.travel.state`
- `backend/tests/state-panel-sidebar/test_context_extraction.py` — update imports/fixtures to travel plugin helpers
- `backend/tests/state-panel-sidebar/test_main_state_handling.py` — update to runtime-backed state merge behavior
- `backend/tests/state-panel-sidebar/test_snapshot_emission.py` — update to runtime emission mapping behavior
- `backend/.env.example` — document `DOMAIN_PLUGIN=travel`

### Test focus

- `backend/tests/test_domain_runtime.py`
- `backend/tests/test_fake_plugin_smoke.py`
- `backend/tests/test_agui_run.py`
- `backend/tests/test_a2a_stream.py`
- `backend/tests/test_health.py`
- `backend/tests/state/test_context_builder.py`
- `backend/tests/state/test_manager.py`
- `backend/tests/state/test_models.py`
- `backend/tests/state-panel-sidebar/test_context_extraction.py`
- `backend/tests/state-panel-sidebar/test_main_state_handling.py`
- `backend/tests/state-panel-sidebar/test_snapshot_emission.py`

---

## Task 1: Define the common plugin contract and runtime emission types

**Files:**
- Create: `backend/domains/__init__.py`
- Create: `backend/domains/base.py`
- Test: `backend/tests/test_domain_runtime.py`

- [ ] **Step 1: Write the failing contract tests**

Create `backend/tests/test_domain_runtime.py` with at least:

```python
from domains.base import RuntimeDeltaPayload, RuntimeSnapshotPayload, RuntimeUiRequestPayload


def test_runtime_emission_payload_shapes_are_dataclasses():
    delta = RuntimeDeltaPayload(ops=[{"op": "replace", "path": "/x", "value": 1}])
    snapshot = RuntimeSnapshotPayload(snapshot={"snapshot_type": "tool_result"})
    request = RuntimeUiRequestPayload(event_name="USER_INPUT_REQUEST", payload={"request_id": "1"})

    assert delta.ops[0]["path"] == "/x"
    assert snapshot.snapshot["snapshot_type"] == "tool_result"
    assert request.event_name == "USER_INPUT_REQUEST"


def test_domain_plugin_protocol_symbols_are_importable():
    from domains.base import DomainPlugin  # noqa: F401
```

- [ ] **Step 2: Run the tests to confirm RED**

Run:

```bash
cd backend
uv run pytest tests/test_domain_runtime.py -v
```

Expected: FAIL with import errors because `domains/base.py` does not exist.

- [ ] **Step 3: Implement `backend/domains/base.py`**

Create a focused contract module with:

```python
from dataclasses import dataclass
from typing import Protocol, TypeAlias

from a2a.types import AgentCard
from google.adk.agents import LlmAgent


@dataclass(frozen=True)
class RuntimeDeltaPayload:
    ops: list[dict]


@dataclass(frozen=True)
class RuntimeSnapshotPayload:
    snapshot: dict


@dataclass(frozen=True)
class RuntimeUiRequestPayload:
    event_name: str
    payload: dict


RuntimeEmission: TypeAlias = RuntimeDeltaPayload | RuntimeSnapshotPayload | RuntimeUiRequestPayload


class DomainPlugin(Protocol):
    id: str

    def build_agent(self) -> LlmAgent: ...
    def agent_card(self) -> AgentCard: ...
    def empty_state(self) -> object: ...
    def serialize_state(self, state: object) -> dict: ...
    def deserialize_state(self, raw_state: dict | None) -> object: ...
    def merge_client_state(self, current_state: object, raw_state: dict) -> object: ...
    def apply_tool_call(self, current_state: object, tool_name: str, args: dict) -> tuple[object, list[RuntimeEmission]]: ...
    def apply_tool_result(self, current_state: object, tool_name: str, result: dict) -> tuple[object, list[RuntimeEmission]]: ...
    def build_context_block(self, state: object, user_message: str) -> str: ...
```

- [ ] **Step 4: Add `backend/domains/__init__.py` exports**

```python
from .base import DomainPlugin, RuntimeDeltaPayload, RuntimeSnapshotPayload, RuntimeUiRequestPayload, RuntimeEmission
```

- [ ] **Step 5: Re-run the focused tests to confirm GREEN**

Run:

```bash
cd backend
uv run pytest tests/test_domain_runtime.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/domains/__init__.py backend/domains/base.py backend/tests/test_domain_runtime.py
git commit -m "feat: add common domain plugin contract"
```

---

## Task 2: Add the singleton common runtime and opaque serialized state store

**Files:**
- Create: `backend/domain_runtime.py`
- Create: `backend/state/store.py`
- Modify: `backend/tests/test_domain_runtime.py`
- Test: `backend/tests/test_domain_runtime.py`

- [ ] **Step 1: Add failing tests for a shared runtime instance and opaque state round-tripping**

Extend `backend/tests/test_domain_runtime.py` with a local stub plugin used only in tests:

```python
class StubPlugin:
    id = "stub"
    def build_agent(self): raise NotImplementedError
    def agent_card(self): raise NotImplementedError
    def empty_state(self): return {"count": 0}
    def serialize_state(self, state): return state
    def deserialize_state(self, raw_state): return raw_state or {"count": 0}
    def merge_client_state(self, current_state, raw_state): return {**current_state, **raw_state}
    def apply_tool_call(self, current_state, tool_name, args): return current_state, []
    def apply_tool_result(self, current_state, tool_name, result): return current_state, []
    def build_context_block(self, state, user_message): return user_message
```

Then add tests:

```python
from domain_runtime import DomainRuntime, initialize_runtime_or_die, get_runtime, reset_runtime_for_tests


def test_domain_runtime_round_trips_serialized_state():
    runtime = DomainRuntime(plugin=StubPlugin())
    runtime.save_state("thread-1", {"count": 2})
    assert runtime.load_state("thread-1") == {"count": 2}


def test_get_runtime_returns_singleton(monkeypatch):
    reset_runtime_for_tests()
    monkeypatch.setenv("DOMAIN_PLUGIN", "travel")
    first = initialize_runtime_or_die()
    second = get_runtime()
    assert first is second
```

- [ ] **Step 2: Run the tests to confirm RED**

Run:

```bash
cd backend
uv run pytest tests/test_domain_runtime.py -k "round_trips or singleton" -v
```

Expected: FAIL because `domain_runtime.py` and `state/store.py` do not exist.

- [ ] **Step 3: Implement the opaque serialized state store**

Create `backend/state/store.py`:

```python
class SerializedStateStore:
    def __init__(self) -> None:
        self._store: dict[str, dict] = {}

    def get(self, thread_id: str) -> dict | None:
        return self._store.get(thread_id)

    def set(self, thread_id: str, state: dict) -> None:
        self._store[thread_id] = state

    def clear(self, thread_id: str) -> None:
        self._store.pop(thread_id, None)
```

- [ ] **Step 4: Implement `backend/domain_runtime.py` with explicit singleton helpers**

Include:

```python
from importlib import import_module
import os

from domains.base import RuntimeDeltaPayload, RuntimeSnapshotPayload, RuntimeUiRequestPayload
from state.store import SerializedStateStore

_runtime = None


class DomainRuntime:
    def __init__(self, plugin, store: SerializedStateStore | None = None) -> None:
        self.plugin = plugin
        self.store = store or SerializedStateStore()

    @classmethod
    def from_env(cls) -> "DomainRuntime":
        plugin_id = os.environ.get("DOMAIN_PLUGIN", "travel")
        module = import_module(f"domains.{plugin_id}.plugin")
        return cls(plugin=module.get_plugin())
```

Also add:

```python
def initialize_runtime_or_die() -> DomainRuntime: ...
def get_runtime() -> DomainRuntime: ...
def reset_runtime_for_tests() -> None: ...
```

Rules:

- `initialize_runtime_or_die()` must eagerly load the plugin from env exactly once
- plugin import/load failure must raise immediately so startup aborts fast
- `get_runtime()` must only return the already-initialized singleton
- `get_runtime()` should raise a clear runtime error if called before initialization

- [ ] **Step 5: Re-run the focused tests to confirm GREEN**

Run:

```bash
cd backend
uv run pytest tests/test_domain_runtime.py -k "round_trips or singleton" -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/domain_runtime.py backend/state/store.py backend/tests/test_domain_runtime.py
git commit -m "feat: add singleton domain runtime and opaque state store"
```

---

## Task 3: Move travel data modules into the travel domain package

**Files:**
- Create: `backend/domains/travel/__init__.py`
- Create: `backend/domains/travel/data/__init__.py`
- Create: `backend/domains/travel/data/flights.py`
- Create: `backend/domains/travel/data/hotels.py`
- Create: `backend/domains/travel/data/preferences.py`
- Create: `backend/domains/travel/data/tips.py`
- Modify: `backend/data/__init__.py`

- [ ] **Step 1: Copy each travel data module into `backend/domains/travel/data/`**

Create exact file-for-file copies of:

- `backend/data/flights.py`
- `backend/data/hotels.py`
- `backend/data/preferences.py`
- `backend/data/tips.py`

Do not change behavior yet.

- [ ] **Step 2: Add package exports**

Create `backend/domains/travel/data/__init__.py`:

```python
from .flights import *
from .hotels import *
from .preferences import *
from .tips import *
```

Create `backend/domains/travel/__init__.py` as a package marker.

- [ ] **Step 3: Add temporary compatibility re-exports in `backend/data/__init__.py`**

Point old imports at the new package so callers can migrate gradually.

- [ ] **Step 4: Smoke-check imports**

Run:

```bash
cd backend
uv run python -c "from domains.travel.data import flights, hotels, preferences, tips; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/domains/travel/__init__.py backend/domains/travel/data backend/data/__init__.py
git commit -m "refactor: move travel data modules under domain package"
```

---

## Task 4: Move travel tool modules into the travel domain package

**Files:**
- Create: `backend/domains/travel/tools/__init__.py`
- Create: `backend/domains/travel/tools/favorite_tools.py`
- Create: `backend/domains/travel/tools/flight_tools.py`
- Create: `backend/domains/travel/tools/hotel_tools.py`
- Create: `backend/domains/travel/tools/input_tools.py`
- Create: `backend/domains/travel/tools/tips_tools.py`
- Modify: `backend/tools/__init__.py`

- [ ] **Step 1: Copy each travel tool module into `backend/domains/travel/tools/`**

Create exact file-for-file copies of the current tool modules. Update their imports so they read travel data from `domains.travel.data`, not the old common path.

- [ ] **Step 2: Add package exports**

Create `backend/domains/travel/tools/__init__.py` with explicit exports for the five travel tools.

- [ ] **Step 3: Add temporary compatibility re-exports in `backend/tools/__init__.py`**

Point old import paths to the new domain tool modules.

- [ ] **Step 4: Smoke-check imports**

Run:

```bash
cd backend
uv run python -c "from domains.travel.tools.hotel_tools import search_hotels; print(search_hotels.__name__)"
```

Expected: `search_hotels`

- [ ] **Step 5: Commit**

```bash
git add backend/domains/travel/tools backend/tools/__init__.py
git commit -m "refactor: move travel tools under domain package"
```

---

## Task 5: Extract travel state, context, agent assembly, and plugin implementation

**Files:**
- Create: `backend/domains/travel/state.py`
- Create: `backend/domains/travel/context.py`
- Create: `backend/domains/travel/agent.py`
- Create: `backend/domains/travel/plugin.py`
- Modify: `backend/tests/state/test_models.py`
- Modify: `backend/tests/state/test_context_builder.py`
- Modify: `backend/tests/state/test_manager.py`
- Test: `backend/tests/state/test_models.py`
- Test: `backend/tests/state/test_context_builder.py`
- Test: `backend/tests/state/test_manager.py`

- [ ] **Step 1: Retarget the travel state tests and confirm RED**

Update tests to import from the new package, for example:

```python
from domains.travel.state import TravelState, TravelContext, UserPreferences
from domains.travel.context import TravelContextBuilder
from domains.travel.plugin import get_plugin
```

Run:

```bash
cd backend
uv run pytest tests/state/test_models.py tests/state/test_context_builder.py tests/state/test_manager.py -v
```

Expected: FAIL because these modules do not exist yet.

- [ ] **Step 2: Create `backend/domains/travel/state.py`**

Move the current travel dataclasses out of `backend/state/models.py` and add pure helpers that return next state plus typed runtime emissions:

```python
def merge_client_state(current: TravelState, raw_state: dict) -> TravelState: ...
def apply_tool_call(current: TravelState, tool_name: str, args: dict) -> tuple[TravelState, list[RuntimeEmission]]: ...
def apply_tool_result(current: TravelState, tool_name: str, result: dict) -> tuple[TravelState, list[RuntimeEmission]]: ...
```

Do not mutate any shared store from these helpers.

- [ ] **Step 3: Create `backend/domains/travel/context.py`**

Move the existing context logic into:

```python
class TravelContextBuilder:
    def build(self, state: TravelState, user_message: str) -> str:
        ...
```

- [ ] **Step 4: Create `backend/domains/travel/agent.py`**

Move the current travel ADK agent creation here. Update imports to use `domains.travel.tools.*`.

- [ ] **Step 5: Create `backend/domains/travel/plugin.py`**

Implement `DomainPlugin` and expose:

```python
def get_plugin() -> TravelDomainPlugin:
    return TravelDomainPlugin()
```

`agent_card()` must return the full travel `AgentCard` metadata contract, not just skills.

- [ ] **Step 6: Re-run the travel-focused tests to confirm GREEN**

Run:

```bash
cd backend
uv run pytest tests/state/test_models.py tests/state/test_context_builder.py tests/state/test_manager.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/domains/travel/state.py backend/domains/travel/context.py backend/domains/travel/agent.py backend/domains/travel/plugin.py backend/tests/state/test_models.py backend/tests/state/test_context_builder.py backend/tests/state/test_manager.py
git commit -m "feat: implement travel domain plugin"
```

---

## Task 6: Route `a2a_server.py` through the singleton runtime

**Files:**
- Modify: `backend/a2a_server.py`
- Modify: `backend/tests/test_health.py`
- Test: `backend/tests/test_health.py`

- [ ] **Step 1: Add a failing test for plugin-backed agent card wiring**

Add or update a test asserting that the module uses the active plugin card rather than hard-coded travel metadata.

- [ ] **Step 2: Run the test to confirm RED**

Run:

```bash
cd backend
uv run pytest tests/test_health.py -v
```

Expected: FAIL once the test targets plugin/runtime wiring that does not exist yet.

- [ ] **Step 3: Update `backend/a2a_server.py`**

Replace direct imports of `create_travel_agent()` and hard-coded `AgentCard(...)` with:

```python
from domain_runtime import initialize_runtime_or_die, get_runtime

initialize_runtime_or_die()
runtime = get_runtime()
plugin = runtime.plugin
session_service = InMemorySessionService()
runner = Runner(app_name=APP_NAME, agent=plugin.build_agent(), session_service=session_service)
agent_card = runtime.build_agent_card(base_url="http://localhost:8001/")
```

If `build_agent_card()` keeps the file cleaner, add it to `domain_runtime.py`.

- [ ] **Step 4: Re-run the focused test to confirm GREEN**

Run:

```bash
cd backend
uv run pytest tests/test_health.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/a2a_server.py backend/tests/test_health.py
git commit -m "refactor: build A2A agent and card from runtime plugin"
```

---

## Task 7: Route `main.py` through the runtime for state merge and context building

**Files:**
- Modify: `backend/main.py`
- Modify: `backend/tests/test_agui_run.py`
- Modify: `backend/tests/state-panel-sidebar/test_main_state_handling.py`
- Test: `backend/tests/test_agui_run.py`
- Test: `backend/tests/state-panel-sidebar/test_main_state_handling.py`

- [ ] **Step 1: Add failing tests for runtime-backed request handling**

Update tests so they verify the request path still returns SSE and that runtime-merged state still affects the enriched message.

- [ ] **Step 2: Run the tests to confirm RED**

Run:

```bash
cd backend
uv run pytest tests/test_agui_run.py tests/state-panel-sidebar/test_main_state_handling.py -v
```

Expected: FAIL after the tests target runtime behavior that is not wired yet.

- [ ] **Step 3: Update `backend/main.py` to use `get_runtime()`**

Refactor the request path to do this instead of using `state_manager` / `ContextBuilder` directly:

```python
initialize_runtime_or_die()
runtime = get_runtime()
state = runtime.load_state(thread_id)
state = runtime.plugin.merge_client_state(state, raw_state)
runtime.save_state(thread_id, state)
user_message = runtime.plugin.build_context_block(state, user_message)
```

Preserve the existing AG-UI event framing and SSE flow exactly.

- [ ] **Step 4: Re-run the focused tests to confirm GREEN**

Run:

```bash
cd backend
uv run pytest tests/test_agui_run.py tests/state-panel-sidebar/test_main_state_handling.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/main.py backend/tests/test_agui_run.py backend/tests/state-panel-sidebar/test_main_state_handling.py
git commit -m "refactor: use runtime plugin for request state and context"
```

---

## Task 8: Route `executor.py` through typed plugin emissions

**Files:**
- Modify: `backend/executor.py`
- Modify: `backend/tests/test_a2a_stream.py`
- Modify: `backend/tests/state-panel-sidebar/test_snapshot_emission.py`
- Modify: `backend/tests/state-panel-sidebar/test_context_extraction.py`
- Modify: `backend/tests/test_domain_runtime.py`
- Test: `backend/tests/test_a2a_stream.py`
- Test: `backend/tests/state-panel-sidebar/test_snapshot_emission.py`
- Test: `backend/tests/state-panel-sidebar/test_context_extraction.py`
- Test: `backend/tests/test_domain_runtime.py`

- [ ] **Step 1: Add failing tests for typed runtime emission validation**

Add tests that verify:

```python
def test_runtime_rejects_unsupported_ui_event_name():
    ...


def test_runtime_rejects_unknown_emission_object():
    ...
```

Update the stream tests to expect runtime-produced `STATE_DELTA`, `STATE_SNAPSHOT`, `USER_INPUT_REQUEST`, and `USER_FAVORITE_REQUEST` events.

- [ ] **Step 2: Run the focused tests to confirm RED**

Run:

```bash
cd backend
uv run pytest tests/test_domain_runtime.py tests/test_a2a_stream.py tests/state-panel-sidebar/test_snapshot_emission.py tests/state-panel-sidebar/test_context_extraction.py -v
```

Expected: FAIL because `executor.py` still uses the travel `state_manager` directly.

- [ ] **Step 3: Add a small runtime helper that maps typed emissions to current event payloads**

Add one focused helper in `domain_runtime.py`, for example:

```python
def emission_to_data_part_payload(emission: RuntimeEmission) -> dict:
    ...
```

Rules:

- `RuntimeDeltaPayload` → `{ "_agui_event": "STATE_DELTA", "delta": ... }`
- `RuntimeSnapshotPayload` → raw `snapshot` dict
- `RuntimeUiRequestPayload` → payload dict plus `_agui_event` set to the validated `event_name`

Raise a runtime error for unsupported UI event names or unknown emission objects.

- [ ] **Step 4: Refactor `backend/executor.py`**

Replace direct `state_manager.apply_tool_call(...)` / `apply_tool_result(...)` usage with runtime-backed logic:

```python
runtime = get_runtime()
state = runtime.load_state(context_id)
state, emissions = runtime.plugin.apply_tool_call(state, fc.name, args_dict)
runtime.save_state(context_id, state)
for emission in emissions:
    data = runtime.emission_to_data_part_payload(emission)
    ...
```

Do the same for `apply_tool_result(...)`. Keep ADK event handling, task status updates, and text chunk streaming common.

- [ ] **Step 5: Re-run the focused tests to confirm GREEN**

Run:

```bash
cd backend
uv run pytest tests/test_domain_runtime.py tests/test_a2a_stream.py tests/state-panel-sidebar/test_snapshot_emission.py tests/state-panel-sidebar/test_context_extraction.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/domain_runtime.py backend/executor.py backend/tests/test_domain_runtime.py backend/tests/test_a2a_stream.py backend/tests/state-panel-sidebar/test_snapshot_emission.py backend/tests/state-panel-sidebar/test_context_extraction.py
git commit -m "refactor: map typed plugin emissions through runtime"
```

---

## Task 9: Add the fake plugin and prove swappability with a real smoke request

**Files:**
- Create: `backend/domains/fake/__init__.py`
- Create: `backend/domains/fake/plugin.py`
- Create: `backend/tests/test_fake_plugin_smoke.py`
- Test: `backend/tests/test_fake_plugin_smoke.py`
- Test: `backend/tests/test_domain_runtime.py`

- [ ] **Step 1: Write failing swappability tests**

Create `backend/tests/test_fake_plugin_smoke.py` with all three kinds of proof:

```python
def test_fake_plugin_boots_via_env(monkeypatch):
    monkeypatch.setenv("DOMAIN_PLUGIN", "fake")
    ...


def test_fake_plugin_main_route_returns_sse(client, monkeypatch):
    monkeypatch.setenv("DOMAIN_PLUGIN", "fake")
    reset_runtime_for_tests()
    response = client.post("/agui/run", json={"messages": [{"role": "user", "content": "hello"}]})
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    body = response.text
    assert '\"type\":\"RUN_STARTED\"' in body
    assert '\"type\":\"STEP_STARTED\"' in body
    assert '\"type\":\"STEP_FINISHED\"' in body
    assert '\"type\":\"RUN_FINISHED\"' in body


def test_shared_modules_do_not_import_domains_travel_directly():
    ...
```

The second test is the actual swappability smoke request required by the spec.

- [ ] **Step 2: Run the new tests to confirm RED**

Run:

```bash
cd backend
uv run pytest tests/test_fake_plugin_smoke.py tests/test_domain_runtime.py -k "fake or imports" -v
```

Expected: FAIL because the fake plugin does not exist yet.

- [ ] **Step 3: Implement the fake plugin minimally**

Create:

```python
@dataclass(frozen=True)
class FakeState:
    last_message: str | None = None
```

The plugin should:

- serialize/deserialize `FakeState`
- echo or snapshot a trivial result path
- build a simple context string without travel fields
- return a minimal valid `AgentCard`

- [ ] **Step 4: Re-run the swappability tests to confirm GREEN**

Run:

```bash
cd backend
uv run pytest tests/test_fake_plugin_smoke.py tests/test_domain_runtime.py -k "fake or imports" -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/domains/fake backend/tests/test_fake_plugin_smoke.py backend/tests/test_domain_runtime.py
git commit -m "test: add fake plugin smoke coverage for swappable runtime"
```

---

## Task 10: Stabilize compatibility wrappers and environment defaults

**Files:**
- Modify: `backend/agent.py`
- Modify: `backend/state/__init__.py`
- Modify: `backend/state/manager.py`
- Modify: `backend/state/models.py`
- Modify: `backend/state/context_builder.py`
- Modify: `backend/data/__init__.py`
- Modify: `backend/tools/__init__.py`
- Modify: `backend/.env.example`
- Test: `backend/tests/test_agui_run.py`
- Test: `backend/tests/test_a2a_stream.py`

- [ ] **Step 1: Add thin compatibility wrappers where they reduce migration risk**

Examples:

```python
# backend/agent.py
from domains.travel.agent import create_travel_agent
```

```python
# backend/state/models.py
from domains.travel.state import TravelState, TravelContext, UIContext, AgentStatus, UserPreferences
```

Use wrappers only if an old import path is still referenced during the rollout.

- [ ] **Step 2: Document the startup plugin env var**

Add `DOMAIN_PLUGIN=travel` to `backend/.env.example`.

- [ ] **Step 3: Run focused regression tests**

Run:

```bash
cd backend
uv run pytest tests/test_agui_run.py tests/test_a2a_stream.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/agent.py backend/state/__init__.py backend/state/manager.py backend/state/models.py backend/state/context_builder.py backend/data/__init__.py backend/tools/__init__.py backend/.env.example
git commit -m "refactor: stabilize compatibility wrappers for plugin rollout"
```

---

## Task 11: Run the full verification matrix and architectural diff review

**Files:**
- Review: `backend/main.py`
- Review: `backend/a2a_server.py`
- Review: `backend/executor.py`
- Review: `backend/domain_runtime.py`
- Review: `backend/domains/travel/plugin.py`
- Review: `backend/domains/fake/plugin.py`
- Review: `backend/tests/test_domain_runtime.py`
- Review: `backend/tests/test_fake_plugin_smoke.py`

- [ ] **Step 1: Run the travel-plugin regression suite**

Run:

```bash
cd backend
DOMAIN_PLUGIN=travel uv run pytest tests/test_agui_run.py tests/test_a2a_stream.py tests/test_health.py tests/state tests/state-panel-sidebar -v
```

Expected: PASS.

- [ ] **Step 2: Run the fake-plugin smoke suite through the shared engine**

Run:

```bash
cd backend
DOMAIN_PLUGIN=fake uv run pytest tests/test_domain_runtime.py tests/test_fake_plugin_smoke.py -v
```

Expected: PASS, including the `/agui/run` smoke request.

Confirm the smoke request returns the normal AG-UI lifecycle sequence, not only a `200` status:

- `RUN_STARTED`
- `STEP_STARTED`
- `STEP_FINISHED`
- `RUN_FINISHED`

- [ ] **Step 3: Run the complete backend suite**

Run:

```bash
cd backend
DOMAIN_PLUGIN=travel uv run pytest -q
```

Expected: full backend suite passes, or only pre-existing unrelated failures remain with notes.

- [ ] **Step 4: Perform the architectural diff review**

Confirm all of the following:

- `backend/main.py`, `backend/a2a_server.py`, `backend/executor.py`, and `backend/converter.py` contain no travel field names for behavior decisions
- shared modules do not import `domains.travel` except through runtime/plugin-loading seams or explicit temporary wrappers
- fake plugin runs without editing shared engine files
- tool implementations do not mutate the common state store directly
- `get_runtime()` is the only runtime entrypoint used by shared modules

- [ ] **Step 5: Capture verification notes**

Record:

- exact commands run
- whether startup config swap (`travel` → `fake`) required source edits
- whether runtime validation rejected unsupported emissions as expected
- whether any compatibility wrappers remain and why

- [ ] **Step 6: Final commit**

```bash
git add backend docs/superpowers/specs/2026-04-21-domain-plugin-boundary-design.md
git commit -m "refactor: introduce swappable domain plugin runtime"
```

---

## Task 12: Execution handoff

**Files:**
- Review: `docs/superpowers/specs/2026-04-21-domain-plugin-boundary-design.md`
- Review: `docs/superpowers/plans/2026-04-21-domain-plugin-boundary.md`

- [ ] **Step 1: Confirm plan/spec alignment**

Verify the implementation still matches the approved spec:

- startup-selected single plugin
- opaque plugin-owned state
- typed runtime emissions
- no transport changes
- fake-plugin swappability proof with a real smoke request

- [ ] **Step 2: Choose execution mode**

Recommended execution approach: **Subagent-Driven** using `superpowers:subagent-driven-development`, because the work now splits cleanly into contract/runtime scaffolding, travel extraction, shared-engine rewiring, and swappability verification.
