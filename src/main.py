"""Main entrypoint for Baba Quran application."""

import argparse
import asyncio
import os
import signal
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.config import load_yaml_settings, settings
from src.core.database import Database
from src.core.logger import setup_logger
from src.quran.page_manager import PageManager
from src.quran.special_schedules import SpecialScheduleResolver
from src.scheduler.scheduler import BabaQuranScheduler
from src.whatsapp.client import WhatsAppClient
from src.whatsapp.event_listener import WhatsAppEventListener
from src.whatsapp.message_builder import MessageBuilder

logger = setup_logger("main")


async def async_main(dry_run: bool = False, run_now: bool = False) -> None:
    logger.info("==========================================")
    logger.info("       BABA QURAN BOT STARTING UP         ")
    logger.info("==========================================")

    # 1. Initialize Database
    db = Database(db_path=settings.DATABASE_PATH)
    logger.info(f"Database connected: {settings.DATABASE_PATH}")

    # 2. Load Configuration & Special Schedules
    yaml_cfg = load_yaml_settings(settings.CONFIG_YAML_PATH)
    special_schedules_raw = yaml_cfg.get("special_schedules", [])
    templates = yaml_cfg.get("templates", {})

    special_resolver = SpecialScheduleResolver(raw_schedules=special_schedules_raw)
    msg_builder = MessageBuilder(templates=templates)
    page_mgr = PageManager(db=db, pages_dir=settings.QURAN_PAGES_DIR)

    # 3. Check Quran Assets
    khatmah_state = db.get_khatmah_state()
    logger.info(f"Current Khatmah: Cycle {khatmah_state.cycle_number}, Starting Page {khatmah_state.current_page}/604")

    # 4. Initialize WhatsApp Client & Event Listener
    wa_client = WhatsAppClient(
        db=db,
        session_dir=settings.WHATSAPP_SESSION_PATH,
        group_jid=settings.WHATSAPP_GROUP_JID,
        dry_run=dry_run,
    )
    event_listener = WhatsAppEventListener(client=wa_client, db=db)

    # 5. Connect to WhatsApp
    await wa_client.connect()
    await wa_client.sync_group_members()

    # 6. Initialize Scheduler
    scheduler = BabaQuranScheduler(
        db=db,
        page_mgr=page_mgr,
        special_resolver=special_resolver,
        wa_client=wa_client,
        msg_builder=msg_builder,
        settings=settings,
    )
    scheduler.start()

    # 7. Optional Immediate Post Trigger
    if run_now:
        logger.info("Immediate post trigger requested (--run-now)...")
        from src.scheduler.jobs import run_daily_post_job
        await run_daily_post_job(
            db=db,
            page_mgr=page_mgr,
            special_resolver=special_resolver,
            wa_client=wa_client,
            msg_builder=msg_builder,
            settings=settings,
        )

    # 8. Keep event loop active until interrupted
    stop_event = asyncio.Event()

    def signal_handler() -> None:
        logger.info("Shutdown signal received.")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            pass  # Windows support

    logger.info("Baba Quran bot is running and listening for scheduled jobs and reactions.")
    try:
        await stop_event.wait()
    finally:
        logger.info("Shutting down Baba Quran...")
        scheduler.shutdown()
        await wa_client.disconnect()
        logger.info("Baba Quran successfully stopped.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Baba Quran WhatsApp Bot")
    parser.add_argument("--dry-run", action="store_true", help="Simulate WhatsApp interactions locally")
    parser.add_argument("--run-now", action="store_true", help="Trigger today's post immediately on startup")
    args = parser.parse_args()

    asyncio.run(async_main(dry_run=args.dry_run, run_now=args.run_now))


if __name__ == "__main__":
    main()
