"""Quran page manager: batching, Khatmah rollover, and image asset resolver."""

import os
from dataclasses import dataclass
from typing import List, Tuple

from src.core.database import Database
from src.core.logger import setup_logger
from src.quran.metadata import get_juz_for_page, get_surahs_for_page_range

logger = setup_logger("page_manager")
TOTAL_QURAN_PAGES = 604


@dataclass
class DailyPageBatch:
    page_start: int
    page_end: int
    page_numbers: List[int]
    image_paths: List[str]
    surah_names_arabic: List[str]
    surah_names_english: List[str]
    juz: int
    cycle_number: int
    next_page_pointer: int
    next_cycle_pointer: int


class PageManager:
    """Manages Quran page progression, image retrieval, and Khatmah lifecycle."""

    def __init__(self, db: Database, pages_dir: str = "data/pages") -> None:
        self.db = db
        self.pages_dir = pages_dir
        os.makedirs(self.pages_dir, exist_ok=True)

    def get_image_path(self, page_number: int) -> str:
        """Returns the local path for a given page number image (e.g. data/pages/1.png)."""
        return os.path.join(self.pages_dir, f"{page_number}.png")

    def verify_pages_exist(self, page_numbers: List[int]) -> Tuple[bool, List[int]]:
        """Verifies if all required page images exist locally."""
        missing = [p for p in page_numbers if not os.path.exists(self.get_image_path(p))]
        return (len(missing) == 0, missing)

    def get_next_daily_batch(self, count: int = 2) -> DailyPageBatch:
        """Computes the next batch of N pages based on current Khatmah state."""
        state = self.db.get_khatmah_state()
        current_page = state.current_page
        current_cycle = state.cycle_number

        page_numbers: List[int] = []
        next_page = current_page
        next_cycle = current_cycle

        for _ in range(count):
            page_numbers.append(next_page)
            if next_page >= TOTAL_QURAN_PAGES:
                next_page = 1
                next_cycle += 1
            else:
                next_page += 1

        page_start = page_numbers[0]
        page_end = page_numbers[-1]
        image_paths = [self.get_image_path(p) for p in page_numbers]

        surahs = get_surahs_for_page_range(min(page_start, page_end), max(page_start, page_end))
        surah_ar = [s.name_arabic for s in surahs]
        surah_en = [s.name_english for s in surahs]
        juz = get_juz_for_page(page_start)

        return DailyPageBatch(
            page_start=page_start,
            page_end=page_end,
            page_numbers=page_numbers,
            image_paths=image_paths,
            surah_names_arabic=surah_ar,
            surah_names_english=surah_en,
            juz=juz,
            cycle_number=current_cycle,
            next_page_pointer=next_page,
            next_cycle_pointer=next_cycle,
        )

    def commit_daily_batch_advance(self, batch: DailyPageBatch) -> None:
        """Advances the Khatmah state pointer in SQLite."""
        self.db.update_khatmah_state(
            current_page=batch.next_page_pointer,
            cycle_number=batch.next_cycle_pointer,
        )
        logger.info(
            f"Advanced Khatmah pointer to Page {batch.next_page_pointer}, Cycle {batch.next_cycle_pointer}"
        )

    def get_custom_page_batch(self, page_start: int, page_end: int) -> DailyPageBatch:
        """Constructs a batch for a custom page range (e.g. for Friday Kahf or ad-hoc post)."""
        page_numbers = list(range(page_start, page_end + 1))
        image_paths = [self.get_image_path(p) for p in page_numbers]
        surahs = get_surahs_for_page_range(page_start, page_end)
        surah_ar = [s.name_arabic for s in surahs]
        surah_en = [s.name_english for s in surahs]
        juz = get_juz_for_page(page_start)
        state = self.db.get_khatmah_state()

        return DailyPageBatch(
            page_start=page_start,
            page_end=page_end,
            page_numbers=page_numbers,
            image_paths=image_paths,
            surah_names_arabic=surah_ar,
            surah_names_english=surah_en,
            juz=juz,
            cycle_number=state.cycle_number,
            next_page_pointer=state.current_page,
            next_cycle_pointer=state.cycle_number,
        )
