Search and load files from the Obsidian vault into this conversation as context.

## Arguments
`$ARGUMENTS` — optional: keywords to search, `--path <folder>`, `--type <type>`, `--type <type> <keywords>`, `--types`, or no args for help.

## Constants

- Vault root: `C:\Users\alexg\Documents\Vault`
- Search scope: all `**/*.md` files under vault root

## Instructions

### Step 1: Parse Arguments

Determine mode from `$ARGUMENTS`:

1. **No arguments** → `mode = help`
2. **`--types`** → `mode = list_types`
3. **`--path <folder>`** → `mode = path_load` — the folder path follows the flag
4. **`--type <type>`** (no other non-flag args) → `mode = type_filter`
5. **`--type <type> <keywords>`** → `mode = type_search` — type is first arg after flag, rest are keywords
6. **`--type <type> --path <folder>`** → `mode = type_path` — combine type filter with path load
7. **Any other text** → `mode = keyword_search`

### Step 2: Execute Mode

#### Mode: keyword_search

This is the primary mode. Search the vault for files matching the keywords.

**a) Run these two searches in parallel:**

1. **Glob** `C:\Users\alexg\Documents\Vault\**\*.md` — from the results, identify files whose filename or path contains any of the search keywords (case-insensitive).

2. **Grep** the search keywords across `C:\Users\alexg\Documents\Vault` in all `.md` files. Use `output_mode: "content"` with 2 lines of context (`-C 2`) so you can see the surrounding text. Use `head_limit: 200` to cap output lines (approximately 20 files worth of snippets). Note: `head_limit` limits output lines, not files — 200 lines is a reasonable cap to get snippets from ~15-20 files without overwhelming context.

**b) Synthesize results:**

Combine both result sets. For each matching file, look at:
- Does the filename/path contain the keywords? (strong signal)
- Does the content match appear in a heading, frontmatter, or key paragraph? (strong signal)
- Does the content match appear in a passing mention or boilerplate? (weak signal)

**c) Rank all matching files** based on your judgment of the snippets. Prefer files where keywords appear in titles, headings, or central paragraphs over files with incidental mentions.

**d) Generate a summary card for each match** (up to 10). For each file, use the Grep snippets to write a 2-3 line summary describing what the file contains and why it matched. Do NOT Read any files at this stage — work only from the snippets you already have.

**e) Display results as a numbered list:**

```
## Vault Search: "<keywords>"

[1] <title or filename>
    <relative path from vault root>
    → <2-3 line summary from snippets: what the file covers, key topics>

[2] <title or filename>
    <relative path from vault root>
    → <2-3 line summary>

...

Say "load 1,3" to bring full documents into context.
```

**f) When the user responds with "load N" or similar**, Read those files and display their full content. This is the only moment files are loaded into context — never auto-load.

Note: the numbered list is only valid in the immediately following user message. If the conversation context has been truncated and the list is no longer visible, re-run the search instead of relying on stale numbers.

**h) If no files match at all**, respond:
"No vault files match '<keywords>'. Try different keywords or `/vault --types` to see available content."

---

#### Mode: path_load

1. Glob all `*.md` files under `C:\Users\alexg\Documents\Vault\<folder>` (the folder from `--path`).
2. If no files found, report: "No .md files found in '<folder>'. Check the path relative to vault root."
3. If more than 5 files found, list them all and ask the user which to load (do not auto-load more than 3).
4. If 3 or fewer files, auto-load all of them using Read.
5. **Large file guard:** If any file appears very large (e.g., you recognize it as a known large document or the Glob results suggest a dense folder), warn the user before loading and ask for confirmation.
6. Show what was loaded:

```
## Vault Path: <folder>

Loaded N files:
1. <filename> — <relative path>
2. ...
```

---

#### Mode: type_filter

Filter vault files by document type.

1. To determine file types, use BOTH:
   - **Grep** for `^type:` in frontmatter across `C:\Users\alexg\Documents\Vault\**\*.md` to find files with explicit type declarations.
   - **Path-based inference** for files without frontmatter type:

     | Path prefix | Inferred type |
     |-------------|---------------|
     | `ClickUp/` | `clickup-doc` |
     | `Claude Code/Sessions/` | `session` |
     | `Claude Code/Tools/` | `tool` |
     | Everything else | `note` |

2. Filter to files matching the requested type.
3. List all matching files with paths. If 3 or fewer, auto-load them. Otherwise, show the list and let the user pick.

---

#### Mode: type_search

1. First, filter files by type (same as type_filter step 1–2).
2. Then, Grep the keywords within ONLY the filtered files.
3. Synthesize and rank results the same way as keyword_search mode.
4. Show summary cards for each match. Do not auto-load — user picks which to load.

---

#### Mode: type_path

1. Glob all `.md` files under the given path.
2. Filter by type (using frontmatter Grep or path inference).
3. Load matching files (same budget guard as path_load).

---

#### Mode: list_types

1. Glob all `**/*.md` files under vault root.
2. For each file, determine its type:
   - Grep for `^type:` lines across all files to find explicit frontmatter types.
   - For files without explicit type, infer from path (see type table above).
3. Count files per type.
4. Display:

```
## Vault Types

| Type | Count | Example Path |
|------|------:|--------------|
| <type> | <N> | <first matching path> |
| ... | ... | ... |

Total: <N> files
```

---

#### Mode: help

1. Glob all `**/*.md` files under vault root.
2. Group files by top-level folder (e.g., `ClickUp/`, `Claude Code/`).
3. Count files per folder and total.
4. Display:

```
## Obsidian Vault — Context Loader

<N> markdown files across:
- ClickUp/ (<N> files)
- Claude Code/ (<N> files)
- <other folders> (<N> files)

Usage:
  /vault <keywords>                Search and load matching files
  /vault --path <folder>           Load all files in a folder
  /vault --type <type>             Filter by document type
  /vault --type <type> <keywords>  Combined filter + search
  /vault --types                   Show available types
```

---

## Error Handling

- If the vault root directory does not exist or is not accessible, report: "Vault root not found at `C:\Users\alexg\Documents\Vault`. Verify the Obsidian vault exists."
- If a file cannot be read (permission error, etc.), skip it and continue. Mention skipped files in the output.
- If Grep returns more than 20 matching files, show only the top 10 most relevant and note: "20+ files matched. Showing top 10 — try a more specific query to narrow results."
- When the user asks to load a file that appears very large, warn before loading and ask for confirmation.
