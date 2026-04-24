from domains.travel.tools import search_hotels


def test_search_hotels_uses_recommendation_query_for_graphrag_ranking():
    result = search_hotels(
        city="제주",
        check_in="2026-06-10",
        check_out="2026-06-14",
        guests=2,
        recommendation_query="제주도 4성급 호텔 중 무료 주차 가능한 곳 추천해줘",
    )

    assert result["status"] == "success"
    assert result["hotels"][0]["hotel_code"] == "HTL-JEJ-003"
    assert result["recommendation"]["query"] == "제주도 4성급 호텔 중 무료 주차 가능한 곳 추천해줘"
    assert result["recommendation"]["matched_hotel_codes"][0] == "HTL-JEJ-003"
    assert result["recommendation"]["evidence"]


def test_search_hotels_preserves_existing_payload_shape_without_recommendation_query():
    result = search_hotels(
        city="제주",
        check_in="2026-06-10",
        check_out="2026-06-14",
        guests=2,
    )

    assert result["status"] == "success"
    assert result["city"] == "제주"
    assert result["check_in"] == "2026-06-10"
    assert result["check_out"] == "2026-06-14"
    assert result["guests"] == 2
    assert result["count"] == len(result["hotels"])
    assert "recommendation" not in result
