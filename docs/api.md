# Baba Quran Web Server REST API Specification

The Baba Quran Web Admin Server runs by default on `http://localhost:8080`.

---

## 1. System & Monitoring Endpoints

### `GET /api/status`
Returns complete runtime health, bot state, Khatmah progress, reactions count, and active configurations.

**Response Example (`200 OK`)**:
```json
{
  "bot_running": false,
  "chrome_connected": true,
  "whatsapp_logged_in": true,
  "khatmah": {
    "current_page": 14,
    "cycle_number": 1,
    "updated_at": "2026-08-27 17:43:40"
  },
  "active_members_count": 7,
  "reactions_count": 1,
  "latest_post": {
    "id": 12,
    "post_date": "2026-08-27",
    "post_type": "regular_khatmah",
    "page_start": 12,
    "page_end": 13,
    "surah_name": "Al-Baqarah",
    "posted_at": "2026-08-27 17:42:58.941408+00:00",
    "reminder_due_at": "2026-08-28 05:42:58.941408+00:00",
    "reminder_processed": false
  },
  "settings": {
    "group_jid": "120363429851468692@g.us",
    "pages_per_day": 2,
    "post_time": "07:00",
    "reminder_hours_after_post": 12,
    "timezone": "Asia/Riyadh",
    "friday_kahf_enabled": true
  }
}
```

### `GET /api/members`
Returns the list of all participating family members with their display names, real phone numbers, and reaction status for today's post.

**Response Example (`200 OK`)**:
```json
[
  {
    "jid": "180569132535857@lid",
    "display_name": "Muammar 🇦🇪",
    "phone_number": "+971 55 123 2716",
    "is_admin": true,
    "is_exempt": false,
    "reacted": false,
    "reaction_emoji": "",
    "reminder_sent": false
  },
  {
    "jid": "17218725249248@lid",
    "display_name": "Muammar 🇨🇦",
    "phone_number": "+1 (289) 885-5514",
    "is_admin": true,
    "is_exempt": false,
    "reacted": true,
    "reaction_emoji": "🙏",
    "reminder_sent": false
  }
]
```

### `GET /api/surahs`
Returns metadata for all 114 Surahs (Surah number, Arabic name, English transliteration, starting page, and ending page).

### `GET /api/logs`
Returns the recent log entries from `logs/web_server.log`.

---

## 2. Action Endpoints

### `POST /api/khatmah/set_page`
Updates the upcoming schedule starting page (1 to 604) in SQLite.

**Request Payload**:
```json
{
  "page": 100
}
```

**Response (`200 OK`)**:
```json
{
  "success": true,
  "message": "تم تحديث صفحة البداية للجدول القادم بنجاح إلى صفحة 100",
  "current_page": 100
}
```

### `POST /api/actions/post_now`
Proactively triggers the daily post routine immediately, advances the Khatmah pointer, and marks today's date in SQLite to automatically skip the scheduled 07:00 AM post.

**Response (`200 OK`)**:
```json
{
  "success": true,
  "message": "تم نشر ورد اليوم بنجاح في المجموعة!",
  "post_id": 13
}
```

### `POST /api/actions/sync_reactions`
Scans WhatsApp Web's `ReactionsStore` on-demand for reactions placed on the active daily post and updates the database.

**Response (`200 OK`)**:
```json
{
  "success": true,
  "message": "تم جلب ومزامنة 1 تفاعل من واتساب",
  "reactions": [
    {
      "msgId": "true_120363429851468692@g.us_3EB08FE684DC03278042BC_180569132535857@lid",
      "sender": "17218725249248@lid",
      "emoji": "🙏"
    }
  ]
}
```

### `POST /api/actions/post_surah`
Publishes an off-the-plan Surah (e.g. Surah Al-Kahf) without advancing the regular Khatmah pointer.

**Request Payload**:
```json
{
  "surah_number": 18
}
```

### `POST /api/members/exempt`
Toggles the 12-hour reminder exemption flag for a specific group member.

**Request Payload**:
```json
{
  "jid": "180569132535857@lid"
}
```

### `POST /api/settings`
Saves updated operational settings into SQLite (`post_time`, `pages_per_day`, `reminder_hours_after_post`, etc.).
