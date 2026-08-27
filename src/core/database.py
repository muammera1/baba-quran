"""SQLite database and state persistence layer for Baba Quran."""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Generator, List, Optional

from src.core.logger import setup_logger
from src.core.models import DailyPost, GroupMember, KhatmahState, MemberActivity

logger = setup_logger("database")


class Database:
    """Manages SQLite connection, schema creation, and stateful CRUD operations."""

    def __init__(self, db_path: str = "data/db/baba_quran.db") -> None:
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.init_db()

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Yields a SQLite connection with row factory and WAL mode enabled."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}", exc_info=True)
            raise
        finally:
            conn.close()

    def init_db(self) -> None:
        """Initializes database schema and default records."""
        with self.get_connection() as conn:
            # 1. Dynamic App Settings
            conn.execute("""
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 2. Khatmah Progression State
            conn.execute("""
                CREATE TABLE IF NOT EXISTS khatmah_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    current_page INTEGER NOT NULL DEFAULT 1,
                    cycle_number INTEGER NOT NULL DEFAULT 1,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Seed default Khatmah state if not exists
            conn.execute("""
                INSERT OR IGNORE INTO khatmah_state (id, current_page, cycle_number)
                VALUES (1, 1, 1);
            """)

            # 3. Group Members
            conn.execute("""
                CREATE TABLE IF NOT EXISTS group_members (
                    jid TEXT PRIMARY KEY,
                    phone_number TEXT,
                    display_name TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    is_admin INTEGER NOT NULL DEFAULT 0,
                    is_exempt INTEGER NOT NULL DEFAULT 0,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 4. Daily Posts
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_date TEXT NOT NULL,
                    post_type TEXT NOT NULL DEFAULT 'regular_khatmah',
                    page_start INTEGER NOT NULL,
                    page_end INTEGER NOT NULL,
                    surah_name TEXT,
                    group_jid TEXT NOT NULL,
                    message_ids TEXT NOT NULL,
                    posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reminder_due_at TIMESTAMP,
                    reminder_processed INTEGER NOT NULL DEFAULT 0
                );
            """)

            # 5. Member Activity & Reaction Tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS member_activity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    daily_post_id INTEGER NOT NULL,
                    member_jid TEXT NOT NULL,
                    reacted INTEGER NOT NULL DEFAULT 0,
                    reaction_emoji TEXT,
                    reacted_at TIMESTAMP,
                    reminder_sent INTEGER NOT NULL DEFAULT 0,
                    reminder_sent_at TIMESTAMP,
                    FOREIGN KEY (daily_post_id) REFERENCES daily_posts (id) ON DELETE CASCADE,
                    FOREIGN KEY (member_jid) REFERENCES group_members (jid) ON DELETE CASCADE,
                    UNIQUE(daily_post_id, member_jid)
                );
            """)
            logger.info("Database schema initialized successfully.")

    # ------------------ Dynamic Settings ------------------

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieves a setting value from SQLite."""
        with self.get_connection() as conn:
            row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        """Sets or updates a setting value in SQLite."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO app_settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP;
            """, (key, value))

    # ------------------ Khatmah Progression ------------------

    def get_khatmah_state(self) -> KhatmahState:
        """Gets current Khatmah progress."""
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM khatmah_state WHERE id = 1").fetchone()
            if row:
                return KhatmahState(
                    id=row["id"],
                    current_page=row["current_page"],
                    cycle_number=row["cycle_number"],
                    updated_at=datetime.fromisoformat(row["updated_at"]) if isinstance(row["updated_at"], str) else row["updated_at"]
                )
            return KhatmahState()

    def update_khatmah_state(self, current_page: int, cycle_number: int) -> None:
        """Updates Khatmah progress pointer."""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE khatmah_state
                SET current_page = ?, cycle_number = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = 1;
            """, (current_page, cycle_number))
            logger.info(f"Khatmah state updated: Page {current_page}, Cycle {cycle_number}")

    # ------------------ Group Members ------------------

    def upsert_member(self, member: GroupMember) -> None:
        """Inserts or updates a group member."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO group_members (jid, phone_number, display_name, is_active, is_admin, is_exempt)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(jid) DO UPDATE SET
                    phone_number = excluded.phone_number,
                    display_name = CASE WHEN excluded.display_name != '' THEN excluded.display_name ELSE group_members.display_name END,
                    is_active = excluded.is_active,
                    is_admin = excluded.is_admin;
            """, (member.jid, member.phone_number, member.display_name, int(member.is_active), int(member.is_admin), int(member.is_exempt)))

    def get_active_members(self, include_exempt: bool = True) -> List[GroupMember]:
        """Retrieves all active group members."""
        with self.get_connection() as conn:
            query = "SELECT * FROM group_members WHERE is_active = 1"
            if not include_exempt:
                query += " AND is_exempt = 0"
            rows = conn.execute(query).fetchall()
            return [
                GroupMember(
                    jid=r["jid"],
                    phone_number=r["phone_number"] or "",
                    display_name=r["display_name"] or "",
                    is_active=bool(r["is_active"]),
                    is_admin=bool(r["is_admin"]),
                    is_exempt=bool(r["is_exempt"]),
                    joined_at=r["joined_at"],
                )
                for r in rows
            ]

    # ------------------ Daily Posts ------------------

    def record_daily_post(self, post: DailyPost) -> int:
        """Inserts a daily post and initializes member activity tracking records."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO daily_posts (
                    post_date, post_type, page_start, page_end, surah_name,
                    group_jid, message_ids, posted_at, reminder_due_at, reminder_processed
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                post.post_date,
                post.post_type,
                post.page_start,
                post.page_end,
                post.surah_name,
                post.group_jid,
                json.dumps(post.message_ids),
                post.posted_at.isoformat(),
                post.reminder_due_at.isoformat() if post.reminder_due_at else None,
                int(post.reminder_processed),
            ))
            post_id = cursor.lastrowid

            # Initialize activity entries for all active non-exempt members
            active_members = self.get_active_members(include_exempt=True)
            for m in active_members:
                conn.execute("""
                    INSERT OR IGNORE INTO member_activity (daily_post_id, member_jid, reacted)
                    VALUES (?, ?, 0)
                """, (post_id, m.jid))

            logger.info(f"Recorded post ID {post_id} for date {post.post_date} (Pages {post.page_start}-{post.page_end})")
            return post_id

    def has_post_for_date(self, date_str: str) -> bool:
        """Checks if a daily post has already been recorded for the given date string (YYYY-MM-DD)."""
        with self.get_connection() as conn:
            row = conn.execute("SELECT id FROM daily_posts WHERE post_date = ? LIMIT 1", (date_str,)).fetchone()
            return row is not None

    def get_latest_post(self) -> Optional[DailyPost]:
        """Fetches the most recent daily post."""
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM daily_posts ORDER BY id DESC LIMIT 1").fetchone()
            if not row:
                return None
            return DailyPost(
                id=row["id"],
                post_date=row["post_date"],
                post_type=row["post_type"],
                page_start=row["page_start"],
                page_end=row["page_end"],
                surah_name=row["surah_name"] or "",
                group_jid=row["group_jid"],
                message_ids=json.loads(row["message_ids"]),
                posted_at=datetime.fromisoformat(row["posted_at"]) if isinstance(row["posted_at"], str) else row["posted_at"],
                reminder_due_at=datetime.fromisoformat(row["reminder_due_at"]) if row["reminder_due_at"] else None,
                reminder_processed=bool(row["reminder_processed"]),
            )

    def get_due_reminder_posts(self, current_time: Optional[datetime] = None) -> List[DailyPost]:
        """Finds daily posts where 12 hours have passed and reminders haven't been processed yet."""
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM daily_posts
                WHERE reminder_processed = 0
                  AND reminder_due_at IS NOT NULL
                  AND reminder_due_at <= ?
            """, (current_time.isoformat(),)).fetchall()
            return [
                DailyPost(
                    id=r["id"],
                    post_date=r["post_date"],
                    post_type=r["post_type"],
                    page_start=r["page_start"],
                    page_end=r["page_end"],
                    surah_name=r["surah_name"] or "",
                    group_jid=r["group_jid"],
                    message_ids=json.loads(r["message_ids"]),
                    posted_at=datetime.fromisoformat(r["posted_at"]) if isinstance(r["posted_at"], str) else r["posted_at"],
                    reminder_due_at=datetime.fromisoformat(r["reminder_due_at"]) if r["reminder_due_at"] else None,
                    reminder_processed=bool(r["reminder_processed"]),
                )
                for r in rows
]

    # ------------------ Reactions & Activity ------------------

    def record_reaction(self, message_id: str, member_jid: str, emoji: str) -> bool:
        """Finds the post associated with message_id (or falls back to the latest post) and records the member reaction."""
        with self.get_connection() as conn:
            # 1. Find post containing message_id or fallback to latest post
            rows = conn.execute("SELECT id, message_ids FROM daily_posts ORDER BY id DESC LIMIT 5").fetchall()
            target_post_id = None
            for r in rows:
                try:
                    msg_ids = json.loads(r["message_ids"]) if r["message_ids"] else []
                    if message_id in msg_ids:
                        target_post_id = r["id"]
                        break
                except Exception:
                    pass

            if not target_post_id and rows:
                target_post_id = rows[0]["id"]

            if not target_post_id:
                return False

            # Normalize phone and match member
            phone = member_jid.split("@")[0]
            matched_member = conn.execute("""
                SELECT jid FROM group_members WHERE jid = ? OR phone_number = ? LIMIT 1
            """, (member_jid, phone)).fetchone()

            db_jid = matched_member["jid"] if matched_member else member_jid

            # Ensure member exists
            conn.execute("""
                INSERT OR IGNORE INTO group_members (jid, phone_number, display_name, is_active)
                VALUES (?, ?, ?, 1);
            """, (db_jid, phone, phone))

            # Record reaction
            conn.execute("""
                INSERT INTO member_activity (daily_post_id, member_jid, reacted, reaction_emoji, reacted_at)
                VALUES (?, ?, 1, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(daily_post_id, member_jid) DO UPDATE SET
                    reacted = 1,
                    reaction_emoji = excluded.reaction_emoji,
                    reacted_at = CURRENT_TIMESTAMP;
            """, (target_post_id, db_jid, emoji))

            logger.info(f"Recorded reaction '{emoji}' for member '{db_jid}' on Post ID {target_post_id}")
            return True

    def get_pending_members_for_reminder(self, daily_post_id: int) -> List[GroupMember]:
        """Returns members who have not reacted and are not exempt for a given post."""
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT m.* FROM group_members m
                JOIN member_activity a ON m.jid = a.member_jid
                WHERE a.daily_post_id = ?
                  AND a.reacted = 0
                  AND a.reminder_sent = 0
                  AND m.is_active = 1
                  AND m.is_exempt = 0;
            """, (daily_post_id,)).fetchall()
            return [
                GroupMember(
                    jid=r["jid"],
                    phone_number=r["phone_number"] or "",
                    display_name=r["display_name"] or "",
                    is_active=bool(r["is_active"]),
                    is_admin=bool(r["is_admin"]),
                    is_exempt=bool(r["is_exempt"]),
                    joined_at=r["joined_at"],
                )
                for r in rows
            ]

    def mark_reminder_sent(self, daily_post_id: int, member_jid: str) -> None:
        """Marks that a private reminder DM has been sent to a member."""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE member_activity
                SET reminder_sent = 1, reminder_sent_at = CURRENT_TIMESTAMP
                WHERE daily_post_id = ? AND member_jid = ?;
            """, (daily_post_id, member_jid))

    def mark_post_reminders_complete(self, daily_post_id: int) -> None:
        """Marks that the 12-hour reminder process has concluded for a post."""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE daily_posts
                SET reminder_processed = 1
                WHERE id = 1;
            """)
            conn.execute("""
                UPDATE daily_posts
                SET reminder_processed = 1
                WHERE id = ?;
            """, (daily_post_id,))
            logger.info(f"Marked reminders completed for post ID {daily_post_id}")
