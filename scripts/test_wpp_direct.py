import asyncio
import base64
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from playwright.async_api import async_playwright

SESSION_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "session", "playwright_wa"))
WA_JS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "whatsapp", "wppconnect-wa.js"))


async def main() -> None:
    print("1. Launching Playwright browser...")
    pw = await async_playwright().start()
    context = await pw.chromium.launch_persistent_context(
        user_data_dir=SESSION_DIR,
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
        viewport={"width": 1280, "height": 800},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    )
    page = context.pages[0] if context.pages else await context.new_page()

    print("2. Loading WhatsApp Web...")
    await page.goto("https://web.whatsapp.com", wait_until="domcontentloaded", timeout=60000)

    # Wait for chat list pane
    await page.wait_for_selector("#pane-side, div[aria-label='Chat list']", timeout=30000)
    print("3. WhatsApp Web session is logged in!")

    # Inject WA-JS
    print("4. Injecting WA-JS bridge...")
    with open(WA_JS_PATH, "r", encoding="utf-8") as f:
        wa_js_content = f.read()
    await page.evaluate(wa_js_content)

    # Wait for WPP to be ready
    print("5. Waiting for WPP.webpack to initialize...")
    wpp_ready = await page.evaluate("""async () => {
        return new Promise((resolve) => {
            if (typeof window.WPP !== 'undefined' && window.WPP.isReady) {
                return resolve(true);
            }
            if (typeof window.WPP !== 'undefined') {
                window.WPP.on('webpack.ready', () => resolve(true));
                setTimeout(() => resolve(window.WPP.isReady || false), 8000);
            } else {
                resolve(false);
            }
        });
    }""")
    print(f"6. WPP Ready Status: {wpp_ready}")

    # Find the target group JID
    print("7. Searching for group chat JID...")
    group_info = await page.evaluate("""async () => {
        try {
            const chats = await WPP.chat.list();
            const g = chats.find(c => 
                (c.name || '').includes('ختمة ابراهيم معمر') || 
                (c.formattedTitle || '').includes('ختمة ابراهيم معمر')
            );
            if (g) {
                return { name: g.name || g.formattedTitle, id: g.id._serialized };
            }
            return null;
        } catch (e) {
            return { error: String(e) };
        }
    }""")
    print(f"8. Target Group: {group_info}")

    if not group_info or "id" not in group_info:
        print("Could not locate group JID. Exiting.")
        await context.close()
        await pw.stop()
        return

    # Convert Page 1 to Base64
    image_path = os.path.abspath("data/pages/1.png")
    with open(image_path, "rb") as f:
        b64_data = base64.b64encode(f.read()).decode("utf-8")
    data_url = f"data:image/png;base64,{b64_data}"

    caption = "📖 *ورد اليوم من القرآن الكريم (صفحة 1)*\nسورة الفاتحة 🤲\n\n_فضلاً ضع تفاعلاً (أي إيموجي) على هذه الرسالة بعد إتمام القراءة_ ✨"

    # Send Image via WPP.chat.sendFileMessage
    print(f"9. Calling WPP.chat.sendFileMessage to {group_info['id']}...")
    send_response = await page.evaluate(f"""async () => {{
        try {{
            const res = await WPP.chat.sendFileMessage(
                '{group_info["id"]}',
                '{data_url}',
                {{
                    type: 'image',
                    caption: {json.dumps(caption)},
                    filename: '1.png'
                }}
            );
            return {{
                success: true,
                id: res && res.id ? (res.id._serialized || res.id) : res
            }};
        }} catch (err) {{
            return {{ success: false, error: String(err) }};
        }}
    }}""")

    print(f"10. WPP Send Response: {send_response}")

    # Wait 6 seconds and capture screenshot of the chat
    print("11. Verifying delivery in chat...")
    await asyncio.sleep(6)
    await page.screenshot(path="data/session/wpp_api_verified.png")
    print("12. Verification screenshot saved to data/session/wpp_api_verified.png")

    await context.close()
    await pw.stop()
    print("🎉 Done!")


if __name__ == "__main__":
    asyncio.run(main())
