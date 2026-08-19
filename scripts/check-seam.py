#!/usr/bin/env python3
"""check-seam.py — integrity check for the agent-config seam.

The seam (AGENT-SEAM.md) is a single source of truth pointed to by every runtime's
instruction file, with canonical skills fanned out as junctions. Its failure modes
are silent: nothing errors when an agent simply never reads a rule. This script
turns the invariants stated in AGENT-SEAM.md into executable checks.

History it guards against:
- 2026-08-05: codebase-memory-mcp overwrote Codex/Gemini instruction files;
  AGENTS-GLOBAL.md was "loaded by nothing". Recurred on antigravity-cli (found
  2026-08-19).
- Pre-2026-08-05: five diverging copies of the Claude pointer across ~/.claude*.

Exit code: 1 if any FAIL, 0 otherwise (WARNs don't fail the run — services may be
intentionally off).

Run: py scripts/check-seam.py     (also step 0 of daily-reflection.sh)

Out of scope (v1): ~/.cursor, ~/.kiro, ~/.codeium/windsurf — not wired to the seam
(cursor has 15 own skills, zero junctions). Add them here if they join the seam.
"""

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from hashlib import md5
from pathlib import Path

HOME = Path.home()
SEAM_MARKER = "AGENT-SEAM.md"
MCP_BLOCK_MARKER = "codebase-memory-mcp:start"
FILE_ATTRIBUTE_REPARSE_POINT = 0x400

# --- What the seam family looks like today ---------------------------------

CLAUDE_POINTERS = [HOME / ".claude" / "CLAUDE.md"] + [
    HOME / f".claude-max-{i}" / "CLAUDE.md" for i in range(1, 5)
]
GEMINI_FAMILY = [
    HOME / ".codex" / "AGENTS.md",
    HOME / ".gemini" / "GEMINI.md",
    HOME / ".gemini" / "antigravity-cli" / "AGENTS.md",
]

SKILL_RUNTIME_DIRS = [HOME / ".claude" / "skills"] + [
    HOME / f".claude-max-{i}" / "skills" for i in range(1, 5)
] + [
    HOME / ".codex" / "skills",
    HOME / ".gemini" / "config" / "skills",
]
CANONICAL_SKILL_DIRS = [
    Path("<your-shared-agent-config-dir>/skills"),
    Path("<your-shared-agent-config-dir>/skills-shared"),
]
# Entries allowed to be real files inside a runtime skills dir.
SKILLS_WHITELIST = {"README-NOT-CANONICAL.md", ".system"}

CLAUDE_SETTINGS = HOME / ".claude" / "settings.json"
EXPECTED_HOOKS = {"SessionEnd": "session-backup.py", "PreCompact": "pre-compact.py"}

SCHEDULED_TASKS = [
    "SecondBrain-ClickUpSync",
    "SecondBrain-DailyReflection",
    "SecondBrain-DailyLinkVault",
    "InsightAgent-DailyBlindSpots",
    "InsightAgent-WeeklyBrief",
    "ResearchAgent-DailyAfterInsight",
]

LIGHTRAG_HEALTH = "http://localhost:9621/health"
QMD_CACHE = HOME / ".cache" / "qmd"
QMD_MAX_AGE_HOURS = 48
VAULT_MEMORY = HOME / "Documents" / "Vaults" / "MyVault" / "Tools" / "Config" / "MEMORY.md"
REFLECTION_MAX_AGE_HOURS = 48

# --- Reporting --------------------------------------------------------------

results = []  # (status, check, detail, fix)


def report(status, check, detail="", fix=""):
    results.append((status, check, detail, fix))


def run(check_fn):
    """A check that crashes reports WARN instead of dying — a watchdog that throws
    is worse than no watchdog."""
    try:
        check_fn()
    except Exception as e:
        report("WARN", check_fn.__name__, f"check could not run: {e}")


# --- A. Instruction files ---------------------------------------------------

def file_hash(path):
    return md5(path.read_bytes()).hexdigest()


def check_claude_pointers():
    missing = [p for p in CLAUDE_POINTERS if not p.is_file()]
    if missing:
        report("FAIL", "A1 claude-pointers",
               f"missing: {', '.join(str(p) for p in missing)}",
               "re-create the pointer from one of the surviving ~/.claude*/CLAUDE.md")
        return
    no_seam = [p for p in CLAUDE_POINTERS if SEAM_MARKER not in p.read_text(encoding="utf-8", errors="replace")]
    hashes = {file_hash(p) for p in CLAUDE_POINTERS}
    if no_seam:
        report("FAIL", "A1 claude-pointers",
               f"no seam marker in: {', '.join(str(p) for p in no_seam)}",
               "file was overwritten — restore the pointer (see a healthy sibling)")
    elif len(hashes) > 1:
        report("FAIL", "A1 claude-pointers",
               f"{len(hashes)} distinct contents across 5 pointers — silent divergence",
               "diff them, pick the survivor, copy to the other four")
    else:
        report("PASS", "A1 claude-pointers", "5 pointers, identical, seam marker present")


