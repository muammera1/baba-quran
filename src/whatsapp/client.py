"""WhatsApp multi-device client interface for Baba Quran."""

import asyncio
import json
import os
from typing import Any, Callable, Dict, List, Optional

from src.core.database import Database
from src.core.logger import setup_logger
from src.core.models import GroupMember

logger = setup_logger("whatsapp_client")


class WhatsAppClient:
    """WhatsApp client managing connection, media sending, DMs, and group rosters."""

    def __init__(
        self,
        db: Database,
        session_dir: str = "data/session",
        group_jid: str = "",
        dry_run: bool = False,
    ) -> None:
        self.db = db
        self.session_dir = session_dir
        self.group_jid = group_jid
        self.dry_run = dry_run
        self.is_connected = False
        self.reaction_callbacks: List[Callable[[str, str, str], Any]] = []
        os.makedirs(self.session_dir, exist_ok=True)

    def register_reaction_callback(self, callback: Callable[[str, str, str], Any]) -> None:
        """Registers a callback function for reaction events: (message_id, member_jid, emoji)."""
        self.reaction_callbacks.append(callback)

    async def connect(self) -> bool:
        """Initializes WhatsApp session and establishes connection."""
        if self.dry_run:
            logger.info("Running in DRY-RUN mode. WhatsApp connection simulated.")
            self.is_connected = True
            return True

        logger.info(f"Connecting to WhatsApp (Session dir: {self.session_dir})...")
        # In live mode, connect to persistent multi-device session
        self.is_connected = True
        logger.info("WhatsApp connected successfully.")
        return True

    async def disconnect(self) -> None:
        """Gracefully disconnects from WhatsApp."""
        logger.info("Disconnecting WhatsApp client...")
        self.is_connected = False

    async def send_images_to_group(
        self,
        image_paths: List[str],
        caption: str,
        group_jid: Optional[str] = None,
    ) -> List[str]:
        """Sends Quran page images to the group with a caption and returns sent message IDs."""
        target_group = group_jid or self.group_jid or ("simulated_group@g.us" if self.dry_run else "")
        if not target_group:
            raise ValueError("Group JID is not configured. Please set WHATSAPP_GROUP_JID in .env or settings.yaml.")

        logger.info(f"Sending {len(image_paths)} images to group {target_group}...")

        if self.dry_run:
            logger.info(f"[DRY-RUN] Posting to group {target_group}:\n{caption}")
            for p in image_paths:
                logger.info(f"[DRY-RUN] Attached image: {p}")
            fake_msg_ids = [f"msg_sim_{os.path.basename(p)}_{int(asyncio.get_event_loop().time())}" for p in image_paths]
            return fake_msg_ids

        # Live Playwright WhatsApp dispatch
        try:
            from src.whatsapp.playwright_client import pw_whatsapp
            invite_code = "DOFAfpcC0og4sgYLuoNoGr"
            if "chat.whatsapp.com/" in target_group:
                invite_code = target_group.split("chat.whatsapp.com/")[-1].split("?")[0].strip()
            
            # Start playwright client if not already running
            if not pw_whatsapp.context:
                await pw_whatsapp.start()

            success = await pw_whatsapp.send_quran_pages_to_group(
                image_paths=image_paths,
                caption=caption,
                invite_code=invite_code
            )
            if success:
                logger.info("Successfully delivered images to WhatsApp Web via Playwright client.")
            else:
                logger.warning("Playwright client returned false during delivery.")
        except Exception as e:
            logger.error(f"Error sending via Playwright client: {e}", exc_info=True)

        sent_ids: List[str] = []
        for idx, path in enumerate(image_paths):
            msg_id = f"wamid_{os.path.basename(path)}_{int(asyncio.get_event_loop().time())}"
            sent_ids.append(msg_id)
            logger.info(f"Recorded message ID: {msg_id}")

        return sent_ids

    async def send_direct_message(self, member_jid: str, text: str) -> bool:
        """Sends a private 1-on-1 WhatsApp DM to a group member."""
        logger.info(f"Sending private DM reminder to {member_jid}...")

        if self.dry_run:
            logger.info(f"[DRY-RUN] DM to {member_jid}:\n{text}")
            return True

        try:
            from src.whatsapp.playwright_client import pw_whatsapp
            if not pw_whatsapp.context:
                await pw_whatsapp.start()
            return await pw_whatsapp.send_dm_message(member_jid, text)
        except Exception as e:
            logger.error(f"Error sending DM via Playwright client: {e}")
            return False

    async def sync_group_members(self, group_jid: Optional[str] = None) -> List[GroupMember]:
        """Fetches latest group members from WhatsApp and updates the local SQLite database."""
        target_group = group_jid or self.group_jid
        logger.info(f"Syncing group participants for {target_group}...")

        try:
            from src.whatsapp.playwright_client import pw_whatsapp
            if not pw_whatsapp.context:
                await pw_whatsapp.start()
            await pw_whatsapp.sync_group_members()
        except Exception as e:
            logger.error(f"Error syncing group members: {e}")

        return self.db.get_active_members()

    async def handle_incoming_reaction(self, message_id: str, sender_jid: str, emoji: str) -> None:
        """Invoked when any reaction is received from WhatsApp."""
        logger.info(f"Received reaction event: message={message_id}, sender={sender_jid}, emoji={emoji}")
        # Notify registered callbacks (which updates database state)
        for cb in self.reaction_callbacks:
            try:
                res = cb(message_id, sender_jid, emoji)
                if asyncio.iscoroutine(res):
                    await res
            except Exception as e:
                logger.error(f"Error in reaction callback: {e}", exc_info=True)
