Query the LightRAG knowledge graph for relationship-aware answers.

## Arguments
`$ARGUMENTS` — the query to search for. Supports natural language questions, especially about relationships between entities.

## Constants

- LightRAG API: `http://localhost:9621`

## Instructions

### Step 1: Check if LightRAG is running

Run a quick health check:
```bash
curl -s http://localhost:9621/health
```

If it fails, tell the user: "LightRAG is not running. Start it with: `cd ~/Documents/Projects/second-brain/lightrag && docker compose up -d`"

### Step 2: Query LightRAG

Call the LightRAG API with the user's query:

```bash
curl -s -X POST http://localhost:9621/query \
  -H "Content-Type: application/json" \
  -d '{"query": "<user query>", "mode": "hybrid", "include_references": true}'
```

**Query modes** (choose based on the question):
- `hybrid` (default) — combines local entity search + global theme search. Best for most queries.
- `local` — searches entity neighborhoods. Best for "tell me about X" questions.
- `global` — searches high-level themes. Best for "what are the main trends?" questions.
- `mix` — runs all modes and combines. Most thorough but slowest.

### Step 3: Present results

Display the response in a clear format:

```
## Graph Search: "<query>"

<LightRAG's answer with references>

---
*Source: LightRAG knowledge graph (hybrid mode) · [Web UI](http://localhost:9621/webui)*
```

If the response includes entity references, format them as vault links where possible (e.g., if it mentions a document that exists in the vault, link it as `[[Document Name]]`).

### Step 4: Suggest follow-ups

If relevant, suggest:
- "Try `/vault <keywords>` for document-level search (QMD)"
- "Try `/query-graph <related question>` to explore connections"

## Error Handling

- **LightRAG not running:** Suggest `docker compose up -d`
- **No results:** Suggest trying a different query mode or using `/vault` instead
- **Timeout:** LightRAG may still be indexing. Check: `curl http://localhost:9621/documents/status_counts`
