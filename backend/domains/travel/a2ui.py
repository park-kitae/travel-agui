"""A2UI v0.9 payload builders for travel domain UI requests."""

from __future__ import annotations

from typing import Any

A2UI_VERSION = "v0.9"
A2UI_BASIC_CATALOG_ID = "https://a2ui.org/specification/v0_9/basic_catalog.json"


def build_favorite_surface_id(request_id: str) -> str:
    return f"favorite-{request_id}"


def build_favorite_a2ui_payload(
    *,
    request_id: str,
    favorite_type: str,
    options: dict[str, Any],
) -> dict[str, Any]:
    surface_id = build_favorite_surface_id(request_id)
    fields = _normalize_options(options)
    field_ids = [f"field-{field_name}" for field_name in fields]
    data_model = {
        "requestId": request_id,
        "favoriteType": favorite_type,
        **{field_name: [] for field_name in fields},
    }

    return {
        "surface_id": surface_id,
        "request_id": request_id,
        "favorite_type": favorite_type,
        "messages": [
            {
                "version": A2UI_VERSION,
                "createSurface": {
                    "surfaceId": surface_id,
                    "catalogId": A2UI_BASIC_CATALOG_ID,
                },
            },
            {
                "version": A2UI_VERSION,
                "updateComponents": {
                    "surfaceId": surface_id,
                    "components": [
                        {"id": "root", "component": "Card", "child": "favorite-form"},
                        {
                            "id": "favorite-form",
                            "component": "Column",
                            "children": ["favorite-title", *field_ids, "favorite-submit"],
                        },
                        {
                            "id": "favorite-title",
                            "component": "Text",
                            "text": _favorite_title(favorite_type),
                            "variant": "h4",
                        },
                        *[
                            _choice_picker_component(field_name, option)
                            for field_name, option in fields.items()
                        ],
                        {
                            "id": "favorite-submit-label",
                            "component": "Text",
                            "text": "선택 완료",
                        },
                        {
                            "id": "favorite-submit",
                            "component": "Button",
                            "variant": "primary",
                            "child": "favorite-submit-label",
                            "action": {
                                "event": {
                                    "name": "submit_favorite_preferences",
                                    "context": _build_submit_context(request_id, favorite_type, fields),
                                }
                            },
                        },
                    ],
                },
            },
            {
                "version": A2UI_VERSION,
                "updateDataModel": {
                    "surfaceId": surface_id,
                    "value": data_model,
                },
            },
        ],
    }


def _normalize_options(options: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        field_name: option
        for field_name, option in options.items()
        if isinstance(option, dict)
    }


def _choice_picker_component(field_name: str, option: dict[str, Any]) -> dict[str, Any]:
    option_type = option.get("type")
    choices = option.get("choices") if isinstance(option.get("choices"), list) else []
    return {
        "id": f"field-{field_name}",
        "component": "ChoicePicker",
        "label": str(option.get("label") or field_name),
        "variant": "multipleSelection" if option_type == "checkbox" else "mutuallyExclusive",
        "displayStyle": "checkbox" if option_type == "checkbox" else "chips",
        "options": [
            {"label": str(choice), "value": str(choice)}
            for choice in choices
        ],
        "value": {"path": f"/{field_name}"},
    }


def _build_submit_context(
    request_id: str,
    favorite_type: str,
    fields: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        "requestId": request_id,
        "favoriteType": favorite_type,
        **{field_name: {"path": f"/{field_name}"} for field_name in fields},
    }


def _favorite_title(favorite_type: str) -> str:
    if favorite_type == "hotel_preference":
        return "호텔 취향을 선택해주세요"
    if favorite_type == "flight_preference":
        return "항공 취향을 선택해주세요"
    return "취향을 선택해주세요"
