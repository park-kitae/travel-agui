# LLM Token Streaming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable true end-to-end assistant token streaming in the existing AG-UI/A2A/ADK pipeline so browser chat bubbles render incrementally instead of appearing all at once.

**Architecture:** Keep `backend/main.py`, `backend/a2a_server.py`, `backend/converter.py`, and the frontend SSE reader intact. Switch the ADK runner in `backend/executor.py` to `RunConfig(streaming_mode=StreamingMode.SSE)`, emit partial text chunks as `TaskArtifactUpdateEvent(TextPart)`, skip the duplicated aggregated final text event when partial text was already shown, and ensure the first text artifact uses `append=False` so the A2A task store accepts streamed chunks.

**Tech Stack:** Python 3.11+, FastAPI, Google ADK, a2a-sdk, ag-ui-protocol, pytest, Playwright, uv, React 18, Vite

---

## Implementation Notes

- Preserve the current request/response contract. This is a streaming-mode change, not a transport rewrite.
- Use `google.adk.agents.run_config.RunConfig(streaming_mode=StreamingMode.SSE)` in the executor path.
- ADK SSE mode yields both partial text events and a final aggregated text event. The executor must suppress duplicate final text when partial text for the same turn has already been emitted.
- The first text artifact for a streamed assistant turn must use `append=False`; subsequent chunks for the same artifact use `append=True`.
- Keep tool-call, tool-result, state delta, state snapshot, and UI request ordering unchanged.

---

## File Map

### Modify

- `backend/executor.py` — enable ADK SSE mode, add streamed-text artifact bookkeeping, suppress duplicate aggregated final text, keep tool/state ordering intact
- `backend/tests/test_executor.py` — add executor-level tests for SSE run config, first-chunk append behavior, and duplicate-final-text suppression
- `backend/tests/test_a2a_stream.py` — add stream conversion tests for multiple text chunks in one assistant turn
- `backend/tests/test_agui_run.py` — add `/agui/run` regression proving chunked A2A text is preserved as multiple AG-UI text events
- `frontend/tests/e2e/response-capture.spec.ts` — add or extend an SSE-capture regression that proves assistant text grows incrementally in the UI

### Verify unchanged

- `backend/main.py` — keep `StreamingResponse` and SSE headers as-is
- `backend/converter.py` — keep existing text event mapping, relying on correct `last_chunk` signaling
- `frontend/src/hooks/useAGUIChat.ts` — keep chunk accumulation logic unchanged

### Test focus

- `backend/tests/test_executor.py`
- `backend/tests/test_a2a_stream.py`
- `backend/tests/test_agui_run.py`
- `frontend/tests/e2e/response-capture.spec.ts`

---

## Task 1: Lock in red tests for streamed text behavior

**Files:**
- Modify: `backend/tests/test_executor.py`
- Modify: `backend/tests/test_a2a_stream.py`
- Modify: `backend/tests/test_agui_run.py`

- [ ] **Step 1: Add failing executor tests for streaming mode and duplicate suppression**

Extend `backend/tests/test_executor.py` with helpers and assertions that describe the exact new behavior:

