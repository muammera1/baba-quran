# Antigravity Guidelines: Baba Quran Bot

## Project Identity & Architecture
**Baba Quran** is an automated, stateful Python application that manages daily Quran reading schedules, posts page images to a WhatsApp group, tracks member emoji reactions on demand, and sends private DM reminders to members who have not reacted within 12 hours.

---

## ⚠️ Critical Operational Rules (DO NOT DEVIATE)

### 1. WhatsApp Dispatch via WA-JS API Only (No DOM Emulation)
- **STRICT RULE**: **NEVER** simulate raw DOM clicks, file dialogs, or keyboard `SendKeys`/`Enter` to send media on WhatsApp Web. WhatsApp Web's obfuscated class names, dynamic modals ("Discard selection?", "What's new"), and unmounted file pickers cause brittle failures.
- **MANDATORY PATTERN**: **ALWAYS** use the direct WA-JS API bridge (`src/whatsapp/wppconnect-wa.js`) injected into the persistent Playwright context:
  ```python
  from src.whatsapp.playwright_client import pw_whatsapp
  await pw_whatsapp.send_quran_pages_to_group(image_paths, caption)
  ```
  Internally, this invokes `WPP.chat.sendFileMessage(jid, dataUrl, { type: 'image', caption, filename })` which directly utilizes WhatsApp's media encryption pipeline.

### 2. ChatStore & Chat Model Pre-Mounting
- **STRICT RULE**: Before sending any message or querying reactions via WA-JS:
  1. Wait for WhatsApp Web chat list to mount (`#pane-side, div[aria-label="Chat list"]`).
  2. Always call `await WPP.chat.find(jid)` and `await WPP.chat.openChatBottom(jid)` to ensure the chat model is indexed in `ChatStore` and avoid `"Chat not found in ChatStore"` errors.

### 3. Reaction Architecture: On-Demand via ReactionsStore
- **STRICT RULE**: Do NOT rely on unmonitored 24/7 background event streams. Reactions are only needed:
  1. **At the 12-Hour Reminder threshold** (before sending private DMs).
  2. **On-Demand / Web Dashboard Refresh** (when the admin clicks "فحص التفاعلات").
- **Parsing Structure**: In WhatsApp Web, member reactions are retrieved via `window.WPP.whatsapp.ReactionsStore.get(msgId)`:
  - Reactions array: `rEntry.reactions`
  - Senders list: `group.senders`
  - Member JID: `sender.senderUserJid` (e.g. `12345678901234@lid`)
  - Emoji: `sender.reactionText` (e.g. `🙏`, `👍`, `❤️`)

### 4. Proactive Manual Posting & Automatic Schedule Skip
- When the admin triggers a post proactively (via Web Dashboard **"نشر ورد اليوم فوراً"** or CLI `python3 scripts/post_now.py`):
  - Post is sent immediately, Khatmah pointer advances, and today's date (`YYYY-MM-DD`) is recorded in SQLite.
  - The scheduled morning job (07:00 AM) inspects SQLite: if a post exists for today's date, it **gracefully skips posting again** to prevent duplicate messages.

### 5. Manual Schedule Start Page Slider
- The admin can slide/set the upcoming schedule starting page anytime (1–604) via the Web Dashboard slider or CLI `python3 scripts/set_page.py <page_number>`.

### 6. Linux / WSL Environment Isolation
- The bot runs **100% inside Linux / WSL**.
- **STRICT RULE**: **NEVER** attempt cross-OS GUI automation into Windows (e.g. running `cmd.exe /c start chrome` or PowerShell keystroke automation).
- All persistent session data resides locally in `data/session/playwright_wa/`.

### 7. Virtual Environment Execution
- Always use the dedicated virtual environment:
  ```bash
  source .venv/bin/activate
  ```
  Or run python commands with `.venv/bin/python`.

### 8. Singleton Session Directory Lock
- The background daemon (`./manage.sh`) holds an exclusive lock on `data/session/playwright_wa/`.
- Never launch standalone Playwright scripts that open the same session directory while the daemon is active without stopping the daemon first or using the Web Server's REST APIs.

### 9. Verification Before Declaring Success
- **STRICT RULE**: Never declare a post sent unless:
  1. The API call returns `{ success: True, msgId: 'true_...' }` from WhatsApp.
  2. The database state and Khatmah pointers are updated accordingly.

### 10. Daemon & Web Admin Management
- The background daemon is controlled via `./manage.sh`:
  - `./manage.sh start` — Start background bot and web dashboard.
  - `./manage.sh stop` — Stop daemon cleanly.
  - `./manage.sh restart` — Restart with latest code.
  - `./manage.sh status` — Check PID and running state.
  - `./manage.sh logs` — Tail live logs.
- The Web Admin Dashboard runs on port `8080` (`http://localhost:8080`).

---

## Directory Conventions
```
baba-quran/
├── config/              # YAML settings & templates
├── data/                # Local data (SQLite db, 604 page images, auth session)
├── src/                 # Source code (core, quran, whatsapp, scheduler, web)
│   ├── core/            # Database, config, logger, models
│   ├── quran/           # Page manager, metadata, special schedules
│   ├── whatsapp/        # Playwright client, WA-JS bridge, event listener
│   ├── scheduler/       # APScheduler daily jobs & reminders
│   └── web/             # Zero-dependency Web Admin Dashboard
├── scripts/             # CLI utilities & setup scripts
│   ├── set_page.py      # CLI utility to slide/set next start page
│   ├── post_now.py      # CLI utility to proactively execute daily post
│   ├── sync_members.py  # Member sync utility
│   └── download_pages.py # Quran images downloader
├── tests/               # Unit and integration test suite
├── manage.sh            # Service lifecycle management script
├── plan.md              # Master architecture and implementation plan
├── GEMINI.md            # Agent instructions and guidelines
└── requirements.txt     # Python dependencies
```
