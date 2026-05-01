#!/usr/bin/env python3
"""
Research Agent — Stage 2 of the intelligence loop.

Reads the latest insight report, picks top 3 research topics via Claude,
synthesizes a research brief per topic, and writes to vault.

Usage:
    python3 research-agent.py                     # reads latest insight
    python3 research-agent.py --topic "KE SLA"   # research a specific topic
    python3 research-agent.py --dry-run           # show topics, no full research
"""

import argparse
import json as _json
import os
import subprocess
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path


# ─── Config ───────────────────────────────────────────────────────────────────

VAULT = Path.home() / "Documents/Vaults/Mex_Vault"
INSIGHTS_DIR = VAULT / "Work" / "Insights"
RESEARCH_DIR = VAULT / "Work" / "Research"
CLICKUP_CHANNEL = "8chy2nm-1493231"  # test-alexandre
CLICKUP_WORKSPACE = "9011399348"
ENV_FILES = [
    Path.home() / "Documents/Projects/search_atlas/mgmt/.env",
    Path.home() / "Documents/Vaults/Mex_Vault/.env",
    Path.home() / "Documents/SADEV/.env",
]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def load_env_var(key: str) -> str | None:
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


def call_claude(prompt: str, system: str = "", timeout: int = 120) -> str:
    """Call Claude via CLI with CLAUDE_SILENT_STOP to bypass stop hook."""
    env = os.environ.copy()
    env["CLAUDE_SILENT_STOP"] = "1"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(prompt)
        tmp = Path(f.name)

    args = ["claude", "-p", "--output-format", "json", "--no-session-persistence"]
    if system:
        args += ["--append-system-prompt", system]
    args.append(f"@{tmp}")

    try:
        result = subprocess.run(args, capture_output=True, timeout=timeout, env=env)
        stdout = result.stdout.decode("utf-8", errors="replace").strip()
        try:
            data = _json.loads(stdout)
            return data.get("result", "")
        except _json.JSONDecodeError:
            return stdout
    finally:
        tmp.unlink(missing_ok=True)


def safe_slug(text: str) -> str:
    """Convert text to filename-safe slug."""
    import re
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    return slug[:50]


# ─── Stage 1: Extract topics ──────────────────────────────────────────────────

def get_latest_insight() -> tuple[str, str]:
    """Return (content, filename) of the most recent insight report."""
    if not INSIGHTS_DIR.exists():
        return "", ""
    files = sorted(INSIGHTS_DIR.glob("*.md"), reverse=True)
    if not files:
        return "", ""
    latest = files[0]
    return latest.read_text(encoding="utf-8", errors="replace"), latest.name


def extract_topics(insight_content: str) -> list[dict]:
    """Ask Claude to pick top 3 research topics from the insight."""
    print("Extracting top research topics...", file=sys.stderr)

    system = """You are a research prioritization assistant.
Given a PM insight report, identify the top 3 topics worth researching in depth.
Each topic should be something that would benefit from more context, data, or best practices.
Return ONLY a JSON array with exactly 3 objects, each with:
  - "topic": short title (5-8 words max)
  - "why": one sentence explaining why this is worth researching
  - "question": the specific research question to answer
Example: [{"topic": "SLA breach escalation playbook", "why": "...", "question": "..."}]"""

    prompt = f"""Here is today's PM insight report:

{insight_content[:8000]}

Pick the top 3 topics that would benefit most from research. Return only the JSON array."""

    response = call_claude(prompt, system=system, timeout=60)

    # Extract JSON from response
    import re
    match = re.search(r"\[.*\]", response, re.DOTALL)
    if not match:
        print(f"WARNING: Could not parse topics JSON. Response: {response[:200]}", file=sys.stderr)
        return []

    try:
        topics = _json.loads(match.group())
        return topics[:3]
    except _json.JSONDecodeError:
        print(f"WARNING: Invalid JSON in response.", file=sys.stderr)
        return []


# ─── Gemini live search ───────────────────────────────────────────────────────

def gemini_search(query: str) -> str:
    """Search web via Gemini. Returns text summary of current best practices."""
    gemini_key = load_env_var("GEMINI_API_KEY")
    if not gemini_key:
        print("  [Gemini] GEMINI_API_KEY not found, skipping.", file=sys.stderr)
        return ""

    try:
        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        result = model.generate_content(
            f"What are the most current (2025-2026) best practices, patterns, and real-world "
            f"examples for: {query}? Be specific, cite recent cases if known, 200 words max."
        )
        text = result.text
        print(f"  [Gemini] {len(text)} chars received", file=sys.stderr)
        return text
    except Exception as exc:
        print(f"  [Gemini] Failed ({exc}), continuing without live data.", file=sys.stderr)
        return ""


# ─── Stage 2: Research each topic ─────────────────────────────────────────────

def research_topic(topic: dict, insight_context: str) -> str:
    """Research a topic using Gemini (live data) + Claude (synthesis)."""
    print(f"  Researching: {topic['topic']}...", file=sys.stderr)

    # Stage 2a: live data from Gemini
    gemini_context = gemini_search(topic["question"])

    # Stage 2b: synthesize with Claude
    system = (
        "You are a senior PM research analyst. Given a research question, optional live web "
        "data from Gemini, and PM context, produce a structured, actionable brief. "
        "When live data is available, prioritize recent examples over general knowledge."
    )

    live_section = f"\n## Live data (Gemini web search):\n{gemini_context}\n" if gemini_context else ""

    prompt = f"""Research question: {topic['question']}

Why this matters: {topic['why']}
{live_section}
PM context:
{insight_context[:2000]}

Write a brief with:
## What's happening — 1-2 sentences on the situation.
## Relevant patterns & best practices — 2-3 bullets with recent examples if available.
## Recommended actions (next 48h) — 2-3 specific actions with owners.
## What to watch for — 1-2 signals that would change the approach.

Under 400 words. Direct and specific."""

    return call_claude(prompt, system=system, timeout=120)