```python
from google.adk.agents.run_config import StreamingMode


def _make_text_adk_event(text: str, *, partial: bool, final: bool):
    part = MagicMock()
    part.text = text
    part.function_call = None
    part.function_response = None

    content = MagicMock()
    content.parts = [part]

    event = MagicMock()
    event.content = content
    event.partial = partial
    event.is_final_response.return_value = final
    return event


@pytest.mark.asyncio
async def test_execute_requests_sse_streaming_mode() -> None:
    runner = MagicMock()
    runner.app_name = "runtime.plugin.app"
    runner.run_async = MagicMock(return_value=_empty_runner_events())

    session_service = MagicMock()
    session_service.get_session = AsyncMock(return_value=object())
    session_service.create_session = AsyncMock()

    executor = ADKAgentExecutor(adk_runner=runner, adk_session_service=session_service)

    context = MagicMock(task_id="task-1", context_id="ctx-1")
    context.get_user_input.return_value = "안녕하세요"
    context.metadata = {}

    event_queue = MagicMock()
    event_queue.enqueue_event = AsyncMock()

    await executor.execute(context, event_queue)

    run_config = runner.run_async.call_args.kwargs["run_config"]
    assert run_config.streaming_mode == StreamingMode.SSE


@pytest.mark.asyncio
async def test_execute_emits_first_text_chunk_without_append_and_skips_duplicate_final_text() -> None:
    runner = MagicMock()
    runner.app_name = "runtime.plugin.app"
    runner.run_async = MagicMock(return_value=_async_gen(
        _make_text_adk_event("안", partial=True, final=False),
        _make_text_adk_event("녕", partial=True, final=False),
        _make_text_adk_event("안녕", partial=False, final=True),
    ))

    session_service = MagicMock()
    session_service.get_session = AsyncMock(return_value=object())
    session_service.create_session = AsyncMock()

    executor = ADKAgentExecutor(adk_runner=runner, adk_session_service=session_service)

    context = MagicMock(task_id="task-1", context_id="ctx-1")
    context.get_user_input.return_value = "안녕하세요"
    context.metadata = {}

    event_queue = MagicMock()
    event_queue.enqueue_event = AsyncMock()

    await executor.execute(context, event_queue)

    text_events = [call.args[0] for call in event_queue.enqueue_event.call_args_list if getattr(call.args[0], "artifact", None)]
    text_artifacts = [event for event in text_events if getattr(event.artifact.parts[0].root, "text", None)]

    assert [event.artifact.parts[0].root.text for event in text_artifacts] == ["안", "녕"]
    assert text_artifacts[0].append is False
    assert text_artifacts[1].append is True
    assert text_artifacts[0].last_chunk is False
    assert text_artifacts[1].last_chunk is False
```

- [ ] **Step 2: Run the executor tests to confirm RED**

Run:

```bash
uv run pytest tests/test_executor.py -v
```

Expected: FAIL because `executor.py` still calls `run_async()` without `RunConfig(streaming_mode=StreamingMode.SSE)`, emits text with `append=True` from the first chunk, and does not suppress the duplicated final aggregate text.

- [ ] **Step 3: Add a failing converter test for one assistant turn with multiple chunks**

Extend `backend/tests/test_a2a_stream.py` with a focused conversion regression:

```python
async def test_multiple_text_artifacts_produce_one_start_two_chunks_and_one_end():
    events = await collect_stream([
        make_text_artifact("안", last_chunk=False),
        make_text_artifact("녕", last_chunk=True),
    ])

    types = [event["type"] for event in events]
    deltas = [event["delta"] for event in events if event["type"] == "TEXT_MESSAGE_CHUNK"]

    assert types.count("TEXT_MESSAGE_START") == 1
    assert deltas == ["안", "녕"]
    assert types.count("TEXT_MESSAGE_END") == 1
```

- [ ] **Step 4: Run the converter test to confirm current behavior is covered**

Run:

```bash
uv run pytest tests/test_a2a_stream.py::test_multiple_text_artifacts_produce_one_start_two_chunks_and_one_end -v
```

Expected: PASS or near-pass. If it already passes, keep it as a guardrail before executor changes.

- [ ] **Step 5: Add a failing `/agui/run` chunk-preservation regression**

Extend `backend/tests/test_agui_run.py` with a mocked A2A stream that yields two text artifacts:

