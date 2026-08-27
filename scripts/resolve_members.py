import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from playwright.async_api import async_playwright
from src.core.database import Database

SESSION_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "session", "playwright_wa"))
WA_JS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "whatsapp", "wppconnect-wa.js"))
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "db", "baba_quran.db"))


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

    # Inspect contacts and participant details
    results = await page.evaluate(f"""async () => {{
        const out = [];
        try {{
            const group = await WPP.chat.find("{jid}");
            const participants = await WPP.group.getParticipants("{jid}");
            
            for (const p of participants) {{
                const pId = p.id ? (p.id._serialized || String(p.id)) : String(p);
                const isAdmin = Boolean(p.isAdmin || p.isSuperAdmin || p.admin);
                
                let contactInfo = {{}};
                try {{
                    const c = window.WPP.whatsapp.ContactStore ? window.WPP.whatsapp.ContactStore.get(pId) : null;
                    if (c) {{
                        contactInfo = {{
                            name: c.name,
                            pushname: c.pushname,
                            verifiedName: c.verifiedName,
                            formattedName: c.formattedName,
                            phoneNumber: c.phoneNumber,
                            formattedPhone: c.formattedPhone,
                            number: c.number,
                            userid: c.id ? c.id.user : null,
                            phoneNumberJid: c.phoneNumberJid ? (c.phoneNumberJid._serialized || c.phoneNumberJid.user || String(c.phoneNumberJid)) : null
                        }};
                    }}
                }} catch(ce) {{
                    contactInfo = {{ err: String(ce) }};
                }}
                
                out.push({{
                    jid: pId,
                    isAdmin: isAdmin,
                    contact: contactInfo
                }});
            }}
            return out;
        }} catch(err) {{
            return [{{ error: String(err) }}];
        }}
    }}""")

    print("=== RESOLVED CONTACTS DUMP ===")
    print(json.dumps(results, indent=2, ensure_ascii=False))

    await context.close()
    await pw.stop()


if __name__ == "__main__":
    asyncio.run(main())
