#!/usr/bin/env python3
"""Session auto-backup: extract user messages from a Claude Code session transcript
and write a lightweight markdown note to the Obsidian vault.

Designed to run as a SessionEnd hook. Reads JSON from stdin with session metadata.
Exits 0 on all errors — must never block session termination.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def get_vault_root() -> Path:
    """Resolve vault root from env var or default."""
    env = os.environ.get("VAULT_ROOT")
    if env:
        return Path(env)
    return Path.home() / "Documents" / "Vaults" / "Mex_Vault"


def read_stdin_json() -> dict:
    """Read the hook input JSON from stdin."""
    return json.loads(sys.stdin.read())


def extract_user_messages(transcript_path: str) -> list[str]:
    """Extract user text messages from a JSONL transcript file.

    Filters out:
    - Non-user messages (assistant, system, tool results)
    - System reminders (text starting with '<')
    - Empty messages
    """
    messages = []
    with open(transcript_path, encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            if obj.get("type") != "user":
                continue

            content = obj.get("message", {}).get("content", "")

            if isinstance(content, str):
                text = content.strip()
                if text and not text.startswith("<"):
                    messages.append(text)
            elif isinstance(content, list):
                # Skip tool_result blocks, only extract text blocks
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text", "").strip()
                        if text and not text.startswith("<"):
                            messages.append(text)
                            break  # One text block per user turn is enough

    return messages


def derive_project_name(cwd: str) -> str:
    """Extract project name from the last component of cwd."""
    return Path(cwd).name or "unknown"


def to_windows_path(posix_path: str) -> str:
    """Convert MSYS/cygwin-style path to Windows path.

    /c/Users/foo → C:\\Users\\foo
    If already Windows-style or not convertible, return as-is.
    """
    if len(posix_path) >= 3 and posix_path[0] == "/" and posix_path[2] == "/":
        drive = posix_path[1].upper()
        rest = posix_path[2:].replace("/", "\\")
        return f"{drive}:{rest}"
    return posix_path


def truncate(text: str, max_len: int = 200) -> str:
    """Truncate text to max_len, adding ellipsis if needed."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def generate_markdown(
    session_id: str,
    project: str,
    project_path: str,
    messages: list[str],
    exit_reason: str,
    date: str,
) -> str:
    """Generate the markdown content for the auto-backup note."""
    msg_lines = "\n".join(f"- {truncate(m)}" for m in messages)

    return f"""---
type: session-auto
date: {date}
project: {project}
session_id: {session_id}
project_path: "{project_path}"
messages: {len(messages)}
exit_reason: {exit_reason}
---

# Auto-backup: {project}

## User messages
{msg_lines}

## Resume
```powershell
cd "{project_path}"; claude --resume {session_id}
```
"""


def append_to_daily_log(project: str, messages: list[str], date: str):
    """Append a session summary to the daily log file.

    The daily log lives at ~/.claude/daily-logs/YYYY-MM-DD.md and is read by
    the /eod command to generate End-of-Day reports. Each session gets a
    timestamped section with the user's messages as bullet points.
    """
    log_dir = Path.home() / ".claude" / "daily-logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{date}.md"

    time_str = datetime.now().strftime("%H:%M")

    # Build a concise topic line from the first few messages
    topic_messages = [truncate(m, 80) for m in messages[:5]]
    bullets = "\n".join(f"- {m}" for m in topic_messages)
    if len(messages) > 5:
        bullets += f"\n- ... (+{len(messages) - 5} more messages)"

    entry = f"\n## {time_str} — {project} (auto)\n\n{bullets}\n"

    # Create file with header if it doesn't exist, otherwise append
    if not log_path.is_file():
        log_path.write_text(f"# {date}\n{entry}", encoding="utf-8")
    else:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(entry)


def main():
    try:
        hook_input = read_stdin_json()
    except (json.JSONDecodeError, ValueError):
        return  # Malformed input, exit silently

    session_id = hook_input.get("session_id", "unknown")
    transcript_path = hook_input.get("transcript_path", "")
    cwd = hook_input.get("cwd", "")
    exit_reason = hook_input.get("session_exit_reason", "unknown")

    if not transcript_path or not os.path.isfile(transcript_path):
        return  # No transcript, nothing to backup

    vault_root = get_vault_root()
    if not vault_root.is_dir():
        return  # Vault not found

    # Extract messages
    messages = extract_user_messages(transcript_path)
    if len(messages) < 3:
        return  # Trivial session, skip

    # Build output
    project = derive_project_name(cwd)
    project_path = to_windows_path(cwd)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    session_short = session_id[:8]

    output_dir = vault_root / "Work" / "Claude Code" / "Sessions" / "auto"
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{date}-{project}-{session_short}.md"
    output_path = output_dir / filename

    markdown = generate_markdown(
        session_id=session_id,
        project=project,
        project_path=project_path,
        messages=messages,
        exit_reason=exit_reason,
        date=date,
    )

    output_path.write_text(markdown, encoding="utf-8")

    # Append session entry to daily log (~/.claude/daily-logs/YYYY-MM-DD.md)
    # This feeds into the /eod command which reads from this directory
    append_to_daily_log(project, messages, date)

    # Sync global config files from ~/.claude/ to vault
    for filename in ("USER.md", "SOUL.md", "CLAUDE.md", "MEMORY.md"):
        source = Path.home() / ".claude" / filename
        dest = vault_root / "Tools" / filename
        if source.is_file():
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # Never fail, never block session termination
