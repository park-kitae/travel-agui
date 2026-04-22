"""Fake domain package used to prove runtime swappability."""

from .plugin import FakeDomainPlugin, FakeState, get_plugin

__all__ = ["FakeDomainPlugin", "FakeState", "get_plugin"]