def check_gemini_family():
    ok = True
    for p in GEMINI_FAMILY:
        if not p.is_file():
            report("FAIL", "A2 gemini-family", f"missing: {p}",
                   "create it as a seam pointer (copy ~/.gemini/GEMINI.md)")
            ok = False
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        if SEAM_MARKER not in text:
            if MCP_BLOCK_MARKER in text:
                report("FAIL", "A2 gemini-family",
                       f"{p}: codebase-memory-mcp block present but seam pointer GONE — overwritten, not appended",
                       "restore pointer block, keep the mcp block appended (mirror ~/.gemini/GEMINI.md)")
            else:
                report("FAIL", "A2 gemini-family", f"{p}: no seam marker",
                       "restore the pointer (mirror ~/.gemini/GEMINI.md)")
            ok = False
    if ok:
        hashes = {file_hash(p) for p in GEMINI_FAMILY}
        if len(hashes) > 1:
            report("WARN", "A2 gemini-family",
                   f"{len(hashes)} distinct contents — drift or legitimate appended block, review",
                   "diff the files; appends are allowed, pointer divergence is not")
        else:
            report("PASS", "A2 gemini-family", "3 files, identical, seam marker present")


# --- B. Skills junctions ------------------------------------------------------

def is_reparse_point(path):
    # lstat: stat() follows the junction and would raise on a dead target,
    # turning a reportable FAIL into a crashed check.
    return bool(os.lstat(path).st_file_attributes & FILE_ATTRIBUTE_REPARSE_POINT)


def check_skills_junctions():
    for d in SKILL_RUNTIME_DIRS:
        if not d.is_dir():
            report("FAIL", "B1 skills-junctions", f"missing dir: {d}",
                   "re-fan canonical skills (junctions) into this runtime")
            continue
        offenders = []
        broken = []
        for entry in d.iterdir():
            if entry.name in SKILLS_WHITELIST:
                continue
            if not is_reparse_point(entry):
                offenders.append(entry.name)
            elif not entry.exists():  # exists() follows the link
                broken.append(entry.name)
        if offenders:
            report("FAIL", "B1 skills-junctions",
                   f"{d}: real directories replaced junctions: {', '.join(sorted(offenders))}",
                   "remove the real dir, re-create as junction to the canonical skill")
        elif broken:
            report("FAIL", "B1 skills-junctions",
                   f"{d}: junctions with dead targets: {', '.join(sorted(broken))}",
                   "target moved or was deleted — repoint or remove the junction")
        else:
            report("PASS", "B1 skills-junctions", f"{d.name} ({d.parent.name}): all junctions healthy")


def check_skills_parity():
    canonical = set()
    for d in CANONICAL_SKILL_DIRS:
        if d.is_dir():
            canonical.update(e.name for e in d.iterdir() if e.name not in SKILLS_WHITELIST)
    if not canonical:
        report("WARN", "B2 skills-parity", "canonical skill dirs not found — Sync offline?")
        return
    for d in SKILL_RUNTIME_DIRS:
        if not d.is_dir():
            continue  # B1 already reported
        names = {e.name for e in d.iterdir()} - SKILLS_WHITELIST
        runtime_only = names - canonical
        not_fanned = canonical - names
        label = f"{d.parent.name}/skills"
        if runtime_only:
            report("FAIL", "B2 skills-parity",
                   f"{label}: skills only here: {', '.join(sorted(runtime_only))}",
                   "seam rule: promote to canonical and re-fan, or delete")
        elif not_fanned:
            report("WARN", "B2 skills-parity",
                   f"{label}: canonical skills not fanned here: {', '.join(sorted(not_fanned))}",
                   "add the missing junctions (or confirm intentional)")
        else:
            report("PASS", "B2 skills-parity", f"{label}: matches canonical")


# --- C. Hooks -----------------------------------------------------------------

def check_hooks():
    if not CLAUDE_SETTINGS.is_file():
        report("FAIL", "C1 hooks", f"{CLAUDE_SETTINGS} missing", "re-run scripts/install.sh")
        return
    settings = json.loads(CLAUDE_SETTINGS.read_text(encoding="utf-8"))
    hooks = settings.get("hooks", {})
    for event, script in EXPECTED_HOOKS.items():
        commands = [
            h.get("command", "")
            for group in hooks.get(event, [])
            for h in group.get("hooks", [])
        ]
        if any(script in c for c in commands):
            report("PASS", "C1 hooks", f"{event} -> {script} registered")
        else:
            report("FAIL", "C1 hooks", f"{event} hook for {script} not registered",
                   "re-run scripts/install.sh")


