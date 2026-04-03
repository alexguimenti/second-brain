Check the status of the LightRAG knowledge base — documents, processing, and top entities.

## Arguments
`$ARGUMENTS` — not used.

## Constants
- LightRAG server: `http://localhost:9621`

## Instructions

### Step 1: Check server health

```bash
curl -s http://localhost:9621/health
```

If it fails: "LightRAG is not running. Start with: `cd ~/Documents/Projects/second-brain/lightrag && docker compose up -d`"

### Step 2: Get document counts

```bash
curl -s http://localhost:9621/documents/status_counts
```

### Step 3: Check processing pipeline

```bash
curl -s http://localhost:9621/documents/pipeline_status
```

### Step 4: Get top entities (knowledge graph hubs)

```bash
curl -s "http://localhost:9621/graph/label/popular?limit=15"
```

### Step 5: Format report

```
## LightRAG Status

**Server:** http://localhost:9621 — Online
**Processing:** Idle (or "Processing N documents...")

### Documents
| Status | Count |
|--------|-------|
| Processed | N |
| Processing | N |
| Pending | N |
| Failed | N |
| **Total** | **N** |

### Top Entities (most connected)
1. <entity> — <connection count>
2. <entity> — <connection count>
...

*[Web UI](http://localhost:9621/webui) · [API Docs](http://localhost:9621/docs)*
```

## Error Handling

- **Server not running:** "Start with `cd ~/Documents/Projects/second-brain/lightrag && docker compose up -d`"
- **No documents:** "Knowledge base is empty. Upload with `/lightrag-upload` or run `bash scripts/setup-lightrag.sh`"
