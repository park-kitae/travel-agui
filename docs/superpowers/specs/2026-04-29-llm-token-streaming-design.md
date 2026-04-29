# LLM Token Streaming Design

**Date:** 2026-04-29  
**Status:** Approved  
**Approach:** Preserve the AG-UI/A2A pipeline and enable true LLM streaming in the ADK execution path

---

## Overview

The current chat stack is already shaped for streaming:

- `frontend/src/hooks/useAGUIChat.ts` reads SSE incrementally with `ReadableStream.getReader()`
- `backend/main.py` returns `StreamingResponse` with `text/event-stream`
- `backend/executor.py` emits `TaskArtifactUpdateEvent` text artifacts
- `backend/converter.py` converts text artifacts into `TEXT_MESSAGE_START`, `TEXT_MESSAGE_CHUNK`, and `TEXT_MESSAGE_END`

Despite that, assistant replies still appear all at once in the browser. The immediate root cause is visible in the backend logs:

- `google_adk.google.adk.models.google_llm: ... stream: False`

That means the transport pipeline is streaming-capable, but the actual ADK-to-Gemini model call is still running in non-streaming mode. The design goal is to switch that execution path to real token streaming without breaking the existing A2A, AG-UI, tool-call, or state-sync contracts.

---

## Goals

- Deliver true end-to-end assistant text streaming to the browser chat bubble.
- Keep the existing `main.py -> a2a_server.py -> executor.py -> converter.py -> frontend` architecture intact.
- Preserve current tool lifecycle events, state snapshot/delta events, and UI request events.
- Keep the frontend message model and event handling stable unless a minimal adjustment is necessary.
- Add regression coverage proving that text arrives as multiple ordered chunks rather than one final payload.

---

## Non-Goals

- Replacing A2A with a direct frontend-to-model transport.
- Rebuilding the frontend chat rendering model.
- Introducing fake streaming that replays a final response in slices.
- Changing AG-UI event names or inventing a second text event protocol.

---

## Approach Comparison

### Approach 1 — Enable real streaming in the ADK execution path (**recommended**)

Keep the current gateway, A2A server, converter, and frontend contracts. Change the ADK/model execution path so the runner yields partial text chunks as they are generated, and forward each chunk through the existing `TaskArtifactUpdateEvent(TextPart)` pipeline.

**Pros**
- Smallest architectural change.
- Preserves the already-working SSE and AG-UI event pipeline.
- Keeps tool calls, snapshots, and UI request events in the same orchestration path.
- Gives the browser true token-like incremental rendering.

**Cons**
- Requires precise alignment with the streaming API exposed by the current ADK version.
- Needs care around chunk boundaries and final-chunk signaling.

### Approach 2 — Bypass A2A and stream directly from the gateway

Have `backend/main.py` call Gemini directly and stream raw model output to the frontend.

**Pros**
- Can be simpler if viewed in isolation.

**Cons**
- Breaks the current separation between gateway, A2A, and executor concerns.
- Duplicates orchestration logic now owned by the A2A/ADK path.
- Higher regression risk for tools, state, and future domain plugins.

### Approach 3 — Pseudo-stream the final answer

Keep the current non-streaming model call, but slice the completed answer into delayed chunks before sending it to the frontend.

**Pros**
- Fastest visible change.

**Cons**
- Not true streaming.
- Tool and status timing becomes misleading.
- Hides the real latency problem instead of solving it.

### Recommendation

Choose **Approach 1**.

The existing system already has the right streaming envelope. The missing piece is the model execution mode, not the transport. The correct fix is to make the ADK runner produce partial text and keep forwarding those partials through the current event pipeline.

---

## Current Failure Mode

The current path behaves like this:

1. The frontend opens `/agui/run` and reads SSE incrementally.
2. `backend/main.py` forwards the request to A2A using `send_message_streaming(...)`.
3. `backend/executor.py` iterates ADK events and converts text parts to `TaskArtifactUpdateEvent`.
4. `backend/converter.py` maps those artifact updates to AG-UI text events.
5. The frontend appends each `TEXT_MESSAGE_CHUNK` to the current assistant message.

The problem is that ADK is currently producing text only after the model finishes. So the downstream layers technically stream, but they only receive one large final text payload.

---

## Proposed Architecture

### Stable layers

These layers should remain structurally unchanged:

- `backend/main.py`
- `backend/a2a_server.py`
- `backend/converter.py`
- `frontend/src/hooks/useAGUIChat.ts`

Their contracts are already correct for incremental text delivery.

### Primary change surface

The main implementation work belongs in:

- `backend/executor.py`
- optionally `backend/domains/travel/agent.py` if the agent or model configuration must explicitly opt into streaming

### Optional support changes

- tests under `backend/tests/`
- frontend E2E coverage under `frontend/tests/e2e/`

---

## Data Flow

### 1. Frontend

`frontend/src/hooks/useAGUIChat.ts` already does the right thing:

- sends a `POST` request to `/agui/run`
- reads `response.body` incrementally
- parses each SSE `data:` line
- appends `TEXT_MESSAGE_CHUNK.delta` into the current assistant bubble

Because of that, no protocol redesign is needed on the frontend. If the backend emits more frequent text chunks, the existing UI will render them incrementally.

### 2. Gateway

`backend/main.py` should continue to:

- return `StreamingResponse(event_stream())`
- use `text/event-stream`
- set `Cache-Control: no-cache`
- set `X-Accel-Buffering: no`

The gateway remains a pass-through stream coordinator and should not become model-specific.

### 3. Executor

`backend/executor.py` is the critical boundary.

The executor must consume the ADK runner in a mode where partial text is yielded before final completion. For each partial text emission:

- create `TaskArtifactUpdateEvent`
- wrap the text in `TextPart(text=<chunk>)`
- keep `append=True`
- set `last_chunk=False` until the actual final text chunk
- set `last_chunk=True` only for the final text fragment of the assistant turn

Tool call and tool response handling must remain in the same path. Text streaming must not bypass tool lifecycle orchestration.

### 4. Converter

`backend/converter.py` can keep the current event mapping:

- first text chunk -> `TEXT_MESSAGE_START`
- each chunk -> `TEXT_MESSAGE_CHUNK`
- final chunk -> `TEXT_MESSAGE_END`

The converter should not need semantic changes as long as `last_chunk` is emitted correctly by the executor/A2A layer.

---

## Behavioral Rules

### Text message lifecycle

For one assistant turn, the intended AG-UI sequence is:

1. `TEXT_MESSAGE_START`
2. one or more `TEXT_MESSAGE_CHUNK`
3. `TEXT_MESSAGE_END`

The system must not emit multiple start/end pairs for one continuous assistant response unless the underlying protocol explicitly begins a new assistant message.

### Tool lifecycle ordering

The existing ordering guarantees must stay intact:

1. optional state updates caused by tool call interpretation
2. `TOOL_CALL_START`
3. `TOOL_CALL_END`
4. optional snapshot or UI request events from tool results
5. resumed assistant text chunks

Streaming text must coexist with tools, not flatten their order.

### State and UI events

`STATE_DELTA`, `STATE_SNAPSHOT`, `USER_INPUT_REQUEST`, and `USER_FAVORITE_REQUEST` remain unchanged. This design changes text timing, not state semantics.

---

## Error Handling

### Pre-stream failure

If setup fails before any model text is emitted:

- keep the current `RUN_STARTED -> RUN_ERROR -> RUN_FINISHED` structure
- do not emit text message events

### Mid-stream failure

If some text chunks were already emitted and then the stream fails:

- keep already-sent text visible in the assistant bubble
- terminate the run with `RUN_ERROR`
- still emit `RUN_FINISHED`
- avoid emitting duplicate `TEXT_MESSAGE_END` if the stream never reached a legitimate final text chunk

### Chunk finalization rule

Only the actual final assistant text chunk may close the message. Premature `last_chunk=True` would split one answer into multiple bubbles or incorrectly finalize a still-running response.

---

## Verification Strategy

### Backend unit tests

Add or update tests to verify:

- multiple text chunks yield multiple `TEXT_MESSAGE_CHUNK` events in order
- the first text chunk opens exactly one `TEXT_MESSAGE_START`
- only the final text chunk yields `TEXT_MESSAGE_END`
- mixed tool/text flows preserve ordering
- failures still produce `RUN_ERROR` and `RUN_FINISHED`

Primary files:

- `backend/tests/test_a2a_stream.py`
- `backend/tests/test_agui_run.py`
- any executor-focused streaming tests if needed

### Frontend/E2E tests

Add or update coverage to verify:

- the assistant bubble becomes visible before the final full answer is complete
- text length increases over time during one response
- tool-call UI still appears correctly during a streamed run

### Runtime verification

Success is not only test-based. A real run should also show:

- backend logs indicating model streaming is enabled rather than `stream: False`
- browser-visible incremental assistant rendering
- no regression in state panel, user-input form requests, or favorite collection flows

---

## Implementation Notes

- Prefer the smallest fix that changes the ADK execution mode instead of rewriting transport code.
- Keep `backend/main.py` and `frontend/src/hooks/useAGUIChat.ts` as stable as possible.
- If the ADK API emits text deltas differently from the current `part.text` assumption, adapt only the executor normalization layer and keep downstream contracts unchanged.
- If the A2A task artifact store requires an initial non-append artifact before appended chunks, fix that at the executor boundary rather than changing the frontend protocol.

---

## Success Criteria

- Assistant answers visibly render incrementally in the browser instead of appearing all at once.
- The backend uses true model streaming rather than non-streaming completion.
- Existing tool-call, state, and UI request flows remain intact.
- Tests prove ordered chunk delivery and finalization behavior.

---

## Open Question Resolved

The desired behavior for this change is explicitly:

> Show the assistant response in the browser as true end-to-end token-style streaming, not as a single final payload and not as fake replayed chunks.
