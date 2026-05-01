#!/usr/bin/env python3
"""Pre-compact hook: extract key decisions from the conversation transcript
before Claude Code compacts (truncates) old messages.

Appends extracted content to the daily log so it survives compaction.
Exits 0 on all errors — must never block compaction.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path


def read_stdin_json() -> dict:
    return json.loads(sys.stdin.read())


def extract_assistant_summaries(transcript_path: str) -> list[str]:
    """Extract assistant messages that contain decisions, outcomes, or key info.

    Focuses on messages that contain decision-like patterns:
    - Lines with "decision", "decided", "chose", "approved"
    - Lines with commit hashes or "commit"
    - Lines with "deployed", "merged", "pushed"
    - Lines with "implemented", "created", "updated"
    """
    keywords = [
        "decision", "decided", "chose", "approved", "commit",
        "deployed", "merged", "pushed", "implemented", "created",
        "updated", "fixed", "resolved", "completed",
    ]

    summaries = []
    with open(transcript_path, encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            if obj.get("type") != "assistant":
                continue

            content = obj.get("message", {}).get("content", "")
            if not isinstance(content, list):
                continue

            for block in content:
                if not isinstance(block, dict) or block.get("type") != "text":
                    continue
                text = block.get("text", "")
                # Check if this message contains decision-like content
                text_lower = text.lower()
                if any(kw in text_lower for kw in keywords):
                    # Extract just the first 500 chars as a summary
                    summary = text[:500].strip()
                    if summary:
                        summaries.append(summary)

    return summaries


def extract_user_topics(transcript_path: str) -> list[str]:
    """Extract user message topics for context."""
    topics = []
    with open(transcript_path, encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            if obj.get("type") != "user":
                continue
            content = obj.get("message", {}).get("content", "")
            if isinstance(content, str):
                text = content.strip()
                if text and not text.startswith("<") and len(text) > 5:
                    topics.append(text[:100])
    return topics


def main():
    try:
        hook_input = read_stdin_json()
    except (json.JSONDecodeError, ValueError):
        return

    transcript_path = hook_input.get("transcript_path", "")
    session_id = hook_input.get("session_id", "unknown")
    cwd = hook_input.get("cwd", "")

    if not transcript_path or not os.path.isfile(transcript_path):
        return

    # Extract topics and decisions
    topics = extract_user_topics(transcript_path)
    if len(topics) < 3:
        return  # Not enough content to save

    # Derive project name
    project = Path(cwd).name if cwd else "unknown"
    date = datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.now().strftime("%H:%M")

    # Build summary
    topic_lines = "\n".join(f"- {t}" for t in topics[:10])
    if len(topics) > 10:
        topic_lines += f"\n- ... (+{len(topics) - 10} more)"

    entry = f"\n## {time_str} — {project} (pre-compact)\n\n"
    entry += f"Context saved before compaction (session: {session_id[:8]})\n\n"
    entry += f"**Topics discussed:**\n{topic_lines}\n"

    # Append to daily log (vault path, outside ~/.claude/ to avoid sensitive-file prompts)
    vault_root = Path.home() / "Documents" / "Vaults" / "Mex_Vault"
    log_dir = vault_root / "Work" / "Claude Code" / "Daily Logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{date}.md"

    if not log_path.is_file():
        log_path.write_text(f"# {date}\n{entry}", encoding="utf-8")
    else:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(entry)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # Never fail, never block compaction
