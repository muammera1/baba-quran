"""WhatsApp event listener connecting real-time events to local SQLite state."""

from src.core.database import Database
from src.core.logger import setup_logger
from src.whatsapp.client import WhatsAppClient

logger = setup_logger("event_listener")


class WhatsAppEventListener:
    """Listens for WhatsApp reaction events and updates member activity in SQLite."""

    def __init__(self, client: WhatsAppClient, db: Database) -> None:
        self.client = client
        self.db = db
        # Register the reaction handler with the client
        self.client.register_reaction_callback(self.on_reaction_received)

    def on_reaction_received(self, message_id: str, sender_jid: str, emoji: str) -> None:
        """Processes an incoming reaction event."""
        if not emoji or emoji.strip() == "":
            logger.info(f"Reaction removed by {sender_jid} on message {message_id}")
            return

        logger.info(f"Processing reaction: {sender_jid} reacted '{emoji}' to message {message_id}")
        # Any emoji counts as completing the reading
        updated = self.db.record_reaction(message_id=message_id, member_jid=sender_jid, emoji=emoji)
        if updated:
            logger.info(f"Successfully recorded reading completion for {sender_jid}")
        else:
            logger.debug(f"Reaction not matched to any active daily post (Message ID: {message_id})")
