Query the LightRAG knowledge base and return a formatted answer with source references.

## Arguments
`$ARGUMENTS` — the question to ask. Supports natural language.

## Constants
- LightRAG server: `http://localhost:9621`

## Instructions

### Step 1: Check server

```bash
curl -s http://localhost:9621/health > /dev/null 2>&1
```

If it fails: "LightRAG is not running. Start with: `cd ~/Documents/Projects/second-brain/lightrag && docker compose up -d`"

### Step 2: Query

```bash
curl -s -X POST http://localhost:9621/query \
  -H "Content-Type: application/json" \
  -d '{"query": "<USER_QUESTION>", "mode": "hybrid", "include_references": true}'
```

**Query modes** (choose based on question type):
- `hybrid` (default) — combines local entity relationships + global graph traversal
- `local` — focuses on immediate entity relationships. Best for "tell me about X"
- `global` — high-level retrieval across the entire graph. Best for "what are the main themes?"
- `naive` — basic vector similarity (like traditional RAG)
- `mix` — all modes combined. Most thorough but slowest.

If the user doesn't specify a mode, always use `hybrid`.

### Step 3: Format output

```
## Knowledge Graph: "<query>"

<answer text>

**Sources:** <referenced documents>

---
*LightRAG (hybrid mode) · [Web UI](http://localhost:9621/webui)*
```

If the response references vault documents, format as `[[Document Name]]` wikilinks.

### Step 4: Suggest follow-ups

- "Try `/vault <keywords>` for document-level search (QMD)"
- "Try `/lightrag-explore <entity>` to explore graph connections"

## Error Handling

- **Server not running:** Suggest `docker compose up -d`
- **No results:** Suggest different query mode or `/vault` instead
- **Timeout:** May still be indexing. Check: `curl http://localhost:9621/documents/status_counts`
