"""Deterministic retrieval over the travel knowledge graph."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from .graph import KnowledgeGraph, KnowledgeNode
from .index import build_travel_knowledge_graph


_BUDGET_TERMS = ("가성비", "저렴", "싼", "낮은", "합리", "예산", "budget")
_LUXURY_TERMS = ("럭셔리", "고급", "5성", "오성", "최고급", "luxury")
_HOTEL_TERMS = ("호텔", "숙소", "객실", "리조트", "수영장", "온천", "스파", "조식", "가족", "비즈니스")
_DESTINATION_TERMS = ("여행", "관광", "팁", "주의", "음식", "맛집", "사원", "시즌", "계절", "언어", "화폐", "현금")
_FLIGHT_TERMS = ("항공", "항공편", "비행", "출발", "귀국", "노선", "이동", "airline", "flight")


def search_knowledge(
    query: str,
    city: str = "",
    hotel_code: str = "",
    intent: str = "",
) -> dict[str, Any]:
    normalized_query = _normalize(query)
    if not normalized_query:
        return {"status": "invalid_request", "message": "query는 비어 있을 수 없습니다."}

    graph = _graph()
    known_cities = [node.label for node in graph.find_nodes("city")]
    matched_city = _resolve_city(graph, city or query)
    if city and not matched_city:
        return {
            "status": "not_found",
            "message": f"{city}에 대한 여행 지식을 찾을 수 없습니다.",
            "known_cities": sorted(known_cities),
        }

    if hotel_code:
        hotel = graph.maybe_node(f"hotel:{hotel_code}")
        if not hotel:
            return {
                "status": "not_found",
                "message": f"호텔 코드 {hotel_code}에 대한 여행 지식을 찾을 수 없습니다.",
                "known_cities": sorted(known_cities),
            }
        return _hotel_response(query, matched_city, [(_score_hotel(graph, hotel, normalized_query), hotel)], graph)

    answer_focus = _answer_focus(normalized_query, intent)
    hotel_matches = _rank_hotels(graph, normalized_query, matched_city)
    destination_evidence = _destination_evidence(graph, normalized_query, matched_city)
    flight_matches = _rank_flights(graph, normalized_query, matched_city)

    if answer_focus == "destination_advice" and destination_evidence:
        return _destination_response(query, matched_city, destination_evidence)
    if answer_focus == "flight_advice" and flight_matches:
        return _flight_response(query, matched_city, flight_matches)
    if hotel_matches:
        return _hotel_response(query, matched_city, hotel_matches, graph)
    if destination_evidence:
        return _destination_response(query, matched_city, destination_evidence)

    return {
        "status": "not_found",
        "query": query,
        "filters": {"city": matched_city or city, "hotel_code": hotel_code, "intent": intent},
        "message": "조건에 맞는 여행 지식을 찾지 못했습니다.",
        "known_cities": sorted(known_cities),
        "suggested_next_actions": [
            "지원 도시 중 하나를 포함해 다시 질문해 주세요.",
            "호텔, 숙소, 관광, 음식, 항공 중 궁금한 주제를 함께 알려주세요.",
        ],
    }


@lru_cache(maxsize=1)
def _graph() -> KnowledgeGraph:
    return build_travel_knowledge_graph()


def _rank_hotels(
    graph: KnowledgeGraph,
    normalized_query: str,
    matched_city: str | None,
) -> list[tuple[float, KnowledgeNode]]:
    scored: list[tuple[float, KnowledgeNode]] = []
    for hotel in graph.find_nodes("hotel"):
        if matched_city and hotel.properties.get("city") != matched_city:
            continue
        score = _score_hotel(graph, hotel, normalized_query)
        if score > 0:
            scored.append((score, hotel))

    if _contains_any(normalized_query, _BUDGET_TERMS):
        return sorted(scored, key=lambda item: (int(item[1].properties.get("price") or 0), -item[0]))
    if _contains_any(normalized_query, _LUXURY_TERMS):
        return sorted(
            scored,
            key=lambda item: (
                -int(item[1].properties.get("stars") or 0),
                -float(item[1].properties.get("rating") or 0),
                -item[0],
            ),
        )
    return sorted(scored, key=lambda item: (-item[0], -float(item[1].properties.get("rating") or 0)))


def _score_hotel(graph: KnowledgeGraph, hotel: KnowledgeNode, normalized_query: str) -> float:
    props = hotel.properties
    text_parts = [
        hotel.label,
        hotel.text,
        str(props.get("area", "")),
        " ".join(props.get("amenities", [])),
        " ".join(props.get("highlights", [])),
    ]
    text = _normalize(" ".join(text_parts))
    score = _token_overlap_score(normalized_query, text)

    if _normalize(str(props.get("city", ""))) in normalized_query:
        score += 5
    if _normalize(str(props.get("area", ""))) in normalized_query:
        score += 4
    if _contains_any(normalized_query, _HOTEL_TERMS):
        score += 2
    if _contains_any(normalized_query, _BUDGET_TERMS):
        score += max(0, 5 - (int(props.get("price") or 0) / 150000))
    if _contains_any(normalized_query, _LUXURY_TERMS):
        score += float(props.get("stars") or 0)

    for edge in graph.outgoing(hotel.id):
        node = graph.maybe_node(edge.target_id)
        if node and _normalize(node.label) in normalized_query:
            score += 6 if edge.type == "HAS_AMENITY" else 3

    return score


def _destination_evidence(
    graph: KnowledgeGraph,
    normalized_query: str,
    matched_city: str | None,
) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    cities = [matched_city] if matched_city else [node.label for node in graph.find_nodes("city")]

    for city in cities:
        if not city:
            continue
        city_id = f"city:{city}"
        destination = graph.maybe_node(f"destination:{city}")
        if destination:
            score = _token_overlap_score(normalized_query, _normalize(destination.text))
            if _normalize(city) in normalized_query:
                score += 4
            if _contains_any(normalized_query, _DESTINATION_TERMS):
                score += 2
            if score > 0:
                evidence.extend(_tip_evidence(destination))
        for edge in graph.outgoing(city_id):
            if edge.type not in {"HAS_SPOT", "HAS_FOOD", "HAS_TIP"}:
                continue
            node = graph.get_node(edge.target_id)
            node_text = _normalize(node.text)
            if node_text in normalized_query or _token_overlap_score(normalized_query, node_text) > 0:
                evidence.append(
                    {
                        "source_id": node.id,
                        "source_label": node.label,
                        "type": node.type,
                        "text": node.label,
                    }
                )
    return _dedupe_evidence(evidence)


def _rank_flights(
    graph: KnowledgeGraph,
    normalized_query: str,
    matched_city: str | None,
) -> list[KnowledgeNode]:
    if not _contains_any(normalized_query, _FLIGHT_TERMS):
        return []
    flights: list[KnowledgeNode] = []
    for flight in graph.find_nodes("flight"):
        if matched_city and matched_city not in {
            flight.properties.get("origin"),
            flight.properties.get("destination"),
        }:
            continue
        if _token_overlap_score(normalized_query, _normalize(flight.text)) > 0 or matched_city:
            flights.append(flight)
    return sorted(flights, key=lambda node: int(node.properties.get("price") or 0))


def _hotel_response(
    query: str,
    matched_city: str | None,
    hotel_matches: list[tuple[float, KnowledgeNode]],
    graph: KnowledgeGraph,
) -> dict[str, Any]:
    selected = [hotel for _, hotel in hotel_matches[:5]]
    evidence = []
    for hotel in selected:
        evidence.append(
            {
                "source_id": hotel.id,
                "source_label": hotel.label,
                "type": "hotel",
                "text": str(hotel.properties.get("description", hotel.text)),
            }
        )
        for edge in graph.outgoing(hotel.id):
            if edge.type not in {"HAS_AMENITY", "HAS_HIGHLIGHT"}:
                continue
            node = graph.get_node(edge.target_id)
            if _normalize(node.label) in _normalize(query) or _token_overlap_score(_normalize(query), _normalize(node.label)) > 0:
                evidence.append(
                    {
                        "source_id": node.id,
                        "source_label": hotel.label,
                        "type": edge.type.lower(),
                        "text": node.label,
                    }
                )

    return {
        "status": "success",
        "query": query,
        "filters": {"city": matched_city or "", "hotel_code": "", "intent": ""},
        "answer_focus": "hotel_recommendation",
        "results": [_hotel_result(hotel) for hotel in selected],
        "evidence": _dedupe_evidence(evidence),
        "suggested_next_actions": ["원하시면 특정 호텔의 객실, 정책, 편의시설을 더 자세히 비교할 수 있습니다."],
    }


def _destination_response(
    query: str,
    matched_city: str | None,
    evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    normalized_query = _normalize(query)
    ranked_evidence = sorted(
        evidence,
        key=lambda item: -_token_overlap_score(normalized_query, _normalize(str(item.get("text", "")))),
    )
    return {
        "status": "success",
        "query": query,
        "filters": {"city": matched_city or "", "hotel_code": "", "intent": ""},
        "answer_focus": "destination_advice",
        "results": [],
        "evidence": ranked_evidence[:8],
        "suggested_next_actions": ["숙소 조건이나 예산을 함께 알려주시면 호텔 추천까지 이어서 도와드릴 수 있습니다."],
    }


def _flight_response(
    query: str,
    matched_city: str | None,
    flights: list[KnowledgeNode],
) -> dict[str, Any]:
    return {
        "status": "success",
        "query": query,
        "filters": {"city": matched_city or "", "hotel_code": "", "intent": ""},
        "answer_focus": "flight_advice",
        "results": [
            {"type": "flight", **flight.properties}
            for flight in flights[:5]
        ],
        "evidence": [
            {
                "source_id": flight.id,
                "source_label": flight.label,
                "type": "flight",
                "text": flight.text,
            }
            for flight in flights[:5]
        ],
        "suggested_next_actions": ["정확한 날짜와 인원을 알려주시면 기존 항공편 검색 도구로 조회할 수 있습니다."],
    }


def _hotel_result(hotel: KnowledgeNode) -> dict[str, Any]:
    return {
        "type": "hotel",
        "hotel_code": hotel.properties.get("hotel_code"),
        "name": hotel.label,
        "city": hotel.properties.get("city"),
        "area": hotel.properties.get("area"),
        "price": hotel.properties.get("price"),
        "stars": hotel.properties.get("stars"),
        "rating": hotel.properties.get("rating"),
        "amenities": hotel.properties.get("amenities", []),
        "highlights": hotel.properties.get("highlights", []),
    }


def _tip_evidence(destination: KnowledgeNode) -> list[dict[str, Any]]:
    props = destination.properties
    items: list[dict[str, Any]] = []
    for key in ("overview", "best_season", "currency", "language"):
        value = props.get(key)
        if value:
            items.append(
                {
                    "source_id": destination.id,
                    "source_label": destination.label,
                    "type": key,
                    "text": str(value),
                }
            )
    for key in ("spots", "food", "tips"):
        for value in props.get(key, []):
            items.append(
                {
                    "source_id": destination.id,
                    "source_label": destination.label,
                    "type": key,
                    "text": str(value),
                }
            )
    return items


def _answer_focus(normalized_query: str, intent: str) -> str:
    normalized_intent = _normalize(intent)
    if "flight" in normalized_intent or _contains_any(normalized_query, _FLIGHT_TERMS):
        return "flight_advice"
    if "destination" in normalized_intent or _contains_any(normalized_query, _DESTINATION_TERMS):
        return "destination_advice"
    return "hotel_recommendation"


def _resolve_city(graph: KnowledgeGraph, raw: str) -> str | None:
    normalized = _normalize(raw)
    for city in sorted((node.label for node in graph.find_nodes("city")), key=len, reverse=True):
        if _normalize(city) in normalized:
            return city
    return None


def _token_overlap_score(query: str, text: str) -> float:
    query_tokens = _tokens(query)
    if not query_tokens:
        return 0
    text_tokens = _tokens(text)
    score = sum(1 for token in query_tokens if token in text_tokens or token in text)
    return float(score)


def _tokens(value: str) -> list[str]:
    return [token for token in _normalize(value).replace("/", " ").replace(",", " ").split() if len(token) >= 2]


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _contains_any(value: str, terms: tuple[str, ...]) -> bool:
    return any(term.lower() in value for term in terms)


def _dedupe_evidence(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for item in items:
        key = (str(item.get("source_id", "")), str(item.get("text", "")))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped
