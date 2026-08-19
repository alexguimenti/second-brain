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
2. Glob `Work/Claude Code/Sessions/**/*.md` in the vault (recursive — notes live in weekly subfolders)
3. For each file, read the first 10 lines and check if `session_id` in the frontmatter matches the current session
4. If a match is found: **update that file** (overwrite with the new, complete summary). Keep its filename, date and week folder exactly as they are — they were stamped on the first save and are frozen. Do NOT rename, re-date or move it.
5. If no match: proceed to create a new note

This ensures one session = one note, even across multiple resumes.

### 3. Determine metadata

Extract from context:
- **`project`**: infer from the working directory name or conversation content
- **`tags`**: 3-7 relevant themes (e.g., `deployment`, `debugging`, `refactor`, `planning`, `architecture`, `mcp`, `obsidian`)
- **`date`** and **`time`**: both come from **one instant — the clock right now, when this note is first written.** That is the end of the work, which is what the note records. Read it with `Get-Date` / `date`; no timezone conversion is involved.

  **`date`, `time`, the filename hour and the `YYYY-WXX` week folder all derive from that same instant.** A session that ran 2026-08-05 18:52 → 2026-08-06 10:45 is `date: 2026-08-06`, `time: "10:45"`, filename `2026-08-06-10h-…`, week folder of Aug 6.

  **Stamp once, then freeze.** On a later update, keep the existing `date`, `time`, filename and week folder untouched — re-stamping would rename the file on every save and break every `[[wikilink]]` pointing at it.

  **Read the clock with PowerShell `Get-Date`, and sanity-check it before stamping.** Bash `date` has been observed returning a date five days stale while `Get-Date`, `git log` and other panes' notes all agreed on the real one — and because the stamp is frozen on first write, a wrong clock becomes a permanent wrong filename. Before writing a new note, confirm the day against a second source: the most recent `git log -1 --date=…`, or the newest existing note in `Sessions/`. If they disagree, trust the majority, not `date`.

  > Do not derive the end from the transcript's last message: while a session stays open that timestamp keeps moving, and separate notes were measured collapsing onto the same hour because of it. The save clock is the only value that is both meaningful and stable.

- **`session_id`**: from step 2 above
- **`project_path`**: current working directory as a **Windows path** (e.g., `C:\Users\username\Documents\Projects\my-project`)
- **Filename** (new notes only): `YYYY-MM-DD-HHh-title-slug.md` — date, then the **hour** zero-padded with a trailing `h`, then a short descriptive kebab-case slug in English. Example: `2026-08-06-07h-session-resume-dual-command.md`. If `$ARGUMENTS` provides a title, use it for the slug.

  The hour makes a day's notes sort chronologically in the file list instead of alphabetically by slug. The `h` stops `07` being misread as a day.

  **The hour is the clock when the note is written — the end of the work, not the start.** Take it from `Get-Date`, stamp it once, and never rename on a later update.

  Notes created before this convention have no hour and are **not** renamed — existing notes are referenced by wikilink, so a retroactive rename would break links to stamp an hour nobody recorded at the time.

### 4. Discover links

Scan the vault to find related notes for wikilinks:

1. **Existing sessions** — Glob `Work/Claude Code/Sessions/**/*.md` in the vault (recursive — notes live in weekly subfolders). For each, read the first 15 lines to get frontmatter (`project`, `tags`). Collect sessions that share the same project or overlapping tags.

2. **Other vault notes** — Glob `**/*.md` in the vault (excluding `Work/Claude Code/Sessions/`). Collect note titles (filename without `.md`) that are topically relevant to this session.

3. **Build wikilinks** — Create `[[Note Title]]` links for:
   - Sessions with the same project (up to 5 most recent)
   - Sessions with 2+ shared tags (up to 3)
   - Other vault notes whose titles relate to topics discussed

If no related notes are found, leave the References section with just external links.

### 5. Write the note

Write the file to `{{VAULT_ROOT}}\Work\Claude Code\Sessions\YYYY-WXX\YYYY-MM-DD-HHh-title-slug.md`, where `YYYY-WXX` is the ISO week — create the week subfolder if it does not exist, and never write to the `Sessions\` root. Use this exact template:

```markdown
---
type: session
date: YYYY-MM-DD
time: HH:MM   # when the note was written, local time (not UTC)
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
cd "C:\path\to\project"; RESUME_COMMAND
`​`​`
```

**Rules for the content:**
- Write in English
- Keep it concise — this is a reference note, not a transcript
- Focus on what matters for future-you: decisions, outcomes, learnings
- The "What Was Done" section should describe intent and impact, not implementation details
- The "Resume" section must use a **PowerShell-compatible command** with Windows paths (double-quoted) and `;` as separator

**Building `RESUME_COMMAND` — never hardcode `claude --resume`.**

A transcript lives under whichever `CLAUDE_CONFIG_DIR` produced it. Gateway wrappers such as `claude-gw` and the `cc` alias use a separate config dir; bare `claude` uses `~/.claude`. The two share no sessions, so a bare `claude --resume` fails for anything that ran through the gateway — the majority in practice (reference workstation: 634 sessions in the gateway config dir against 336 in `~/.claude`, zero UUIDs in common).

Resolve it from the environment of the session being saved:

| `$env:CLAUDE_CONFIG_DIR` | `RESUME_COMMAND` |
|---|---|
| unset, or the default config dir | `claude --resume <id>` |
| the gateway config dir | `cc --resume <id>` |
| anything else | `$env:CLAUDE_CONFIG_DIR='<that path>'; claude --resume <id>` |

Then add one line directly below the code block, because the transcript does not outlive the note. **Emit it verbatim in English, substituting only the date. Do not translate or paraphrase it, even when the surrounding conversation is in another language** — the note, the confirmation output and this line are always English:

```
Resumable until roughly YYYY-MM-DD — after that Claude Code prunes the transcript and this note is the record. /retrieve resolves it either way.
```

Transcripts are pruned after `cleanupPeriodDays` (default 30), counted from last activity. Most notes outlive their transcript, so a resume command with no expiry is a promise the note cannot keep.

### 6. Confirm

Output a short summary:
- File path (created or updated)
- Tags assigned
- Wikilinks found (list them)
- Whether this was a new note or an update to an existing one
- The resume command as a copyable code block:
```
cd "C:\Users\username\Documents\Projects\..."; RESUME_COMMAND
```
This should use the actual `project_path` and `session_id` from the note, and the same `RESUME_COMMAND` resolution as above, so the user can copy-paste it directly to resume later.

State the expiry here too, and **emit this line verbatim in English, substituting only the date — do not translate or paraphrase it**, exactly as in step 5. The whole confirmation is English even when the conversation is not:

```
Resumable until roughly YYYY-MM-DD.
```

> This is the second half of a fix that was only applied to step 5. On 2026-08-06 a note carried the correct English line while the terminal confirmation printed "Resumível até aproximadamente 2026-09-05" — the rule existed, just not here. When pinning wording, pin every place that emits it.

**Important rules:**
- ALWAYS Read existing files before trying to find links
- The vault root is `{{VAULT_ROOT}}`
- Do NOT create notes for trivial conversations
- Keep the note under 60 lines — brevity is key
