"""Message formatting for WhatsApp daily posts and private DM reminders."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from src.quran.page_manager import DailyPageBatch


class MessageBuilder:
    """Builds formatted WhatsApp messages with customizable templates."""

    def __init__(self, templates: Optional[Dict[str, str]] = None) -> None:
        self.templates = templates or {}

    def build_daily_post_caption(self, batch: DailyPageBatch, date: Optional[datetime] = None) -> str:
        """Constructs the group caption for regular daily Quran page posts."""
        if date is None:
            date = datetime.now()

        date_str = date.strftime("%Y-%m-%d")
        surah_names_str = "، ".join(batch.surah_names_arabic)

        default_template = (
            "📖 *ورد اليوم من القرآن الكريم*\n"
            "📅 {date}\n"
            "📄 الصفحات: {page_start} - {page_end}\n"
            "🕋 السور: {surah_names}\n"
            "✨ الجزء: {juz}\n\n"
            "_فضلاً ضع تفاعلاً (أي إيموجي) على هذه الرسالة بعد إتمام القراءة_ 🤲"
        )
        template = self.templates.get("daily_post_caption", default_template)

        return template.format(
            date=date_str,
            page_start=batch.page_start,
            page_end=batch.page_end,
            surah_names=surah_names_str,
            juz=batch.juz,
            cycle=batch.cycle_number,
        ).strip()

    def build_special_post_caption(self, surah_arabic: str, page_start: int, page_end: int, date: Optional[datetime] = None) -> str:
        """Constructs the group caption for special off-the-plan Surah posts (e.g. Friday Kahf)."""
        if date is None:
            date = datetime.now()

        date_str = date.strftime("%Y-%m-%d")
        default_template = (
            "🕌 *قراءة {surah_arabic}*\n"
            "📅 {date}\n"
            "📄 الصفحات: {page_start} - {page_end}\n\n"
            "_فضلاً ضع تفاعلاً (أي إيموجي) بعد إتمام القراءة_ 🤲"
        )
        template = self.templates.get("special_post_caption", default_template)

        return template.format(
            surah_arabic=surah_arabic,
            date=date_str,
            page_start=page_start,
            page_end=page_end,
        ).strip()

    def build_dm_reminder(self, member_name: str, page_start: int, page_end: int) -> str:
        """Constructs the private 12-hour reminder WhatsApp DM."""
        name_display = member_name.strip() if member_name.strip() else "أخي/أختي الكريمة"
        default_template = (
            "السلام عليكم ورحمة الله وبركاته يا {member_name} 🌸\n\n"
            "تذكير لطيف بقراءة ورد القرآن الكريم لليوم (صفحة {page_start} إلى {page_end}).\n\n"
            "عند الانتهاء، فضلاً ضع تفاعلاً (أي إيموجي) على رسالة الورد في المجموعة لتسجيل إتمام القراءة.\n\n"
            "جزاك الله خيراً وتقبل الله طاعتكم 🤲"
        )
        template = self.templates.get("dm_reminder", default_template)

        return template.format(
            member_name=name_display,
            page_start=page_start,
            page_end=page_end,
        ).strip()
