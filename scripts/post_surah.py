#!/usr/bin/env python3
"""CLI utility to post an off-the-plan Surah or custom page range immediately."""

import argparse
import asyncio
import os
import sys
from datetime import datetime

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.config import load_yaml_settings, settings
from src.core.database import Database
from src.core.models import DailyPost
from src.quran.metadata import get_surah_by_name_or_number
from src.quran.page_manager import PageManager
from src.whatsapp.client import WhatsAppClient
from src.whatsapp.message_builder import MessageBuilder


async def run_post_surah(surah_input: str, advance_khatmah: bool = False, dry_run: bool = False) -> None:
    db = Database(db_path=settings.DATABASE_PATH)
    page_mgr = PageManager(db=db, pages_dir=settings.QURAN_PAGES_DIR)
    yaml_cfg = load_yaml_settings(settings.CONFIG_YAML_PATH)
    templates = yaml_cfg.get("templates", {})
    msg_builder = MessageBuilder(templates=templates)
    wa_client = WhatsAppClient(db=db, session_dir=settings.WHATSAPP_SESSION_PATH, group_jid=settings.WHATSAPP_GROUP_JID, dry_run=dry_run)

    surah = get_surah_by_name_or_number(surah_input)
    if not surah:
        print(f"Error: Surah '{surah_input}' not found. You can enter Surah name (e.g. 'Kahf', 'Al-Mulk') or number (1-114).")
        return

    print(f"Found Surah: {surah.name_arabic} ({surah.name_english}) - Pages {surah.page_start} to {surah.page_end}")
    
    batch = page_mgr.get_custom_page_batch(surah.page_start, surah.page_end)
    caption = msg_builder.build_special_post_caption(
        surah_arabic=f"سورة {surah.name_arabic}",
        page_start=batch.page_start,
        page_end=batch.page_end,
    )

    await wa_client.connect()
    msg_ids = await wa_client.send_images_to_group(
        image_paths=batch.image_paths,
        caption=caption,
    )

    now = datetime.now()
    post = DailyPost(
        post_date=now.strftime("%Y-%m-%d"),
        post_type=f"adhoc_{surah.name_english.lower()}",
        page_start=batch.page_start,
        page_end=batch.page_end,
        surah_name=surah.name_english,
        group_jid=wa_client.group_jid or "local_test_group",
        message_ids=msg_ids,
        posted_at=now,
    )
    post_id = db.record_daily_post(post)
    print(f"Posted Surah {surah.name_arabic} successfully (Recorded Post ID: {post_id}).")


def main() -> None:
    parser = argparse.ArgumentParser(description="Post an off-the-plan Surah to the WhatsApp group")
    parser.add_argument("surah", type=str, help="Surah name (e.g. 'Kahf', 'Mulk', 'Yasin') or number (1-114)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate posting without real WhatsApp")
    args = parser.parse_args()

    asyncio.run(run_post_surah(args.surah, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
