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

    # Close any open dialogs / Select chats modal
    close_btn = await page.query_selector('div[role="button"][aria-label="Close"], button[aria-label="Close"], span[data-icon="x"]')
    if close_btn:
        print("Dismissing open modal...")
        await close_btn.click()
        await asyncio.sleep(1)

    # 3. Click the group chat directly in the sidebar
    print("3. Clicking 'ختمة ابراهيم معمر رحمه الله' in the sidebar...")
    chat_locator = page.locator('div[role="listitem"]').filter(has_text="ختمة ابراهيم معمر").first
    await chat_locator.click()
    await asyncio.sleep(2)

    # Verify chat header is open
    await page.screenshot(path="data/session/step_chat_opened.png")
    print("4. Chat opened screenshot saved to data/session/step_chat_opened.png")

    # 4. Attach image via the file input inside the chat
    print("5. Attaching image 1.png...")
    file_inputs = await page.query_selector_all('input[type="file"]')
    image_path = os.path.abspath("data/pages/1.png")
    
    # Attach to image file input
    attached = False
    for fi in file_inputs:
        accept = await fi.get_attribute("accept") or ""
        if "image" in accept or "*" in accept:
            await fi.set_input_files(image_path)
            attached = True
            print(f"6. File attached to input with accept={accept}")
            break
            
    if not attached and file_inputs:
        await file_inputs[-1].set_input_files(image_path)
        print("6. File attached to last input")

    # 5. Wait for media preview overlay to appear
    print("7. Waiting for media preview...")
    await asyncio.sleep(3)
    await page.screenshot(path="data/session/step_media_preview.png")
    print("8. Media preview screenshot saved.")

    # 6. Click green send button in preview
    print("9. Clicking green send button...")
    send_loc = page.locator('span[data-icon="send"]').last
    await send_loc.click()
    print("10. Send icon clicked!")

    # 7. Wait for upload to finish
    await asyncio.sleep(8)
    await page.screenshot(path="data/session/step_image_in_chat.png")
    print("11. Final chat screenshot saved to data/session/step_image_in_chat.png")

    await pw_whatsapp.stop()


if __name__ == "__main__":
    asyncio.run(main())
