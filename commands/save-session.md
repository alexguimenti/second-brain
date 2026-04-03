Save a structured summary of this session to the Obsidian vault for future reference and graph navigation.

## Arguments
`$ARGUMENTS` — optional: custom title or focus filter (e.g., `/save-session deployment fix`)

## Instructions

### 1. Review the conversation

Scan the entire conversation and extract:
- **Context/motivation** — why this conversation happened, what problem or need triggered it
- **What was done** — objectives and their concrete outcomes (no code diffs)
- **Decisions made** — choices with brief rationale
- **External references** — PRs, issues, commits, docs, URLs mentioned
- **Insights and learnings** — patterns discovered, lessons, things to remember

If the conversation was trivial (greeting, simple lookup, quick question with no lasting impact), say so and stop — do not create an empty note.

### 2. Check for existing note

Before creating anything, check if this session already has a note:

1. Get the current `session_id` by finding the most recently modified `.jsonl` file in the project's session directory. The directory path follows the pattern `~/.claude/projects/<PROJECT_DIR_SLUG>/` where the slug is the working directory path with path separators replaced by `--`. Run:
   ```bash
   ls -lt ~/.claude/projects/<SLUG>/*.jsonl 2>/dev/null | head -1 | awk '{print $NF}' | sed 's/.*\///' | sed 's/\.jsonl//'
   ```
   For example, if the working directory is `C:\Users\username\Documents\Projects\my-project`, the slug is `C--Users-username-Documents-Projects-my-project`.
   Note: `claude session list` cannot run inside an active session, so always use the file-based approach.
2. Glob `Work/Claude Code/Sessions/*.md` in the vault
3. For each file, read the first 10 lines and check if `session_id` in the frontmatter matches the current session
4. If a match is found: **update that file** (overwrite with the new, complete summary). Keep the original filename — do NOT rename it.
5. If no match: proceed to create a new note

This ensures one session = one note, even across multiple resumes.

### 3. Determine metadata

Extract from context:
- **`project`**: infer from the working directory name or conversation content
- **`tags`**: 3-7 relevant themes (e.g., `deployment`, `debugging`, `refactor`, `planning`, `architecture`, `mcp`, `obsidian`)
- **`date`**: the date when the session was **first created** (keep the original date if updating an existing note; use today if creating new)
- **`session_id`**: from step 2 above
- **`project_path`**: current working directory as a **Windows path** (e.g., `C:\Users\username\Documents\Projects\my-project`)
- **Filename** (new notes only): `YYYY-MM-DD-title-slug.md` — a short, descriptive kebab-case slug in English. If `$ARGUMENTS` provides a title, use it for the slug.

### 4. Discover links

Scan the vault to find related notes for wikilinks:

1. **Existing sessions** — Glob `Work/Claude Code/Sessions/*.md` in the vault. For each, read the first 15 lines to get frontmatter (`project`, `tags`). Collect sessions that share the same project or overlapping tags.

2. **Other vault notes** — Glob `**/*.md` in the vault (excluding `Work/Claude Code/Sessions/`). Collect note titles (filename without `.md`) that are topically relevant to this session.

3. **Build wikilinks** — Create `[[Note Title]]` links for:
   - Sessions with the same project (up to 5 most recent)
   - Sessions with 2+ shared tags (up to 3)
   - Other vault notes whose titles relate to topics discussed

If no related notes are found, leave the References section with just external links.

### 5. Write the note

Write the file to `{{VAULT_ROOT}}\Work\Claude Code\Sessions\YYYY-MM-DD-title-slug.md` using this exact template:

```markdown
---
type: session
date: YYYY-MM-DD
project: project-name
session_id: abc123
project_path: "C:\\Users\\username\\path\\to\\project"
tags:
  - tag1
  - tag2
  - tag3
---

# Descriptive Session Title

## Context
Why this conversation happened — what problem or need triggered it.

## What Was Done
- **Objective** → Concrete impact/result
- **Objective** → Concrete impact/result

## Decisions Made
- **Decision**: brief rationale

## References
- [[Related Session]]
- [[Relevant Document]]
- External links (PRs, issues, commits)

## Insights and Learnings
Lessons, patterns discovered, things to remember for future sessions.

## Resume This Conversation
`​`​`powershell
cd "C:\path\to\project"; claude --resume SESSION_ID
`​`​`
```

**Rules for the content:**
- Write in English
- Keep it concise — this is a reference note, not a transcript
- Focus on what matters for future-you: decisions, outcomes, learnings
- The "What Was Done" section should describe intent and impact, not implementation details
- The "Resume" section must use a **PowerShell-compatible command** with Windows paths (double-quoted) and `;` as separator

### 6. Confirm

Output a short summary:
- File path (created or updated)
- Tags assigned
- Wikilinks found (list them)
- Whether this was a new note or an update to an existing one
- The resume command as a copyable code block:
```
cd "C:\Users\username\Documents\Projects\..."; claude --resume SESSION_ID
```
This should use the actual `project_path` and `session_id` from the note, so the user can copy-paste it directly to resume later.

**Important rules:**
- ALWAYS Read existing files before trying to find links
- The vault root is `{{VAULT_ROOT}}`
- Do NOT create notes for trivial conversations
- Keep the note under 60 lines — brevity is key
