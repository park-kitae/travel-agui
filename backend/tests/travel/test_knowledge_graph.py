from domains.travel.knowledge import build_travel_knowledge_graph, search_knowledge


def test_build_graph_contains_city_hotel_and_amenity_edges():
    graph = build_travel_knowledge_graph()

    assert graph.get_node("city:오사카").label == "오사카"
    assert graph.get_node("hotel:HTL-OSA-003").label == "도미 인 난바"

    hotel_edges = graph.outgoing("hotel:HTL-OSA-003")
    assert any(edge.type == "LOCATED_IN" and edge.target_id == "city:오사카" for edge in hotel_edges)
    assert any(edge.type == "HAS_AMENITY" and "온천" in graph.get_node(edge.target_id).label for edge in hotel_edges)


def test_build_graph_contains_destination_tip_nodes():
    graph = build_travel_knowledge_graph()

    tokyo_edges = graph.outgoing("city:도쿄")
    labels = [graph.get_node(edge.target_id).label for edge in tokyo_edges]

    assert "시부야 스크램블 교차로" in labels
    assert "스시" in labels


def test_search_knowledge_matches_amenity_and_city():
    result = search_knowledge("오사카에서 온천 있는 숙소 추천", city="오사카")

    assert result["status"] == "success"
    assert result["answer_focus"] == "hotel_recommendation"
    assert result["results"][0]["hotel_code"] == "HTL-OSA-003"
    assert any("온천 대욕장" in evidence["text"] for evidence in result["evidence"])


def test_search_knowledge_ranks_budget_query_by_price():
    result = search_knowledge("도쿄 가성비 호텔", city="도쿄")

    assert result["status"] == "success"
    prices = [item["price"] for item in result["results"] if item["type"] == "hotel"]
    assert prices == sorted(prices)


def test_search_knowledge_returns_destination_tips():
    result = search_knowledge("방콕 사원 방문 주의할 점")

    assert result["status"] == "success"
    assert result["answer_focus"] == "destination_advice"
    assert any("사원 방문 시 긴 옷 착용" in evidence["text"] for evidence in result["evidence"])


def test_search_knowledge_handles_unknown_city():
    result = search_knowledge("숙소 추천", city="부산")

    assert result["status"] == "not_found"
    assert "known_cities" in result