```python
async def test_run_agent_preserves_multiple_text_chunks_from_a2a_stream(client):
    async def mock_a2a_stream(_request):
        yield make_event_response(make_text_artifact("안", last_chunk=False).root.result)
        yield make_event_response(make_text_artifact("녕", last_chunk=True).root.result)

    mock_card = MagicMock()
    mock_a2a_client = MagicMock()
    mock_a2a_client.send_message_streaming = MagicMock(side_effect=mock_a2a_stream)
    runtime = make_runtime(enriched_message="안녕하세요")

    with (
        patch("main.httpx.AsyncClient") as mock_http,
        patch("main.AgentCard.model_validate", return_value=mock_card),
        patch("main.A2AClient", return_value=mock_a2a_client),
        patch("main.initialize_runtime_or_die"),
        patch("main.get_runtime", return_value=runtime),
    ):
        mock_response = AsyncMock()
        mock_response.json = MagicMock(return_value={"name": "test-agent", "url": "http://test"})
        mock_response.raise_for_status = MagicMock()

        mock_http_instance = AsyncMock()
        mock_http_instance.get = AsyncMock(return_value=mock_response)
        mock_http.return_value.__aenter__ = AsyncMock(return_value=mock_http_instance)
        mock_http.return_value.__aexit__ = AsyncMock(return_value=None)

        response = await client.post("/agui/run", json=make_request_body())

    events = parse_sse_events(response.text)
    chunks = [event["delta"] for event in events if event.get("type") == "TEXT_MESSAGE_CHUNK"]
    assert chunks == ["안", "녕"]
```

- [ ] **Step 6: Run the `/agui/run` regression**

Run:

```bash
uv run pytest tests/test_agui_run.py::test_run_agent_preserves_multiple_text_chunks_from_a2a_stream -v
```

Expected: PASS or near-pass. Keep it to prove the gateway path already preserves chunked A2A responses.

- [ ] **Step 7: Commit the test harness baseline**

```bash
git add tests/test_executor.py tests/test_a2a_stream.py tests/test_agui_run.py
git commit -m "test: cover token streaming behavior"
```

---

## Task 2: Enable ADK SSE mode and emit correct text artifacts

**Files:**
- Modify: `backend/executor.py`
- Test: `backend/tests/test_executor.py`

- [ ] **Step 1: Add a focused text-stream tracker to `ADKAgentExecutor`**

Update the executor state in `backend/executor.py` so each context tracks a current text artifact and whether partial text has already been emitted:

```python
from dataclasses import dataclass


@dataclass
class _TextStreamState:
    artifact_id: str
    has_emitted_text: bool = False
    saw_partial_text: bool = False


class ADKAgentExecutor(AgentExecutor):
    def __init__(self, adk_runner: Runner, adk_session_service: InMemorySessionService, runtime: DomainRuntime | None = None):
        self._runner = adk_runner
        self._session_service = adk_session_service
        if runtime is None:
            initialize_runtime_or_die()
            runtime = get_runtime()
        self._runtime = runtime
        self._app_name = get_runtime_app_name(adk_runner)
        self._tool_call_ids: dict[str, dict[str, str]] = {}
        self._text_streams: dict[str, _TextStreamState] = {}
```

- [ ] **Step 2: Add helper methods that emit the first text artifact with `append=False`**

Add helpers to `backend/executor.py`:

```python
    def _get_text_stream_state(self, context_id: str) -> _TextStreamState:
        state = self._text_streams.get(context_id)
        if state is None:
            state = _TextStreamState(artifact_id=str(uuid.uuid4()))
            self._text_streams[context_id] = state
        return state

    async def _enqueue_text_chunk(
        self,
        event_queue: EventQueue,
        task_id: str,
        context_id: str,
        text: str,
        *,
        is_partial: bool,
        is_last: bool,
    ) -> None:
        if not text:
            return

        state = self._get_text_stream_state(context_id)
        if is_partial:
            state.saw_partial_text = True

        await event_queue.enqueue_event(
            TaskArtifactUpdateEvent(
                task_id=task_id,
                context_id=context_id,
                artifact=Artifact(
                    artifact_id=state.artifact_id,
                    parts=[Part(root=TextPart(text=text))],
                ),
                append=state.has_emitted_text,
                last_chunk=is_last,
            )
        )
        state.has_emitted_text = True

        if is_last:
            self._text_streams.pop(context_id, None)
```

