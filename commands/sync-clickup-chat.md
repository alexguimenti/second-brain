Sync ClickUp chat channels to the Obsidian vault as snapshot files (one-way: ClickUp → Vault).

## Arguments
`$ARGUMENTS` — optional: `--discover` to list available channels, or a channel name to sync one. No args = sync all configured channels.

## Constants

- Vault root: `{{VAULT_ROOT}}`
- Config file: `{{VAULT_ROOT}}/Work/ClickUp/chat-sync-config.json`

## Instructions

### Step 1: Read Config

Read `{{VAULT_ROOT}}/Work/ClickUp/chat-sync-config.json`. If missing, tell the user:
"No chat sync config found. Run `/sync-clickup-chat --discover` to find channels, then add them to `Work/ClickUp/chat-sync-config.json`."

Config format:
```json
{
  "channels": [
    {
      "channel_id": "channel-uuid",
      "name": "Channel Name",
      "vault_file": "Work/ClickUp/Chat/channel-name.md"
    }
  ],
  "defaults": {
    "messages_limit": 50,
    "include_replies": false
  }
}
```

### Step 2: Parse Arguments

1. **No arguments** → `mode = sync_all` — sync every channel in config
2. **`--discover`** → `mode = discover` — list available ClickUp chat channels
3. **Any other text** → `mode = sync_one` — match against `name` in config (case-insensitive)

### Step 3: Execute Mode

#### Mode: discover

1. Call `clickup_get_chat_channels` to list all available channels
2. Display as numbered list:

```
## ClickUp Chat Channels

[1] #product-rb (channel-uuid-1)
[2] #product-llmv (channel-uuid-2)
[3] #engineering-general (channel-uuid-3)
...

To track a channel, add it to:
  <vault>/Work/ClickUp/chat-sync-config.json

Example entry:
  {"channel_id": "channel-uuid-1", "name": "product-rb", "vault_file": "Work/ClickUp/Chat/product-rb.md"}
```

#### Mode: sync_all / sync_one

For each channel to sync:

**a) Fetch messages:**

```
clickup_get_chat_channel_messages(channelId: "<channel_id>", limit: <messages_limit>)
```

**b) Write snapshot file:**

One file per channel, overwritten on every sync:

**File path:** from `vault_file` in config (e.g., `Work/ClickUp/Chat/product-rb.md`)

**Content:**

```markdown
---
type: clickup-chat
channel: <channel name>
channel_id: <channel_id>
last_synced: <current ISO 8601 timestamp>
message_count: <N>
---

# ClickUp Chat — <channel name>

*Last synced: <YYYY-MM-DD HH:MM> · Showing last <N> messages*

---

**<author name>** · <relative or absolute timestamp>
<message content>

---

**<author name>** · <timestamp>
<message content>

---

...
```

**Rules:**
- Always overwrite — this is a snapshot of the most recent messages
- Messages ordered chronologically (oldest first)
- Render message content as markdown
- If `include_replies` is true in config, fetch and include thread replies indented under the parent message
- Create directories as needed

### Step 4: Summary report

```
## Chat Sync Complete

| Channel | Messages | File |
|---------|----------|------|
| <name> | <N> | <vault_file> |
| ... | ... | ... |
```

## Error Handling

- **ClickUp MCP not connected:** "ClickUp MCP is not connected. Check your Claude Code settings."
- **Config not found:** Suggest running `--discover` first.
- **Channel not found in config:** List available configured channels.
- **No messages:** Write file with "No recent messages" note.
