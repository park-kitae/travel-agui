# Domain Plugin Boundary Design

**Date:** 2026-04-21  
**Status:** Approved  
**Approach:** Startup-configured `DomainPlugin` boundary

---

## Overview

The current backend already has a strong common chat pipeline:

- `backend/main.py` receives AG-UI requests and returns SSE responses
- `backend/a2a_server.py` exposes the ADK agent through A2A
- `backend/executor.py` orchestrates agent execution and tool lifecycle events
- `backend/converter.py` translates A2A events into AG-UI events

The problem is that travel-specific concerns are mixed into this pipeline through:

- `backend/agent.py` travel prompt and tool registration
- `backend/state/models.py` travel-specific state schema
- `backend/state/context_builder.py` travel-specific context injection
- `backend/state/manager.py` travel-specific tool-call and tool-result interpretation
- `backend/tools/*` and `backend/data/*`

The goal is to preserve the chat transport/orchestration once and make domains swappable so future work focuses on **what domain data exists and how it flows**, not on rebuilding chat behavior.

---

## Goals

- Keep the core chat request/response pipeline domain-agnostic.
- Make domain behavior replaceable through a single startup-selected plugin.
- Ensure new domains can be added without modifying `main.py`, `executor.py`, or `converter.py`.
- Move prompt rules, tools, state schema, and context rendering behind a domain contract.
- Preserve the existing AG-UI and A2A event model so the frontend transport remains unchanged.

---

## Non-Goals

- Multi-domain routing in a single server process.
- Declarative JSON/YAML-only domain definition.
- Changing AG-UI event types or the A2A streaming transport.
- Rebuilding the frontend around domain-specific UI in this phase.

---

## Approach Comparison

### Approach 1 — Thin Domain Plugin boundary (**recommended**)

Keep the chat engine in common backend modules and introduce a `DomainPlugin` contract that owns:

- agent creation
- domain state schema
- client-state merge rules
- tool-call and tool-result interpretation
- context block rendering
- domain metadata for the agent card

**Pros**
- Preserves the current working request/streaming pipeline.
- Creates a clean swap boundary with minimal leakage.
- Lets each domain keep code-level flexibility for state and tools.
- Makes regression testing straightforward: same engine, different plugin.

**Cons**
- Requires extraction work in `state/manager.py` and `context_builder.py`.
- Needs a small shared contract layer for plugin loading and state access.

### Approach 2 — Full domain-owned app packages

Make each domain package own nearly everything except raw HTTP/SSE transport.

**Pros**
- Very flexible for domain teams.
- Fewer constraints on state and agent design.

**Cons**
- The chat lifecycle starts leaking back into each domain.
- Harder to guarantee that new domains preserve transport behavior.
- Higher duplication risk.

### Approach 3 — Config-driven domain definitions

Move prompts, tools, and field definitions into configuration files and keep a generic engine reading them.

**Pros**
- Fast for simple domains.
- Easy to add small variants.

**Cons**
- Breaks down quickly once state logic and tool-result mapping become non-trivial.
- Pushes code complexity into a hard-to-maintain generic interpreter.
- Weak fit for the current Python codebase.

### Recommendation

Choose **Approach 1**.

It best matches the current architecture and the desired operating model: the chat lifecycle remains common, while domain authors only implement the rules and data shape of their domain.

---

## Boundary Rule

The key architectural rule is:

> **The common engine must not know the meaning of domain state.**

That means the common engine may store, pass, and stream domain state, but it must not contain logic like:

- "destination", "check_in", or other travel field names
- hotel vs flight branching
- domain-specific prompt augmentation rules
- tool-specific state interpretation tied to one business domain

If a future domain requires editing `main.py`, `executor.py`, or `converter.py` to explain what its data means, the boundary has failed.

This rule also applies to **state storage and event emission**:

- common code may store plugin-owned state by thread/session key
- common code may persist or retrieve that state only as an opaque runtime value
- common code may not inspect domain fields to decide behavior
- plugins may not emit transport-native payloads with arbitrary ad hoc dict shapes

---

## Proposed Architecture

### Common engine (stays shared)

- `backend/main.py`
  - request intake
  - AG-UI input normalization
  - client state handoff to the plugin runtime
  - context-enriched message dispatch
  - SSE response streaming

