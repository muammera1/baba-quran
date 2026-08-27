"""Unit tests for special schedules, off-the-plan Surah lookup, and Friday Kahf using unittest."""

from datetime import datetime
import unittest

from src.quran.metadata import get_surah_by_name_or_number
from src.quran.special_schedules import SpecialScheduleResolver


class TestSpecialSchedules(unittest.TestCase):

    def test_surah_metadata_lookup(self):
        kahf = get_surah_by_name_or_number("Kahf")
        self.assertIsNotNone(kahf)
        self.assertEqual(kahf.number, 18)
        self.assertEqual(kahf.page_start, 293)
        self.assertEqual(kahf.page_end, 304)

        mulk = get_surah_by_name_or_number("67")
        self.assertIsNotNone(mulk)
        self.assertEqual(mulk.name_english, "Al-Mulk")
        self.assertEqual(mulk.name_arabic, "الملك")

    def test_friday_schedule_matching(self):
        raw_schedules = [
            {
                "id": "friday_kahf",
                "enabled": True,
                "trigger": "friday",
                "surah_name": "Al-Kahf",
                "surah_arabic": "سورة الكهف",
                "page_start": 293,
                "page_end": 304,
                "advance_khatmah": False,
            }
        ]
        resolver = SpecialScheduleResolver(raw_schedules=raw_schedules)

        # 2026-08-28 is a Friday
        friday_dt = datetime(2026, 8, 28, 6, 0, 0)
        matched = resolver.get_matching_schedule_for_date(friday_dt)
        self.assertIsNotNone(matched)
        self.assertEqual(matched.id, "friday_kahf")
        self.assertEqual(matched.page_start, 293)
        self.assertEqual(matched.page_end, 304)

        # 2026-08-27 is a Thursday -> Should be None
        thursday_dt = datetime(2026, 8, 27, 6, 0, 0)
        matched_thursday = resolver.get_matching_schedule_for_date(thursday_dt)
        self.assertIsNone(matched_thursday)


if __name__ == "__main__":
    unittest.main()
