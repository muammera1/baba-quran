import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.config import load_yaml_settings, settings
from src.core.database import Database
from src.whatsapp.client import WhatsAppClient
from src.whatsapp.message_builder import MessageBuilder


async def main() -> None:
    print("--- 📨 Testing Private WhatsApp DM Reminder to 'Muammar 🇦🇪' ---")
    db = Database(settings.DATABASE_PATH)
    yaml_cfg = load_yaml_settings(settings.CONFIG_YAML_PATH)
    msg_builder = MessageBuilder(templates=yaml_cfg.get("templates", {}))

    # Member details for Muammar 🇦🇪
    member_name = "Muammar 🇦🇪"
    member_jid = "180569132535857@lid"
    page_start = 12
    page_end = 13

    dm_text = msg_builder.build_dm_reminder(
        member_name=member_name,
        page_start=page_start,
        page_end=page_end,
    )
    print("Message Content to be sent:\n")
    print(dm_text)
    print("\n" + "=" * 60)

    wa_client = WhatsAppClient(
        db=db,
        session_dir=settings.WHATSAPP_SESSION_PATH,
        group_jid=settings.WHATSAPP_GROUP_JID,
        dry_run=False,
    )

    print(f"Sending private DM to {member_jid}...")
    success = await wa_client.send_direct_message(member_jid=member_jid, text=dm_text)

    if success:
        print(f"✅ تم إرسال رسالة التذكير الخاصة بنجاح إلى: {member_name} ({member_jid})")
    else:
        print(f"❌ تعذر إرسال التذكير إلى: {member_name}")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
