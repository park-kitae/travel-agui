from domains.travel.tools.graph_query_tools import (
    _query_travel_graph_with_driver,
    query_travel_graph,
    validate_readonly_cypher,
)


class FakeResult:
    def __iter__(self):
        return iter(
            [
                {
                    "hotel": {"hotel_code": "HTL-OSA-003", "name": "도미 인 난바"},
                    "amenity": "온천 대욕장",
                }
            ]
        )


class FakeSession:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def run(self, cypher, parameters=None):
        assert "MATCH" in cypher
        assert parameters == {"city": "오사카"}
        return FakeResult()


class FakeDriver:
    def session(self, database):
        assert database == "neo4j"
        return FakeSession()

    def close(self):
        pass


def test_validate_readonly_cypher_allows_match_return_queries():
    valid = validate_readonly_cypher(
        "MATCH (h:Hotel)-[:HAS_AMENITY]->(a:Amenity) RETURN h.label, a.label LIMIT 5"
    )

    assert valid["ok"] is True


def test_validate_readonly_cypher_rejects_writes_and_procedure_calls():
    for cypher in (
        "MATCH (n) DETACH DELETE n",
        "CREATE (:Hotel {name: 'bad'})",
        "CALL db.labels()",
        "MATCH (n) RETURN n; MATCH (m) RETURN m",
    ):
        valid = validate_readonly_cypher(cypher)
        assert valid["ok"] is False


def test_query_travel_graph_executes_read_query_with_supplied_driver():
    result = _query_travel_graph_with_driver(
        "MATCH (c:City {label: $city})<-[:LOCATED_IN]-(h:Hotel)-[:HAS_AMENITY]->(a:Amenity) "
        "RETURN h { .hotel_code, name: h.label } AS hotel, a.label AS amenity LIMIT 3",
        parameters={"city": "오사카"},
        driver=FakeDriver(),
    )

    assert result["status"] == "success"
    assert result["row_count"] == 1
    assert result["rows"][0]["hotel"]["hotel_code"] == "HTL-OSA-003"
    assert result["rows"][0]["amenity"] == "온천 대욕장"


def test_query_travel_graph_rejects_invalid_parameters_json():
    result = query_travel_graph("MATCH (n:TravelEntity) RETURN n LIMIT 1", parameters_json="{")

    assert result["status"] == "rejected"
    assert "parameters_json" in result["message"]
