"""Travel domain data exports."""

from . import flights, hotels, preferences, tips
from .flights import INBOUND_DB, OUTBOUND_DB
from .hotels import HOTEL_DB, HOTEL_DETAIL_DB
from .preferences import FLIGHT_PREFERENCE_OPTIONS, HOTEL_PREFERENCE_OPTIONS, OptionDef, PREFERENCE_OPTIONS
from .tips import TIPS_DB

__all__ = [
    "flights",
    "hotels",
    "preferences",
    "tips",
    "INBOUND_DB",
    "OUTBOUND_DB",
    "HOTEL_DB",
    "HOTEL_DETAIL_DB",
    "FLIGHT_PREFERENCE_OPTIONS",
    "HOTEL_PREFERENCE_OPTIONS",
    "OptionDef",
    "PREFERENCE_OPTIONS",
    "TIPS_DB",
]
