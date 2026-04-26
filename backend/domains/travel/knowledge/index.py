"""Build a travel knowledge graph from static domain data."""

from __future__ import annotations

import re
from typing import Any

from domains.travel.data import HOTEL_DETAIL_DB, INBOUND_DB, OUTBOUND_DB, PREFERENCE_OPTIONS, TIPS_DB

from .graph import KnowledgeEdge, KnowledgeGraph, KnowledgeNode


def build_travel_knowledge_graph() -> KnowledgeGraph:
    graph = KnowledgeGraph()

    for hotel in HOTEL_DETAIL_DB.values():
        _add_hotel(graph, hotel)

    for city, tips in TIPS_DB.items():
        _ensure_city(graph, city)
        _add_destination_tips(graph, city, tips)

    for route, flights in OUTBOUND_DB.items():
        _add_route_flights(graph, route, flights, direction="outbound")
    for route, flights in INBOUND_DB.items():
        _add_route_flights(graph, route, flights, direction="inbound")

    _add_preferences(graph)

    return graph


def _add_hotel(graph: KnowledgeGraph, hotel: dict[str, Any]) -> None:
    city = str(hotel["city"])
    hotel_code = str(hotel["hotel_code"])
    hotel_id = f"hotel:{hotel_code}"
    _ensure_city(graph, city)

    description = str(hotel.get("description", ""))
    highlights = [str(item) for item in hotel.get("highlights", [])]
    amenities = [str(item) for item in hotel.get("amenities", [])]
    room_types = hotel.get("room_types", [])
    search_text = " ".join(
        [
            str(hotel.get("name", "")),
            city,
            str(hotel.get("area", "")),
            description,
            " ".join(highlights),
            " ".join(amenities),
            " ".join(str(room.get("type", "")) for room in room_types),
        ]
    )

    graph.add_node(
        KnowledgeNode(
            id=hotel_id,
            type="hotel",
            label=str(hotel["name"]),
            text=search_text,
            properties={
                "hotel_code": hotel_code,
                "city": city,
                "area": hotel.get("area"),
                "price": _lowest_room_price(hotel),
                "stars": hotel.get("stars"),
                "rating": hotel.get("rating"),
                "description": description,
                "address": hotel.get("address"),
                "phone": hotel.get("phone"),
                "check_in_time": hotel.get("check_in_time"),
                "check_out_time": hotel.get("check_out_time"),
                "cancel_policy": hotel.get("cancel_policy"),
                "amenities": amenities,
                "highlights": highlights,
            },
        )
    )
    graph.add_edge(KnowledgeEdge(source_id=hotel_id, target_id=f"city:{city}", type="LOCATED_IN"))

    area = str(hotel.get("area", ""))
    if area:
        area_id = f"area:{city}:{area}"
        graph.add_node(KnowledgeNode(id=area_id, type="area", label=area, properties={"city": city}))
        graph.add_edge(KnowledgeEdge(source_id=hotel_id, target_id=area_id, type="LOCATED_IN_AREA"))

    for amenity in amenities:
        amenity_id = f"amenity:{_slug(amenity)}"
        graph.add_node(KnowledgeNode(id=amenity_id, type="amenity", label=amenity, text=amenity))
        graph.add_edge(KnowledgeEdge(source_id=hotel_id, target_id=amenity_id, type="HAS_AMENITY"))

    for highlight in highlights:
        highlight_id = f"highlight:{hotel_code}:{_slug(highlight)}"
        graph.add_node(KnowledgeNode(id=highlight_id, type="highlight", label=highlight, text=highlight))
        graph.add_edge(KnowledgeEdge(source_id=hotel_id, target_id=highlight_id, type="HAS_HIGHLIGHT"))

    for room in room_types:
        room_type = str(room.get("type", "객실"))
        room_id = f"room:{hotel_code}:{_slug(room_type)}"
        graph.add_node(
            KnowledgeNode(
                id=room_id,
                type="room_type",
                label=room_type,
                text=" ".join(str(value) for value in room.values()),
                properties={**room, "hotel_code": hotel_code},
            )
        )
        graph.add_edge(KnowledgeEdge(source_id=hotel_id, target_id=room_id, type="HAS_ROOM_TYPE"))