- [ ] **Step 3: Run ADK in SSE mode and suppress duplicate aggregated final text**

Replace the current `run_async()` invocation and text branch in `backend/executor.py` with:

```python
from google.adk.agents.run_config import RunConfig, StreamingMode

            async for adk_event in self._runner.run_async(
                user_id=USER_ID,
                session_id=context_id,
                new_message=adk_types.Content(
                    role="user",
                    parts=[adk_types.Part(text=user_input)],
                ),
                run_config=RunConfig(streaming_mode=StreamingMode.SSE),
            ):
                if not (adk_event.content and adk_event.content.parts):
                    continue

                stream_state = self._text_streams.get(context_id)

                for part in adk_event.content.parts:
                    if hasattr(part, "text") and part.text:
                        is_partial = bool(getattr(adk_event, "partial", False))
                        is_last = adk_event.is_final_response() and not is_partial

                        if stream_state and stream_state.saw_partial_text and not is_partial:
                            continue

                        await self._enqueue_text_chunk(
                            event_queue=event_queue,
                            task_id=task_id,
                            context_id=context_id,
                            text=part.text,
                            is_partial=is_partial,
                            is_last=is_last,
                        )
                        continue

                    # existing function_call / function_response branches remain below
```

- [ ] **Step 4: Ensure completion/failure cleanup does not leak stream state**

At the end of `execute()` and in the exception path, clear any pending stream state:

```python
        except Exception as e:
            self._text_streams.pop(context_id, None)
            logger.error(f"ADK 실행 오류: {e}", exc_info=True)
            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    task_id=task_id,
                    context_id=context_id,
                    final=True,
                    status=TaskStatus(state=TaskState.failed),
                )
            )
            return

        self._text_streams.pop(context_id, None)
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=task_id,
                context_id=context_id,
                final=True,
                status=TaskStatus(state=TaskState.completed),
            )
        )
```

- [ ] **Step 5: Run the focused executor tests to confirm GREEN**

Run:

```bash
uv run pytest tests/test_executor.py -v
```

Expected: PASS. The tests should prove SSE mode is requested, the first streamed text artifact uses `append=False`, the second uses `append=True`, and the aggregated final text is not duplicated.

- [ ] **Step 6: Commit the executor streaming change**

```bash
git add executor.py tests/test_executor.py
git commit -m "feat: stream ADK text chunks through executor"
```

---

## Task 3: Verify the A2A-to-AG-UI path still emits clean message events

**Files:**
- Modify: `backend/tests/test_a2a_stream.py`
- Modify: `backend/tests/test_agui_run.py`

- [ ] **Step 1: Keep converter behavior explicit for multi-chunk turns**

If Task 1's converter test was only added as a guard, keep the helper and assertions exactly like this in `backend/tests/test_a2a_stream.py`:

```python
async def test_multiple_text_artifacts_produce_one_start_two_chunks_and_one_end():
    events = await collect_stream([
        make_text_artifact("안", last_chunk=False),
        make_text_artifact("녕", last_chunk=True),
    ])

    types = [event["type"] for event in events]
    chunks = [event["delta"] for event in events if event["type"] == "TEXT_MESSAGE_CHUNK"]

    assert types == [
        "TEXT_MESSAGE_START",
        "TEXT_MESSAGE_CHUNK",
        "TEXT_MESSAGE_CHUNK",
        "TEXT_MESSAGE_END",
    ]
    assert chunks == ["안", "녕"]
```

- [ ] **Step 2: Keep `/agui/run` preserving chunk order end-to-end**

Keep the Task 1 regression in `backend/tests/test_agui_run.py` and add one extra assertion proving there is only one assistant message envelope:

```python
    starts = [event for event in events if event.get("type") == "TEXT_MESSAGE_START"]
    ends = [event for event in events if event.get("type") == "TEXT_MESSAGE_END"]

    assert len(starts) == 1
    assert len(ends) == 1
```

- [ ] **Step 3: Run the backend streaming regression suite**

Run:

