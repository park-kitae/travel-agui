from domains.travel.knowledge.neo4j_repository import Neo4jKnowledgeRepository


class FakeSession:
    def __init__(self):
        self.queries = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def run(self, query):
        self.queries.append(query)
        if "RETURN n.id AS id" in query:
            return [
                {
                    "id": "city:서울",
                    "type": "city",
                    "label": "서울",
                    "text": "서울",
                    "properties": {"city": "서울"},
                },
                {
                    "id": "hotel:HTL-SEO-TEST",
                    "type": "hotel",
                    "label": "테스트 호텔",
                    "text": "수영장 있는 서울 호텔",
                    "properties": {
                        "hotel_code": "HTL-SEO-TEST",
                        "city": "서울",
                        "price": 120000,
                    },
                },
            ]
        return [
            {
                "source_id": "hotel:HTL-SEO-TEST",
                "target_id": "city:서울",
                "type": "LOCATED_IN",
                "properties": {},
            }
        ]


class FakeDriver:
    def __init__(self):
        self.fake_session = FakeSession()

    def session(self, database):
        assert database == "neo4j"
        return self.fake_session


def test_neo4j_repository_loads_knowledge_graph_from_travel_entities():
    driver = FakeDriver()
    repository = Neo4jKnowledgeRepository(driver, database="neo4j")

    graph = repository.load_graph()

    assert graph.get_node("hotel:HTL-SEO-TEST").label == "테스트 호텔"
    assert graph.get_node("city:서울").properties["city"] == "서울"
    assert graph.outgoing("hotel:HTL-SEO-TEST")[0].type == "LOCATED_IN"
