# ADR-001: Direct WA-JS API Injected Media Dispatch

## Status
**Accepted & Mandatory**

## Context
Initial implementations attempted to send media files by automating the WhatsApp Web DOM (clicking the `+` paperclip icon, interacting with OS file dialogs via desktop automation, and pressing `Enter`). This proved brittle due to:
1. Dynamic popup modals ("Discard selection?", "What's new in WhatsApp Web").
2. Obfuscated class names and unmounted React file inputs.
3. Windows UIPI security boundaries in headless background sessions.

## Decision
All WhatsApp media dispatching and message actions MUST use the injected `wppconnect-wa.js` (WA-JS) API bridge directly inside the persistent Playwright browser context:
```python
from src.whatsapp.playwright_client import pw_whatsapp
await pw_whatsapp.send_quran_pages_to_group(image_paths, caption)
```
Internally, this invokes:
```javascript
await WPP.chat.find(jid);
await WPP.chat.openChatBottom(jid);
await WPP.chat.sendFileMessage(jid, dataUrl, { type: 'image', caption, filename });
```

## Consequences
- **Positive**: 100% deterministic dispatch utilizing WhatsApp Web's internal media encryption pipeline without DOM dependencies.
- **Positive**: Returns verified WhatsApp Server Message IDs (`msgId`).
- **Requirement**: Must wait for `#pane-side` and call `WPP.chat.find(jid)` before dispatching.
