-- ============================================================================
-- Baba Quran Bot: Master SQLite Database Schema
-- Location: data/db/baba_quran.db
-- Engine: SQLite 3 with WAL Mode (Write-Ahead Logging)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Dynamic Application Settings
-- Stores runtime key-value settings (e.g. pages_per_day, post_time, reminder_hours)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 2. Khatmah Progression State
-- Tracks the ongoing Khatmah cycle and the next starting page (1 to 604)
-- Enforced singleton row (id = 1)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS khatmah_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    current_page INTEGER NOT NULL DEFAULT 1,
    cycle_number INTEGER NOT NULL DEFAULT 1,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed initial Khatmah state if not exists
INSERT OR IGNORE INTO khatmah_state (id, current_page, cycle_number)
VALUES (1, 1, 1);

-- ----------------------------------------------------------------------------
-- 3. Group Members
-- Stores family members participating in the daily Quran reading group
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS group_members (
    jid TEXT PRIMARY KEY,                              -- WhatsApp JID (e.g. 12345678901234@lid)
    phone_number TEXT,                                 -- Formatted phone number (e.g. +971 50 000 0000)
    display_name TEXT,                                 -- Saved contact name or pushname
    is_active INTEGER NOT NULL DEFAULT 1,              -- 1 = Active member, 0 = Inactive
    is_admin INTEGER NOT NULL DEFAULT 0,               -- 1 = Group Admin, 0 = Regular member
    is_exempt INTEGER NOT NULL DEFAULT 0,              -- 1 = Exclude from 12-hour DM reminders
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indices for rapid member filtering
CREATE INDEX IF NOT EXISTS idx_group_members_active ON group_members (is_active);
CREATE INDEX IF NOT EXISTS idx_group_members_phone ON group_members (phone_number);

-- ----------------------------------------------------------------------------
-- 4. Daily Posts
-- Logs every published Quran post (regular Khatmah, Friday Al-Kahf, special override)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS daily_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_date TEXT NOT NULL,                           -- Date string: YYYY-MM-DD
    post_type TEXT NOT NULL DEFAULT 'regular_khatmah', -- 'regular_khatmah' | 'friday_kahf' | 'special_override'
    page_start INTEGER NOT NULL,                       -- Starting Mushaf page (1-604)
    page_end INTEGER NOT NULL,                         -- Ending Mushaf page (1-604)
    surah_name TEXT,                                   -- Arabic name(s) of Surahs in batch
    group_jid TEXT NOT NULL,                           -- Target WhatsApp Group JID
    message_ids TEXT NOT NULL,                         -- JSON array of WhatsApp server message IDs
    posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,     -- Timestamp of actual dispatch
    reminder_due_at TIMESTAMP,                         -- 12-hour reminder threshold timestamp
    reminder_processed INTEGER NOT NULL DEFAULT 0      -- 1 = Reminders completed, 0 = Pending
);

-- Indices for date lookups and reminder scheduler
CREATE INDEX IF NOT EXISTS idx_daily_posts_date ON daily_posts (post_date);
CREATE INDEX IF NOT EXISTS idx_daily_posts_reminder ON daily_posts (reminder_processed, reminder_due_at);

-- ----------------------------------------------------------------------------
-- 5. Member Activity & Reaction Tracking
-- Tracks individual member reading completion and reminder DM statuses per post
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS member_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    daily_post_id INTEGER NOT NULL,                    -- Foreign Key -> daily_posts.id
    member_jid TEXT NOT NULL,                          -- Foreign Key -> group_members.jid
    reacted INTEGER NOT NULL DEFAULT 0,                -- 1 = Completed reading (emoji reaction placed)
    reaction_emoji TEXT,                               -- The emoji character used (e.g. 🙏, 👍, ❤️)
    reacted_at TIMESTAMP,                              -- Timestamp when reaction was placed/synced
    reminder_sent INTEGER NOT NULL DEFAULT 0,          -- 1 = Private DM reminder was sent
    reminder_sent_at TIMESTAMP,                        -- Timestamp when private DM was sent
    FOREIGN KEY (daily_post_id) REFERENCES daily_posts (id) ON DELETE CASCADE,
    FOREIGN KEY (member_jid) REFERENCES group_members (jid) ON DELETE CASCADE,
    UNIQUE(daily_post_id, member_jid)
);

-- Indices for reaction checks and pending reminder queries
CREATE INDEX IF NOT EXISTS idx_member_activity_post ON member_activity (daily_post_id);
CREATE INDEX IF NOT EXISTS idx_member_activity_member ON member_activity (member_jid);
CREATE INDEX IF NOT EXISTS idx_member_activity_pending ON member_activity (daily_post_id, reacted, reminder_sent);
