"""Neo4j-backed repository for travel knowledge retrieval."""

from __future__ import annotations

import os
from typing import Any

from .graph import KnowledgeEdge, KnowledgeGraph, KnowledgeNode


class Neo4jKnowledgeRepository:
    def __init__(self, driver: Any, *, database: str = "neo4j") -> None:
        self._driver = driver
        self._database = database

    @classmethod
    def from_env(cls) -> "Neo4jKnowledgeRepository":
        try:
            from neo4j import GraphDatabase
        except ImportError as exc:
            raise RuntimeError("Install the Neo4j Python driver: pip install neo4j") from exc

        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        username = os.getenv("NEO4J_USERNAME", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "travel-agui-neo4j")
        database = os.getenv("NEO4J_DATABASE", "neo4j")
        return cls(GraphDatabase.driver(uri, auth=(username, password)), database=database)

    def load_graph(self) -> KnowledgeGraph:
        graph = KnowledgeGraph()
        with self._driver.session(database=self._database) as session:
            for record in session.run(
                """
                MATCH (n:TravelEntity)
                RETURN n.id AS id,
                       n.type AS type,
                       n.label AS label,
                       n.text AS text,
                       properties(n) AS properties
                """
            ):
                properties = dict(record["properties"])
                properties.pop("id", None)
                properties.pop("type", None)
                properties.pop("label", None)
                properties.pop("text", None)
                graph.add_node(
                    KnowledgeNode(
                        id=str(record["id"]),
                        type=str(record["type"]),
                        label=str(record["label"]),
                        text=str(record["text"] or ""),
                        properties=properties,
                    )
                )

            for record in session.run(
                """
                MATCH (source:TravelEntity)-[r]->(target:TravelEntity)
                RETURN source.id AS source_id,
                       target.id AS target_id,
                       type(r) AS type,
                       properties(r) AS properties
                """
            ):
                graph.add_edge(
                    KnowledgeEdge(
                        source_id=str(record["source_id"]),
                        target_id=str(record["target_id"]),
                        type=str(record["type"]),
                        properties=dict(record["properties"]),
                    )
                )
        return graph

    def close(self) -> None:
        self._driver.close()
