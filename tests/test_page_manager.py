"""Unit tests for Quran page progression and Khatmah rollover using unittest."""

import os
import shutil
import tempfile
import unittest

from src.core.database import Database
from src.quran.page_manager import PageManager, TOTAL_QURAN_PAGES


class TestPageManager(unittest.TestCase):

    def setUp(self):
        self.fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(self.fd)
        self.db = Database(db_path=self.path)
        self.pages_dir = tempfile.mkdtemp()
        self.mgr = PageManager(db=self.db, pages_dir=self.pages_dir)

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)
        if os.path.exists(self.pages_dir):
            shutil.rmtree(self.pages_dir)

    def test_next_daily_batch_regular(self):
        batch = self.mgr.get_next_daily_batch(count=2)
        self.assertEqual(batch.page_start, 1)
        self.assertEqual(batch.page_end, 2)
        self.assertEqual(batch.page_numbers, [1, 2])
        self.assertEqual(batch.cycle_number, 1)
        self.assertEqual(batch.next_page_pointer, 3)
        self.assertEqual(batch.next_cycle_pointer, 1)

        self.mgr.commit_daily_batch_advance(batch)
        state = self.db.get_khatmah_state()
        self.assertEqual(state.current_page, 3)

    def test_khatmah_rollover(self):
        self.db.update_khatmah_state(current_page=603, cycle_number=1)
        batch = self.mgr.get_next_daily_batch(count=2)
        self.assertEqual(batch.page_numbers, [603, 604])
        self.assertEqual(batch.next_page_pointer, 1)
        self.assertEqual(batch.next_cycle_pointer, 2)

        self.mgr.commit_daily_batch_advance(batch)
        state = self.db.get_khatmah_state()
        self.assertEqual(state.current_page, 1)
        self.assertEqual(state.cycle_number, 2)

    def test_custom_page_batch(self):
        batch = self.mgr.get_custom_page_batch(293, 304)
        self.assertEqual(batch.page_start, 293)
        self.assertEqual(batch.page_end, 304)
        self.assertEqual(len(batch.page_numbers), 12)
        self.assertIn("الكهف", batch.surah_names_arabic)


if __name__ == "__main__":
    unittest.main()
