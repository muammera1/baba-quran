"""Direct WhatsApp Web API Client powered by WA-JS and Playwright.

Provides 100% reliable programmatic media sending, reaction tracking, and member sync.
"""

import asyncio
import base64
import json
import os
import sys
from typing import Any, Callable, Dict, List, Optional
from playwright.async_api import async_playwright, BrowserContext, Page

from src.core.database import Database
from src.core.logger import setup_logger
from src.core.models import GroupMember

logger = setup_logger("wpp_client")

SESSION_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "session", "playwright_wa"))
WA_JS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "wppconnect-wa.js"))
QR_IMAGE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "session", "qr.png"))
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "db", "baba_quran.db"))


class WhatsAppApiClient:
    """Direct API-based WhatsApp Web automation using injected WPP client."""

    def __init__(self, group_name: Optional[str] = None) -> None:
        self.group_name = group_name or os.getenv("WHATSAPP_GROUP_NAME", "ختمة القرآن الكريم")
        self.session_dir = SESSION_DIR
        self.playwright = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.is_logged_in = False
        self.is_ready = False
        self.db = Database(DB_PATH)
        self.group_jid: Optional[str] = self.db.get_setting("group_jid") or os.getenv("WHATSAPP_GROUP_JID", "")
        self.reaction_callbacks: List[Callable[[Dict[str, Any]], Any]] = []

    @property
    def has_saved_session(self) -> bool:
        """Checks if a valid persistent WhatsApp session exists on disk."""
        indexed_db = os.path.join(self.session_dir, "Default", "IndexedDB")
        cookies = os.path.join(self.session_dir, "Default", "Cookies")
        network_cookies = os.path.join(self.session_dir, "Default", "Network", "Cookies")
        return os.path.exists(indexed_db) or os.path.exists(cookies) or os.path.exists(network_cookies)

    def register_reaction_callback(self, callback: Callable[[Dict[str, Any]], Any]) -> None:
        self.reaction_callbacks.append(callback)

    async def _on_reaction_received(self, reaction_json: str) -> None:
        """Called automatically when any member reacts with an emoji on a post."""
        try:
            data = json.loads(reaction_json)
            logger.info(f"✨ Reaction event received: {data}")

            # Extract reaction details
            msg_id = data.get("id") or data.get("msgId")
            sender = data.get("sender") or data.get("senderJid") or data.get("author")
            reaction = data.get("reaction") or data.get("reactionText") or data.get("emoji")

            if msg_id and sender:
                # Record in SQLite database
                self.db.record_reaction(
                    message_id=str(msg_id),
                    member_jid=str(sender),
                    emoji=str(reaction) if reaction else "👍"
                )
                logger.info(f"✅ Recorded reaction '{reaction}' from member '{sender}' on post '{msg_id}'")

            for cb in self.reaction_callbacks:
                try:
                    if asyncio.iscoroutinefunction(cb):
                        await cb(data)
                    else:
                        cb(data)
                except Exception as cbe:
                    logger.error(f"Error in reaction callback: {cbe}")

        except Exception as e:
            logger.error(f"Error handling reaction event: {e}")

    async def start(self) -> None:
        """Launches headless Chromium, loads persistent session, and initializes WPP."""
        os.makedirs(SESSION_DIR, exist_ok=True)
        logger.info(f"Starting WhatsApp API Client (Session: {SESSION_DIR})...")

        self.playwright = await async_playwright().start()
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=SESSION_DIR,
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        )

        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()

        # Expose python reaction callback to browser context
        await self.page.expose_function("onReactionReceived", self._on_reaction_received)

        logger.info("Loading https://web.whatsapp.com...")
        await self.page.goto("https://web.whatsapp.com", wait_until="domcontentloaded", timeout=60000)

        # Start background monitor for login & WPP injection
        asyncio.create_task(self._init_wpp_loop())

    async def _init_wpp_loop(self) -> None:
        """Monitors login and injects WA-JS bridge when session is authenticated."""
        while True:
            try:
                if not self.page:
                    break

                chat_list = await self.page.query_selector('#pane-side, div[aria-label="Chat list"]')
                if chat_list:
                    if not self.is_logged_in:
                        logger.info("🎉 WhatsApp Web session detected! Injecting WA-JS API bridge...")
                        self.is_logged_in = True

                    # Inject WA-JS if not present
                    has_wpp = await self.page.evaluate("() => typeof window.WPP !== 'undefined'")
                    if not has_wpp:
                        with open(WA_JS_PATH, "r", encoding="utf-8") as f:
                            wpp_code = f.read()
                        await self.page.evaluate(wpp_code)
                        logger.info("WA-JS injected into WhatsApp Web context.")

                    # Check WPP readiness
                    wpp_ready = await self.page.evaluate("""async () => {
                        return new Promise((resolve) => {
                            if (typeof window.WPP !== 'undefined' && window.WPP.isReady) {
                                return resolve(true);
                            }
                            if (typeof window.WPP !== 'undefined') {
                                window.WPP.on('webpack.ready', () => resolve(true));
                                setTimeout(() => resolve(window.WPP.isReady || false), 5000);
                            } else {
                                resolve(false);
                            }
                        });
                    }""")

                    if wpp_ready and not self.is_ready:
                        self.is_ready = True
                        logger.info("🚀 WPP WhatsApp Web API is 100% READY and authenticated!")

                        # Find group JID
                        jid = await self.get_group_jid_by_name(self.group_name)
                        if jid:
                            self.group_jid = jid
                        logger.info(f"Target Group '{self.group_name}' JID: {self.group_jid}")

                        # Setup real-time reaction listener in JS
                        await self.page.evaluate("""() => {
                            if (typeof window.WPP !== 'undefined' && window.WPP.on) {
                                window.WPP.on('chat.msg_reaction', (evt) => {
                                    if (window.onReactionReceived) {
                                        window.onReactionReceived(JSON.stringify(evt));
                                    }
                                });
                            }
                        }""")
                        logger.info("✨ Real-time reaction listener hooked successfully!")

                    await asyncio.sleep(5)
                    continue

                # QR code screenshot capture if not logged in
                qr_canvas = await self.page.query_selector('canvas[aria-label="Scan this QR code to link a device"], div[data-ref]')
                if qr_canvas:
                    self.is_logged_in = False
                    self.is_ready = False
                    await qr_canvas.screenshot(path=QR_IMAGE_PATH)

            except Exception as e:
                logger.debug(f"WPP loop tick: {e}")

            await asyncio.sleep(3)

    async def get_group_jid_by_name(self, name_substr: str) -> Optional[str]:
        """Finds group JID by matching name substring."""
        if not self.page or not self.is_ready:
            return self.group_jid

        try:
            return await self.page.evaluate(f"""async () => {{
                const chats = await WPP.chat.list();
                const group = chats.find(c => 
                    (c.name || '').includes('{name_substr}') || 
                    (c.formattedTitle || '').includes('{name_substr}')
                );
                return group ? group.id._serialized : null;
            }}""")
        except Exception as e:
            logger.warning(f"Could not search group JID: {e}")
            return self.group_jid

    async def send_image_direct(self, image_path: str, caption: str, target_jid: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Direct API call to send image binary to WhatsApp chat."""
        if not self.page:
            logger.error("Playwright page not available.")
            return None

        # Convert image to base64 data URL
        with open(image_path, "rb") as f:
            b64_data = base64.b64encode(f.read()).decode("utf-8")
        data_url = f"data:image/png;base64,{b64_data}"
        filename = os.path.basename(image_path)

        jid = target_jid or self.group_jid or self.db.get_setting("group_jid") or os.getenv("WHATSAPP_GROUP_JID", "")
        logger.info(f"Sending image {filename} directly via WPP API to {jid}...")

        # Ensure chat is open and loaded into ChatStore
        try:
            chat_item = await self.page.query_selector(f'span[title*="{self.group_name}" i]')
            if chat_item:
                await chat_item.click()
                await self.page.wait_for_timeout(1000)
        except Exception:
            pass

        result = await self.page.evaluate(f"""async () => {{
            try {{
                // Ensure chat model is loaded into ChatStore
                try {{
                    await WPP.chat.find('{jid}');
                }} catch (fe) {{}}
                try {{
                    await WPP.chat.openChatBottom('{jid}');
                }} catch (oe) {{}}

                const sendResult = await WPP.chat.sendFileMessage(
                    '{jid}',
                    '{data_url}',
                    {{
                        type: 'image',
                        caption: {json.dumps(caption)},
                        filename: '{filename}'
                    }}
                );
                return {{
                    success: true,
                    msgId: sendResult && sendResult.id ? (sendResult.id._serialized || sendResult.id) : String(sendResult),
                    timestamp: Date.now()
                }};
            }} catch (err) {{
                return {{ success: false, error: String(err) }};
            }}
        }}""")

        logger.info(f"WPP sendFileMessage response: {result}")
        return result

    async def send_quran_pages_to_group(self, image_paths: List[str], caption: str, invite_code: Optional[str] = None) -> bool:
        """Sends multi-page Quran images with caption directly using the WhatsApp Web API."""
        if not self.page:
            logger.error("Playwright page not available.")
            return False

        # Ensure WhatsApp Web chat list is loaded into ChatStore
        try:
            logger.info("Waiting for WhatsApp Web chat list to populate...")
            await self.page.wait_for_selector('#pane-side, div[aria-label="Chat list"]', timeout=30000)
            await self.page.wait_for_timeout(2000)
        except Exception as we:
            logger.warning(f"Wait for chat list warning: {we}")

        # Ensure WA-JS bridge is injected and ready
        try:
            has_wpp = await self.page.evaluate("() => typeof window.WPP !== 'undefined'")
            if not has_wpp:
                logger.info("Injecting WA-JS before sending media...")
                with open(WA_JS_PATH, "r", encoding="utf-8") as f:
                    await self.page.evaluate(f.read())
                await self.page.evaluate("""async () => {
                    return new Promise((resolve) => {
                        if (typeof window.WPP !== 'undefined' && window.WPP.isReady) return resolve(true);
                        if (typeof window.WPP !== 'undefined') {
                            window.WPP.on('webpack.ready', () => resolve(true));
                            setTimeout(() => resolve(true), 6000);
                        } else {
                            resolve(false);
                        }
                    });
                }""")
        except Exception as ie:
            logger.warning(f"WA-JS check warning: {ie}")

        jid = self.group_jid or self.db.get_setting("group_jid") or os.getenv("WHATSAPP_GROUP_JID", "")
        logger.info(f"Posting {len(image_paths)} Quran page images directly via WPP API to {jid}...")
        all_success = True

        for idx, img_path in enumerate(image_paths):
            msg_caption = caption if idx == 0 else f"صفحة {os.path.splitext(os.path.basename(img_path))[0]}"
            res = await self.send_image_direct(image_path=img_path, caption=msg_caption, target_jid=jid)
            if not res or not res.get("success"):
                all_success = False
            await asyncio.sleep(1.5)

        return all_success

    async def send_dm_message(self, phone_or_jid: str, text: str) -> bool:
        """Sends private direct reminder message to an inactive member."""
        if not self.page or not self.is_ready:
            if not self.context:
                await self.start()
            for _ in range(25):
                if self.is_ready and self.page:
                    break
                await asyncio.sleep(1)

        if not self.page:
            return False

        jid = phone_or_jid if "@" in phone_or_jid else f"{phone_or_jid}@c.us"
        logger.info(f"Sending private reminder DM to {jid}...")

        try:
            res = await self.page.evaluate(f"""async () => {{
                try {{
                    try {{
                        await WPP.chat.find('{jid}');
                    }} catch (fe) {{}}
                    try {{
                        await WPP.chat.openChatBottom('{jid}');
                    }} catch (oe) {{}}

                    const r = await WPP.chat.sendTextMessage('{jid}', {json.dumps(text)});
                    return {{ success: true, id: r.id ? (r.id._serialized || r.id) : String(r) }};
                }} catch (e) {{
                    return {{ success: false, error: String(e) }};
                }}
            }}""")
            logger.info(f"DM send result to {jid}: {res}")
            return bool(res and res.get("success"))
        except Exception as e:
            logger.error(f"Failed to send DM to {jid}: {e}")
            return False

    async def sync_group_members(self) -> List[Dict[str, Any]]:
        """Syncs all group members from WhatsApp into local SQLite database with real phone numbers."""
        if not self.page or not self.is_ready:
            return []

        jid = self.group_jid or self.db.get_setting("group_jid") or os.getenv("WHATSAPP_GROUP_JID", "")
        try:
            members = await self.page.evaluate(f"""async () => {{
                try {{
                    const participants = await WPP.group.getParticipants('{jid}');
                    const results = [];
                    for (const p of participants) {{
                        const pId = p.id ? (p.id._serialized || String(p.id)) : String(p);
                        let name = '';
                        let phone = '';

                        try {{
                            const c = window.WPP.whatsapp.ContactStore ? window.WPP.whatsapp.ContactStore.get(pId) : (await WPP.contact.get(pId));
                            if (c) {{
                                name = c.name || c.formattedName || '';
                                if (!name || name === 'You' || name.startsWith('+')) {{
                                    name = c.pushname || c.verifiedName || name;
                                }}
                                if (!name) {{
                                    name = c.pushname || c.shortName || '';
                                }}

                                if (c.formattedPhone) {{
                                    phone = c.formattedPhone;
                                }} else if (c.phoneNumber && typeof c.phoneNumber === 'object' && c.phoneNumber.user) {{
                                    phone = '+' + c.phoneNumber.user;
                                }} else if (c.phoneNumber && typeof c.phoneNumber === 'string') {{
                                    phone = c.phoneNumber;
                                }} else if (c.number) {{
                                    phone = '+' + c.number;
                                }}
                            }}
                        }} catch (ce) {{}}

                        if (!phone) {{
                            phone = pId.split('@')[0];
                        }}

                        results.push({{
                            id: pId,
                            phone: phone,
                            name: name || 'عضو',
                            isAdmin: Boolean(p.isAdmin || p.isSuperAdmin || p.admin)
                        }});
                    }}
                    return results;
                }} catch (e) {{
                    return [];
                }}
            }}""")

            for m in members:
                if m.get("id"):
                    member_obj = GroupMember(
                        jid=m["id"],
                        phone_number=m.get("phone", m["id"].split('@')[0]),
                        display_name=m.get("name", "عضو"),
                        is_active=True,
                        is_admin=m.get("isAdmin", False),
                        is_exempt=False,
                    )
                    self.db.upsert_member(member_obj)
            logger.info(f"Synced {len(members)} group members with real phone numbers into SQLite database.")
            return members
        except Exception as e:
            logger.error(f"Error syncing group members: {e}")
            return []

    async def sync_recent_reactions(self) -> List[Dict[str, Any]]:
        """Scans the latest messages in the WhatsApp group and records any member emoji reactions into SQLite."""
        if not self.page or not self.is_ready:
            if not self.context:
                await self.start()
            for _ in range(25):
                if self.is_ready and self.page:
                    break
                await asyncio.sleep(1)

        if not self.page:
            return []

        jid = self.group_jid or self.db.get_setting("group_jid") or os.getenv("WHATSAPP_GROUP_JID", "")
        try:
            raw_reactions = await self.page.evaluate(f"""async () => {{
                try {{
                    await WPP.chat.find('{jid}');
                    await WPP.chat.openChatBottom('{jid}');
                    const msgs = await WPP.chat.getMessages('{jid}', {{ count: 12 }});
                    const list = [];
                    const store = window.WPP.whatsapp.ReactionsStore;

                    for (const m of msgs) {{
                        const msgId = m.id ? (m.id._serialized || m.id) : String(m.id);
                        if (store) {{
                            const rEntry = store.get(msgId);
                            if (rEntry) {{
                                const json = (typeof rEntry.toJSON === 'function') ? rEntry.toJSON() : rEntry;
                                const reactionsArr = json.reactions || [];
                                for (const grp of reactionsArr) {{
                                    const senders = grp.senders || [];
                                    for (const s of senders) {{
                                        const userJid = s.senderUserJid || (s.id && s.id.participant ? s.id.participant._serialized : (s.id ? s.id.participant : null));
                                        const emoji = s.reactionText || grp.aggregateEmoji || grp.id || '👍';
                                        if (userJid) {{
                                            list.push({{ msgId: msgId, sender: String(userJid), emoji: String(emoji) }});
                                        }}
                                    }}
                                }}
                            }}
                        }}
                    }}
                    return list;
                }} catch(e) {{
                    return [];
                }}
            }}""")

            for item in raw_reactions:
                if item.get("sender"):
                    self.db.record_reaction(
                        message_id=str(item.get("msgId")),
                        member_jid=str(item.get("sender")),
                        emoji=str(item.get("emoji", "👍"))
                    )
            if raw_reactions:
                logger.info(f"✨ Synced {len(raw_reactions)} live reactions from WhatsApp group.")
            return raw_reactions
        except Exception as e:
            logger.error(f"Error syncing reactions: {e}")
            return []

    async def stop(self) -> None:
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("WhatsApp API client stopped.")


pw_whatsapp = WhatsAppApiClient()
