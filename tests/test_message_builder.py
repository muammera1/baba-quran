"""Unit tests for message builder and captions using unittest."""

from datetime import datetime
import unittest

from src.quran.page_manager import DailyPageBatch
from src.whatsapp.message_builder import MessageBuilder


class TestMessageBuilder(unittest.TestCase):

    def test_build_daily_post_caption(self):
        builder = MessageBuilder()
        batch = DailyPageBatch(
            page_start=1,
            page_end=2,
            page_numbers=[1, 2],
            image_paths=["1.png", "2.png"],
            surah_names_arabic=["الفاتحة", "البقرة"],
            surah_names_english=["Al-Fatihah", "Al-Baqarah"],
            juz=1,
            cycle_number=1,
            next_page_pointer=3,
            next_cycle_pointer=1,
        )
        caption = builder.build_daily_post_caption(batch, date=datetime(2026, 8, 27))
        self.assertIn("ورد اليوم من القرآن الكريم", caption)
        self.assertIn("الصفحات: 1 - 2", caption)
        self.assertIn("الفاتحة", caption)
        self.assertIn("2026-08-27", caption)

    def test_build_dm_reminder(self):
        builder = MessageBuilder()
        dm = builder.build_dm_reminder(member_name="أحمد", page_start=1, page_end=2)
        self.assertIn("السلام عليكم ورحمة الله وبركاته يا أحمد", dm)
        self.assertIn("صفحة 1 إلى 2", dm)


if __name__ == "__main__":
    unittest.main()
