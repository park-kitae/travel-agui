"""Opaque serialized state storage for runtime plugins."""

from __future__ import annotations

from typing import Any


class SerializedStateStore:
    """Store already-serialized plugin state without inspecting it."""

    def __init__(self) -> None:
        self._states: dict[str, dict[str, Any]] = {}

    def get(self, key: str) -> dict[str, Any] | None:
        return self._states.get(key)

    def set(self, key: str, value: dict[str, Any]) -> None:
        self._states[key] = value

    def clear(self, key: str) -> None:
        self._states.pop(key, None)