- `backend/a2a_server.py`
  - A2A server bootstrap
  - ADK `Runner` wiring using the active plugin agent
  - agent card assembly using plugin metadata

- `backend/executor.py`
  - session acquisition
  - ADK run loop
  - tool call lifecycle emission
  - plugin hook invocation for state mutation and snapshots

- `backend/converter.py`
  - A2A → AG-UI event conversion
  - text, tool-call, state snapshot, and state delta emission

- `backend/domain_runtime.py` (**new**)
  - loads the active plugin from startup config
  - exposes the shared plugin instance to the common engine
  - provides any shared runtime wrappers/helpers

### Domain package (swappable)

Example target layout:

```text
backend/
  domains/
    travel/
      __init__.py
      plugin.py
      agent.py
      state.py
      context.py
      tools/
      data/
```

Each domain package owns:

- prompt/instruction behavior
- tool definitions and registration
- domain data access
- state schema and empty-state construction
- client-state merge rules
- tool-call and tool-result interpretation
- context rendering rules
- domain-specific agent card skill metadata

---

## Domain Contract

The common engine talks to a domain only through a contract. The exact Python type may be a `Protocol`, abstract base class, or a lightweight concrete interface, but the responsibilities are fixed.

Illustrative contract:

```python
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


RuntimeEmission = RuntimeDeltaPayload | RuntimeSnapshotPayload | RuntimeUiRequestPayload


class DomainPlugin(Protocol):
    id: str

    def build_agent(self) -> LlmAgent: ...
    def build_agent(self) -> LlmAgent: ...
    def empty_state(self) -> object: ...
    def serialize_state(self, state: object) -> dict: ...
    def deserialize_state(self, raw_state: dict | None) -> object: ...
    def merge_client_state(self, current_state: object, raw_state: dict) -> object: ...
    def apply_tool_call(self, current_state: object, tool_name: str, args: dict) -> tuple[object, list[RuntimeEmission]]: ...
    def apply_tool_result(self, current_state: object, tool_name: str, result: dict) -> tuple[object, list[RuntimeEmission]]: ...
    def build_context_block(self, state: object, user_message: str) -> str: ...
    def agent_card(self) -> AgentCard: ...
```

The important point is not the exact signature but the dependency direction:

- **Common engine depends on the plugin contract**
- **Plugins depend on common transport/event infrastructure**
- **Common engine does not depend on any domain field names**

### Contract rules

1. **Plugin state is plugin-owned**
   - The plugin defines the in-memory state type.
   - The common runtime treats it as opaque.
   - The plugin must provide `serialize_state()` / `deserialize_state()` so persistence format is explicit.

2. **Persistence format is runtime-safe, not domain-inferred**
   - Common storage persists only serialized plugin state.
   - Common code may store/retrieve by thread or session key.
   - Common code must not access domain subfields during persistence.

3. **Mutability safety belongs to the plugin contract**
   - Plugins return the next state value explicitly.
   - Plugins must not rely on mutating shared state store objects in place.
   - The runtime always replaces the per-thread state with the returned state.

4. **Plugin emissions use typed runtime payloads only**
   - Plugins may emit only `RuntimeDeltaPayload`, `RuntimeSnapshotPayload`, or `RuntimeUiRequestPayload`.
   - Plugins must not emit raw AG-UI or A2A transport envelopes.
   - The common runtime converts typed runtime payloads into the existing stream format.

5. **UI request events are runtime-level concepts with domain payloads**
   - A plugin may request known UI-facing events through `RuntimeUiRequestPayload`.
   - The runtime owns validation of allowed `event_name` values.
   - Unsupported event names fail fast at runtime/plugin boundary.

6. **Agent card ownership is fully domain-owned**
   - The plugin returns the full `AgentCard` metadata contract, not just skills.
   - The common runtime may only inject environment-derived URL/host values if necessary.

---

## Runtime Selection Model

The active domain is selected at **startup config** time.

Example:

```env
DOMAIN_PLUGIN=travel
```

`backend/domain_runtime.py` resolves that identifier and loads:

- `backend/domains/travel/plugin.py`

This keeps the first version simple:

