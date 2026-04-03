Discover and create connections between vault files using Obsidian wikilinks.

## Arguments
`$ARGUMENTS` — optional: `--dry-run`, `--auto`, `--path <folder>`, a specific `.md` file path, or no args to scan the entire vault with confirmation.

## Constants

- Vault root: `{{VAULT_ROOT}}`
- Search scope: all `**/*.md` files under vault root

## Instructions

### Step 1: Parse Arguments

Determine mode and scope from `$ARGUMENTS`:

1. **No arguments** → `scope = all`, `mode = confirm`
2. **`--dry-run`** → `scope = all`, `mode = dry_run`
3. **`--auto`** → `scope = all`, `mode = auto`
4. **`--path <folder>`** → `scope = folder`, `mode = confirm`
5. **`--path <folder> --dry-run`** → `scope = folder`, `mode = dry_run`
6. **`--path <folder> --auto`** → `scope = folder`, `mode = auto`
7. **Any argument ending in `.md`** → `scope = single_file`, `mode = confirm`

Flags can be combined freely: `--path Work/ClickUp/ --dry-run` is valid.

---

### Step 2: Build Filename Index

1. **Glob** all `**/*.md` files under vault root (or scoped path).
2. For each file, extract:
   - **Full path** relative to vault root (e.g., `Work/ClickUp/Engineering/API Standards.md`)
   - **Title** — filename without `.md` extension (e.g., `API Standards`)
   - **Aliases** — from YAML frontmatter `aliases:` field if present
3. Store as the **filename index** — used to detect inline text mentions.

---

### Step 3: Discover Inline Links

For each file in scope:

**a) Read the file content.**

**b) For each other file in the filename index**, check if its title (or alias) appears in the current file's body text. Skip:
- Mentions already inside `[[...]]`
- Mentions inside YAML frontmatter (between `---` markers at the top)
- Mentions inside code blocks (fenced ` ``` ` or indented)

**c) For each potential mention, judge relevance from context.**

Read the sentence or paragraph containing the mention. Decide:
- **LINK** — the mention clearly refers to the specific vault document (e.g., "as described in the API Standards" → the doc is being cited)
- **SKIP** — the mention is a generic use of the words, not a reference to the document (e.g., "we need better api standards" → general statement)

**When in doubt, SKIP.** False positives are worse than false negatives.

**d) Record all LINK decisions** as proposed inline changes:
```
File: <current file path>
Line N: "...as described in the API Standards..." → "...as described in the [[API Standards]]..."
```

---

### Step 4: Discover Semantic References

For each file in scope:

**a) Identify the file's 2-5 key topics** from its headings, frontmatter tags, and main content themes.

**b) Grep those topics across the vault** to find other files that discuss the same subjects. Use `output_mode: "content"` with `-C 2` for context snippets.

**c) For each candidate file, judge the connection:**
- **STRONG** — the files substantively discuss the same subject, project, decision, or event. Worth linking.
- **WEAK** — topical overlap is tangential or coincidental. Skip.

**d) Check existing links:**
- If the current file has a `## Related` section, read it and skip files already listed there.
- Also skip files already proposed as inline links (from Step 3).
- Skip the file linking to itself.

**e) Record STRONG connections:**
```
File: <current file path>
Add to ## Related:
  - [[API Standards]] — both discuss retry logic and error handling
  - [[Billing Incident Post-mortem]] — covers the same payment failure scenario
```

---

### Step 5: Generate Report

After processing all files in scope, display:

```
## Link Discovery Report

### Inline Links (N proposed)

<file path>:
  Line 12: "...the API Standards..." → "...the [[API Standards]]..."
  Line 45: "...Reliability Plan discusses..." → "...[[Reliability Plan]] discusses..."

<file path>:
  Line 8: "...see Benchmark Study..." → "...see [[Benchmark Study]]..."

### Reference Links (N proposed)

<file path>:
  Add to ## Related:
    - [[API Standards]] — both cover error handling patterns
    - [[2026-02-15 billing incident]] — related debugging session

### Summary
- Files scanned: N
- Inline links proposed: N
- Reference links proposed: N
- Files to be modified: N
```

If no connections are found, respond: "No new connections discovered. Your vault may already be well-linked, or try adding more interconnected content."

---

### Step 6: Apply Changes

**If `mode = dry_run`:** Stop after the report. Say: "Dry run complete. Run `/link-vault` (without --dry-run) to apply these changes."

**If `mode = confirm`:** After the report, ask:
> "Apply these changes to N files? You can say 'yes', 'no', 'only inline', 'only references', or 'skip <file>'."
- Respect partial approvals (e.g., "only inline links", "skip Work/ClickUp/X.md").
- If the user says no, stop.

**If `mode = auto`:** Apply immediately after the report without asking.

**Applying changes:**

1. **Inline links:** For each proposed inline change, use Edit to replace the plain text mention with the `[[wikilink]]` version. Process one file at a time. Be precise — replace only the exact match, preserve surrounding text.

2. **Reference links:** For each file with proposed references:
   - If the file already has a `## Related` section, append the new items to it.
   - If the file does not have a `## Related` section, append one at the end:
     ```

     ## Related
     - [[File Name]] — brief reason for the connection
     ```

3. After applying, report:
```
## Links Applied

- Inline links added: N
- Reference links added: N
- Files modified: N
```

---

## Error Handling

- **Empty vault or no files in scope:** "No .md files found. Check the vault root or the --path argument."
- **No connections found:** "No new connections discovered."
- **File read failure:** Skip the file, continue with others, mention skipped files in the summary.
- **Scope path not found:** "Path '<path>' not found in vault. Check the path relative to vault root."
- **Already fully linked:** If all potential links for a file already exist, skip it silently.
