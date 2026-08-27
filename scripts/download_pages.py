#!/usr/bin/env python3
"""Script to download all 604 Madinah Mushaf Tajweed pages (1.png - 604.png) from QuranHub."""

import asyncio
import os
import sys
from typing import List

try:
    import aiohttp
except ImportError:
    aiohttp = None

RAW_BASE_URL = "https://raw.githubusercontent.com/QuranHub/quran-pages-images/main/ayat/tajweed"
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "pages"))
TOTAL_PAGES = 604
CONCURRENCY_LIMIT = 10


async def download_page(session: "aiohttp.ClientSession", page_num: int, semaphore: asyncio.Semaphore) -> bool:
    """Downloads a single page image asynchronously."""
    target_path = os.path.join(OUTPUT_DIR, f"{page_num}.png")
    if os.path.exists(target_path) and os.path.getsize(target_path) > 1000:
        return True  # Already cached

    url = f"{RAW_BASE_URL}/{page_num}.png"
    async with semaphore:
        for attempt in range(3):
            try:
                async with session.get(url, timeout=30) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        with open(target_path, "wb") as f:
                            f.write(content)
                        return True
                    else:
                        print(f"Failed page {page_num}: HTTP {resp.status}")
            except Exception as e:
                if attempt == 2:
                    print(f"Error downloading page {page_num}: {e}")
                await asyncio.sleep(1)
        return False


async def download_all_async() -> None:
    """Downloads all 604 pages concurrently using aiohttp."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    timeout = aiohttp.ClientTimeout(total=60)
    
    print(f"Downloading {TOTAL_PAGES} Quran pages to: {OUTPUT_DIR}")
    async with aiohttp.ClientSession(timeout=timeout) as session:
        tasks = [download_page(session, p, semaphore) for p in range(1, TOTAL_PAGES + 1)]
        results = []
        for i, coro in enumerate(asyncio.as_completed(tasks), 1):
            res = await coro
            results.append(res)
            if i % 50 == 0 or i == TOTAL_PAGES:
                print(f"Progress: {i}/{TOTAL_PAGES} pages downloaded/verified...")

    success_count = sum(1 for r in results if r)
    print(f"\nCompleted: {success_count}/{TOTAL_PAGES} pages ready in {OUTPUT_DIR}")


def download_sync_fallback() -> None:
    """Synchronous urllib fallback if aiohttp is not yet installed."""
    import urllib.request
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Downloading {TOTAL_PAGES} Quran pages using standard urllib to: {OUTPUT_DIR}")
    success_count = 0
    for p in range(1, TOTAL_PAGES + 1):
        target_path = os.path.join(OUTPUT_DIR, f"{p}.png")
        if os.path.exists(target_path) and os.path.getsize(target_path) > 1000:
            success_count += 1
            continue
        url = f"{RAW_BASE_URL}/{p}.png"
        try:
            urllib.request.urlretrieve(url, target_path)
            success_count += 1
            if p % 50 == 0 or p == TOTAL_PAGES:
                print(f"Progress: {p}/{TOTAL_PAGES} pages downloaded...")
        except Exception as e:
            print(f"Error downloading page {p}: {e}")
    print(f"\nCompleted: {success_count}/{TOTAL_PAGES} pages ready in {OUTPUT_DIR}")


def main() -> None:
    if aiohttp is not None:
        asyncio.run(download_all_async())
    else:
        download_sync_fallback()


if __name__ == "__main__":
    main()
