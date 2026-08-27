import asyncio
import base64
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

    # Inject WA-JS
    with open("src/whatsapp/wppconnect-wa.js", "r") as f:
        await page.evaluate(f.read())

    # Wait for WPP to initialize
    await asyncio.sleep(2)
    print("3. WA-JS injected.")

    # Find the target group JID
    group_info = await page.evaluate("""async () => {
        const chats = await WPP.chat.list();
        const g = chats.find(c => (c.name || '').includes("ختمة ابراهيم معمر") || (c.formattedTitle || '').includes("ختمة ابراهيم معمر"));
        return g ? { name: g.name, id: g.id._serialized } : null;
    }""")
    print("4. Target Group:", group_info)

    if not group_info:
        print("Group not found!")
        await pw_whatsapp.stop()
        return

    # Convert image to Base64 data URL
    image_path = os.path.abspath("data/pages/1.png")
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    data_url = f"data:image/png;base64,{b64}"

    caption = "📖 *ورد اليوم من القرآن الكريم (صفحة 1)*\nسورة الفاتحة 🤲\n\n_فضلاً ضع تفاعلاً (أي إيموجي) على هذه الرسالة بعد إتمام القراءة_ ✨"

    print(f"5. Calling WPP.chat.sendFileMessage to {group_info['id']}...")
    send_result = await page.evaluate(f"""async () => {{
        try {{
            const res = await WPP.chat.sendFileMessage(
                '{group_info["id"]}',
                '{data_url}',
                {{
                    type: 'image',
                    caption: {repr(caption)},
                    filename: 'quran_page_1.png'
                }}
            );
            return {{ success: true, res: res }};
        }} catch (err) {{
            return {{ success: false, error: String(err) }};
        }}
    }}""")

    print("6. WPP.chat.sendFileMessage Result:", send_result)

    # Wait 5s and take a screenshot of the chat to verify the real image in chat
    await asyncio.sleep(5)
    await page.screenshot(path="data/session/verified_real_image_post.png")
    print("7. Screenshot saved to data/session/verified_real_image_post.png")

    await pw_whatsapp.stop()


if __name__ == "__main__":
    asyncio.run(main())