```bash
uv run pytest tests/test_a2a_stream.py tests/test_agui_run.py -v
```

Expected: PASS. This proves the gateway and converter preserve chunk ordering and do not split one assistant turn into multiple start/end pairs.

- [ ] **Step 4: Commit the A2A/AG-UI regression coverage**

```bash
git add tests/test_a2a_stream.py tests/test_agui_run.py
git commit -m "test: verify chunked text survives AG-UI pipeline"
```

---

## Task 4: Add browser-level proof that assistant text grows incrementally

**Files:**
- Modify: `frontend/tests/e2e/response-capture.spec.ts`

- [ ] **Step 1: Add a stubbed SSE route that delivers chunked text with a delay**

Extend `frontend/tests/e2e/response-capture.spec.ts` with a browser-facing regression that does not depend on a live LLM:

```typescript
test('assistant text grows incrementally during streaming', async ({ page }) => {
  await page.route('**/agui/run', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'text/event-stream',
      body: [
        'data: {"type":"RUN_STARTED","threadId":"t1","runId":"r1"}\n\n',
        'data: {"type":"TEXT_MESSAGE_START","messageId":"m1","role":"assistant"}\n\n',
        'data: {"type":"TEXT_MESSAGE_CHUNK","messageId":"m1","delta":"안"}\n\n',
        'data: {"type":"TEXT_MESSAGE_CHUNK","messageId":"m1","delta":"녕"}\n\n',
        'data: {"type":"TEXT_MESSAGE_END","messageId":"m1"}\n\n',
        'data: {"type":"RUN_FINISHED","threadId":"t1","runId":"r1"}\n\n',
      ].join(''),
    })
  })

  await gotoApp(page)
  await sendUserMessage(page, '안녕')

  const assistantBubble = page.locator(selectors.assistantBubble).first()
  await expect(assistantBubble).toContainText('안')
  await expect(assistantBubble).toContainText('안녕')
})
```

- [ ] **Step 2: Make the stub truly incremental by splitting the fulfilled body through response capture if needed**

If the browser test runner buffers a fulfilled body and the assertion becomes meaningless, switch the test to the same event-capture helper pattern already used in this file and assert the event sequence explicitly:

```typescript
const events: string[] = []
page.on('response', async response => {
  if (!response.url().includes('/agui/run')) return
  const text = await response.text()
  for (const line of text.split('\n')) {
    if (!line.startsWith('data: ')) continue
    const payload = JSON.parse(line.slice(6))
    if (payload.type === 'TEXT_MESSAGE_CHUNK') {
      events.push(payload.delta)
    }
  }
})

await gotoApp(page)
await sendUserMessage(page, '안녕')

await expect.poll(() => events.join('')).toBe('안녕')
```

- [ ] **Step 3: Run the focused Playwright regression**

Run:

```bash
npm run test -- response-capture.spec.ts
```

Expected: PASS. The test should prove the browser path handles multiple text chunks for one assistant turn.

- [ ] **Step 4: Run the full verification slice for this feature**

Run:

```bash
cd ../backend && uv run pytest tests/test_executor.py tests/test_a2a_stream.py tests/test_agui_run.py -v && cd ../frontend && npm run test -- response-capture.spec.ts
```

Expected: PASS for all targeted backend and frontend streaming regressions.

- [ ] **Step 5: Commit the browser regression**

```bash
git add tests/e2e/response-capture.spec.ts
git commit -m "test: cover browser token streaming behavior"
```

---

## Self-Review

- Spec coverage: addressed root cause (`stream: False`), ADK SSE enablement, duplicate aggregated event handling, first-artifact append semantics, backend transport preservation, frontend regression proof, and success verification.
- Placeholder scan: removed generic "handle edge cases" language and replaced it with concrete duplicate suppression, cleanup, and test commands.
- Type consistency: all tasks use `RunConfig`, `StreamingMode.SSE`, `TaskArtifactUpdateEvent`, `TextPart`, and the existing AG-UI event names already present in the repo.
