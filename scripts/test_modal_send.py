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

    # Close any open dialogs
    close_btn = await page.query_selector('button[aria-label="Close"], span[data-icon="x"]')
    if close_btn:
        await close_btn.click()
        await asyncio.sleep(1)

    # 3. Open group chat
    print("3. Clicking group in sidebar...")
    chat = page.locator('div[role="listitem"]').filter(has_text="ختمة ابراهيم معمر").first
    await chat.click()
    await asyncio.sleep(2)

    # 4. Attach image
    print("4. Attaching image 1.png...")
    file_inputs = await page.query_selector_all('input[type="file"]')
    for fi in file_inputs:
        accept = await fi.get_attribute("accept") or ""
        if "image" in accept or "*" in accept:
            await fi.set_input_files(os.path.abspath("data/pages/1.png"))
            print("5. Set file on input.")
            break
    else:
        if file_inputs:
            await file_inputs[0].set_input_files(os.path.abspath("data/pages/1.png"))

    # 5. Wait for media preview overlay
    await asyncio.sleep(3)
    await page.screenshot(path="data/session/modal_preview_before.png")

    # 6. Click green send button using multiple robust methods
    print("6. Clicking green send button...")
    
    # Method A: Playwright locator on green button
    try:
        btn = page.locator('span[data-icon="send"]').last
        await btn.click(timeout=3000)
        print("7. Clicked via locator span[data-icon='send']")
    except Exception as e:
        print(f"Locator click failed: {e}")

    # Method B: Mouse click on bottom right coordinates of green button
    await page.mouse.click(964, 738)
    print("8. Mouse clicked at (964, 738)")

    # Method C: Keyboard Enter
    await page.keyboard.press("Enter")
    print("9. Pressed Enter")

    # Wait for upload
    await asyncio.sleep(8)
    await page.screenshot(path="data/session/modal_chat_after.png")
    print("10. Final screenshot saved to data/session/modal_chat_after.png")

    await pw_whatsapp.stop()


if __name__ == "__main__":
    asyncio.run(main())
