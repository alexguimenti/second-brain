Sync ClickUp Docs into the Obsidian vault as Markdown files (one-way: ClickUp → Vault).

## Arguments
`$ARGUMENTS` — optional: `--discover [keywords]`, `--add <doc_id> <name> <vault_path>`, a ClickUp URL, or a document name to sync individually. No args = sync all tracked documents.

## Instructions

### Step 1: Read Config

Read `C:\Users\alexg\Documents\Vault\ClickUp\sync-config.json`. If missing, create it with:
```json
{
  "documents": [],
  "defaults": {
    "content_format": "text/md",
    "max_page_depth": -1,
    "flatten": false
  }
}
```

Store the parsed config as `CONFIG`.

### Step 2: Parse Arguments

Determine mode from `$ARGUMENTS`:

1. **No arguments** → `mode = sync_all` — sync every document in `CONFIG.documents`
2. **`--discover`** → `mode = discover` — call `clickup_search` with `filters: { asset_types: ["doc"] }` (no keywords)
3. **`--discover <keywords>`** → `mode = discover` — call `clickup_search` with `keywords: "<keywords>", filters: { asset_types: ["doc"] }`
4. **`--add <doc_id> <name> <vault_path>`** → `mode = add` — append entry to config and save
5. **URL containing `app.clickup.com`** → `mode = add_url` — extract `doc_id` from the URL path (the last segment after the last `/`), ask user for a name and vault_path, then append to config
6. **Any other text** → `mode = sync_one` — match against `name` field in `CONFIG.documents` (case-insensitive). If no match, report error and list available names.

### Step 3: Execute Mode

#### Mode: discover

1. Call `clickup_search(keywords, filters: { asset_types: ["doc"] })` — include `keywords` only if provided
2. Display results as a numbered list: `[N] doc_name (doc_id)`
3. Ask user: "Which docs would you like to track? Enter numbers, or use `/sync-clickup --add <doc_id> <name> <vault_path>` to add manually."
4. If user picks numbers, for each selected doc ask for a `vault_path` (relative to vault root, e.g., `ClickUp/Produto/Product Roadmap`), then append entries to config and save.

**Stop here** — do not proceed to sync.

#### Mode: add / add_url

1. Build a new document entry:
   ```json
   {
     "document_id": "<doc_id>",
     "name": "<name>",
     "vault_path": "<vault_path>"
   }
   ```
2. Check for duplicate `document_id` in `CONFIG.documents`. If exists, update the existing entry instead.
3. Append (or update) in `CONFIG.documents` and write `sync-config.json`.
4. Confirm: "Added `<name>` (doc_id: `<doc_id>`) → `<vault_path>`. Run `/sync-clickup` to sync it."

**Stop here** — do not proceed to sync unless user explicitly asks.

#### Mode: sync_all / sync_one

For each document to sync (all documents if `sync_all`, matched document if `sync_one`):

**Process one document at a time** to manage context:

**a) Get page tree:**
```
clickup_list_document_pages(document_id: "<doc_id>", max_page_depth: <CONFIG.defaults.max_page_depth or doc-level override>)
```
Store the returned page hierarchy: each page has `id`, `name`, and optional `pages` (children).

**b) Flatten page tree into a list** with computed paths:
- Root pages → `<vault_path>/<page_name>.md`
- Child pages → `<vault_path>/<parent_name>/<child_name>.md`
- Grandchild pages → `<vault_path>/<parent_name>/<child_name>/<grandchild_name>.md`
- And so on recursively

If `flatten: true` (per-doc or default), all pages go directly into `<vault_path>/` regardless of hierarchy.

**Filename sanitization**: Strip these characters from page names: `< > : " / \ | ? *`. If two sibling pages produce the same sanitized filename, append `-<page_id>` suffix to both.

**c) Fetch page content in batches of 5:**
```
clickup_get_document_pages(document_id: "<doc_id>", page_ids: ["id1", "id2", "id3", "id4", "id5"], content_format: "text/md")
```
Process each batch before fetching the next to keep context manageable.

**d) Write each page as a Markdown file** in the vault:

File path: `C:\Users\alexg\Documents\Vault\<computed_path>`

Content format:
```markdown
---
type: clickup-doc
clickup_doc_id: "<doc_id>"
clickup_page_id: "<page_id>"
title: "<page_title>"
last_synced: <current ISO 8601 timestamp>
source_url: "https://app.clickup.com/9011399348/v/dc/<doc_id>"
parent_page: "<parent_page_title or empty if root>"
---

<markdown content from ClickUp>
```

**Always overwrite** — no unchanged detection. Write every file fresh.

Create parent directories as needed (use `mkdir -p`).

**e) After all pages for a document are written**, report:
```
Synced "<doc_name>": <N> pages written to <vault_path>/
```

### Step 4: Summary Report

After all documents are processed:

```
## Sync Complete

| Document | Pages | Path |
|----------|:-----:|------|
| <name> | <count> | <vault_path> |
| ... | ... | ... |

**Total:** <N> documents, <M> pages synced
**Errors:** <any errors or "None">
```

## Error Handling

- **MCP not connected**: "ClickUp MCP is not connected. Add it via Claude settings to use this command."
- **Document not found**: "Document `<doc_id>` not found in ClickUp. It may have been deleted or the ID is incorrect."
- **Empty config**: "No documents tracked. Use `/sync-clickup --discover` to find docs or `/sync-clickup --add` to add one manually."
- **Page fetch failure**: Log the error, continue with remaining pages. Report failures in summary.
