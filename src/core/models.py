"""Data models and schemas for Baba Quran."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class KhatmahState:
    id: int = 1
    current_page: int = 1
    cycle_number: int = 1
    updated_at: datetime = field(default_factory=utc_now)


@dataclass
class GroupMember:
    jid: str
    phone_number: str = ""
    display_name: str = ""
    is_active: bool = True
    is_admin: bool = False
    is_exempt: bool = False
    joined_at: datetime = field(default_factory=utc_now)


@dataclass
class DailyPost:
    id: Optional[int] = None
    post_date: str = ""  # YYYY-MM-DD
    post_type: str = "regular_khatmah"  # 'regular_khatmah', 'friday_kahf', 'special_override'
    page_start: int = 1
    page_end: int = 2
    surah_name: str = ""
    group_jid: str = ""
    message_ids: List[str] = field(default_factory=list)
    posted_at: datetime = field(default_factory=utc_now)
    reminder_due_at: Optional[datetime] = None
    reminder_processed: bool = False


@dataclass
class MemberActivity:
    id: Optional[int] = None
    daily_post_id: int = 0
    member_jid: str = ""
    reacted: bool = False
    reaction_emoji: Optional[str] = None
    reacted_at: Optional[datetime] = None
    reminder_sent: bool = False
    reminder_sent_at: Optional[datetime] = None


@dataclass
class SpecialSchedule:
    id: str
    enabled: bool = True
    trigger: str = ""  # e.g. 'friday' or '2026-09-01'
    surah_name: str = ""
    surah_arabic: str = ""
    page_start: int = 1
    page_end: int = 1
    advance_khatmah: bool = False
