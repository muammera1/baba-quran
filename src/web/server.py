"""Standalone Web Admin Server for Baba Quran (Zero External Dependencies)."""

import argparse
import asyncio
import json
import os
import sys
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

import site

# Ensure project root and user packages are in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)
user_site = site.getusersitepackages()
if user_site and os.path.exists(user_site) and user_site not in sys.path:
    sys.path.append(user_site)

from src.core.config import load_yaml_settings, settings
from src.core.database import Database
from src.core.logger import setup_logger
from src.core.models import GroupMember
from src.quran.metadata import SURAHS, get_surah_by_name_or_number
from src.quran.page_manager import PageManager
from src.quran.special_schedules import SpecialScheduleResolver
from src.scheduler.jobs import run_daily_post_job, run_reminder_check_job
from src.scheduler.scheduler import BabaQuranScheduler
from src.whatsapp.client import WhatsAppClient
from src.whatsapp.event_listener import WhatsAppEventListener
from src.whatsapp.message_builder import MessageBuilder

logger = setup_logger("web_admin")

# Global Bot Controller State
class BotManager:
    def __init__(self) -> None:
        self.is_running = False
        self.db = Database(db_path=settings.DATABASE_PATH)
        self.yaml_cfg = load_yaml_settings(settings.CONFIG_YAML_PATH)
        self.special_resolver = SpecialScheduleResolver(raw_schedules=self.yaml_cfg.get("special_schedules", []))
        self.msg_builder = MessageBuilder(templates=self.yaml_cfg.get("templates", {}))
        self.page_mgr = PageManager(db=self.db, pages_dir=settings.QURAN_PAGES_DIR)
        self.wa_client = WhatsAppClient(
            db=self.db,
            session_dir=settings.WHATSAPP_SESSION_PATH,
            group_jid=settings.WHATSAPP_GROUP_JID,
            dry_run=False,
        )
        self.event_listener = WhatsAppEventListener(client=self.wa_client, db=self.db)
        self.scheduler: Optional[BabaQuranScheduler] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None

    def start_bot(self) -> bool:
        if self.is_running:
            return True

        def run_in_thread() -> None:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self.scheduler = BabaQuranScheduler(
                db=self.db,
                page_mgr=self.page_mgr,
                special_resolver=self.special_resolver,
                wa_client=self.wa_client,
                msg_builder=self.msg_builder,
                settings=settings,
            )
            from src.whatsapp.playwright_client import pw_whatsapp
            self._loop.run_until_complete(self.wa_client.connect())
            self._loop.run_until_complete(pw_whatsapp.start())
            self.scheduler.start()
            self.is_running = True
            logger.info("Bot started successfully with live WhatsApp API client in background thread.")
            self._loop.run_forever()

        self._thread = threading.Thread(target=run_in_thread, daemon=True)
        self._thread.start()
        self.is_running = True
        return True

    def stop_bot(self) -> bool:
        if not self.is_running:
            return True
        if self.scheduler:
            self.scheduler.shutdown()
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        self.is_running = False
        logger.info("Bot stopped.")
        return True

    def run_async_coroutine(self, coro: Any) -> Any:
        """Executes an async task synchronously."""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


bot_manager = BotManager()


