Explore entities and relationships in the LightRAG knowledge graph.

## Arguments
`$ARGUMENTS` — entity or topic to explore.

## Constants
- LightRAG server: `http://localhost:9621`

## Instructions

### Step 1: Check server

```bash
curl -s http://localhost:9621/health > /dev/null 2>&1
```

If it fails: "LightRAG is not running. Start with: `cd ~/Documents/Projects/second-brain/lightrag && docker compose up -d`"

### Step 2: Search for matching entities

```bash
curl -s "http://localhost:9621/graph/label/search?q=<SEARCH_TERM>&limit=10"
```

Returns a JSON array of entity names matching the search (fuzzy matching).

### Step 3: Get the subgraph around the best matching entity

```bash
curl -s "http://localhost:9621/graphs?label=<ENTITY_NAME>&max_depth=2&max_nodes=30"
```

Parameters:
- `label` — entity name to center the graph on
- `max_depth` — relationship hops to traverse (default: 2)
- `max_nodes` — maximum nodes to return (default: 30)

Returns JSON with:
- `nodes` — array of entities (each has `id`, `description`)
- `edges` — array of relationships (each has `source`, `target`, `description`)

### Step 4: Format output

```
## Graph Explore: "<topic>"

**Entity:** <name>
<description>

### Connections

| Related Entity | Relationship |
|---------------|-------------|
| <entity> | <description> |
| ... | ... |

### Key Insights
<2-3 interesting observations about the connections>

---
*LightRAG graph · [Web UI](http://localhost:9621/webui)*
```

### Other useful endpoints

**Most connected entities (hubs):**
```bash
curl -s "http://localhost:9621/graph/label/popular?limit=20"
```

**Check if entity exists:**
```bash
curl -s "http://localhost:9621/graph/entity/exists?name=<ENTITY_NAME>"
```

**List all entities:**
```bash
curl -s "http://localhost:9621/graph/label/list"
```

## Error Handling

- **No entities match:** Suggest broader search terms
- **Empty graph:** Knowledge base may not be populated yet. Run `/lightrag-status`
