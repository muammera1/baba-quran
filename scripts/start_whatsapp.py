"""Script to initialize Playwright WhatsApp Web session and QR code pairing."""

import asyncio
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.whatsapp.playwright_client import pw_whatsapp


async def main() -> None:
    print("🚀 Initializing Baba Quran WhatsApp Web Client...")
    await pw_whatsapp.start()
    print("📡 Watching for login or QR code...")
    
    while not pw_whatsapp.is_logged_in:
        await asyncio.sleep(2)
        if pw_whatsapp.has_qr:
            print(f"📱 QR Code is ready! Open http://localhost:8080 or data/session/qr.png to scan.")
            
    print("🎉 WhatsApp Web paired successfully!")


if __name__ == "__main__":
    asyncio.run(main())