class AdminRequestHandler(BaseHTTPRequestHandler):

    def _send_json(self, data: Any, status: int = 200) -> None:
        response = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(response)

    def _send_html(self, html_content: str, status: int = 200) -> None:
        response = html_content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def _read_json_body(self) -> Dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        body = self.rfile.read(content_length).decode("utf-8")
        try:
            return json.loads(body)
        except Exception:
            return {}

    def do_HEAD(self) -> None:
        url = urlparse(self.path)
        path = url.path
        if path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
        elif path.startswith("/api/"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, HEAD")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        url = urlparse(self.path)
        path = url.path

        # 1. Serve QR Code Image if waiting for pairing
        if path == "/qr":
            qr_file = os.path.join(PROJECT_ROOT, "data", "session", "qr.png")
            if os.path.exists(qr_file):
                with open(qr_file, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.end_headers()
                self.wfile.write(content)
            else:
                self._send_json({"logged_in": True, "message": "WhatsApp is already connected or QR code generating..."}, 200)
            return

        # 2. Serve Web Admin Dashboard Frontend
        if path in ("/", "/index.html"):
            template_path = os.path.join(PROJECT_ROOT, "src", "web", "templates", "index.html")
            if os.path.exists(template_path):
                with open(template_path, "r", encoding="utf-8") as f:
                    self._send_html(f.read())
            else:
                self._send_html("<h1>Template not found</h1>", 404)
            return

        # 2. API: Status
        if path == "/api/status":
            khatmah = bot_manager.db.get_khatmah_state()
            active_members = bot_manager.db.get_active_members()
            latest_post = bot_manager.db.get_latest_post()
            reactions_count = 0

            if latest_post:
                with bot_manager.db.get_connection() as conn:
                    row = conn.execute(
                        "SELECT COUNT(*) as c FROM member_activity WHERE daily_post_id = ? AND reacted = 1",
                        (latest_post.id,),
                    ).fetchone()
                    reactions_count = row["c"] if row else 0

            pages_per_day = bot_manager.db.get_setting("pages_per_day", str(settings.PAGES_PER_DAY))
            post_time = bot_manager.db.get_setting("post_time", settings.POST_TIME)
            reminder_hours = bot_manager.db.get_setting("reminder_hours_after_post", str(settings.REMINDER_HOURS_AFTER_POST))
            timezone_setting = bot_manager.db.get_setting("timezone", settings.TIMEZONE)
            group_jid_setting = bot_manager.db.get_setting("group_jid", settings.WHATSAPP_GROUP_JID)

            from src.whatsapp.playwright_client import pw_whatsapp
            whatsapp_logged_in = pw_whatsapp.is_logged_in or pw_whatsapp.has_saved_session

            self._send_json({
                "bot_running": bot_manager.is_running,
                "chrome_connected": whatsapp_logged_in,
                "whatsapp_logged_in": whatsapp_logged_in,
                "khatmah": {
                    "current_page": khatmah.current_page,
                    "cycle_number": khatmah.cycle_number,
                    "updated_at": khatmah.updated_at,
                },
                "active_members_count": len(active_members),
                "reactions_count": reactions_count,
                "latest_post": latest_post.__dict__ if latest_post else None,
                "settings": {
                    "group_jid": group_jid_setting,
                    "pages_per_day": int(pages_per_day),
                    "post_time": post_time,
                    "reminder_hours_after_post": int(reminder_hours),
                    "timezone": timezone_setting,
                    "friday_kahf_enabled": True,
                }
            })
            return

        # 3. API: Members List with Reactions
        if path == "/api/members":
            members = bot_manager.db.get_active_members(include_exempt=True)
            latest_post = bot_manager.db.get_latest_post()
            res = []
            with bot_manager.db.get_connection() as conn:
                for m in members:
                    reacted = False
                    reaction_emoji = ""
                    reminder_sent = False
                    if latest_post:
                        act = conn.execute(
                            "SELECT reacted, reaction_emoji, reminder_sent FROM member_activity WHERE daily_post_id = ? AND member_jid = ?",
                            (latest_post.id, m.jid),
                        ).fetchone()
                        if act:
                            reacted = bool(act["reacted"])
                            reaction_emoji = act["reaction_emoji"] or ""
                            reminder_sent = bool(act["reminder_sent"])
                    res.append({
                        "jid": m.jid,
                        "display_name": m.display_name,
                        "phone_number": m.phone_number,
                        "is_admin": m.is_admin,
                        "is_exempt": m.is_exempt,
                        "reacted": reacted,
                        "reaction_emoji": reaction_emoji,
                        "reminder_sent": reminder_sent,
                    })
            self._send_json(res)
            return

        # 4. API: Surahs List
        if path == "/api/surahs":
            surahs_list = [
                {
                    "number": s.number,
                    "name_arabic": s.name_arabic,
                    "name_english": s.name_english,
                    "page_start": s.page_start,
                    "page_end": s.page_end,
                }
                for s in SURAHS
            ]
            self._send_json(surahs_list)
            return

        # 5. API: Logs
        if path == "/api/logs":
            log_path = os.path.join(PROJECT_ROOT, "logs", "baba_quran.log")
            if os.path.exists(log_path):
                with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                    last_lines = lines[-150:]  # last 150 lines
                    self._send_json({"logs": "".join(last_lines)})
            else:
                self._send_json({"logs": "Log file not created yet."})
            return

        self._send_json({"error": "Not Found"}, 404)

    def do_POST(self) -> None:
        url = urlparse(self.path)
        path = url.path
        body = self._read_json_body()

        # Bot Start / Stop
        if path == "/api/bot/start":
            bot_manager.start_bot()
            self._send_json({"success": True, "message": "تم تشغيل البوت بنجاح"})
            return

        if path == "/api/bot/stop":
            bot_manager.stop_bot()
            self._send_json({"success": True, "message": "تم إيقاف البوت بنجاح"})
            return

        # Khatmah Pointer: Set Next Starting Page
        if path == "/api/khatmah/set_page":
            try:
                new_page = int(body.get("page", 1))
                new_cycle = int(body.get("cycle", 1))
                if 1 <= new_page <= 604:
                    bot_manager.db.update_khatmah_state(current_page=new_page, cycle_number=new_cycle)
                    logger.info(f"Admin manually set next Khatmah start page to: {new_page} (Cycle: {new_cycle})")
                    self._send_json({
                        "success": True, 
                        "message": f"تم بنجاح تعيين بداية الورد القادم لتكون الصفحة {new_page} (الختمة رقم {new_cycle})",
                        "current_page": new_page,
                        "cycle_number": new_cycle
                    })
                else:
                    self._send_json({"success": False, "message": "رقم الصفحة يجب أن يكون بين 1 و 604"}, 400)
            except Exception as e:
                logger.error(f"Error setting khatmah page: {e}")
                self._send_json({"success": False, "message": f"خطأ: {str(e)}"}, 500)
            return

        # Chrome Profile 2 Launch
        if path == "/api/chrome/launch":
            from src.whatsapp.chrome_driver import chrome_driver
            success = chrome_driver.launch_chrome()
            if success:
                self._send_json({"success": True, "message": "تم إطلاق Google Chrome بروفايل 2 وتفعيل منفذ التحكم 9222 بنجاح"})
            else:
                self._send_json({"success": False, "message": "تعذر تشغيل Google Chrome. يرجى التأكد من المسار"}, 500)
            return

        # Actions: Post Today's Pages Now (Proactive Execution)
        if path == "/api/actions/post_now":
            try:
                post_id = bot_manager.run_async_coroutine(
                    run_daily_post_job(
                        db=bot_manager.db,
                        page_mgr=bot_manager.page_mgr,
                        special_resolver=bot_manager.special_resolver,
                        wa_client=bot_manager.wa_client,
                        msg_builder=bot_manager.msg_builder,
                        settings=settings,
                        force=True,
                    )
                )
                self._send_json({"success": True, "message": f"تم نشر الورد مبكراً بنجاح (المعرف: {post_id}). سيتم تخطي الجدولة التلقائية لليوم تلقائياً."})
            except Exception as e:
                logger.error(f"Error in post_now: {e}", exc_info=True)
                self._send_json({"success": False, "message": f"خطأ أثناء النشر: {str(e)}"}, 500)
            return

        # Actions: Post Off-the-Plan Surah
        if path == "/api/actions/post_surah":
            surah_input = str(body.get("surah", "")).strip()
            surah = get_surah_by_name_or_number(surah_input)
            if not surah:
                self._send_json({"success": False, "message": "السورة غير موجودة"}, 400)
                return

            try:
                batch = bot_manager.page_mgr.get_custom_page_batch(surah.page_start, surah.page_end)
                caption = bot_manager.msg_builder.build_special_post_caption(
                    surah_arabic=f"سورة {surah.name_arabic}",
                    page_start=batch.page_start,
                    page_end=batch.page_end,
                )
                bot_manager.run_async_coroutine(
                    bot_manager.wa_client.send_images_to_group(batch.image_paths, caption)
                )
                self._send_json({"success": True, "message": f"تم نشر سورة {surah.name_arabic} بنجاح"})
            except Exception as e:
                self._send_json({"success": False, "message": str(e)}, 500)
            return

        # Actions: Check Reminders Now
        if path == "/api/actions/check_reminders":
            try:
                count = bot_manager.run_async_coroutine(
                    run_reminder_check_job(
                        db=bot_manager.db,
                        wa_client=bot_manager.wa_client,
                        msg_builder=bot_manager.msg_builder,
                    )
                )
                self._send_json({"success": True, "message": f"تم فحص التذكيرات وإرسال {count} تذكير خاص"})
            except Exception as e:
                self._send_json({"success": False, "message": str(e)}, 500)
            return

        # Actions: Sync Reactions from WhatsApp
        if path == "/api/actions/sync_reactions":
            try:
                from src.whatsapp.playwright_client import pw_whatsapp
                reactions = bot_manager.run_async_coroutine(pw_whatsapp.sync_recent_reactions())
                self._send_json({"success": True, "message": f"تم جلب ومزامنة {len(reactions)} تفاعل من واتساب", "reactions": reactions})
            except Exception as e:
                logger.error(f"Error syncing reactions: {e}")
                self._send_json({"success": False, "message": str(e)}, 500)
            return

        # Members: Toggle Exemption
        if path == "/api/members/exempt":
            jid = body.get("jid")
            with bot_manager.db.get_connection() as conn:
                row = conn.execute("SELECT is_exempt FROM group_members WHERE jid = ?", (jid,)).fetchone()
                if row:
                    new_val = 0 if row["is_exempt"] else 1
                    conn.execute("UPDATE group_members SET is_exempt = ? WHERE jid = ?", (new_val, jid))
                    msg = "تم إعفاء العضو من التذكيرات" if new_val else "تم تفعيل التذكيرات للعضو"
                    self._send_json({"success": True, "message": msg})
                else:
                    self._send_json({"success": False, "message": "العضو غير موجود"}, 404)
            return

        # Members: Add Member
        if path == "/api/members/add":
            name = body.get("name", "").strip()
            phone = body.get("phone", "").strip()
            jid = phone.replace("+", "").replace(" ", "").replace("-", "") + "@s.whatsapp.net"
            bot_manager.db.upsert_member(GroupMember(jid=jid, phone_number=phone, display_name=name))
            self._send_json({"success": True, "message": f"تمت إضافة العضو {name} بنجاح"})
            return

        # Members: Sync from WhatsApp
        if path == "/api/members/sync":
            try:
                members = bot_manager.run_async_coroutine(bot_manager.wa_client.sync_group_members())
                self._send_json({"success": True, "message": f"تمت مزامنة {len(members)} عضو من واتساب"})
            except Exception as e:
                self._send_json({"success": False, "message": str(e)}, 500)
            return

        # Settings: Save
        if path == "/api/settings":
            env_updates = {}
            if "pages_per_day" in body:
                val = str(body["pages_per_day"])
                bot_manager.db.set_setting("pages_per_day", val)
                env_updates["PAGES_PER_DAY"] = val
            if "post_time" in body:
                val = str(body["post_time"])
                bot_manager.db.set_setting("post_time", val)
                env_updates["POST_TIME"] = val
            if "reminder_hours" in body:
                val = str(body["reminder_hours"])
                bot_manager.db.set_setting("reminder_hours_after_post", val)
                env_updates["REMINDER_HOURS_AFTER_POST"] = val
            if "timezone" in body:
                val = str(body["timezone"])
                bot_manager.db.set_setting("timezone", val)
                env_updates["TIMEZONE"] = val
            if "group_jid" in body:
                val = str(body["group_jid"]).strip()
                bot_manager.db.set_setting("group_jid", val)
                bot_manager.wa_client.group_jid = val
                env_updates["WHATSAPP_GROUP_JID"] = val

            # Write to .env file
            env_file_path = os.path.join(PROJECT_ROOT, ".env")
            if os.path.exists(env_file_path):
                with open(env_file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                new_lines = []
                for line in lines:
                    k = line.split("=")[0].strip() if "=" in line else ""
                    if k in env_updates:
                        new_lines.append(f"{k}={env_updates.pop(k)}\n")
                    else:
                        new_lines.append(line)
                for k, v in env_updates.items():
                    new_lines.append(f"{k}={v}\n")
                with open(env_file_path, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)

            self._send_json({"success": True, "message": "تم حفظ وتحديث الإعدادات بنجاح"})
            return

        self._send_json({"error": "Method Not Allowed"}, 405)


class ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True


def run_web_server(host: str = "0.0.0.0", port: int = 8080) -> None:
    server_address = (host, port)
    httpd = ReusableHTTPServer(server_address, AdminRequestHandler)
    print(f"\n=======================================================")
    print(f"  📖 BABA QURAN WEB ADMIN DASHBOARD STARTED          ")
    print(f"  Access URL: http://localhost:{port}               ")
    print(f"=======================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down web server...")
        bot_manager.stop_bot()
        httpd.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Baba Quran Web Admin Server")
    parser.add_argument("--port", type=int, default=8080, help="Web server port (default: 8080)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host address (default: 0.0.0.0)")
    args = parser.parse_args()

    run_web_server(host=args.host, port=args.port)
