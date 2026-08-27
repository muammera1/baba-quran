"""Special schedules and off-the-plan Surah readings resolver."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from src.core.models import SpecialSchedule
from src.quran.metadata import get_surah_by_name_or_number


class SpecialScheduleResolver:
    """Evaluates whether the current date matches any special off-the-plan Quran readings."""

    def __init__(self, raw_schedules: Optional[List[Dict[str, Any]]] = None) -> None:
        self.schedules: List[SpecialSchedule] = []
        if raw_schedules:
            for s in raw_schedules:
                self.schedules.append(
                    SpecialSchedule(
                        id=s.get("id", ""),
                        enabled=s.get("enabled", True),
                        trigger=s.get("trigger", "").lower(),
                        surah_name=s.get("surah_name", ""),
                        surah_arabic=s.get("surah_arabic", ""),
                        page_start=s.get("page_start", 1),
                        page_end=s.get("page_end", 1),
                        advance_khatmah=s.get("advance_khatmah", False),
                    )
                )

    def get_matching_schedule_for_date(self, target_date: Optional[datetime] = None) -> Optional[SpecialSchedule]:
        """Returns the active special schedule matching the target date (e.g. 'friday' or 'YYYY-MM-DD')."""
        if target_date is None:
            target_date = datetime.utcnow()

        weekday_name = target_date.strftime("%A").lower()  # e.g. 'friday'
        date_str = target_date.strftime("%Y-%m-%d")        # e.g. '2026-08-27'

        for s in self.schedules:
            if not s.enabled:
                continue
            if s.trigger == weekday_name or s.trigger == date_str:
                return s
        return None

    def create_adhoc_schedule(self, surah_name_or_num: str, advance_khatmah: bool = False) -> Optional[SpecialSchedule]:
        """Dynamically creates a SpecialSchedule for an ad-hoc Surah request."""
        surah = get_surah_by_name_or_number(surah_name_or_num)
        if not surah:
            return None
        return SpecialSchedule(
            id=f"adhoc_{surah.name_english.lower()}",
            enabled=True,
            trigger="now",
            surah_name=surah.name_english,
            surah_arabic=surah.name_arabic,
            page_start=surah.page_start,
            page_end=surah.page_end,
            advance_khatmah=advance_khatmah,
        )
