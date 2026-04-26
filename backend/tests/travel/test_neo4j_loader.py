from domains.travel.knowledge.graph import KnowledgeEdge, KnowledgeGraph, KnowledgeNode
from domains.travel.knowledge.neo4j_loader import build_seed_payload


def test_build_seed_payload_sanitizes_nested_properties_and_keeps_labels():
    graph = KnowledgeGraph()
    graph.add_node(
        KnowledgeNode(
            id="hotel:HTL-TEST",
            type="hotel",
            label="테스트 호텔",
            text="테스트 호텔 설명",
            properties={
                "hotel_code": "HTL-TEST",
                "price": 100000,
                "none_value": None,
                "nested": {"unsupported": True},
                "amenities": ["수영장", "조식"],
            },
        )
    )
    graph.add_node(KnowledgeNode(id="city:서울", type="city", label="서울"))
    graph.add_edge(
        KnowledgeEdge(
            source_id="hotel:HTL-TEST",
            target_id="city:서울",
            type="LOCATED_IN",
            properties={"source": "test", "nested": {"ignored": True}},
        )
    )

    payload = build_seed_payload(graph)

    assert payload["nodes"][0]["labels"] == ["TravelEntity", "Hotel"]
    assert payload["nodes"][0]["properties"]["hotel_code"] == "HTL-TEST"
    assert "none_value" not in payload["nodes"][0]["properties"]
    assert "nested" not in payload["nodes"][0]["properties"]
    assert payload["relationships"][0]["type"] == "LOCATED_IN"
    assert payload["relationships"][0]["properties"] == {"source": "test"}
