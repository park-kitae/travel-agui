"""
a2a_to_agui_stream 변환 로직 단위 테스트
A2A 이벤트를 직접 생성하여 AG-UI 이벤트로 올바르게 변환되는지 검증
"""
import json
import pytest
from unittest.mock import MagicMock

from converter import a2a_to_agui_stream


def make_text_artifact(text: str, last_chunk: bool = True):
    """TextPart를 담은 TaskArtifactUpdateEvent mock 생성."""
    from a2a.types import TaskArtifactUpdateEvent, Artifact, Part, TextPart

    part = MagicMock()
    part.root = TextPart(text=text)

    artifact = MagicMock()
    artifact.parts = [part]

    event = MagicMock(spec=TaskArtifactUpdateEvent)
    event.artifact = artifact
    event.last_chunk = last_chunk

    response = MagicMock()
    response.root.result = event
    return response


def make_task_status(state_value: str):
    """TaskStatusUpdateEvent mock 생성."""
    from a2a.types import TaskStatusUpdateEvent, TaskState

    state_map = {
        "working": TaskState.working,
        "completed": TaskState.completed,
    }

    status = MagicMock()
    status.state = state_map.get(state_value, TaskState.completed)

    event = MagicMock(spec=TaskStatusUpdateEvent)
    event.status = status

    response = MagicMock()
    response.root.result = event
    return response


def make_data_artifact(data: dict):
    """DataPart를 담은 TaskArtifactUpdateEvent mock 생성."""
    from a2a.types import TaskArtifactUpdateEvent, Artifact, DataPart, Part

    part = MagicMock()
    part.root = DataPart(data=data)

    artifact = MagicMock()
    artifact.parts = [part]

    event = MagicMock(spec=TaskArtifactUpdateEvent)
    event.artifact = artifact
    event.last_chunk = False

    response = MagicMock()
    response.root.result = event
    return response


async def collect_stream(responses: list) -> list[dict]:
    """a2a_to_agui_stream 결과를 이벤트 목록으로 수집."""
    async def mock_a2a_gen():
        for r in responses:
            yield r

    results = []
    async for raw in a2a_to_agui_stream(mock_a2a_gen(), "run-1", "thread-1"):
        # SSE 형식: "data: {...}\n\n"
        for line in raw.splitlines():
            if line.startswith("data:"):
                payload = line[len("data:"):].strip()
                if payload:
                    results.append(json.loads(payload))
    return results


async def test_text_artifact_produces_message_events():
    """TextPart → TEXT_MESSAGE_START, CHUNK, END 순서 검증."""
    events = await collect_stream([make_text_artifact("안녕하세요", last_chunk=True)])
    types = [e["type"] for e in events]

    assert "TEXT_MESSAGE_START" in types
    assert "TEXT_MESSAGE_CHUNK" in types
    assert "TEXT_MESSAGE_END" in types
    assert types.index("TEXT_MESSAGE_START") < types.index("TEXT_MESSAGE_CHUNK")
    assert types.index("TEXT_MESSAGE_CHUNK") < types.index("TEXT_MESSAGE_END")


async def test_text_chunk_contains_correct_delta():
    """TEXT_MESSAGE_CHUNK의 delta 값이 원본 텍스트와 일치해야 한다."""
    events = await collect_stream([make_text_artifact("테스트 텍스트")])
    chunk = next(e for e in events if e["type"] == "TEXT_MESSAGE_CHUNK")
    assert chunk["delta"] == "테스트 텍스트"


async def test_working_status_produces_step_started():
    """working 상태 → STEP_STARTED 이벤트."""
    events = await collect_stream([make_task_status("working")])
    types = [e["type"] for e in events]
    assert "STEP_STARTED" in types


async def test_completed_status_produces_step_finished():
    """completed 상태 → STEP_FINISHED 이벤트."""
    events = await collect_stream([make_task_status("completed")])
    types = [e["type"] for e in events]
    assert "STEP_FINISHED" in types


async def test_empty_stream_produces_no_events():
    """빈 A2A 스트림 → 이벤트 없음."""
    events = await collect_stream([])
    assert events == []


async def test_state_delta_artifact_produces_state_delta_event():
    """STATE_DELTA DataPart → STATE_DELTA SSE 이벤트 변환."""
    events = await collect_stream([
        make_data_artifact({
            "_agui_event": "STATE_DELTA",
            "delta": [
                {"op": "replace", "path": "/travel_context/destination", "value": "도쿄"},
                {"op": "replace", "path": "/agent_status/current_intent", "value": "searching"},
            ],
        })
    ])
    delta_event = next(e for e in events if e["type"] == "STATE_DELTA")
    assert delta_event["delta"][0]["path"] == "/travel_context/destination"
    assert delta_event["delta"][1]["value"] == "searching"