# --- D. Scheduled tasks -------------------------------------------------------

def check_scheduled_tasks():
    names = ",".join(SCHEDULED_TASKS)
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"@({' ,'.join(repr(t) for t in SCHEDULED_TASKS)}) | ForEach-Object "
         "{ $t = Get-ScheduledTask -TaskName $_ -ErrorAction SilentlyContinue; "
         "if ($t) { [PSCustomObject]@{Name=$_.ToString(); State=$t.State.ToString()} } "
         "else { [PSCustomObject]@{Name=$_.ToString(); State='MISSING'} } } | ConvertTo-Json"],
        capture_output=True, text=True, timeout=60,
    )
    tasks = json.loads(out.stdout or "[]")
    if isinstance(tasks, dict):
        tasks = [tasks]
    state = {t["Name"]: t["State"] for t in tasks}
    bad = [t for t in SCHEDULED_TASKS if state.get(t) in (None, "MISSING", "Disabled")]
    if bad:
        detail = ", ".join("{} ({})".format(t, state.get(t, "MISSING")) for t in bad)
        report("FAIL", "D1 scheduled-tasks",
               f"not runnable: {detail}",
               "re-register via scripts/register-*.ps1 (or Task Scheduler for the Intelligence Loop ones)")
    else:
        report("PASS", "D1 scheduled-tasks", f"{len(SCHEDULED_TASKS)} tasks registered and enabled")


# --- E. Services (WARN only) --------------------------------------------------

def check_lightrag():
    try:
        with urllib.request.urlopen(LIGHTRAG_HEALTH, timeout=3) as r:
            report("PASS", "E1 lightrag", f":9621 responded {r.status}")
    except Exception:
        report("WARN", "E1 lightrag", ":9621 not responding — graph search offline",
               "docker compose up in lightrag/ if you want it back")


def check_qmd():
    if not shutil.which("qmd"):
        report("WARN", "E2 qmd", "qmd CLI not on PATH", "re-run scripts/setup-qmd.sh")
        return
    if not QMD_CACHE.is_dir():
        report("WARN", "E2 qmd", f"{QMD_CACHE} missing — never indexed?", "run: qmd embed")
        return
    newest = max((f.stat().st_mtime for f in QMD_CACHE.rglob("*") if f.is_file()), default=0)
    age_h = (time.time() - newest) / 3600
    if age_h > QMD_MAX_AGE_HOURS:
        report("WARN", "E2 qmd", f"index is {age_h:.0f}h old — search silently stale",
               "run: qmd embed")
    else:
        report("PASS", "E2 qmd", f"CLI present, index {age_h:.1f}h old")


def check_reflection_freshness():
    """The daily reflection copies MEMORY.md to the vault on every run — so a
    stale vault copy means the pipeline silently stopped working (as it did for
    weeks in Aug 2026: the agent asked a permission prompt nobody could see,
    the script logged 'exit 0', and MEMORY.md went untouched)."""
    if not VAULT_MEMORY.is_file():
        report("WARN", "E3 reflection", f"vault copy missing: {VAULT_MEMORY}",
               "run scripts/daily-reflection.sh manually and watch for errors")
        return
    age_h = (time.time() - VAULT_MEMORY.stat().st_mtime) / 3600
    if age_h > REFLECTION_MAX_AGE_HOURS:
        report("WARN", "E3 reflection",
               f"vault MEMORY.md is {age_h:.0f}h old — reflection may be silently failing",
               "tail ~/.claude/daily-logs/sync.log around 19:00")
    else:
        report("PASS", "E3 reflection", f"vault MEMORY.md synced {age_h:.1f}h ago")


# --- Main ---------------------------------------------------------------------

def main():
    print(f"check-seam — {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    for fn in (check_claude_pointers, check_gemini_family,
               check_skills_junctions, check_skills_parity,
               check_hooks, check_scheduled_tasks,
               check_lightrag, check_qmd, check_reflection_freshness):
        run(fn)

    for status, check, detail, fix in results:
        line = f"{status:<5} {check:<22} {detail}"
        print(line)
        if fix and status != "PASS":
            print(f"      -> {fix}")

    counts = {s: sum(1 for r in results if r[0] == s) for s in ("PASS", "WARN", "FAIL")}
    print(f"\n{counts['PASS']} pass, {counts['WARN']} warn, {counts['FAIL']} fail")
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
