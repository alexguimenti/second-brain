#!/usr/bin/env python3
"""One-shot chat sync: fetches all configured channels via ClickUp API and writes snapshots.

Usage:
    python scripts/sync-chat-now.py

Requires CLICKUP_API_TOKEN env var or ~/.clickup-token file.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
import urllib.request
import urllib.error

VAULT_ROOT = Path(os.environ.get("VAULT_ROOT", Path.home() / "Documents" / "Vaults" / "Mex_Vault"))
CONFIG_PATH = VAULT_ROOT / "Work" / "ClickUp" / "chat-sync-config.json"
TZ = timezone(timedelta(hours=-3))

USER_MAP = {
    "78727799": "Manick Bhan",
    "81303260": "Arman Ekhlasi",
    "81330117": "Tomas Lopes",
    "81359530": "Ismar Costa",
    "81482341": "Laiq Butt",
    "81490441": "Jason Sobers",
    "81511159": "Victor Igbokwe",
    "81517612": "Juan Nicolas Villamil",
    "81525366": "Nirman Rasadiya",
    "81551684": "Yahia Mazouzi",
    "81552914": "Runor Adjekpiyede",
    "81565783": "Basit Afraz",
    "81568530": "Aleksandar Ignjatović",
    "81568541": "Muhammad Mutasim",
    "81568544": "Saad Bin Abid",
    "81568546": "Shoaib Amjad",
    "81580540": "Charles Oraegbu",
    "81588320": "Miracle Adebunmi",
    "87303818": "DevOps Bot",
    "87312848": "Victor Igbokwe (KE)",
    "87312923": "Rizwan Arshad",
    "87327810": "Peter Olayinka",
    "87329015": "Victor (SE)",
    "87332703": "Timileyin Bamgbose",
    "87339190": "Mohsin Khan",
    "87345629": "Hassan (DevBot)",
    "87345632": "Ahsan Bilal",
    "87353982": "Nnaemezie Okeke",
    "87359910": "Xavier Odhiambo",
    "87364357": "Alexandre Guimenti",
    "87368939": "Rafael Mordomo",
    "87370674": "Omar Sajid",
    "87371978": "Umar Javed",
    "87379953": "Oluwatosin Ayodele",
    "87390374": "Andre Rocha",
    "87393610": "Harib Siddique",
    "87403466": "Keshav Sharma",
    "87403467": "Jagjeevan Brar",
    "87404847": "Rehan Ahmed",
    "87405802": "Muhammad Abdullah",
    "87415424": "Juan Golindano",
    "158660117": "Asif Dilshad",
    "170526112": "Haseeb Ahmad (PM)",
    "170529675": "Haseeb Ahmad (QA)",
    "-1": "Automation Bot",
}


def get_token():
    token = os.environ.get("CLICKUP_API_TOKEN")
    if token:
        return token
    token_file = Path.home() / ".clickup-token"
    if token_file.exists():
        return token_file.read_text().strip()
    # Try to extract from claude MCP config
    claude_json = Path.home() / ".claude.json"
    if claude_json.exists():
        data = json.loads(claude_json.read_text())
        servers = data.get("mcpServers", {})
        clickup = servers.get("clickup", {})
        env = clickup.get("env", {})
        token = env.get("CLICKUP_API_TOKEN") or env.get("CLICKUP_TOKEN")
        if token:
            return token
    print("ERROR: No ClickUp API token found. Set CLICKUP_API_TOKEN env var.", file=sys.stderr)
    sys.exit(1)


def fetch_messages(channel_id: str, token: str, limit: int = 50) -> list:
    url = f"https://api.clickup.com/api/v3/chat/channel/{channel_id}/message?limit={limit}"
    req = urllib.request.Request(url, headers={
        "Authorization": token,
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            return data.get("messages", [])
    except urllib.error.HTTPError as e:
        print(f"  ERROR fetching {channel_id}: HTTP {e.code}", file=sys.stderr)
        return []


def clean_mentions(text: str) -> str:
    import re
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


def resolve_author(user_id: str) -> str:
    return USER_MAP.get(str(user_id), f"User {user_id}")


def write_snapshot(channel: dict, messages: list):
    name = channel["name"]
    channel_id = channel["channel_id"]
    vault_file = channel["vault_file"]
    filepath = VAULT_ROOT / vault_file

    # Ensure directory exists
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Reverse messages (API returns newest first)
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
    if not CONFIG_PATH.exists():
        print(f"ERROR: Config not found at {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)

    config = json.loads(CONFIG_PATH.read_text())
    channels = config["channels"]
    limit = config.get("defaults", {}).get("messages_limit", 50)
    token = get_token()

    print(f"Syncing {len(channels)} channels (limit={limit})...")
    results = []

    for ch in channels:
        name = ch["name"]
        print(f"  [{name}] fetching...", end=" ", flush=True)
        messages = fetch_messages(ch["channel_id"], token, limit)
        if messages:
            count = write_snapshot(ch, messages)
            print(f"{count} messages written")
            results.append((name, count, ch["vault_file"]))
        else:
            print("no messages or error")
            results.append((name, 0, ch["vault_file"]))
        time.sleep(0.2)  # rate limit courtesy

    print("\n## Chat Sync Complete\n")
    print(f"| Channel | Messages | File |")
    print(f"|---------|----------|------|")
    for name, count, path in results:
        print(f"| {name} | {count} | {path} |")


if __name__ == "__main__":
    main()
