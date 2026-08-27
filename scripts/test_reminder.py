#!/usr/bin/env python3
"""CLI utility to test 12-hour reminder dispatcher and simulate reaction events."""

import argparse
import asyncio
import os
import sys
from datetime import datetime, timedelta

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.config import load_yaml_settings, settings
from src.core.database import Database
from src.core.models import GroupMember
from src.scheduler.jobs import run_reminder_check_job
from src.whatsapp.client import WhatsAppClient
from src.whatsapp.message_builder import MessageBuilder


async def run_test() -> None:
    db = Database(db_path=settings.DATABASE_PATH)
    yaml_cfg = load_yaml_settings(settings.CONFIG_YAML_PATH)
    templates = yaml_cfg.get("templates", {})
    msg_builder = MessageBuilder(templates=templates)
    wa_client = WhatsAppClient(db=db, session_dir=settings.WHATSAPP_SESSION_PATH, group_jid=settings.WHATSAPP_GROUP_JID, dry_run=True)

    # 1. Ensure test members exist
    member1 = GroupMember(jid="1111111111@s.whatsapp.net", phone_number="+1111111111", display_name="أحمد")
    member2 = GroupMember(jid="2222222222@s.whatsapp.net", phone_number="+2222222222", display_name="فاطمة")
    db.upsert_member(member1)
    db.upsert_member(member2)

    print("Running reminder check job test in dry-run mode...")
    count = await run_reminder_check_job(db=db, wa_client=wa_client, msg_builder=msg_builder)
    print(f"Test completed. Reminders dispatched: {count}")


def main() -> None:
    asyncio.run(run_test())


if __name__ == "__main__":
    main()
