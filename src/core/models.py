"""Master data models and dataclass schemas for Baba Quran Bot."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


def utc_now() -> datetime:
    """Returns the current UTC timestamp."""
    return datetime.now(timezone.utc)


@dataclass
class KhatmahState:
    """Represents the global singleton Khatmah progress state.

    Attributes:
        id: Primary key (enforced singleton id = 1).
        current_page: The next page to be posted in the active Khatmah cycle (1 to 604).
        cycle_number: The sequential Khatmah iteration number (e.g. 1st Khatmah, 2nd Khatmah).
        updated_at: Timestamp when the Khatmah pointer was last updated or slid.
    """
    id: int = 1
    current_page: int = 1
    cycle_number: int = 1
    updated_at: datetime = field(default_factory=utc_now)


@dataclass
class GroupMember:
    """Represents a WhatsApp family group participant.

    Attributes:
        jid: Unique WhatsApp user/LID JID (e.g. '180569132535857@lid' or '123456@s.whatsapp.net').
        phone_number: Verified international formatted phone number (e.g. '+971 55 123 2716').
        display_name: Saved address book contact name or pushname (e.g. 'Muammar 🇦🇪').
        is_active: Whether the member is currently active in the group.
        is_admin: Whether the member holds admin privileges in the group.
        is_exempt: If True, this member is excluded from automated 12-hour reminder DMs.
        joined_at: Timestamp when the member was first synced into the database.
    """
    jid: str
    phone_number: str = ""
    display_name: str = ""
    is_active: bool = True
    is_admin: bool = False
    is_exempt: bool = False
    joined_at: datetime = field(default_factory=utc_now)


@dataclass
class DailyPost:
    """Represents a published Quran post in the WhatsApp group.

    Attributes:
        id: Primary key autoincrement ID.
        post_date: Date string formatted as 'YYYY-MM-DD'.
        post_type: 'regular_khatmah' | 'friday_kahf' | 'special_override'.
        page_start: Starting Madinah Mushaf page (1 to 604).
        page_end: Ending Madinah Mushaf page (1 to 604).
        surah_name: Arabic names of Surahs included in this page batch.
        group_jid: Target WhatsApp group JID.
        message_ids: List of verified WhatsApp Server message IDs ('msgId').
        posted_at: Timestamp of actual message dispatch.
        reminder_due_at: 12-hour threshold timestamp when pending reminders become due.
        reminder_processed: Whether the 12-hour reminder check routine has executed for this post.
    """
    id: Optional[int] = None
    post_date: str = ""
    post_type: str = "regular_khatmah"
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
    """Tracks an individual member's reaction and reminder status for a specific daily post.

    Attributes:
        id: Primary key autoincrement ID.
        daily_post_id: Foreign key referencing DailyPost.id.
        member_jid: Foreign key referencing GroupMember.jid.
        reacted: Whether the member placed an emoji reaction on this post.
        reaction_emoji: The specific emoji placed by the member (e.g. '🙏', '👍', '❤️').
        reacted_at: Timestamp when the reaction was recorded.
        reminder_sent: Whether a private 12-hour reminder DM was dispatched to this member.
        reminder_sent_at: Timestamp when the private reminder DM was sent.
    """
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
    """Configuration for off-the-plan special Quran readings (e.g. Friday Surah Al-Kahf).

    Attributes:
        id: Unique identifier string (e.g. 'friday_kahf').
        enabled: Whether this special schedule is active.
        trigger: Schedule trigger rule (e.g. 'friday' or specific date 'YYYY-MM-DD').
        surah_name: English transliteration of the Surah.
        surah_arabic: Arabic name of the Surah (e.g. 'سورة الكهف').
        page_start: Starting page for this special reading.
        page_end: Ending page for this special reading.
        advance_khatmah: If True, advances the Khatmah pointer; if False, preserves regular progress.
    """
    id: str
    enabled: bool = True
    trigger: str = ""
    surah_name: str = ""
    surah_arabic: str = ""
    page_start: int = 1
    page_end: int = 1
    advance_khatmah: bool = False