# ─── Stage 3: Write output ────────────────────────────────────────────────────

def write_research_report(topics: list[dict], briefs: list[str], insight_file: str) -> Path:
    """Write combined research report to vault."""
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    # Use first topic slug for filename
    slug = safe_slug(topics[0]["topic"]) if topics else "research"
    output_file = RESEARCH_DIR / f"{today}-research.md"

    content = f"""# Research Report — {today}
_Generated from: {insight_file}_
_Topics: {len(topics)}_

---

"""
    for i, (topic, brief) in enumerate(zip(topics, briefs), 1):
        content += f"""## Topic {i}: {topic['topic']}

**Why:** {topic['why']}
**Question:** {topic['question']}

{brief}

---

"""

    output_file.write_text(content, encoding="utf-8")
    return output_file


def post_to_clickup(topics: list[dict], output_file: Path) -> None:
    """Post research summary to ClickUp."""
    import urllib.request
    import urllib.error

    token = load_env_var("CLICKUP_API_TOKEN")
    if not token:
        print("WARNING: CLICKUP_API_TOKEN not found, skipping ClickUp post.", file=sys.stderr)
        return

    today = date.today().strftime("%B %d, %Y")
    topic_lines = "\n".join(f"• {t['topic']}" for t in topics)

    message = (
        f"🔬 **Research Agent** ({today})\n\n"
        f"Researched {len(topics)} topics from today's blind-spots insight:\n\n"
        f"{topic_lines}\n\n"
        f"_Full report: Vault/Work/Research/{output_file.name}_"
    )

    url = f"https://api.clickup.com/api/v3/workspaces/{CLICKUP_WORKSPACE}/chat/channels/{CLICKUP_CHANNEL}/messages"
    payload = _json.dumps({"content": message}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Authorization": token, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"Posted to ClickUp ({resp.status})", file=sys.stderr)
    except Exception as e:
        print(f"WARNING: ClickUp post failed: {e}", file=sys.stderr)


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Research Agent — PM intelligence loop Stage 2")
    parser.add_argument("--topic", help="Research a specific topic instead of reading latest insight")
    parser.add_argument("--dry-run", action="store_true", help="Show topics only, no full research")
    args = parser.parse_args()

    print(f"\n{'='*60}", file=sys.stderr)
    print(f"  Research Agent", file=sys.stderr)
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)

    # Specific topic override
    if args.topic:
        topics = [{"topic": args.topic, "why": "User-requested research", "question": f"What should I know about: {args.topic}?"}]
        insight_content, insight_file = "", "manual"
        print(f"\nManual topic: {args.topic}", file=sys.stderr)
    else:
        # Read latest insight
        insight_content, insight_file = get_latest_insight()
        if not insight_content:
            print("ERROR: No insight files found in Vault/Work/Insights/", file=sys.stderr)
            print("Run insight-agent.py first.", file=sys.stderr)
            sys.exit(1)
        print(f"\nReading insight: {insight_file}", file=sys.stderr)

        # Extract top 3 topics
        topics = extract_topics(insight_content)
        if not topics:
            print("ERROR: Could not extract topics from insight.", file=sys.stderr)
            sys.exit(1)

    # Show topics
    print(f"\nTop {len(topics)} research topics:", file=sys.stderr)
    for i, t in enumerate(topics, 1):
        print(f"  {i}. {t['topic']}", file=sys.stderr)
        print(f"     → {t['question']}", file=sys.stderr)

    if args.dry_run:
        print("\n[DRY RUN] Skipping research.", file=sys.stderr)
        sys.exit(0)

    # Research each topic
    print(f"\nGenerating research briefs...", file=sys.stderr)
    briefs = []
    for topic in topics:
        brief = research_topic(topic, insight_content)
        briefs.append(brief)

    # Write report
    output_file = write_research_report(topics, briefs, insight_file)
    print(f"\nSaved to: {output_file}", file=sys.stderr)

    # Print report
    content = output_file.read_text(encoding="utf-8")
    sys.stdout.buffer.write(content.encode("utf-8", errors="replace"))
    sys.stdout.buffer.flush()

    # Post to ClickUp
    post_to_clickup(topics, output_file)


def post_error_to_clickup(script: str, error: str) -> None:
    """Post error notification to ClickUp if the agent fails."""
    import urllib.request, urllib.error
    token = load_env_var("CLICKUP_API_TOKEN")
    if not token:
        return
    message = (
        f"⚠️ **{script} failed** ({date.today().isoformat()})\n\n"
        f"Error: `{error[:300]}`\n\n"
        f"Check logs or run manually to investigate."
    )
    url = f"https://api.clickup.com/api/v3/workspaces/{CLICKUP_WORKSPACE}/chat/channels/{CLICKUP_CHANNEL}/messages"
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
        post_error_to_clickup("Research Agent", str(exc))
        sys.exit(1)
