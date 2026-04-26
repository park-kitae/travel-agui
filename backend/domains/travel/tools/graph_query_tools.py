"""Read-only Neo4j graph query tool for travel knowledge exploration."""

from __future__ import annotations

import os
import json
import re
from typing import Any


_FORBIDDEN_CYPHER_TERMS = {
    "CALL",
    "CREATE",
    "DELETE",
    "DETACH",
    "DROP",
    "FOREACH",
    "LOAD",
    "MERGE",
    "REMOVE",
    "SET",
    "START",
    "STOP",
}
_ALLOWED_START_TERMS = {"MATCH", "OPTIONAL", "WITH", "UNWIND"}


def query_travel_graph(
    cypher: str,
    parameters_json: str = "{}",
    limit: int = 25,
) -> dict[str, object]:
    """
    Neo4j 여행 지식그래프를 읽기 전용 Cypher로 조회합니다.

    Args:
        cypher: MATCH/RETURN 중심의 읽기 전용 Cypher. 쓰기/삭제/프로시저 호출은 거부됩니다.
        parameters_json: Cypher parameter JSON 문자열. 사용자 입력 값은 문자열 결합 대신 $parameter로 전달합니다.
        limit: 반환 행 최대 개수.

    Returns:
        조회된 row 목록과 실행 정보. Hotel row는 hotel_code/name 등을 포함할 수 있습니다.
    """
    try:
        parameters = json.loads(parameters_json or "{}")
    except json.JSONDecodeError as exc:
        return {
            "status": "rejected",
            "message": f"parameters_json must be a valid JSON object: {exc}",
            "rows": [],
            "row_count": 0,
        }
    if not isinstance(parameters, dict):
        return {
            "status": "rejected",
            "message": "parameters_json must decode to a JSON object.",
            "rows": [],
            "row_count": 0,
        }

    return _query_travel_graph_with_driver(cypher, parameters=parameters, limit=limit, driver=_driver_from_env())


def _query_travel_graph_with_driver(
    cypher: str,
    parameters: dict[str, object] | None,
    limit: int = 25,
    driver: Any | None = None,
) -> dict[str, object]:
    validation = validate_readonly_cypher(cypher)
    if not validation["ok"]:
        return {
            "status": "rejected",
            "message": validation["message"],
            "rows": [],
            "row_count": 0,
        }

    bounded_limit = max(1, min(int(limit or 25), 50))
    query = _ensure_limit(cypher, bounded_limit)
    try:
        database = os.getenv("NEO4J_DATABASE", "neo4j")
        with driver.session(database=database) as session:
            rows = [_serialize_record(record) for record in session.run(query, parameters or {})]
    except Exception as exc:
        return {
            "status": "error",
            "message": f"Neo4j query failed: {exc}",
            "rows": [],
            "row_count": 0,
        }
    finally:
        if driver:
            driver.close()

    return {
        "status": "success",
        "cypher": query,
        "parameters": parameters or {},
        "row_count": len(rows),
        "rows": rows,
    }


def validate_readonly_cypher(cypher: str) -> dict[str, object]:
    normalized = " ".join(cypher.strip().split())
    if not normalized:
        return {"ok": False, "message": "Cypher query is empty."}
    if ";" in normalized:
        return {"ok": False, "message": "Only one Cypher statement is allowed."}

    terms = [term.upper() for term in re.findall(r"\b[A-Za-z]+\b", normalized)]
    if not terms or terms[0] not in _ALLOWED_START_TERMS:
        return {"ok": False, "message": "Cypher must start with MATCH, OPTIONAL MATCH, WITH, or UNWIND."}
    if "RETURN" not in terms:
        return {"ok": False, "message": "Cypher must return data."}

    forbidden = sorted(term for term in set(terms) if term in _FORBIDDEN_CYPHER_TERMS)
    if forbidden:
        return {"ok": False, "message": f"Cypher contains forbidden write/procedure terms: {', '.join(forbidden)}."}
    return {"ok": True, "message": "ok"}


def _driver_from_env() -> Any:
    try:
        from neo4j import GraphDatabase
    except ImportError as exc:
        raise RuntimeError("Install the Neo4j Python driver: pip install neo4j") from exc

    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "travel-agui-neo4j")
    return GraphDatabase.driver(uri, auth=(username, password))


def _ensure_limit(cypher: str, limit: int) -> str:
    if re.search(r"\bLIMIT\s+\d+\b", cypher, flags=re.IGNORECASE):
        return cypher
    return f"{cypher.rstrip()} LIMIT {limit}"


def _serialize_record(record: Any) -> dict[str, Any]:
    return {key: _serialize_value(value) for key, value in dict(record).items()}


def _serialize_value(value: Any) -> Any:
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _serialize_value(item) for key, item in value.items()}
    if hasattr(value, "items"):
        return {str(key): _serialize_value(item) for key, item in value.items()}
    return str(value)
