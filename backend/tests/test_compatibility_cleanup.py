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
    remaining = [path.relative_to(BACKEND_ROOT).as_posix() for path in LEGACY_WRAPPERS if path.exists()]

    assert remaining == []


def test_state_store_remains_available() -> None:
    assert (BACKEND_ROOT / "state" / "store.py").exists()
