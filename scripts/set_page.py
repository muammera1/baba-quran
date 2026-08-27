"""CLI utility to manually adjust the next upcoming Khatmah starting page."""

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.database import Database
from src.quran.metadata import get_juz_for_page, get_surahs_for_page_range

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "db", "baba_quran.db"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Set the next starting page for the Baba Quran schedule.")
    parser.add_argument("page", type=int, help="Target page number (1-604)")
    parser.add_argument("--cycle", type=int, default=None, help="Khatmah cycle number (optional)")
    args = parser.parse_args()

    if not (1 <= args.page <= 604):
        print("❌ Error: Page number must be between 1 and 604.")
        sys.exit(1)

    db = Database(DB_PATH)
    current_state = db.get_khatmah_state()
    cycle = args.cycle if args.cycle is not None else current_state.cycle_number

    db.update_khatmah_state(current_page=args.page, cycle_number=cycle)

    surahs = get_surahs_for_page_range(args.page, args.page)
    surah_names = " / ".join([f"سورة {s.name_arabic}" for s in surahs]) if surahs else "تلاوة مباركة"
    juz = get_juz_for_page(args.page)

    print("=" * 60)
    print("✅ تم تعديل بداية الورد القادم بنجاح!")
    print(f"📖 الصفحة القادمة: {args.page} ({surah_names} - الجزء {juz})")
    print(f"🔄 رقم الختمة: {cycle}")
    print("=" * 60)


if __name__ == "__main__":
    main()
