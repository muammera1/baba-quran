#!/usr/bin/env python3
"""CLI utility to list and manage WhatsApp group members in the local SQLite database."""

import argparse
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.config import settings
from src.core.database import Database
from src.core.models import GroupMember


def main() -> None:
    parser = argparse.ArgumentParser(description="Baba Quran Member Management")
    parser.add_argument("--list", action="store_true", help="List all group members in database")
    parser.add_argument("--add", nargs=3, metavar=("JID", "PHONE", "NAME"), help="Add or update a member manually")
    parser.add_argument("--exempt", metavar="JID", help="Toggle exempt status for member (exclude from DM reminders)")
    args = parser.parse_args()

    db = Database(db_path=settings.DATABASE_PATH)

    if args.add:
        jid, phone, name = args.add
        db.upsert_member(GroupMember(jid=jid, phone_number=phone, display_name=name, is_active=True))
        print(f"Upserted member: {name} ({jid})")

    if args.exempt:
        with db.get_connection() as conn:
            row = conn.execute("SELECT is_exempt FROM group_members WHERE jid = ?", (args.exempt,)).fetchone()
            if row:
                new_val = 0 if row["is_exempt"] else 1
                conn.execute("UPDATE group_members SET is_exempt = ? WHERE jid = ?", (new_val, args.exempt))
                print(f"Updated {args.exempt}: is_exempt = {bool(new_val)}")
            else:
                print(f"Member with JID '{args.exempt}' not found.")

    members = db.get_active_members(include_exempt=True)
    print("\n--- Active Group Members in Local DB ---")
    if not members:
        print("No members found in database yet.")
    for m in members:
        status_flags = []
        if m.is_admin:
            status_flags.append("Admin")
        if m.is_exempt:
            status_flags.append("Exempt from DMs")
        flag_str = f" [{', '.join(status_flags)}]" if status_flags else ""
        print(f"• {m.display_name} ({m.phone_number or m.jid}){flag_str}")
    print("----------------------------------------\n")


if __name__ == "__main__":
    main()
