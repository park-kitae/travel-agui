"""Backward-compatible travel data re-exports."""

from domains.travel.data import (
    FLIGHT_PREFERENCE_OPTIONS,
    HOTEL_DB,
    HOTEL_DETAIL_DB,
    HOTEL_PREFERENCE_OPTIONS,
    INBOUND_DB,
    OUTBOUND_DB,
    OptionDef,
    PREFERENCE_OPTIONS,
    TIPS_DB,
    flights,
    hotels,
    preferences,
    tips,
)

__all__ = [
    "flights",
    "hotels",
    "preferences",
    "tips",
    "OUTBOUND_DB",
    "INBOUND_DB",
    "HOTEL_DB",
    "HOTEL_DETAIL_DB",
    "OptionDef",
    "HOTEL_PREFERENCE_OPTIONS",
    "FLIGHT_PREFERENCE_OPTIONS",
    "PREFERENCE_OPTIONS",
    "TIPS_DB",
]
