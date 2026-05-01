#!/usr/bin/env python3
"""
Insight Agent — Stage 1 of the intelligence loop.

Reads vault context (sessions, daily logs, memory, chat, product state)
and runs analytical lenses via Claude API.

Usage:
    python3 insight-agent.py                    # blind-spots lens (default)
    python3 insight-agent.py --lens weekly      # weekly exec brief
    python3 insight-agent.py --lens patterns    # cross-product patterns
    python3 insight-agent.py --dry-run          # show context sizes, no API call
"""

import argparse
import os
import sys
from datetime import datetime, date, timedelta
from pathlib import Path


# ─── Config ───────────────────────────────────────────────────────────────────

VAULT = Path.home() / "Documents/Vaults/Mex_Vault"
CLICKUP_INSIGHT_CHANNEL = "8chy2nm-1493231"  # test-alexandre channel
CLICKUP_WORKSPACE = "9011399348"
ENV_FILES = [
    Path.home() / "Documents/Projects/search_atlas/mgmt/.env",
    Path.home() / "Documents/Vaults/Mex_Vault/.env",
    Path.home() / "Documents/SADEV/.env",
]
CLAUDE_HOME = Path.home() / ".claude"
PRODUCT_MENTOR_MEMORY = (
    CLAUDE_HOME / "projects"
    / "C--Users-alexg-Documents-Projects-search-atlas-product-mentor"
    / "memory"
)
INSIGHTS_DIR = VAULT / "Work" / "Insights"
MAX_CONTEXT_CHARS = 120_000

LENSES = {
    "blind-spots": """You are an analytical PM mentor reviewing Alexandre's work.

Analyze the context below and surface:
1. **Attention gaps** — topics mentioned repeatedly but with no concrete action taken
2. **Assumption risks** — decisions made without validation (user research, data)
3. **Voice-vs-action disconnects** — things said in channels that don't appear in board/tickets
4. **Neglected products** — which of {RB, LLMv, GSC, SE, KE} got zero attention recently?
5. **Stale threads** — conversations that started but were never resolved or closed

Be specific and direct. Reference actual content from the context.
Format as: ## {Signal Type} followed by 1-3 concrete observations.""",

    "patterns": """You are a senior PM analyst reviewing work across multiple products.

Analyze the context below and identify:
1. **Cross-product themes** — same problem appearing in multiple products
2. **Repeated decisions** — patterns in how decisions are made (rushed? data-driven? delegated?)
3. **Velocity signals** — where is work moving fast vs stuck
4. **Convergence opportunities** — where could solutions in one product help another

Reference specific examples. Format as ## {Pattern Type} with 2-3 concrete observations each.""",

    "weekly": """You are preparing a 1-page executive brief.

Based on the context below, write a structured weekly brief:

## Scorecard
| Product | Status | Top Signal |
For each of {RB, LLMv, GSC, SE, KE} — use 🟢/🟡/🔴 based on activity and issues.

## Decisions Needed
List 2-4 open questions that need a PM decision this week.

## Blind Spots This Week
1-2 things that were not given enough attention.

## What Moved Well
1-2 genuine wins worth noting.

Keep it to under 400 words. Be direct.""",
}


# ─── Context loading ───────────────────────────────────────────────────────────

def load_file_safe(path: Path, label: str) -> tuple[str, int]:
    """Load a file, return (content_with_header, char_count)."""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        header = f"\n\n{'='*60}\n# {label}\n{'='*60}\n"
        full = header + content
        return full, len(full)
    except Exception as e:
        return f"\n\n[Could not load {label}: {e}]\n", 0


def collect_sessions(days_back: int = 2) -> list[tuple[str, int]]:
    """Load all session notes from today and yesterday."""
    sessions_dir = VAULT / "Work" / "Claude Code" / "Sessions"
    results = []
    today = date.today()
    for i in range(days_back):
        target_date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        for f in sorted(sessions_dir.glob(f"{target_date}-*.md")):
            content, chars = load_file_safe(f, f"Session: {f.stem}")
            if chars > 100:  # skip empty files
                results.append((content, chars))
    return results


def collect_daily_logs(days_back: int = 2) -> list[tuple[str, int]]:
    """Load daily logs from today and yesterday."""
    logs_dir = VAULT / "Work" / "Claude Code" / "Daily Logs"
    results = []
    today = date.today()
    for i in range(days_back):
        target_date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        log_file = logs_dir / f"{target_date}.md"
        if log_file.exists():
            content, chars = load_file_safe(log_file, f"Daily Log: {target_date}")
            results.append((content, chars))
    return results


