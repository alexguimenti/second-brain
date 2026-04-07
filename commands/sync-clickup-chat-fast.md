Fetch ClickUp chat messages and save raw JSON for offline conversion.

## Instructions

1. Read config from `{{VAULT_ROOT}}/Work/ClickUp/chat-sync-config.json`
2. Create temp directory: `/tmp/clickup-chat-sync/`
3. For EACH channel in config, call `clickup_get_chat_channel_messages(channelId, limit)` where limit comes from `defaults.messages_limit`
4. Save the raw JSON response to `/tmp/clickup-chat-sync/<channel_id>.json`
5. After all channels are fetched, run: `python scripts/convert-chat-json.py /tmp/clickup-chat-sync/`
6. Report how many channels were synced

IMPORTANT: Do NOT format or process the messages yourself. Just fetch and save the raw JSON. The Python script handles all formatting. This saves tokens.
