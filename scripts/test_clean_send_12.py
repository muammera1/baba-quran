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
    print("1. Starting client...")
    pw = await async_playwright().start()
    context = await pw.chromium.launch_persistent_context(
        user_data_dir=SESSION_DIR,
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
        viewport={"width": 1280, "height": 800},
    )
    page = context.pages[0] if context.pages else await context.new_page()

    print("2. Loading WhatsApp Web...")
    await page.goto("https://web.whatsapp.com", wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_selector("#pane-side", timeout=30000)
    print("3. Logged in confirmed!")

    # Inject WA-JS
    with open(WA_JS_PATH, "r", encoding="utf-8") as f:
        await page.evaluate(f.read())

    # Wait for WPP.isReady
    print("4. Waiting for WPP.isReady...")
    ready = await page.evaluate("""async () => {
        return new Promise((resolve) => {
            if (typeof window.WPP !== 'undefined' && window.WPP.isReady) {
                return resolve(true);
            }
            if (typeof window.WPP !== 'undefined') {
                window.WPP.on('webpack.ready', () => resolve(true));
                setTimeout(() => resolve(window.WPP.isReady || false), 15000);
            } else {
                resolve(false);
            }
        });
    }""")
    print(f"5. WPP Ready: {ready}")

    group_jid = "120363429851468692@g.us"
    pages = ["12.png", "13.png"]

    for idx, p in enumerate(pages):
        img_path = os.path.abspath(f"data/pages/{p}")
        with open(img_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        data_url = f"data:image/png;base64,{b64}"
        caption = "📖 *ورد اليوم من القرآن الكريم*\nسورة البقرة (صفحة 12 و 13) 🤲\n\n_فضلاً ضع تفاعلاً على هذه الرسالة بعد إتمام القراءة_ ✨" if idx == 0 else f"صفحة {p.split('.')[0]}"

        print(f"6. Sending {p} directly via WPP...")
        res = await page.evaluate(f"""async () => {{
            try {{
                const r = await WPP.chat.sendFileMessage(
                    '{group_jid}',
                    '{data_url}',
                    {{
                        type: 'image',
                        caption: {json.dumps(caption)},
                        filename: '{p}'
                    }}
                );
                return {{ success: true, id: r && r.id ? (r.id._serialized || r.id) : r }};
            }} catch (e) {{
                return {{ success: false, error: String(e) }};
            }}
        }}""")
        print(f"   => Result for {p}:", res)
        await asyncio.sleep(2)

    await context.close()
    await pw.stop()
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
