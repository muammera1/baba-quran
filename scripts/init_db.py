#!/usr/bin/env python3
"""CLI utility to initialize, inspect, or reset the local SQLite database."""

import argparse
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.config import settings
from src.core.database import Database


def main() -> None:
    parser = argparse.ArgumentParser(description="Baba Quran Database Utility")
    parser.add_argument("--status", action="store_true", help="Print current database status")
    parser.add_argument("--set-page", type=int, help="Set current Khatmah start page (1-604)")
    parser.add_argument("--set-pages-per-day", type=int, help="Set pages per day (e.g. 2, 4)")
    args = parser.parse_args()

    db = Database(db_path=settings.DATABASE_PATH)

    if args.set_page:
        state = db.get_khatmah_state()
        db.update_khatmah_state(current_page=args.set_page, cycle_number=state.cycle_number)
        print(f"Khatmah progress set to Page {args.set_page}")

    if args.set_pages_per_day:
        db.set_setting("pages_per_day", str(args.set_pages_per_day))
        print(f"Pages per day set to {args.set_pages_per_day}")

    state = db.get_khatmah_state()
    members = db.get_active_members()
    latest_post = db.get_latest_post()
    pages_per_day = db.get_setting("pages_per_day", str(settings.PAGES_PER_DAY))

    print("\n--- Baba Quran Database Status ---")
    print(f"Database Path: {settings.DATABASE_PATH}")
    print(f"Current Khatmah: Cycle {state.cycle_number}, Next Page: {state.current_page}/604")
    print(f"Pages per Day: {pages_per_day}")
    print(f"Active Group Members: {len(members)}")
    if latest_post:
        print(f"Latest Post: ID {latest_post.id} ({latest_post.post_date}) - Pages {latest_post.page_start} to {latest_post.page_end}")
        print(f"Reminder Processed: {latest_post.reminder_processed}")
    else:
        print("No daily posts recorded yet.")
    print("-----------------------------------\n")


if __name__ == "__main__":
    main()
