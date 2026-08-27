# ADR-002: On-Demand Reaction Scanning via ReactionsStore

## Status
**Accepted & Mandatory**

## Context
Initial attempts used 24/7 background event listeners (`WPP.on('chat.msg_reaction')`). Over prolonged idle periods or after background daemon restarts, persistent event streams can drop silently without health checks. Furthermore, reaction state is only strictly required at two specific moments:
1. When the 12-hour reminder job evaluates pending members.
2. When the admin manually refreshes the web dashboard.

## Decision
1. **Daily Reset on Posting**: Immediately upon posting new daily Quran pages, the database initializes a clean roster in `member_activity` for all active group members with `reacted = 0`.
2. **On-Demand Inspection**: Exactly prior to dispatching 12-hour reminder DMs (or upon manual refresh), the bot queries WhatsApp Web's internal `ReactionsStore`:
   ```javascript
   const store = window.WPP.whatsapp.ReactionsStore;
   const rEntry = store.get(msgId);
   // Traverses rEntry.reactions[].senders[].senderUserJid and reactionText
   ```
3. **Targeted Reminders**: Private reminder DMs are dispatched strictly to members with `reacted = 0`.

## Consequences
- **Positive**: Eliminates fragile 24/7 listener streaming overhead.
- **Positive**: Guarantees deterministic state verification immediately before sending messages to real family members.