def _add_destination_tips(graph: KnowledgeGraph, city: str, tips: dict[str, Any]) -> None:
    city_id = f"city:{city}"
    overview = str(tips.get("overview", ""))
    graph.add_node(
        KnowledgeNode(
            id=f"destination:{city}",
            type="destination",
            label=city,
            text=" ".join(
                [
                    overview,
                    str(tips.get("best_season", "")),
                    str(tips.get("currency", "")),
                    str(tips.get("language", "")),
                    " ".join(tips.get("spots", [])),
                    " ".join(tips.get("food", [])),
                    " ".join(tips.get("tips", [])),
                ]
            ),
            properties={"city": city, **tips},
        )
    )
    graph.add_edge(KnowledgeEdge(source_id=city_id, target_id=f"destination:{city}", type="HAS_DESTINATION_INFO"))

    for key, node_type, edge_type in (
        ("spots", "spot", "HAS_SPOT"),
        ("food", "food", "HAS_FOOD"),
        ("tips", "tip", "HAS_TIP"),
    ):
        for value in tips.get(key, []):
            label = str(value)
            node_id = f"{node_type}:{city}:{_slug(label)}"
            graph.add_node(
                KnowledgeNode(
                    id=node_id,
                    type=node_type,
                    label=label,
                    text=label,
                    properties={"city": city},
                )
            )
            graph.add_edge(KnowledgeEdge(source_id=city_id, target_id=node_id, type=edge_type))


def _add_route_flights(
    graph: KnowledgeGraph,
    route: tuple[str, str],
    flights: list[dict[str, Any]],
    direction: str,
) -> None:
    origin, destination = route
    _ensure_city(graph, origin)
    _ensure_city(graph, destination)
    route_id = f"route:{origin}:{destination}:{direction}"
    graph.add_node(
        KnowledgeNode(
            id=route_id,
            type="route",
            label=f"{origin} -> {destination}",
            text=f"{origin} {destination} {direction}",
            properties={"origin": origin, "destination": destination, "direction": direction},
        )
    )
    graph.add_edge(KnowledgeEdge(source_id=route_id, target_id=f"city:{origin}", type="DEPARTS_FROM"))
    graph.add_edge(KnowledgeEdge(source_id=route_id, target_id=f"city:{destination}", type="ARRIVES_AT"))

    for flight in flights:
        flight_no = str(flight["flight"])
        flight_id = f"flight:{flight_no}"
        airline = str(flight["airline"])
        graph.add_node(
            KnowledgeNode(
                id=flight_id,
                type="flight",
                label=flight_no,
                text=" ".join(str(value) for value in flight.values()),
                properties={**flight, "origin": origin, "destination": destination, "direction": direction},
            )
        )
        graph.add_edge(KnowledgeEdge(source_id=route_id, target_id=flight_id, type="HAS_FLIGHT"))
        airline_id = f"airline:{airline}"
        graph.add_node(KnowledgeNode(id=airline_id, type="airline", label=airline, text=airline))
        graph.add_edge(KnowledgeEdge(source_id=flight_id, target_id=airline_id, type="OPERATED_BY"))


def _ensure_city(graph: KnowledgeGraph, city: str) -> None:
    city_id = f"city:{city}"
    if graph.maybe_node(city_id):
        return
    graph.add_node(KnowledgeNode(id=city_id, type="city", label=city, text=city, properties={"city": city}))


def _add_preferences(graph: KnowledgeGraph) -> None:
    for group_key, options in PREFERENCE_OPTIONS.items():
        group_id = f"preference_group:{group_key}"
        graph.add_node(
            KnowledgeNode(
                id=group_id,
                type="preference_group",
                label=group_key,
                text=group_key,
                properties={"key": group_key},
            )
        )

        for option_key, option in options.items():
            label = str(option["label"])
            option_id = f"preference_option:{group_key}:{option_key}"
            choices = [str(choice) for choice in option.get("choices", [])]
            graph.add_node(
                KnowledgeNode(
                    id=option_id,
                    type="preference_option",
                    label=label,
                    text=" ".join([label, " ".join(choices)]),
                    properties={
                        "group": group_key,
                        "key": option_key,
                        "input_type": option["type"],
                        "choices": choices,
                    },
                )
            )
            graph.add_edge(KnowledgeEdge(source_id=group_id, target_id=option_id, type="HAS_PREFERENCE_OPTION"))

            for choice in choices:
                choice_id = f"preference_choice:{group_key}:{option_key}:{_slug(choice)}"
                graph.add_node(
                    KnowledgeNode(
                        id=choice_id,
                        type="preference_choice",
                        label=choice,
                        text=choice,
                        properties={"group": group_key, "option": option_key},
                    )
                )
                graph.add_edge(KnowledgeEdge(source_id=option_id, target_id=choice_id, type="HAS_CHOICE"))


def _lowest_room_price(hotel: dict[str, Any]) -> int:
    prices = [
        int(room["price_per_night"])
        for room in hotel.get("room_types", [])
        if isinstance(room.get("price_per_night"), int)
    ]
    if prices:
        return min(prices)
    return int(hotel.get("price", 0) or 0)


def _slug(value: str) -> str:
    compact = re.sub(r"\s+", "-", value.strip())
    return re.sub(r"[^0-9A-Za-z가-힣ぁ-んァ-ヶ一-龯+-]", "", compact)