def collect_memory_files() -> list[tuple[str, int]]:
    """Load MEMORY.md (global) and product state files."""
    results = []

    # Global memory
    global_memory = CLAUDE_HOME / "MEMORY.md"
    if global_memory.exists():
        content, chars = load_file_safe(global_memory, "Global MEMORY.md")
        results.append((content, chars))

    # Decisions log
    decisions = PRODUCT_MENTOR_MEMORY / "decisions-log.md"
    if decisions.exists():
        content, chars = load_file_safe(decisions, "Decisions Log")
        # Only keep last ~6000 chars (recent decisions)
        if chars > 6000:
            content = content[-6000:]
        results.append((content, len(content)))

    # Product state files
    for state_file in sorted(PRODUCT_MENTOR_MEMORY.glob("*-state.md")):
        content, chars = load_file_safe(state_file, f"Product State: {state_file.stem}")
        results.append((content, chars))

    return results


def collect_clickup_chat(max_files: int = 5) -> list[tuple[str, int]]:
    """Load recent ClickUp chat snapshots (most recently modified)."""
    chat_dir = VAULT / "Work" / "ClickUp" / "Chat"
    results = []
    if not chat_dir.exists():
        return results

    # Get all .md files sorted by modification time (most recent first)
    chat_files = sorted(
        chat_dir.glob("*.md"),
        key=lambda f: f.stat().st_mtime,
        reverse=True
    )[:max_files]

    for f in chat_files:
        content, chars = load_file_safe(f, f"ClickUp Chat: {f.stem}")
        if chars > 200:  # skip nearly empty files
            results.append((content, chars))

    return results


def collect_product_docs(max_per_product: int = 2) -> list[tuple[str, int]]:
    """Load ClickUp product docs (roadmaps, PRDs) and Linear snapshots."""
    results = []

    # ClickUp product docs
    clickup_dir = VAULT / "Work" / "ClickUp"
    priority_docs = ["Product Roadmap", "PRD", "Reliability Plan", "Sprint Calendar"]

    for product_dir in sorted(clickup_dir.iterdir()):
        if not product_dir.is_dir() or product_dir.name == "Chat":
            continue
        loaded = 0
        # Load priority docs first
        for priority in priority_docs:
            if loaded >= max_per_product:
                break
            for f in sorted(product_dir.iterdir()):
                if f.is_dir() and loaded < max_per_product:
                    # Check subdirectory files
                    for subf in sorted(f.iterdir()):
                        if subf.suffix == ".md" and priority.lower() in subf.stem.lower():
                            content, chars = load_file_safe(subf, f"Product Doc: {product_dir.name}/{f.name}/{subf.stem}")
                            if chars > 200:
                                results.append((content[:3000], min(chars, 3000)))
                                loaded += 1
                elif f.suffix == ".md" and priority.lower() in f.stem.lower() and loaded < max_per_product:
                    content, chars = load_file_safe(f, f"Product Doc: {product_dir.name}/{f.stem}")
                    if chars > 200:
                        results.append((content[:3000], min(chars, 3000)))
                        loaded += 1

    # Linear snapshots (LLMV.md, RB.md, GSC.md)
    linear_dir = VAULT / "Work" / "Linear"
    if linear_dir.exists():
        for f in sorted(linear_dir.glob("*.md")):
            content, chars = load_file_safe(f, f"Linear Snapshot: {f.stem}")
            if chars > 200:
                results.append((content[:4000], min(chars, 4000)))

    return results


def collect_previous_insights() -> list[tuple[str, int]]:
    """Load previous insight reports (if any exist)."""
    if not INSIGHTS_DIR.exists():
        return []
    # Load last 2 HTML insights (just grab text content, not rendered HTML)
    results = []
    for f in sorted(INSIGHTS_DIR.glob("*.html"), reverse=True)[:2]:
        content, chars = load_file_safe(f, f"Previous Insight: {f.stem}")
        if chars > 200:
            # Strip HTML tags roughly
            import re
            text = re.sub(r'<[^>]+>', ' ', content)
            text = re.sub(r'\s+', ' ', text)[:3000]
            results.append((f"\n\n# Previous Insight: {f.stem}\n{text}", len(text)))
    return results


# ─── Context assembly ──────────────────────────────────────────────────────────

