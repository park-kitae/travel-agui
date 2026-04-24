# Travel GraphRAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a domain-local GraphRAG-lite retrieval tool so the travel agent can answer broader recommendation, comparison, and condition-based travel questions from existing static data.

**Architecture:** Build an in-memory graph under `backend/domains/travel/knowledge/`, expose deterministic retrieval through `search_travel_knowledge`, and register that tool with the existing travel ADK agent. The common AG-UI/A2A transport remains unchanged.

**Tech Stack:** Python 3.11, dataclasses, existing Google ADK `FunctionTool`, pytest.

---

## File Structure

- Create `backend/domains/travel/knowledge/__init__.py`
  - exports graph construction and retrieval entry points.
- Create `backend/domains/travel/knowledge/graph.py`
  - owns dependency-free graph dataclasses and lookup helpers.
- Create `backend/domains/travel/knowledge/index.py`
  - converts current travel data dictionaries into typed graph nodes and edges.
- Create `backend/domains/travel/knowledge/retrieval.py`
  - scores query matches and returns compact structured evidence.
- Create `backend/domains/travel/tools/knowledge_tools.py`
  - wraps retrieval as an ADK function tool.
- Modify `backend/domains/travel/tools/__init__.py`
  - exports `search_travel_knowledge`.
- Modify `backend/domains/travel/agent.py`
  - imports, registers, and documents the new tool selection rule.
- Create `backend/tests/travel/test_knowledge_graph.py`
  - verifies index construction and retrieval behavior.
- Create `backend/tests/travel/test_knowledge_tool.py`
  - verifies tool contract and agent registration.

---

### Task 1: Graph Model and Index

**Files:**
- Create: `backend/domains/travel/knowledge/__init__.py`
- Create: `backend/domains/travel/knowledge/graph.py`
- Create: `backend/domains/travel/knowledge/index.py`
- Test: `backend/tests/travel/test_knowledge_graph.py`

- [ ] **Step 1: Write failing graph construction tests**

```python
from domains.travel.knowledge import build_travel_knowledge_graph


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/travel/test_knowledge_graph.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'domains.travel.knowledge'`.

- [ ] **Step 3: Implement graph dataclasses**

Create `backend/domains/travel/knowledge/graph.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class KnowledgeNode:
    id: str
    type: str
    label: str
    text: str = ""
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class KnowledgeEdge:
    source_id: str
    target_id: str
    type: str
    properties: dict[str, Any] = field(default_factory=dict)


class KnowledgeGraph:
    def __init__(self) -> None:
        self._nodes: dict[str, KnowledgeNode] = {}
        self._edges: list[KnowledgeEdge] = []

    @property
    def nodes(self) -> dict[str, KnowledgeNode]:
        return dict(self._nodes)

    @property
    def edges(self) -> list[KnowledgeEdge]:
        return list(self._edges)

    def add_node(self, node: KnowledgeNode) -> None:
        self._nodes[node.id] = node

    def add_edge(self, edge: KnowledgeEdge) -> None:
        self._edges.append(edge)

    def get_node(self, node_id: str) -> KnowledgeNode:
        return self._nodes[node_id]

    def find_nodes(self, node_type: str) -> list[KnowledgeNode]:
        return [node for node in self._nodes.values() if node.type == node_type]

    def outgoing(self, source_id: str, edge_type: str | None = None) -> list[KnowledgeEdge]:
        return [
            edge
            for edge in self._edges
            if edge.source_id == source_id and (edge_type is None or edge.type == edge_type)
        ]
```

- [ ] **Step 4: Implement index builder**

Create `backend/domains/travel/knowledge/index.py` with graph construction from `HOTEL_DETAIL_DB`, `TIPS_DB`, `OUTBOUND_DB`, and `INBOUND_DB`.

- [ ] **Step 5: Export builder**

Create `backend/domains/travel/knowledge/__init__.py`:

```python
"""Travel-domain knowledge graph exports."""

from .graph import KnowledgeEdge, KnowledgeGraph, KnowledgeNode
from .index import build_travel_knowledge_graph

__all__ = [
    "KnowledgeEdge",
    "KnowledgeGraph",
    "KnowledgeNode",
    "build_travel_knowledge_graph",
]
```

- [ ] **Step 6: Run graph tests**

Run: `cd backend && uv run pytest tests/travel/test_knowledge_graph.py -v`

Expected: PASS.

---

### Task 2: Deterministic Retrieval

**Files:**
- Create: `backend/domains/travel/knowledge/retrieval.py`
- Modify: `backend/domains/travel/knowledge/__init__.py`
- Test: `backend/tests/travel/test_knowledge_graph.py`

- [ ] **Step 1: Add failing retrieval tests**

Append:

```python
from domains.travel.knowledge import search_knowledge


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/travel/test_knowledge_graph.py -v`

Expected: FAIL with `ImportError` for `search_knowledge`.