- one deployment = one active domain
- one backend process = one plugin instance
- no per-request routing complexity

The design should still avoid assumptions that would prevent multi-domain routing later, but that is explicitly deferred.

At runtime this means:

- plugin loading is a startup-only operation
- a failed plugin load aborts process startup
- no per-request plugin resolution logic exists in phase 1
- every thread in a process uses the same active plugin

---

## Data Flow

### 1. Request intake

`backend/main.py` receives `RunAgentInput`, extracts the latest user message, and reads `state` from the incoming body.

Instead of manipulating travel-specific state directly, it calls the active plugin runtime to:

- get or initialize the current domain state for the thread
- merge incoming client state into that domain state
- build the context-enriched user message

The runtime persists thread state using `serialize_state()` / `deserialize_state()` and never reaches into domain-specific subfields.

### 2. Agent execution

`backend/a2a_server.py` builds the ADK `Runner` from `plugin.build_agent()`.

`AgentCard` metadata is also sourced from `plugin.agent_card()`, with only environment-dependent endpoint values patched by the common bootstrap if needed.

The executor remains responsible for ADK execution mechanics, not domain semantics.

### 3. Tool call lifecycle

When ADK emits a function call, `backend/executor.py`:

- emits common working/tool lifecycle events
- passes `(state, tool_name, args)` to `plugin.apply_tool_call(...)`
- receives updated state plus typed runtime emissions
- wraps those payloads in the existing event stream

Argument validation rules:

- ADK/tool signature validation remains part of normal tool execution
- domain semantic validation belongs in the plugin/tool layer
- the executor does not reinterpret tool args by domain

### 4. Tool result lifecycle

When ADK emits a function response, `backend/executor.py`:

- passes `(state, tool_name, result)` to `plugin.apply_tool_result(...)`
- receives updated state plus typed runtime emissions
- emits those payloads without needing to understand their meaning

Tool exception normalization rules:

- tools may raise domain exceptions internally
- the plugin/runtime boundary is responsible for converting them into normalized failure payloads or propagated runtime errors
- common executor code must not branch on domain exception types

### 5. Response conversion

`backend/converter.py` remains unchanged in principle. It continues to translate the event stream into AG-UI SSE events.

This is critical: **the converter should care about event types, not domain meaning**.

The converter should only ever see common runtime event shapes, never plugin-private structures.

---

## File Responsibility Changes

### Current travel-specific files to extract behind the boundary

- `backend/agent.py`
  - becomes travel-domain agent assembly inside `domains/travel/agent.py` or `plugin.py`

- `backend/tools/*`
  - move under `domains/travel/tools/*`

- `backend/data/*`
  - move under `domains/travel/data/*`

- `backend/state/models.py`
  - travel-specific schema moves into `domains/travel/state.py`
  - common state container logic should no longer assume travel field names

- `backend/state/context_builder.py`
  - travel-specific context formatting moves into `domains/travel/context.py`

- `backend/state/manager.py`
  - split into:
    - common per-thread state store/runtime orchestration
    - plugin-owned merge/tool interpretation rules

### New common responsibility split

- `backend/domain_runtime.py`
  - active plugin loading
  - serialized state store access
  - plugin emission validation
  - plugin/runtime exception normalization

- `backend/state/store.py` (**optional split if needed**)
  - thread/session keyed opaque serialized state persistence
  - no domain-specific branching

### Common files expected to remain stable after the refactor

- `backend/main.py`
- `backend/a2a_server.py`
- `backend/executor.py`
- `backend/converter.py`

Future domain additions should not require behavior changes in these files.

---

## Error Handling Model

### Common engine errors

Handled in the common layer:

- AG-UI request parsing/validation failures
- SSE/A2A transport errors
- ADK runner execution failures
- plugin loading failures at startup
- event encoding/serialization failures
- unsupported runtime UI event names
- invalid plugin emission types

### Domain plugin errors

Handled by the plugin or normalized by the runtime:

- invalid tool arguments for the domain
- domain data lookup failures
- context rendering errors
- client-state merge failures
- tool-result interpretation failures
- state serialization/deserialization failures

The common engine should never need domain-specific `if` branches to explain domain errors. It should only handle normalized plugin/runtime exceptions.

