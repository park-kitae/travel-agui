# Travel GraphRAG Design

**Date:** 2026-04-24  
**Status:** Draft  
**Approach:** In-memory GraphRAG-lite inside the travel domain

---

## Overview

The travel domain already has structured static data under `backend/domains/travel/data/`:

- hotels and hotel details
- flights
- destination tips
- preference options

The current agent exposes this data mostly through task-specific tools such as `search_hotels`, `get_hotel_detail`, `search_flights`, and `get_travel_tips`. That works for direct lookup, but it limits broader consultation-style questions such as:

- "가족 여행에 좋은 제주 호텔 추천해줘"
- "오사카에서 온천 있고 도톤보리 가까운 숙소 있어?"
- "쇼핑하기 좋은 도쿄 지역과 호텔을 같이 추천해줘"
- "수영장 있는 5성급 호텔을 가격 낮은 순으로 비교해줘"
- "방콕 여행 시 주의할 점과 숙소 선택 기준 알려줘"

The goal is to add a domain-owned knowledge retrieval layer that lets the agent answer condition-based, comparison, explanation, and recommendation questions using the existing data.

---

## Goals

- Build a lightweight graph representation from the existing travel data.
- Keep GraphRAG behavior inside the travel domain package.
- Add one consultation-oriented retrieval tool for broad travel questions.
- Preserve existing direct tools for booking-like searches and exact detail lookup.
- Use current thread state and context when available, without changing the AG-UI transport.
- Make the implementation easy to test without external services.

---

## Non-Goals

- No Neo4j, external graph database, or vector database in the first version.
- No embedding model dependency in the first version.
- No live web travel data.
- No replacement of existing hotel, flight, tips, or input-request tools.
- No frontend protocol change.
- No durable graph index persistence requirement.

---

## Approach Comparison

### Approach 1 — In-memory GraphRAG-lite (**recommended**)

Build a small graph index at process startup from Python data modules. The index stores typed nodes and edges, then exposes a retrieval function that scores nodes by city, hotel attributes, amenities, highlights, room types, tips, and route data.

**Pros**
- Matches the current static-data demo app.
- No new infrastructure.
- Deterministic enough for unit tests.
- Keeps implementation inside the `domains.travel` boundary.
- Easy to evolve later into vector or graph DB retrieval.

**Cons**
- Keyword matching will be less flexible than embeddings.
- Restart rebuilds the index, though the source data is static.
- Ranking quality depends on hand-written normalization and scoring rules.

### Approach 2 — Prompt-only enrichment

Inject more static data into the agent instruction or context.

**Pros**
- Smallest implementation.
- No new retrieval layer.

**Cons**
- Scales poorly as data grows.
- Increases prompt size.
- Higher risk of unsupported answers.
- Harder to test exact retrieval behavior.

### Approach 3 — External GraphRAG stack

Load the travel data into Neo4j, LlamaIndex, LangChain, or a vector database.

**Pros**
- Better fit for larger datasets.
- Supports more sophisticated graph traversal and semantic retrieval.

**Cons**
- Overkill for current static dictionaries.
- Adds setup, network, and operational dependencies.
- Makes local sample app harder to run.

### Recommendation

Choose **Approach 1**. It provides the behavioral improvement the agent needs while keeping the sample app simple and domain-local.

---

## Proposed Architecture

Add a travel-domain knowledge package:

```text
backend/domains/travel/
  knowledge/
    __init__.py
    graph.py
    index.py
    retrieval.py
```

Responsibilities:

- `graph.py`
  - defines `KnowledgeNode`, `KnowledgeEdge`, and `KnowledgeGraph`
  - keeps the graph data structure dependency-free