- [ ] **Step 3: Implement retrieval**

Create `backend/domains/travel/knowledge/retrieval.py` with:

```python
from __future__ import annotations

from functools import lru_cache
from typing import Any

from .graph import KnowledgeGraph, KnowledgeNode
from .index import build_travel_knowledge_graph


def search_knowledge(
    query: str,
    city: str = "",
    hotel_code: str = "",
    intent: str = "",
) -> dict[str, Any]:
    ...
```

Implementation requirements:

- Return `invalid_request` when `query.strip()` is empty.
- Resolve city by exact/contains match against city nodes.
- Resolve `hotel_code` to `hotel:{hotel_code}` when provided.
- Score hotel nodes using label, area, description, amenities, highlights, room types, price, stars, and rating.
- Sort budget queries by `price`, luxury queries by `stars` and `rating`, and general matches by score then rating.
- Include `evidence` entries with `source_id`, `source_label`, `type`, and `text`.
- Return destination tips when the query matches spots, food, season, language, currency, or tip text.

- [ ] **Step 4: Export retrieval function**

Modify `backend/domains/travel/knowledge/__init__.py`:

```python
from .retrieval import search_knowledge

__all__ = [
    "KnowledgeEdge",
    "KnowledgeGraph",
    "KnowledgeNode",
    "build_travel_knowledge_graph",
    "search_knowledge",
]
```

- [ ] **Step 5: Run retrieval tests**

Run: `cd backend && uv run pytest tests/travel/test_knowledge_graph.py -v`

Expected: PASS.

---

### Task 3: Tool Wrapper and Agent Registration

**Files:**
- Create: `backend/domains/travel/tools/knowledge_tools.py`
- Modify: `backend/domains/travel/tools/__init__.py`
- Modify: `backend/domains/travel/agent.py`
- Test: `backend/tests/travel/test_knowledge_tool.py`

- [ ] **Step 1: Write failing tool tests**

```python
from domains.travel.agent import create_travel_agent
from domains.travel.tools import search_travel_knowledge


def test_search_travel_knowledge_tool_returns_structured_evidence():
    result = search_travel_knowledge("수영장 있는 서울 5성 호텔", city="서울")

    assert result["status"] == "success"
    assert result["query"] == "수영장 있는 서울 5성 호텔"
    assert result["results"]
    assert result["evidence"]


def test_travel_agent_registers_knowledge_tool():
    agent = create_travel_agent()

    tool_names = {
        getattr(getattr(tool, "func", None), "__name__", getattr(tool, "name", ""))
        for tool in agent.tools
    }

    assert "search_travel_knowledge" in tool_names
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/travel/test_knowledge_tool.py -v`

Expected: FAIL with `ImportError` for `search_travel_knowledge`.

- [ ] **Step 3: Implement tool wrapper**

Create `backend/domains/travel/tools/knowledge_tools.py`:

```python
"""Knowledge retrieval tool for broader travel consultation."""

from typing import Any

from domains.travel.knowledge import search_knowledge


def search_travel_knowledge(
    query: str,
    city: str = "",
    hotel_code: str = "",
    intent: str = "",
) -> dict[str, Any]:
    """Search the travel knowledge graph for recommendations, comparisons, and advice."""
    return search_knowledge(query=query, city=city, hotel_code=hotel_code, intent=intent)
```

- [ ] **Step 4: Export tool**

Modify `backend/domains/travel/tools/__init__.py` to import and include `search_travel_knowledge` in `__all__`.

- [ ] **Step 5: Register tool and instruction**

Modify `backend/domains/travel/agent.py`:

- import `search_travel_knowledge`
- add `FunctionTool(search_travel_knowledge)` to `tools`
- add instruction text saying broad recommendation, comparison, condition-based, and context-dependent questions should use `search_travel_knowledge`

- [ ] **Step 6: Run tool tests**

Run: `cd backend && uv run pytest tests/travel/test_knowledge_tool.py -v`

Expected: PASS.

---

### Task 4: Regression Verification

**Files:**
- Verify only.

- [ ] **Step 1: Run travel knowledge tests**

Run: `cd backend && uv run pytest tests/travel/test_knowledge_graph.py tests/travel/test_knowledge_tool.py -v`

Expected: PASS.

- [ ] **Step 2: Run existing backend tests**

Run: `cd backend && uv run pytest -q`

Expected: PASS.

- [ ] **Step 3: Inspect git diff**

Run: `git diff --stat`

Expected: only knowledge package, travel tool exports, travel agent, tests, and this plan are changed.

- [ ] **Step 4: Commit implementation**

```bash
git add backend/domains/travel/knowledge backend/domains/travel/tools/knowledge_tools.py backend/domains/travel/tools/__init__.py backend/domains/travel/agent.py backend/tests/travel docs/superpowers/plans/2026-04-24-travel-graphrag.md
git commit -m "Add travel GraphRAG knowledge retrieval"
```