### Tool ownership clarification

- tool registration is domain-owned
- tool implementation is domain-owned
- tool arguments are interpreted semantically by the domain
- tool lifecycle timing/events are common-engine owned
- direct mutation of the common state store from tools is forbidden
- all state updates must flow back through plugin hooks

---

## Testing Strategy

### 1. Common contract tests

Verify that the shared engine works the same regardless of which plugin is loaded.

Examples:

- a plugin can merge client state and produce an enriched message
- tool call lifecycle still emits start/end/state events
- tool result lifecycle still emits snapshot/delta events
- SSE output shape remains stable
- runtime rejects unsupported plugin emission types
- runtime rejects unsupported UI event names
- common modules boot successfully with a fake plugin

### 2. Plugin unit tests

Each plugin tests its own behavior:

- empty state creation
- client-state merge rules
- context block rendering
- tool-call state mutation rules
- tool-result state mutation and snapshot generation

### 3. Swappability tests

Add a minimal fake domain plugin for tests and prove that:

- the common engine boots
- the request/response lifecycle still works
- no travel-specific imports or field assumptions leak into common modules

Verification examples:

- boot the server with `DOMAIN_PLUGIN=fake` and assert startup success
- run one smoke request and assert normal AG-UI lifecycle events are returned
- assert shared modules do not import `domains.travel` directly
- assert shared modules contain no travel field names such as `destination`, `check_in`, `check_out`, `hotel`, `flight`

This is the test that guards the architectural goal, not just correctness.

---

## Migration Strategy

Refactor in stages to keep the system working.

### Stage 1 — Introduce the domain contract and runtime

- add `domain_runtime.py`
- define the `DomainPlugin` contract
- load the travel domain through the runtime without changing behavior yet
- acceptance gate: travel smoke flow still passes with runtime wrapper in place
- rollback: revert startup wiring to current direct travel module imports

### Stage 2 — Wrap the current travel implementation as a plugin

- move or adapt travel agent assembly into `domains/travel/plugin.py`
- route `a2a_server.py` through the plugin
- acceptance gate: travel tool registration and agent card output match baseline behavior
- rollback: point runtime back to compatibility adapter around current travel modules

### Stage 3 — Extract state meaning out of the common layer

- move travel schema/context logic into the travel domain package
- shrink `state/manager.py` into common storage/runtime responsibilities
- replace travel-specific merge/apply logic with plugin hooks
- invalidate or migrate existing in-memory thread state at process restart during this stage
- acceptance gate: common modules no longer reference travel field names
- rollback: restore compatibility adapter that reuses pre-extraction travel state manager

### Stage 4 — Add a fake or sample second domain

- prove that a non-travel plugin can run without common-file edits
- use tests to lock in the boundary
- acceptance gate: fake plugin boot + smoke request + no shared-file edits

### State/session rollout rule

Because the current store is in-memory only, refactor rollout may invalidate active process memory on restart. That is acceptable in this phase, but it must be explicit:

- no attempt is made to preserve in-memory sessions across process restarts
- serialized plugin state format becomes the future persistence contract
- if durable persistence is added later, migration must occur at the serialized-state layer, not through common-module field inspection

---

## Success Criteria

The boundary is successful when all of the following are true:

1. A new domain can be added under `backend/domains/<domain>/...` and loaded through startup config.
2. Swapping from `travel` to `fake` in startup config requires no source edits in shared modules.
3. `main.py`, `executor.py`, and `converter.py` are unchanged when adding the fake plugin.
4. Shared modules contain no direct `domains.travel` imports and no travel field names used for behavior decisions.
5. Booting with the travel plugin still passes one end-to-end smoke request through the existing AG-UI/A2A flow.
6. Booting with a fake plugin passes one smoke request through the same lifecycle event sequence.
7. Runtime validation rejects unsupported plugin emission types and unsupported UI event names.

---

## Decision Summary

- Use a **startup-configured single active domain plugin**.
- Keep the existing chat engine common.
- Move prompts, tools, state schema, context building, and tool interpretation into domain packages.
- Enforce the rule that the common engine must not know domain-state meaning.
- Validate the architecture with swappability tests, not only behavioral tests.
