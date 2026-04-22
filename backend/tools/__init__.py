"""Compatibility re-exports for legacy travel tool imports."""

from domains.travel.tools import (
    get_hotel_detail,
    get_travel_tips,
    request_user_favorite,
    request_user_input,
    search_flights,
    search_hotels,
)

__all__ = [
    "get_hotel_detail",
    "get_travel_tips",
    "request_user_favorite",
    "request_user_input",
    "search_flights",
    "search_hotels",
]
