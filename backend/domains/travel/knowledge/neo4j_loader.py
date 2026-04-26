"""Load the travel knowledge graph into Neo4j."""

from __future__ import annotations

import argparse
import os
import re
from collections import defaultdict
from typing import Any

from .graph import KnowledgeGraph
from .index import build_travel_knowledge_graph


CONSTRAINT_QUERIES = (
    "CREATE CONSTRAINT travel_entity_id IF NOT EXISTS FOR (n:TravelEntity) REQUIRE n.id IS UNIQUE",
)


def build_seed_payload(graph: KnowledgeGraph) -> dict[str, list[dict[str, Any]]]:
    nodes = [
        {
            "id": node.id,
            "labels": ["TravelEntity", _node_label(node.type)],
            "type": node.type,
            "label": node.label,
            "text": node.text,
            "properties": _flat_properties(node.properties),
        }
        for node in graph.nodes.values()
    ]
    relationships = [
        {
            "source_id": edge.source_id,
            "target_id": edge.target_id,
            "type": _relationship_type(edge.type),
            "properties": _flat_properties(edge.properties),
        }
        for edge in graph.edges
    ]
    return {"nodes": nodes, "relationships": relationships}


def seed_neo4j(
    uri: str,
    username: str,
    password: str,
    *,
    database: str = "neo4j",
    clear: bool = False,
) -> dict[str, int]:
    try:
        from neo4j import GraphDatabase
    except ImportError as exc:
        raise RuntimeError("Install the Neo4j Python driver: pip install neo4j") from exc

    payload = build_seed_payload(build_travel_knowledge_graph())
    driver = GraphDatabase.driver(uri, auth=(username, password))
    try:
        with driver.session(database=database) as session:
            if clear:
                session.run("MATCH (n:TravelEntity) DETACH DELETE n")
            for query in CONSTRAINT_QUERIES:
                session.run(query)
            _upsert_nodes(session, payload["nodes"])
            _upsert_relationships(session, payload["relationships"])
    finally:
        driver.close()

    return {"nodes": len(payload["nodes"]), "relationships": len(payload["relationships"])}


def _upsert_nodes(session: Any, nodes: list[dict[str, Any]]) -> None:
    nodes_by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in nodes:
        nodes_by_label[node["labels"][1]].append(node)

    for label, label_nodes in nodes_by_label.items():
        session.run(
            f"""
            UNWIND $nodes AS node
            MERGE (n:TravelEntity:{label} {{id: node.id}})
            SET n.type = node.type,
                n.label = node.label,
                n.text = node.text,
                n += node.properties
            """,
            nodes=label_nodes,
        )


def _upsert_relationships(session: Any, relationships: list[dict[str, Any]]) -> None:
    relationships_by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for relationship in relationships:
        relationships_by_type[relationship["type"]].append(relationship)

    for relationship_type, typed_relationships in relationships_by_type.items():
        session.run(
            f"""
            UNWIND $relationships AS relationship
            MATCH (source:TravelEntity {{id: relationship.source_id}})
            MATCH (target:TravelEntity {{id: relationship.target_id}})
            MERGE (source)-[r:{relationship_type}]->(target)
            SET r += relationship.properties
            """,
            relationships=typed_relationships,
        )


def _flat_properties(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in properties.items()
        if value is not None and _is_neo4j_property_value(value)
    }


def _is_neo4j_property_value(value: Any) -> bool:
    if isinstance(value, bool | int | float | str):
        return True
    if isinstance(value, list):
        return all(isinstance(item, bool | int | float | str) for item in value)
    return False


def _node_label(node_type: str) -> str:
    return "".join(part.capitalize() for part in node_type.split("_"))


def _relationship_type(edge_type: str) -> str:
    relationship_type = re.sub(r"[^0-9A-Za-z_]", "_", edge_type.upper())
    if not relationship_type or relationship_type[0].isdigit():
        raise ValueError(f"Invalid relationship type: {edge_type}")
    return relationship_type


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed travel knowledge data into Neo4j.")
    parser.add_argument("--uri", default=os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    parser.add_argument("--username", default=os.getenv("NEO4J_USERNAME", "neo4j"))
    parser.add_argument("--password", default=os.getenv("NEO4J_PASSWORD", "travel-agui-neo4j"))
    parser.add_argument("--database", default=os.getenv("NEO4J_DATABASE", "neo4j"))
    parser.add_argument("--clear", action="store_true")
    args = parser.parse_args()

    counts = seed_neo4j(
        args.uri,
        args.username,
        args.password,
        database=args.database,
        clear=args.clear,
    )
    print(f"Seeded {counts['nodes']} nodes and {counts['relationships']} relationships into Neo4j.")


if __name__ == "__main__":
    main()
