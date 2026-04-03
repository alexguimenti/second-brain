Upload a document to LightRAG for indexing into the knowledge graph.

## Arguments
`$ARGUMENTS` — file path to upload, or raw text to index.

## Constants
- LightRAG server: `http://localhost:9621`

## Instructions

### Step 1: Check server

```bash
curl -s http://localhost:9621/health > /dev/null 2>&1
```

If it fails: "LightRAG is not running. Start with: `cd ~/Documents/Projects/second-brain/lightrag && docker compose up -d`"

### Step 2: Determine input type

- If `$ARGUMENTS` is a file path → upload file
- If `$ARGUMENTS` is raw text or "scan" → insert text or trigger scan

### Step 3a: Upload file

```bash
curl -s -X POST http://localhost:9621/documents/upload \
  -F "file=@<FILE_PATH>"
```

Supported: TXT, MD, PDF, DOCX, PPTX, CSV.

### Step 3b: Insert raw text

```bash
curl -s -X POST http://localhost:9621/documents/text \
  -H "Content-Type: application/json" \
  -d '{"text": "<TEXT_CONTENT>", "description": "<optional name>"}'
```

### Step 3c: Scan input directory

```bash
curl -s -X POST http://localhost:9621/documents/scan
```

Scans `lightrag/data/inputs/` for new files.

### Step 4: Check processing status

Poll until done:

```bash
curl -s http://localhost:9621/documents/status_counts
```

Wait until `processing` is 0 and `processed` has increased.

### Step 5: Confirm

```
## Upload Complete

File: <filename>
Status: Processed
Entities extracted: check with /lightrag-status

*LightRAG · [Web UI](http://localhost:9621/webui)*
```

## Error Handling

- **File not found:** Check the path
- **Unsupported format:** Convert to TXT/MD first
- **Processing stuck:** `curl -X POST http://localhost:9621/documents/reprocess_failed`