- `index.py`
  - builds the graph from `HOTEL_DB`, `HOTEL_DETAIL_DB`, `OUTBOUND_DB`, `INBOUND_DB`, and `TIPS_DB`
  - creates typed nodes for cities, hotels, amenities, room types, highlights, destinations, spots, foods, routes, flights, and airlines
  - creates typed edges such as `LOCATED_IN`, `HAS_AMENITY`, `HAS_ROOM_TYPE`, `HAS_HIGHLIGHT`, `HAS_SPOT`, `HAS_FOOD`, `HAS_TIP`, `HAS_FLIGHT`, and `OPERATED_BY`

- `retrieval.py`
  - accepts a natural-language query plus optional filters
  - normalizes Korean and English-ish query tokens where useful
  - ranks relevant hotels, destinations, tips, flights, and evidence snippets
  - returns compact structured evidence for the LLM to synthesize

Add one tool:

```python
def search_travel_knowledge(
    query: str,
    city: str = "",
    hotel_code: str = "",
    intent: str = "",
) -> dict:
    ...
```

The tool returns:

- `status`
- `query`
- `filters`
- `answer_focus`
- `results`
- `evidence`
- `suggested_next_actions`

---

## Data Flow

1. User asks a broad travel question.
2. Existing context injection adds known destination, dates, people, preferences, and selected hotel if present.
3. The agent decides whether the question is a direct booking/search request or a broader consultation request.
4. For direct requests, the agent keeps using existing tools.
5. For broad or comparative requests, the agent calls `search_travel_knowledge`.
6. The retrieval tool searches the in-memory graph and returns structured evidence.
7. The LLM writes the final answer using only the retrieved evidence plus current state.

The common backend engine remains unchanged. The travel plugin still owns the agent, tools, state interpretation, and context rendering.

---

## Tool Selection Rules

The travel agent instruction should add these rules:

- Use `search_hotels` when the user asks for hotel availability/list by city, date, and guest count.
- Use `get_hotel_detail` when the user asks about a specific hotel code or selected hotel.
- Use `search_flights` when the user asks for flight options by origin, destination, and date.
- Use `get_travel_tips` for simple destination overview questions.
- Use `search_travel_knowledge` for:
  - recommendations based on purpose, amenities, area, budget, or travel style
  - comparisons across hotels, cities, areas, amenities, or tips
  - questions combining hotel attributes and destination information
  - vague follow-up questions that depend on current travel context

---

## Retrieval Behavior

The first version uses deterministic scoring:

- Exact city/hotel/area/code matches get highest priority.
- Amenity and highlight matches boost hotel results.
- Price, star rating, and review rating can be used for ranking when the query asks for budget, luxury, 가성비, 5성급, 평점, or similar terms.
- Destination spots, foods, seasons, and local tips provide supporting evidence.
- Flight route matches are returned only when the query references route, airline, flight, departure, return, or 이동.

The tool should avoid unsupported claims. If evidence is weak, it should return `status: "not_found"` or a low-confidence result with suggested clarifying filters.

---

## Error Handling

- Unknown city: return `not_found` with known city suggestions.
- Unknown hotel code: return `not_found` and suggest using existing hotel search first.
- Empty query: return `invalid_request`.
- No strong match: return `not_found` with supported question examples.
- Index build errors should fail fast during tests and startup, because the source data is local and expected to be valid.

---

## Testing

Backend unit tests should cover:

- graph index construction from current data
- hotel amenity retrieval, such as 수영장 or 온천
- city-scoped recommendation retrieval
- budget/luxury/rating ranking behavior
- destination tip retrieval
- unknown city and empty query handling
- agent tool registration includes `search_travel_knowledge`

No frontend test is required for the first version because the AG-UI transport and UI event types do not change.

---

## Implementation Scope

First implementation slice:

1. Add the domain-local knowledge graph model and index builder.
2. Add deterministic retrieval logic.
3. Add `search_travel_knowledge` tool.
4. Register the tool in `create_travel_agent`.
5. Update the agent instruction with tool selection rules.
6. Add focused backend tests.

Future slices can add:

- embedding-based semantic ranking
- persisted index snapshots
- UI cards for knowledge results
- richer taxonomy aliases for amenities, purposes, and travel styles
