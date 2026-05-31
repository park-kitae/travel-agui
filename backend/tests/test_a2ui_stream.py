import json
import asyncio
from unittest.mock import MagicMock

from converter import a2a_to_agui_stream


def make_data_artifact(data: dict):
    from a2a.types import DataPart, TaskArtifactUpdateEvent  # type: ignore[reportMissingImports]

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
    async def mock_a2a_gen():
        for response in responses:
            yield response

    results = []
    async for raw in a2a_to_agui_stream(mock_a2a_gen(), "run-1", "thread-1"):
        for line in raw.splitlines():
            if line.startswith("data:"):
                payload = line[len("data:"):].strip()
                if payload:
                    results.append(json.loads(payload))
    return results


def test_a2ui_message_data_artifact_produces_a2ui_message_event() -> None:
    events = asyncio.run(
        collect_stream([
            make_data_artifact(
                {
                    "_agui_event": "A2UI_MESSAGE",
                    "surface_id": "favorite-req-1",
                    "request_id": "req-1",
                    "favorite_type": "hotel_preference",
                    "messages": [{"version": "v0.9"}],
                }
            )
        ])
    )

    assert events == [
        {
            "type": "A2UI_MESSAGE",
            "surfaceId": "favorite-req-1",
            "requestId": "req-1",
            "favoriteType": "hotel_preference",
            "messages": [{"version": "v0.9"}],
        }
    ]
