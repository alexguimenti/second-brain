#!/usr/bin/env python3
"""Convert ClickUp chat JSON to Obsidian vault markdown snapshots."""
import json, sys, os
from datetime import datetime, timezone

USER_MAP = {
    "87364357": "Alexandre Guimenti", "158660117": "Asif Dilshad",
    "87379953": "Oluwatosin Ayodele", "81565783": "Basit Afraz",
    "81568546": "Shoaib Amjad", "87339190": "Mohsin Khan",
    "87370674": "Omar Sajid", "87345632": "Ahsan Bilal",
    "81568541": "Muhammad Mutasim", "87371978": "Umar Javed",
    "87345629": "Muhammad Hassan Siddiqi", "87359910": "Xavier Odhiambo",
    "81551684": "Yahia mazouzi", "87405802": "Muhammad Abdullah",
    "78727799": "Manick Bhan", "81330117": "Tomas Lopes",
    "87390374": "Andre Rocha", "81568544": "Saad Bin Abid",
    "81482341": "Laiq Butt", "81517612": "Juan Nicolas Villamil",
    "81359530": "Ismar Costa", "81568530": "Aleksandar Ignjatovic",
    "87327810": "Peter Olayinka", "81552914": "Runor Adjekpiyede",
    "81490441": "Jason Sobers", "87403467": "Anjali Sharma",
    "87403466": "Unknown PM", "81342219": "Unknown",
    "87348835": "Boluwatife Popoola", "87329015": "Victor Igbokwe",
    "81511159": "Unknown", "87312923": "Rizwan Arshad",
    "81580540": "Charles Oraegbu", "87353982": "Nnaemezie Okeke",
    "170526112": "Bhargav Gajjar", "87303818": "George Obamogie",
    "87354350": "Unknown", "87312848": "Victor Igbokwe",
    "81525366": "Nirman Rasadiya", "87404847": "Rehan Ahmed",
    "81588320": "Miracle Adebunmi", "87332703": "Timileyin Bamgbose",
    "87330861": "Daniella Orika", "87351164": "Muhammad Faizan",
    "87415424": "Juan Golindano", "75599880": "Justin Rondeau",
    "87368939": "Rafael Mordomo", "170529675": "Haseeb Ahmad",
    "-1": "Automation",
}

import re

def clean_mentions(text):
    # [@Name](#user_mention#id) -> @Name
    text = re.sub(r'\[@([^\]]+)\]\(#user_mention#[^)]+\)', r'@\1', text)
    # [](#user_group_mention#id) -> @team
    text = re.sub(r'\[([^\]]*)\]\(#user_group_mention#[^)]+\)', lambda m: m.group(1) if m.group(1) else '@team', text)
    # [@followers](#task_user_group_mention#followers_tag) -> @followers
    text = re.sub(r'\[@followers\]\(#task_user_group_mention#[^)]+\)', '@followers', text)
    # Also handle the format without brackets for group mentions
    text = re.sub(r'\[\]\(#user_group_mention#[^)]+\)', '@team', text)
    return text

def epoch_to_str(epoch_ms):
    dt = datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M UTC")

def process_channel(json_path, channel_name, channel_id, output_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    messages = data.get("messages", [])
    # Reverse to chronological (oldest first)
    messages.sort(key=lambda m: m["date"])

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    now_short = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    count = len(messages)

    lines = [
        "---",
        "type: clickup-chat",
        f"channel: {channel_name}",
        f"channel_id: {channel_id}",
        f"last_synced: {now}",
        f"message_count: {count}",
        "---",
        "",
        f"# ClickUp Chat — {channel_name}",
        "",
        f"*Last synced: {now_short} · Showing last {count} messages*",
        "",
    ]

    for msg in messages:
        user_id = str(msg.get("user_id", ""))
        author = USER_MAP.get(user_id, f"User {user_id}")
        timestamp = epoch_to_str(msg["date"])
        content = clean_mentions(msg.get("content", ""))

        if not content.strip():
            continue

        lines.append("---")
        lines.append("")
        lines.append(f"**{author}** · {timestamp}")
        lines.append(content)
        lines.append("")

    lines.append("---")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"Wrote {count} messages to {output_path}")

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: chat-snapshot.py <json_path> <channel_name> <channel_id> <output_path>")
        sys.exit(1)

    process_channel(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
