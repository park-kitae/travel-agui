# Backend Compatibility Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove unused backend compatibility wrapper modules while keeping the real `state.store` implementation and runtime behavior intact.

**Architecture:** The backend already uses `domains.travel.*` for real implementation code, so this cleanup stays minimal. Add one regression test that proves the legacy wrapper files are gone, delete the pure re-export modules, then run targeted and broad backend tests to confirm the runtime still imports and executes through the direct domain paths.

**Tech Stack:** Python, pytest, FastAPI, ADK/A2A backend runtime

---

### File Map

**Create:**
- `backend/tests/test_compatibility_cleanup.py`

**Delete:**
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

**Retain:**
- `backend/state/store.py`

**Verify Against:**
- `backend/domain_runtime.py`
- `backend/main.py`
- `backend/executor.py`
- `backend/tests/test_domain_runtime.py`
- `backend/tests/test_a2a_stream.py`
- `backend/tests/state/test_models.py`
- `backend/tests/state/test_manager.py`
- `backend/tests/state/test_context_builder.py`
- `backend/tests/state-panel-sidebar/test_main_state_handling.py`
- `backend/tests/state-panel-sidebar/test_context_extraction.py`
- `backend/tests/state-panel-sidebar/test_snapshot_emission.py`

### Task 1: Add a Failing Regression Test for Wrapper Removal

**Files:**
- Create: `backend/tests/test_compatibility_cleanup.py`
- Test: `backend/tests/test_compatibility_cleanup.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
LEGACY_WRAPPERS = (
    BACKEND_ROOT / "agent.py",
    BACKEND_ROOT / "tools" / "__init__.py",
    BACKEND_ROOT / "tools" / "favorite_tools.py",
    BACKEND_ROOT / "tools" / "flight_tools.py",
    BACKEND_ROOT / "tools" / "hotel_tools.py",
    BACKEND_ROOT / "tools" / "input_tools.py",
    BACKEND_ROOT / "tools" / "tips_tools.py",
    BACKEND_ROOT / "data" / "__init__.py",
    BACKEND_ROOT / "data" / "flights.py",
    BACKEND_ROOT / "data" / "hotels.py",
    BACKEND_ROOT / "data" / "preferences.py",
    BACKEND_ROOT / "data" / "tips.py",
    BACKEND_ROOT / "state" / "__init__.py",
    BACKEND_ROOT / "state" / "manager.py",
    BACKEND_ROOT / "state" / "models.py",
    BACKEND_ROOT / "state" / "context_builder.py",
)


def test_legacy_compatibility_wrappers_are_removed() -> None:
    remaining = [
        path.relative_to(BACKEND_ROOT).as_posix()
        for path in LEGACY_WRAPPERS
        if path.exists()
    ]

    assert remaining == []


def test_state_store_remains_available() -> None:
    assert (BACKEND_ROOT / "state" / "store.py").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_compatibility_cleanup.py -q`
Expected: FAIL because the listed compatibility wrapper files still exist.

### Task 2: Remove the Pure Re-Export Wrapper Modules

**Files:**
- Delete: `backend/agent.py`
- Delete: `backend/tools/__init__.py`
- Delete: `backend/tools/favorite_tools.py`
- Delete: `backend/tools/flight_tools.py`
- Delete: `backend/tools/hotel_tools.py`
- Delete: `backend/tools/input_tools.py`
- Delete: `backend/tools/tips_tools.py`
- Delete: `backend/data/__init__.py`
- Delete: `backend/data/flights.py`
- Delete: `backend/data/hotels.py`
- Delete: `backend/data/preferences.py`
- Delete: `backend/data/tips.py`
- Delete: `backend/state/__init__.py`
- Delete: `backend/state/manager.py`
- Delete: `backend/state/models.py`
- Delete: `backend/state/context_builder.py`
- Test: `backend/tests/test_compatibility_cleanup.py`

- [ ] **Step 1: Delete the wrapper files**

Remove exactly these files and nothing else:

```text
backend/agent.py
backend/tools/__init__.py
backend/tools/favorite_tools.py
backend/tools/flight_tools.py
backend/tools/hotel_tools.py
backend/tools/input_tools.py
backend/tools/tips_tools.py
backend/data/__init__.py
backend/data/flights.py
backend/data/hotels.py
backend/data/preferences.py
backend/data/tips.py
backend/state/__init__.py
backend/state/manager.py
backend/state/models.py
backend/state/context_builder.py
```

- [ ] **Step 2: Re-run the regression test**

Run: `cd backend && uv run pytest tests/test_compatibility_cleanup.py -q`
Expected: PASS with `2 passed`.

- [ ] **Step 3: Check for any hidden legacy imports in runtime/test code**

Run: `cd backend && rg "from (agent|tools|data|state)\\b|import (agent|tools|data|state)\\b" . -g '*.py'`
Expected: only `from state.store import SerializedStateStore` references remain under runtime/tests, plus domain-local imports such as `from . import data`.

### Task 3: Verify Runtime and Test Surface Still Works

**Files:**
- Test: `backend/tests/test_domain_runtime.py`
- Test: `backend/tests/test_a2a_stream.py`
- Test: `backend/tests/state/test_models.py`
- Test: `backend/tests/state/test_manager.py`
- Test: `backend/tests/state/test_context_builder.py`
- Test: `backend/tests/state-panel-sidebar/test_main_state_handling.py`
- Test: `backend/tests/state-panel-sidebar/test_context_extraction.py`
- Test: `backend/tests/state-panel-sidebar/test_snapshot_emission.py`

- [ ] **Step 1: Run the focused regression suite**

Run: `cd backend && uv run pytest tests/test_compatibility_cleanup.py tests/test_domain_runtime.py tests/test_a2a_stream.py tests/state/test_models.py tests/state/test_manager.py tests/state/test_context_builder.py tests/state-panel-sidebar/test_main_state_handling.py tests/state-panel-sidebar/test_context_extraction.py tests/state-panel-sidebar/test_snapshot_emission.py -q`
Expected: PASS with no import errors.

- [ ] **Step 2: Run the full backend test suite**

Run: `cd backend && uv run pytest -q`
Expected: PASS with no `ModuleNotFoundError`, no broken state-store imports, and no runtime regressions.

- [ ] **Step 3: Review the final diff**

Run: `git diff -- backend`
Expected: one new regression test file, deletion of the pure re-export compatibility wrappers, and no changes to domain logic.

### Self-Review

- Spec coverage: the plan removes only the approved compatibility wrappers, keeps `backend/state/store.py`, and limits scope to runtime/test code.
- Placeholder scan: no `TODO`, `TBD`, or implicit "fix as needed" steps remain.
- Type consistency: all referenced modules and paths match the current backend layout and the approved design.
