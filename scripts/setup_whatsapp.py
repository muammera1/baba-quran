#!/usr/bin/env python3
"""Interactive Onboarding & WhatsApp Pairing Setup Wizard for Baba Quran."""

import argparse
import asyncio
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.config import settings
from src.core.database import Database
from src.core.models import GroupMember
from src.whatsapp.client import WhatsAppClient


def update_env_file(key: str, value: str, env_path: str = ".env") -> None:
    """Updates or adds a key-value pair in the .env file."""
    lines = []
    found = False
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    new_lines = []
    for line in lines:
        if line.strip().startswith(f"{key}=") or line.strip() == key:
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"{key}={value}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


async def run_setup_wizard(dry_run: bool = False) -> None:
    print("=" * 60)
    print("        📖 BABA QURAN - INTERACTIVE SETUP WIZARD         ")
    print("=" * 60)
    print("\nThis wizard will guide you through connecting your WhatsApp account,")
    print("selecting your Quran group, and syncing the member roster.\n")

    db = Database(db_path=settings.DATABASE_PATH)
    wa_client = WhatsAppClient(
        db=db,
        session_dir=settings.WHATSAPP_SESSION_PATH,
        group_jid=settings.WHATSAPP_GROUP_JID,
        dry_run=dry_run,
    )

    print("Step 1: Connecting to WhatsApp...")
    print("---------------------------------")
    if not dry_run:
        print("📱 On your dedicated WhatsApp phone:")
        print("  1. Open WhatsApp.")
        print("  2. Tap Settings (or 3 dots on Android) ➔ 'Linked Devices' (الأجهزة المرتبطة).")
        print("  3. Tap 'Link a Device' (ربط جهاز) and scan the QR code if prompted.\n")

    await wa_client.connect()
    print("✅ WhatsApp session connected successfully!\n")

    print("Step 2: Group Configuration")
    print("----------------------------")
    current_jid = settings.WHATSAPP_GROUP_JID
    if current_jid:
        print(f"Current configured Group JID: {current_jid}")
        change = input("Do you want to keep this group JID? (y/n) [default: y]: ").strip().lower()
        if change == "n":
            new_jid = input("Enter the WhatsApp Group JID or invite link: ").strip()
            if new_jid:
                update_env_file("WHATSAPP_GROUP_JID", new_jid)
                wa_client.group_jid = new_jid
                print(f"✅ Updated WHATSAPP_GROUP_JID in .env: {new_jid}")
    else:
        print("No WhatsApp Group JID is currently set.")
        group_input = input("Enter your WhatsApp Group JID or Group Name: ").strip()
        if group_input:
            update_env_file("WHATSAPP_GROUP_JID", group_input)
            wa_client.group_jid = group_input
            print(f"✅ Saved WHATSAPP_GROUP_JID in .env: {group_input}")

    print("\nStep 3: Syncing Group Members to Local Database")
    print("------------------------------------------------")
    members = await wa_client.sync_group_members()
    print(f"✅ Synced {len(members)} active members into local SQLite database.")
    for m in members:
        print(f"   • {m.display_name or 'Member'} ({m.phone_number or m.jid})")

    print("\n" + "=" * 60)
    print("🎉 SETUP COMPLETE!")
    print("=" * 60)
    print("You can now start the bot anytime using:")
    print("   python3 src/main.py")
    print("\nOr test today's post immediately using:")
    print("   python3 src/main.py --run-now")
    print("=" * 60 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Baba Quran Setup Wizard")
    parser.add_argument("--dry-run", action="store_true", help="Simulate setup wizard")
    args = parser.parse_args()

    asyncio.run(run_setup_wizard(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
