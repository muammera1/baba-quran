import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.whatsapp.playwright_client import pw_whatsapp


async def main() -> None:
    print("1. Starting WhatsApp client...")
    await pw_whatsapp.start()

    for i in range(30):
        if pw_whatsapp.is_logged_in:
            print("2. Logged in confirmed!")
            break
        await asyncio.sleep(1)

    page = pw_whatsapp.page

    # 3. Open group chat
    print("3. Clicking group chat 'ختمة ابراهيم معمر رحمه الله'...")
    chat_el = page.locator('span[title*="ختمة ابراهيم معمر" i]').first
    await chat_el.click()
    await asyncio.sleep(2)

    # 4. Click the attach (+) button in footer
    print("4. Clicking footer attach (+) button...")
    attach_btn = page.locator('footer span[data-icon="plus"], footer div[title="Attach"], span[data-icon="attach-menu-plus"]').first
    if await attach_btn.is_visible():
        await attach_btn.click()
        await asyncio.sleep(1)
        print("5. Clicked attach menu.")

    # 5. Populate the Photos & Videos file input
    print("6. Setting file on Photos & Videos input...")
    image_path = os.path.abspath("data/pages/1.png")
    image_input = page.locator('input[type="file"][accept*="image"], input[type="file"]').first
    await image_input.set_input_files(image_path)
    print("7. Image attached successfully!")

    # 6. Wait for media preview overlay
    await asyncio.sleep(3)
    await page.screenshot(path="data/session/step_preview_verified.png")
    print("8. Screenshot saved to data/session/step_preview_verified.png")

    # 7. Click green send button in media preview
    print("9. Clicking green send button...")
    send_btn = page.locator('span[data-icon="send"], div[role="button"]:has(span[data-icon="send"])').last
    await send_btn.click()
    print("10. Send button clicked!")

    # 8. Wait for upload to complete
    await asyncio.sleep(8)
    await page.screenshot(path="data/session/step_chat_verified.png")
    print("11. Final chat screenshot saved to data/session/step_chat_verified.png")

    await pw_whatsapp.stop()


if __name__ == "__main__":
    asyncio.run(main())
