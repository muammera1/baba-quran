"""Scheduler engine supporting APScheduler with pure asyncio fallback."""

import asyncio
from datetime import datetime, time, timedelta, timezone
from typing import Optional

from src.core.config import Settings
from src.core.database import Database
from src.core.logger import setup_logger
from src.quran.page_manager import PageManager
from src.quran.special_schedules import SpecialScheduleResolver
from src.scheduler.jobs import run_daily_post_job, run_reminder_check_job
from src.whatsapp.client import WhatsAppClient
from src.whatsapp.message_builder import MessageBuilder

logger = setup_logger("scheduler")


class BabaQuranScheduler:
    """Manages scheduled cron and interval tasks with built-in asyncio fallback."""

    def __init__(
        self,
        db: Database,
        page_mgr: PageManager,
        special_resolver: SpecialScheduleResolver,
        wa_client: WhatsAppClient,
        msg_builder: MessageBuilder,
        settings: Settings,
    ) -> None:
        self.db = db
        self.page_mgr = page_mgr
        self.special_resolver = special_resolver
        self.wa_client = wa_client
        self.msg_builder = msg_builder
        self.settings = settings
        self.running = False
        self._loop_task: Optional[asyncio.Task] = None
        self._apscheduler = None

        # Check if APScheduler is installed
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            self._apscheduler = AsyncIOScheduler()
        except ImportError:
            self._apscheduler = None
            logger.info("Using built-in asyncio scheduler engine.")

    def _get_target_post_time(self) -> time:
        post_time_str = self.db.get_setting("post_time", self.settings.POST_TIME)
        try:
            hour_str, min_str = post_time_str.split(":")
            return time(hour=int(hour_str), minute=int(min_str))
        except Exception:
            return time(hour=7, minute=0)

    async def _asyncio_scheduler_loop(self) -> None:
        """Internal background loop for pure-Python scheduling."""
        logger.info("Asyncio scheduler loop started.")
        last_posted_date = None

        while self.running:
            try:
                now = datetime.now()
                target_time = self._get_target_post_time()
                today_date_str = now.strftime("%Y-%m-%d")

                # Check if it's post time (e.g. 07:00) and hasn't posted today yet
                if (now.hour == target_time.hour and now.minute == target_time.minute) and last_posted_date != today_date_str:
                    logger.info(f"Triggering scheduled daily post for {today_date_str}...")
                    await run_daily_post_job(
                        db=self.db,
                        page_mgr=self.page_mgr,
                        special_resolver=self.special_resolver,
                        wa_client=self.wa_client,
                        msg_builder=self.msg_builder,
                        settings=self.settings,
                    )
                    last_posted_date = today_date_str

                # Check for due 12-hour reminders
                await run_reminder_check_job(
                    db=self.db,
                    wa_client=self.wa_client,
                    msg_builder=self.msg_builder,
                )

            except Exception as e:
                logger.error(f"Scheduler loop error: {e}", exc_info=True)

            # Sleep 30 seconds between checks
            await asyncio.sleep(30)

    def start(self) -> None:
        """Starts the scheduler engine."""
        self.running = True

        if self._apscheduler is not None:
            try:
                from apscheduler.triggers.cron import CronTrigger
                from apscheduler.triggers.interval import IntervalTrigger
                target_time = self._get_target_post_time()

                self._apscheduler.add_job(
                    func=run_daily_post_job,
                    trigger=CronTrigger(hour=target_time.hour, minute=target_time.minute),
                    id="daily_quran_post_job",
                    name="Daily Quran Post",
                    replace_existing=True,
                    kwargs={
                        "db": self.db,
                        "page_mgr": self.page_mgr,
                        "special_resolver": self.special_resolver,
                        "wa_client": self.wa_client,
                        "msg_builder": self.msg_builder,
                        "settings": self.settings,
                    },
                )
                self._apscheduler.add_job(
                    func=run_reminder_check_job,
                    trigger=IntervalTrigger(minutes=10),
                    id="reminder_check_job",
                    name="12h Reminder Check",
                    replace_existing=True,
                    kwargs={
                        "db": self.db,
                        "wa_client": self.wa_client,
                        "msg_builder": self.msg_builder,
                    },
                )
                self._apscheduler.start()
                logger.info(f"APScheduler started (Daily post scheduled at {target_time.hour:02d}:{target_time.minute:02d}).")
                return
            except Exception as e:
                logger.warning(f"Failed to start APScheduler ({e}), falling back to built-in asyncio loop.")

        # Built-in asyncio scheduler fallback
        self._loop_task = asyncio.create_task(self._asyncio_scheduler_loop())
        logger.info("Built-in asyncio scheduler started.")

    def shutdown(self) -> None:
        """Stops the scheduler."""
        self.running = False
        if self._apscheduler and self._apscheduler.running:
            self._apscheduler.shutdown()
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
        logger.info("Scheduler shut down.")
