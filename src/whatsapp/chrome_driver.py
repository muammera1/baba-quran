"""Google Chrome Automation Driver for WhatsApp Web via Chrome DevTools Protocol (CDP).

Connects directly to your logged-in Google Chrome Profile (Profile 2) on Windows/WSL.
"""

import asyncio
import json
import os
import subprocess
import sys
import urllib.request
from typing import Any, Dict, List, Optional

from src.core.logger import setup_logger

logger = setup_logger("chrome_driver")

CHROME_EXE_PATH = "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"
CHROME_USER_DATA = "/mnt/c/Users/ahmed/AppData/Local/Google/Chrome/User Data"
DEFAULT_PROFILE = "Profile 2"
CDP_PORT = 9222


class WhatsAppChromeDriver:
    """Automates WhatsApp Web using the user's existing Chrome Profile 2."""

    def __init__(
        self,
        profile_name: str = DEFAULT_PROFILE,
        port: int = CDP_PORT,
    ) -> None:
        self.profile_name = profile_name
        self.port = port
        self.ws_url: Optional[str] = None

    def is_cdp_available(self) -> bool:
        """Checks if Chrome DevTools Protocol port is open and responding."""
        try:
            url = f"http://127.0.0.1:{self.port}/json/version"
            with urllib.request.urlopen(url, timeout=2) as resp:
                return resp.status == 200
        except Exception:
            return False

    def launch_chrome(self, headless: bool = False) -> bool:
        """Launches Google Chrome with Profile 2 and Remote Debugging Port enabled."""
        if self.is_cdp_available():
            logger.info(f"Chrome remote debugging port {self.port} is already active.")
            return True

        if not os.path.exists(CHROME_EXE_PATH):
            logger.error(f"Chrome executable not found at: {CHROME_EXE_PATH}")
            return False

        logger.info(f"Launching Google Chrome with Profile '{self.profile_name}' and debugging port {self.port}...")
        
        args = [
            CHROME_EXE_PATH,
            f"--remote-debugging-port={self.port}",
            f"--profile-directory={self.profile_name}",
            "https://web.whatsapp.com",
        ]
        
        if headless:
            args.append("--headless=new")

        subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        # Wait for CDP endpoint to become ready
        for _ in range(15):
            import time
            time.sleep(1)
            if self.is_cdp_available():
                logger.info("Chrome launched and CDP port 9222 is active!")
                return True

        logger.warning("Chrome launched, waiting for user interaction or page load.")
        return True

    def get_whatsapp_tab_info(self) -> Optional[Dict[str, Any]]:
        """Finds the open WhatsApp Web tab via CDP JSON API."""
        try:
            url = f"http://127.0.0.1:{self.port}/json"
            with urllib.request.urlopen(url, timeout=3) as resp:
                tabs = json.loads(resp.read().decode("utf-8"))
                for tab in tabs:
                    if "web.whatsapp.com" in tab.get("url", ""):
                        return tab
                # Return first page tab if whatsapp tab not yet navigated
                for tab in tabs:
                    if tab.get("type") == "page":
                        return tab
        except Exception as e:
            logger.debug(f"Error querying CDP tabs: {e}")
        return None

    def execute_script_in_tab(self, js_code: str) -> Optional[Any]:
        """Executes JavaScript in the active WhatsApp Web tab via CDP WebSocket."""
        # Query active tab
        tab = self.get_whatsapp_tab_info()
        if not tab:
            logger.warning("No active WhatsApp tab found.")
            return None

        ws_url = tab.get("webSocketDebuggerUrl")
        if not ws_url:
            return None

        import websockets
        import asyncio

        async def run_cdp():
            async with websockets.connect(ws_url) as ws:
                req = {
                    "id": 1,
                    "method": "Runtime.evaluate",
                    "params": {
                        "expression": js_code,
                        "returnByValue": True,
                        "awaitPromise": True,
                    }
                }
                await ws.send(json.dumps(req))
                resp = await ws.recv()
                data = json.loads(resp)
                return data.get("result", {}).get("result", {}).get("value")

        return asyncio.run(run_cdp())


chrome_driver = WhatsAppChromeDriver()
