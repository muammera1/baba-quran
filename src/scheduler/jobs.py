"""Background job routines: Daily posting and 12-hour reminder checking."""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

from src.core.config import Settings
from src.core.database import Database
from src.core.logger import setup_logger
from src.core.models import DailyPost
from src.quran.page_manager import PageManager
from src.quran.special_schedules import SpecialScheduleResolver
from src.whatsapp.client import WhatsAppClient
from src.whatsapp.message_builder import MessageBuilder

logger = setup_logger("jobs")


async def run_daily_post_job(
    db: Database,
    page_mgr: PageManager,
    special_resolver: SpecialScheduleResolver,
    wa_client: WhatsAppClient,
    msg_builder: MessageBuilder,
    settings: Settings,
    custom_date: Optional[datetime] = None,
    force: bool = False,
) -> Optional[int]:
    """Executes the daily Quran post to the WhatsApp group.
    
    If force=False (scheduled run) and a post was already published today (e.g. triggered proactively by Admin),
    it gracefully skips to avoid duplicate posts on the same day.
    """
    target_date = custom_date or datetime.now()
    date_str = target_date.strftime("%Y-%m-%d")
    logger.info(f"--- Starting Daily Quran Post Routine for {date_str} (Force: {force}) ---")

    # If scheduled (force=False), check if today was already executed proactively
    if not force and db.has_post_for_date(date_str):
        logger.info(f"⏭️ Daily post for {date_str} was already executed proactively by Admin. Skipping scheduled post.")
        return None

    # Auto-sync group participants to capture any newly joined members
    try:
        await wa_client.sync_group_members()
    except Exception as se:
        logger.warning(f"Auto-sync group members warning: {se}")

    # 1. Check for dynamic settings in DB (e.g. pages_per_day)
    pages_per_day_str = db.get_setting("pages_per_day", str(settings.PAGES_PER_DAY))
    pages_per_day = int(pages_per_day_str)
    reminder_hours_str = db.get_setting("reminder_hours_after_post", str(settings.REMINDER_HOURS_AFTER_POST))
    reminder_hours = int(reminder_hours_str)

    # 2. Check for special schedules (e.g. Friday Surah Al-Kahf)
    special_sched = special_resolver.get_matching_schedule_for_date(target_date)

    if special_sched:
        logger.info(f"Applying special schedule: {special_sched.surah_name} (Pages {special_sched.page_start}-{special_sched.page_end})")
        batch = page_mgr.get_custom_page_batch(special_sched.page_start, special_sched.page_end)
        caption = msg_builder.build_special_post_caption(
            surah_arabic=special_sched.surah_arabic or special_sched.surah_name,
            page_start=batch.page_start,
            page_end=batch.page_end,
            date=target_date,
        )
        post_type = special_sched.id
        surah_name = special_sched.surah_name
        should_advance = special_sched.advance_khatmah
    else:
        logger.info(f"Loading regular Khatmah batch ({pages_per_day} pages)...")
        batch = page_mgr.get_next_daily_batch(count=pages_per_day)
        caption = msg_builder.build_daily_post_caption(batch=batch, date=target_date)
        post_type = "regular_khatmah"
        surah_name = ", ".join(batch.surah_names_english)
        should_advance = True

    # 3. Verify local page images
    all_exist, missing = page_mgr.verify_pages_exist(batch.page_numbers)
    if not all_exist:
        logger.error(f"Missing local page images for pages: {missing}. Please run scripts/download_pages.py!")
        # Fallback: still attempt to proceed if images exist or will be simulated
        if not wa_client.dry_run:
            raise FileNotFoundError(f"Missing Quran page images: {missing}")

    # 4. Send images to group
    now = datetime.now(timezone.utc)
    reminder_due = now + timedelta(hours=reminder_hours)
    
    msg_ids = await wa_client.send_images_to_group(
        image_paths=batch.image_paths,
        caption=caption,
    )

    # 5. Refresh group roster to capture any newly added members, then record post
    await wa_client.sync_group_members()
    daily_post = DailyPost(
        post_date=date_str,
        post_type=post_type,
        page_start=batch.page_start,
        page_end=batch.page_end,
        surah_name=surah_name,
        group_jid=wa_client.group_jid,
        message_ids=msg_ids,
        posted_at=now,
        reminder_due_at=reminder_due,
        reminder_processed=False,
    )
    post_id = db.record_daily_post(daily_post)

    # 6. Advance Khatmah pointer if applicable
    if should_advance:
        page_mgr.commit_daily_batch_advance(batch)

    logger.info(f"--- Daily Post Routine Completed (Post ID: {post_id}, 12h Reminder Due at {reminder_due.isoformat()}) ---")
    return post_id


async def run_reminder_check_job(
    db: Database,
    wa_client: WhatsAppClient,
    msg_builder: MessageBuilder,
) -> int:
    """Checks for posts that passed the 12-hour threshold and sends private DM reminders to pending members."""
    now = datetime.now(timezone.utc)
    due_posts = db.get_due_reminder_posts(current_time=now)
    if not due_posts:
        logger.debug("No posts due for 12-hour reminders at this time.")
        return 0

    total_reminders_sent = 0

    for post in due_posts:
        logger.info(f"Processing 12-hour reminders for Post ID {post.id} (Date: {post.post_date}, Pages {post.page_start}-{post.page_end})")

        # 1. On-Demand Scan: Query WhatsApp Web directly for all reactions placed on this post
        try:
            logger.info(f"Scanning WhatsApp Web for member reactions on Post ID {post.id}...")
            from src.whatsapp.playwright_client import pw_whatsapp
            await pw_whatsapp.sync_recent_reactions()
        except Exception as se:
            logger.warning(f"Could not refresh reactions before reminders: {se}")

        pending_members = db.get_pending_members_for_reminder(post.id)
        
        if not pending_members:
            logger.info(f"All members have completed reading for Post ID {post.id}! No reminders needed.")
            db.mark_post_reminders_complete(post.id)
            continue

        logger.info(f"Found {len(pending_members)} members who have not reacted after 12 hours.")

        for member in pending_members:
            dm_text = msg_builder.build_dm_reminder(
                member_name=member.display_name,
                page_start=post.page_start,
                page_end=post.page_end,
            )
            success = await wa_client.send_direct_message(member.jid, dm_text)
            if success:
                db.mark_reminder_sent(post.id, member.jid)
                total_reminders_sent += 1
                # Throttle DM sending to avoid WhatsApp anti-spam rate limits
                await asyncio.sleep(2.0)

        db.mark_post_reminders_complete(post.id)

    logger.info(f"Completed reminder check: {total_reminders_sent} reminder DMs dispatched.")
    return total_reminders_sent
