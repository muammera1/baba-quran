import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from playwright.async_api import async_playwright

SESSION_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "session", "playwright_wa"))
WA_JS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "whatsapp", "wppconnect-wa.js"))


async def main() -> None:
    pw = await async_playwright().start()
    context = await pw.chromium.launch_persistent_context(
        user_data_dir=SESSION_DIR,
        headless=True,
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
        viewport={"width": 1280, "height": 800},
    )
    page = context.pages[0] if context.pages else await context.new_page()
    await page.goto("https://web.whatsapp.com", wait_until="domcontentloaded", timeout=60000)

    await page.wait_for_selector('#pane-side, div[aria-label="Chat list"], [data-testid="chat-list"]', timeout=90000)

    with open(WA_JS_PATH, "r", encoding="utf-8") as f:
        await page.evaluate(f.read())

    await page.wait_for_timeout(3000)
    jid = "120363429851468692@g.us"

    await page.evaluate(f"""async () => {{
        try {{
            await WPP.chat.find("{jid}");
            await WPP.chat.openChatBottom("{jid}");
        }} catch(e) {{}}
    }}""")

    await page.wait_for_timeout(3000)

    # Inspect the exact reaction object keys and fields
    reaction_debug = await page.evaluate(f"""async () => {{
        try {{
            const msgs = await WPP.chat.getMessages("{jid}", {{ count: 6 }});
            const out = [];
            const store = window.WPP.whatsapp.ReactionsStore;
            for (const m of msgs) {{
                const msgId = m.id ? (m.id._serialized || m.id) : String(m.id);
                if (store) {{
                    const rEntry = store.get(msgId);
                    if (rEntry) {{
                        let reactionsArray = [];
                        try {{
                            if (typeof rEntry.toJSON === 'function') reactionsArray = rEntry.toJSON();
                            else if (rEntry.reactions && typeof rEntry.reactions.toJSON === 'function') reactionsArray = rEntry.reactions.toJSON();
                            else if (rEntry.reactions && rEntry.reactions._models) reactionsArray = rEntry.reactions._models.map(x => x.toJSON ? x.toJSON() : x);
                            else reactionsArray = rEntry;
                        }} catch(je) {{
                            reactionsArray = {{ err: String(je) }};
                        }}
                        out.push({{
                            msgId: msgId,
                            caption: m.caption || m.body || '',
                            rEntryKeys: Object.keys(rEntry),
                            reactionsData: reactionsArray
                        }});
                    }}
                }}
            }}
            return out;
        }} catch(err) {{
            return {{ error: String(err) }};
        }}
    }}""")

    print("=== REACTION OBJECT DUMP ===")
    print(json.dumps(reaction_debug, indent=2, ensure_ascii=False))

    await context.close()
    await pw.stop()


if __name__ == "__main__":
    asyncio.run(main())
