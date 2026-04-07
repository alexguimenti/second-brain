#!/usr/bin/env python3
"""Convert raw ClickUp chat JSON files to markdown snapshots.

Phase 2 of the two-phase chat sync:
  Phase 1: Claude (haiku) fetches messages via MCP → saves JSON to temp dir
  Phase 2: This script converts JSON → markdown (zero LLM tokens)

Usage:
    python scripts/convert-chat-json.py <json_dir>

Where <json_dir> contains files named <channel_id>.json, each with the raw
MCP response: {"messages": [...], "total_count": N, ...}
"""

import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

VAULT_ROOT = Path(os.environ.get("VAULT_ROOT", Path.home() / "Documents" / "Vaults" / "Mex_Vault"))
CONFIG_PATH = VAULT_ROOT / "Work" / "ClickUp" / "chat-sync-config.json"
TZ = timezone(timedelta(hours=-3))

USER_MAP = {
    "78727799": "Manick Bhan",
    "81303260": "Arman Ekhlasi",
    "81330117": "Tomas Lopes",
    "81342219": "Unknown",
    "81359530": "Ismar Costa",
    "81482341": "Laiq Butt",
    "81490441": "Jason Sobers",
    "81511159": "Victor Igbokwe",
    "81517612": "Juan Nicolas Villamil",
    "81525366": "Nirman Rasadiya",
    "81551684": "Yahia Mazouzi",
    "81552914": "Runor Adjekpiyede",
    "81555830": "Jonathan Kilton",
    "81565783": "Basit Afraz",
    "81568530": "Aleksandar Ignjatovic",
    "81568541": "Muhammad Mutasim",
    "81568544": "Saad Bin Abid",
    "81568546": "Shoaib Amjad",
    "81580540": "Charles Oraegbu",
    "81588320": "Miracle Adebunmi",
    "87303818": "George Obamogie",
    "87312848": "Victor Igbokwe (KE)",
    "87312923": "Rizwan Arshad",
    "87327810": "Peter Olayinka",
    "87329015": "Victor (SE)",
    "87330861": "Daniella Orika",
    "87332703": "Timileyin Bamgbose",
    "87339190": "Mohsin Khan",
    "87345629": "Hassan (DevBot)",
    "87345632": "Ahsan Bilal",
    "87351164": "Muhammad Faizan",
    "87353982": "Nnaemezie Okeke",
    "87359910": "Xavier Odhiambo",
    "87364357": "Alexandre Guimenti",
    "87368939": "Rafael Mordomo",
    "87370674": "Omar Sajid",
    "87371978": "Umar Javed",
    "87379953": "Oluwatosin Ayodele",
    "87390374": "Andre Rocha",
    "87390596": "Mariana Vieira",
    "87393610": "Harib Siddique",
    "87403466": "Keshav Sharma",
    "87403467": "Jagjeevan Brar",
    "87404847": "Rehan Ahmed",
    "87405802": "Muhammad Abdullah",
    "87415424": "Juan Golindano",
    "75599880": "Justin Rondeau",
    "158660117": "Asif Dilshad",
    "170526112": "Haseeb Ahmad (PM)",
    "170529675": "Haseeb Ahmad (QA)",
    "242501920": "Zubaidat Abdulsalam",
    "-1": "Automation Bot",
}


def clean_mentions(text: str) -> str:
    # [@Name](#user_mention#id) → @Name
    text = re.sub(r'\[@([^\]]+)\]\(#user_mention#\d+\)', r'@\1', text)
    # [](#user_group_mention#id) → @team
    text = re.sub(r'\[([^\]]*)\]\(#user_group_mention#[^)]+\)', lambda m: m.group(1) if m.group(1) else '@team', text)
    # [@followers](#task_user_group_mention#followers_tag) → @followers
    text = re.sub(r'\[@followers\]\(#task_user_group_mention#followers_tag\)', '@followers', text)
    return text


def format_timestamp(epoch_ms: int) -> str:
    dt = datetime.fromtimestamp(epoch_ms / 1000, tz=TZ)
    return dt.strftime("%Y-%m-%d %H:%M")


def resolve_author(user_id) -> str:
    return USER_MAP.get(str(user_id), f"User {user_id}")


def write_snapshot(channel: dict, messages: list):
    name = channel["name"]
    channel_id = channel["channel_id"]
    vault_file = channel["vault_file"]
    filepath = VAULT_ROOT / vault_file

    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Reverse: API returns newest first, we want oldest first
    messages = list(reversed(messages))
    count = len(messages)
    now = datetime.now(tz=TZ).strftime("%Y-%m-%dT%H:%M:%S%z")
    now_short = datetime.now(tz=TZ).strftime("%Y-%m-%d %H:%M")

    lines = [
        "---",
        "type: clickup-chat",
        f"channel: {name}",
        f"channel_id: {channel_id}",
        f"last_synced: {now}",
        f"message_count: {count}",
        "---",
        "",
        f"# ClickUp Chat — {name}",
        "",
        f"*Last synced: {now_short} · Showing last {count} messages*",
        "",
    ]

    for msg in messages:
        author = resolve_author(msg.get("user_id", ""))
        ts = format_timestamp(msg["date"])
        content = clean_mentions(msg.get("content", ""))
        if not content.strip():
            content = "*(empty message)*"
        lines.append("---")
        lines.append("")
        lines.append(f"**{author}** · {ts}")
        lines.append(content)
        lines.append("")

    filepath.write_text("\n".join(lines), encoding="utf-8")
    return count


def main():
    if len(sys.argv) < 2:
        print("Usage: python convert-chat-json.py <json_dir>", file=sys.stderr)
        sys.exit(1)

    json_dir = Path(sys.argv[1])
    if not json_dir.exists():
        print(f"ERROR: Directory {json_dir} not found", file=sys.stderr)
        sys.exit(1)

    config = json.loads(CONFIG_PATH.read_text())
    channel_map = {ch["channel_id"]: ch for ch in config["channels"]}

    written = 0
    skipped = 0

    for json_file in sorted(json_dir.glob("*.json")):
        channel_id = json_file.stem
        if channel_id not in channel_map:
            print(f"  SKIP {json_file.name} — not in config")
            skipped += 1
            continue

        data = json.loads(json_file.read_text())
        messages = data.get("messages", [])
        if not messages:
            print(f"  SKIP {channel_id} — no messages")
            skipped += 1
            continue

        ch = channel_map[channel_id]
        count = write_snapshot(ch, messages)
        print(f"  OK {ch['name']}: {count} messages → {ch['vault_file']}")
        written += 1

    print(f"\nDone: {written} written, {skipped} skipped")


if __name__ == "__main__":
    main()
