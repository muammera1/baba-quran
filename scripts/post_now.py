"""CLI command to proactively execute the daily Quran post immediately and skip the next schedule."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.config import load_yaml_settings, settings
from src.core.database import Database
from src.quran.page_manager import PageManager
from src.quran.special_schedules import SpecialScheduleResolver
from src.scheduler.jobs import run_daily_post_job
from src.whatsapp.client import WhatsAppClient
from src.whatsapp.message_builder import MessageBuilder


async def main() -> None:
    print("--- 🚀 Proactively Triggering Daily Quran Post ---")
    db = Database(settings.DATABASE_PATH)
    yaml_cfg = load_yaml_settings(settings.CONFIG_YAML_PATH)
    page_mgr = PageManager(db=db, pages_dir=settings.QURAN_PAGES_DIR)
    special_resolver = SpecialScheduleResolver(raw_schedules=yaml_cfg.get("special_schedules", []))
    msg_builder = MessageBuilder(templates=yaml_cfg.get("templates", {}))
    wa_client = WhatsAppClient(
        db=db,
        session_dir=settings.WHATSAPP_SESSION_PATH,
        group_jid=settings.WHATSAPP_GROUP_JID,
        dry_run=False,
    )

    post_id = await run_daily_post_job(
        db=db,
        page_mgr=page_mgr,
        special_resolver=special_resolver,
        wa_client=wa_client,
        msg_builder=msg_builder,
        settings=settings,
        force=True,
    )

    print("=" * 60)
    print(f"✅ تم نشر الورد مبكراً بنجاح! (معرف المنشور: {post_id})")
    print("⏭️ تم تسجيل تاريخ اليوم، وسيتم تخطي الجدولة التلقائية القادمة لليوم تلقائياً لمنع التكرار.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