def assemble_context(dry_run: bool = False) -> str:
    """Assemble all context sources with budget management."""
    print("Loading context sources...", file=sys.stderr)

    sources = []
    total_chars = 0

    # Priority order: sessions > daily logs > memory > chat > previous insights
    print("  → Sessions (today + yesterday)...", file=sys.stderr)
    for content, chars in collect_sessions():
        sources.append(("sessions", content, chars))
        total_chars += chars

    print("  → Daily logs...", file=sys.stderr)
    for content, chars in collect_daily_logs():
        sources.append(("daily_logs", content, chars))
        total_chars += chars

    print("  → Memory files...", file=sys.stderr)
    for content, chars in collect_memory_files():
        sources.append(("memory", content, chars))
        total_chars += chars

    print("  → Product docs (roadmaps, PRDs, Linear)...", file=sys.stderr)
    for content, chars in collect_product_docs():
        sources.append(("product_docs", content, chars))
        total_chars += chars

    print("  → ClickUp chat snapshots...", file=sys.stderr)
    for content, chars in collect_clickup_chat():
        sources.append(("chat", content, chars))
        total_chars += chars

    print("  → Previous insights...", file=sys.stderr)
    for content, chars in collect_previous_insights():
        sources.append(("insights", content, chars))
        total_chars += chars

    # Print summary
    by_type = {}
    for stype, _, chars in sources:
        by_type[stype] = by_type.get(stype, 0) + chars

    print("\nContext summary:", file=sys.stderr)
    for stype, chars in sorted(by_type.items()):
        print(f"  {stype:20s} {chars:>8,} chars", file=sys.stderr)
    print(f"  {'TOTAL':20s} {total_chars:>8,} chars", file=sys.stderr)
    print(f"  {'BUDGET':20s} {MAX_CONTEXT_CHARS:>8,} chars", file=sys.stderr)

    if dry_run:
        print("\n[DRY RUN] Skipping API call.", file=sys.stderr)
        return ""

    # Assemble context (trim if over budget, prioritizing earlier sources)
    context_parts = []
    used_chars = 0
    header = f"""# Context for Insight Analysis
Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}
PM: Alexandre Guimenti (Senior PM at SearchAtlas)
Products: RB (Report Builder), LLMv (LLM Visibility), GSC, SE (Site Explorer), KE (Keyword Explorer)
"""
    context_parts.append(header)
    used_chars += len(header)

    for stype, content, chars in sources:
        remaining = MAX_CONTEXT_CHARS - used_chars
        if remaining <= 500:
            break
        if chars <= remaining:
            context_parts.append(content)
            used_chars += chars
        else:
            # Trim to fit
            trimmed = content[:remaining]
            context_parts.append(trimmed + "\n[...trimmed to fit context budget]")
            used_chars += remaining

    print(f"\nFinal context: {used_chars:,} chars ({used_chars/MAX_CONTEXT_CHARS:.0%} of budget)", file=sys.stderr)
    return "".join(context_parts)


# ─── API call ─────────────────────────────────────────────────────────────────

def run_insight(context: str, lens: str) -> str:
    """Call Claude via CLI using JSON output format and silent stop hook."""
    import subprocess
    import tempfile
    import json as _json

    system_prompt = LENSES.get(lens, LENSES["blind-spots"])
    user_message = (
        f"Context from the last 48 hours:\n\n{context}\n\n"
        f"---\n\nPlease analyze this context using the {lens} lens. Be specific and direct."
    )

    print(f"\nCalling Claude (lens: {lens})...", file=sys.stderr)

    # Write prompt to UTF-8 temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False,
                                     encoding="utf-8") as f:
        f.write(user_message)
        tmp_path = Path(f.name)

    env = os.environ.copy()
    env["CLAUDE_SILENT_STOP"] = "1"  # disables save-session-hook rewake

    try:
        result = subprocess.run(
            [
                "claude", "-p",
                "--output-format", "json",
                "--no-session-persistence",
                "--append-system-prompt", system_prompt,
                f"@{tmp_path}",  # @ prefix reads from file
            ],
            capture_output=True,
            timeout=180,
            env=env,
        )
        stdout = result.stdout.decode("utf-8", errors="replace").strip()
        stderr = result.stderr.decode("utf-8", errors="replace").strip()

        if stderr:
            print(f"  [stderr]: {stderr[:300]}", file=sys.stderr)

        # Parse JSON response
        try:
            data = _json.loads(stdout)
            return data.get("result", "[No result in JSON]")
        except _json.JSONDecodeError:
            return stdout if stdout else "[No output received]"

    finally:
        tmp_path.unlink(missing_ok=True)


# ─── ClickUp posting ──────────────────────────────────────────────────────────

def load_env_var(key: str) -> str | None:
    """Load a variable from known .env files."""
    value = os.environ.get(key)
    if value:
        return value
    for env_path in ENV_FILES:
        if env_path.exists():
            for line in env_path.read_bytes().split(b"\n"):
                line = line.strip()
                if line.startswith(key.encode()):
                    parts = line.split(b"=", 1)
                    if len(parts) == 2:
                        return parts[1].strip().strip(b'"').strip(b"'").decode("utf-8", errors="replace")
    return None


