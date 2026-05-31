from domains.travel.a2ui import (
    A2UI_BASIC_CATALOG_ID,
    build_favorite_a2ui_payload,
    build_favorite_surface_id,
)


def test_build_favorite_a2ui_payload_creates_stable_v09_surface_messages() -> None:
    payload = build_favorite_a2ui_payload(
        request_id="req-123",
        favorite_type="hotel_preference",
        options={
            "hotel_grade": {
                "type": "radio",
                "label": "호텔 등급",
                "choices": ["4성", "5성"],
            },
            "amenities": {
                "type": "checkbox",
                "label": "편의시설",
                "choices": ["조식포함", "주차"],
            },
        },
    )

    surface_id = build_favorite_surface_id("req-123")

    assert payload["surface_id"] == surface_id
    assert payload["messages"][0] == {
        "version": "v0.9",
        "createSurface": {
            "surfaceId": surface_id,
            "catalogId": A2UI_BASIC_CATALOG_ID,
        },
    }
    assert payload["messages"][1]["updateComponents"]["surfaceId"] == surface_id
    assert payload["messages"][1]["updateComponents"]["components"][0] == {
        "id": "root",
        "component": "Card",
        "child": "favorite-form",
    }
    assert payload["messages"][2] == {
        "version": "v0.9",
        "updateDataModel": {
            "surfaceId": surface_id,
            "value": {
                "requestId": "req-123",
                "favoriteType": "hotel_preference",
                "hotel_grade": [],
                "amenities": [],
            },
        },
    }

    choice_components = {
        component["id"]: component
        for component in payload["messages"][1]["updateComponents"]["components"]
        if component["component"] == "ChoicePicker"
    }
    assert choice_components["field-hotel_grade"]["variant"] == "mutuallyExclusive"
    assert choice_components["field-hotel_grade"]["value"] == {"path": "/hotel_grade"}
    assert choice_components["field-amenities"]["variant"] == "multipleSelection"
    assert choice_components["field-amenities"]["value"] == {"path": "/amenities"}


def test_build_favorite_a2ui_payload_handles_unsupported_favorite_type_with_empty_options() -> None:
    payload = build_favorite_a2ui_payload(
        request_id="req-empty",
        favorite_type="unknown_preference",
        options={},
    )

    data_model = payload["messages"][2]["updateDataModel"]["value"]
    assert data_model == {
        "requestId": "req-empty",
        "favoriteType": "unknown_preference",
    }
