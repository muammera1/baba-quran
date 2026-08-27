"""Unit tests for SQLite database state management and reaction tracking using unittest."""

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from src.core.database import Database
from src.core.models import DailyPost, GroupMember


class TestDatabase(unittest.TestCase):

    def setUp(self):
        self.fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(self.fd)
        self.db = Database(db_path=self.path)

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_initial_khatmah_state(self):
        state = self.db.get_khatmah_state()
        self.assertEqual(state.current_page, 1)
        self.assertEqual(state.cycle_number, 1)

    def test_update_khatmah_state(self):
        self.db.update_khatmah_state(current_page=15, cycle_number=2)
        state = self.db.get_khatmah_state()
        self.assertEqual(state.current_page, 15)
        self.assertEqual(state.cycle_number, 2)

    def test_dynamic_settings(self):
        self.assertIsNone(self.db.get_setting("pages_per_day"))
        self.db.set_setting("pages_per_day", "4")
        self.assertEqual(self.db.get_setting("pages_per_day"), "4")

    def test_member_and_reaction_workflow(self):
        m1 = GroupMember(jid="user1@s.whatsapp.net", phone_number="+111", display_name="User 1")
        m2 = GroupMember(jid="user2@s.whatsapp.net", phone_number="+222", display_name="User 2")
        m3_exempt = GroupMember(jid="exempt@s.whatsapp.net", display_name="Exempt User", is_exempt=True)
        self.db.upsert_member(m1)
        self.db.upsert_member(m2)
        self.db.upsert_member(m3_exempt)

        now = datetime.now(timezone.utc)
        due = now + timedelta(hours=12)
        post = DailyPost(
            post_date="2026-08-27",
            page_start=1,
            page_end=2,
            group_jid="group@g.us",
            message_ids=["msg_1", "msg_2"],
            posted_at=now,
            reminder_due_at=due,
        )
        post_id = self.db.record_daily_post(post)
        self.assertIsNotNone(post_id)

        # User 1 reacts with any emoji (e.g. ❤️)
        reacted = self.db.record_reaction(message_id="msg_1", member_jid="user1@s.whatsapp.net", emoji="❤️")
        self.assertTrue(reacted)

        # Check pending members for 12h reminder
        pending = self.db.get_pending_members_for_reminder(post_id)
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].jid, "user2@s.whatsapp.net")

        # Mark reminder sent for User 2
        self.db.mark_reminder_sent(post_id, "user2@s.whatsapp.net")
        pending_after = self.db.get_pending_members_for_reminder(post_id)
        self.assertEqual(len(pending_after), 0)


if __name__ == "__main__":
    unittest.main()