def summarize_for_clickup(result: str, lens: str, max_bullets: int = 5) -> str:
    """Extract top bullet points from insight result for ClickUp message."""
    lines = result.splitlines()
    bullets = []
    for line in lines:
        stripped = line.strip()
        # Pick header lines (## ...) and bold first lines of sections
        if stripped.startswith("**") and stripped.endswith("**") and len(stripped) < 100:
            bullets.append(f"• {stripped.strip('*')}")
        elif stripped.startswith("**") and "**" in stripped[2:] and len(stripped) < 120:
            # Extract bold title from "**Title.** description..."
            title = stripped.split("**")[1] if stripped.count("**") >= 2 else stripped
            bullets.append(f"• {title}")
        if len(bullets) >= max_bullets:
            break
    return "\n".join(bullets) if bullets else result[:500]


def post_to_clickup(result: str, lens: str) -> None:
    """Post insight summary to ClickUp channel."""
    import urllib.request
    import urllib.error
    import json as _json

    token = load_env_var("CLICKUP_API_TOKEN")
    if not token:
        print("WARNING: CLICKUP_API_TOKEN not found, skipping ClickUp post.", file=sys.stderr)
        return

    today = date.today().strftime("%B %d, %Y")
    summary = summarize_for_clickup(result, lens)

    LENS_EMOJI = {
        "blind-spots": "🔍",
        "patterns": "🔗",
        "weekly": "📋",
    }
    emoji = LENS_EMOJI.get(lens, "💡")

    message = (
        f"{emoji} **Insight Agent — {lens.replace('-', ' ').title()}** ({today})\n\n"
        f"{summary}\n\n"
        f"_Full report saved to Vault/Work/Insights/{date.today().isoformat()}-{lens}.md_"
    )

    url = f"https://api.clickup.com/api/v3/workspaces/{CLICKUP_WORKSPACE}/chat/channels/{CLICKUP_INSIGHT_CHANNEL}/messages"
    payload = _json.dumps({"content": message}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": token,
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"Posted to ClickUp channel ({resp.status})", file=sys.stderr)
    except urllib.error.HTTPError as e:
        print(f"WARNING: ClickUp post failed ({e.code}): {e.read().decode()[:200]}", file=sys.stderr)
    except Exception as e:
        print(f"WARNING: ClickUp post error: {e}", file=sys.stderr)


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Insight Agent — PM intelligence loop Stage 1")
    parser.add_argument("--lens", choices=list(LENSES.keys()), default="blind-spots",
                        help="Analysis lens to apply (default: blind-spots)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show context sizes without making API call")
    args = parser.parse_args()

    print(f"\n{'='*60}", file=sys.stderr)
    print(f"  Insight Agent — {args.lens} lens", file=sys.stderr)
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)

    # Assemble context
    context = assemble_context(dry_run=args.dry_run)

    if args.dry_run:
        sys.exit(0)

    # Run lens
    result = run_insight(context, args.lens)

    # Output (encode safely for Windows terminal)
    def safe_print(text: str):
        sys.stdout.buffer.write((text + "\n").encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()

    safe_print(f"\n{'='*60}")
    safe_print(f"  INSIGHT REPORT — {args.lens.upper()}")
    safe_print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    safe_print(f"{'='*60}\n")
    safe_print(result)
    safe_print(f"\n{'='*60}")

    # Save to vault/Insights/ for future use
    INSIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    output_file = INSIGHTS_DIR / f"{date.today().isoformat()}-{args.lens}.md"
    output_file.write_text(f"# Insight: {args.lens}\n{datetime.now().isoformat()}\n\n{result}\n",
                           encoding="utf-8")
    print(f"\nSaved to: {output_file}", file=sys.stderr)

    # Post summary to ClickUp
    post_to_clickup(result, args.lens)


def post_error_to_clickup(script: str, error: str) -> None:
    """Post error notification to ClickUp if the agent fails."""
    import urllib.request, urllib.error, json as _json
    token = load_env_var("CLICKUP_API_TOKEN")
    if not token:
        return
    message = (
        f"⚠️ **{script} failed** ({date.today().isoformat()})\n\n"
        f"Error: `{error[:300]}`\n\n"
        f"Check logs or run manually to investigate."
    )
    url = f"https://api.clickup.com/api/v3/workspaces/{CLICKUP_WORKSPACE}/chat/channels/{CLICKUP_INSIGHT_CHANNEL}/messages"
    try:
        req = urllib.request.Request(url, data=_json.dumps({"content": message}).encode(),
                                     headers={"Authorization": token, "Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        import traceback
        print(traceback.format_exc(), file=sys.stderr)
        post_error_to_clickup("Insight Agent", str(exc))
        sys.exit(1)
