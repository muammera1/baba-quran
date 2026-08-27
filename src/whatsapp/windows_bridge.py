"""Windows WhatsApp Bridge: Automates sending Quran page images via active WhatsApp Web."""

import asyncio
import os
import shutil
import subprocess
from typing import List, Optional

from src.core.logger import setup_logger

logger = setup_logger("windows_bridge")

POWERSHELL_EXE = "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
WIN_TEMP_DIR = "/mnt/c/Users/ahmed/AppData/Local/Temp"
WIN_TEMP_PATH_DOS = r"C:\Users\ahmed\AppData\Local\Temp"


class WindowsWhatsAppBridge:
    """Automates WhatsApp Web in the active Windows browser using PowerShell."""

    def __init__(self, group_invite_code: str = "DOFAfpcC0og4sgYLuoNoGr") -> None:
        self.group_invite_code = group_invite_code

    def copy_images_to_windows_temp(self, image_paths: List[str]) -> List[str]:
        """Copies image files to Windows Temp folder and returns Windows DOS paths."""
        win_paths = []
        os.makedirs(WIN_TEMP_DIR, exist_ok=True)
        for idx, src_path in enumerate(image_paths):
            filename = f"quran_page_{idx}_{os.path.basename(src_path)}"
            dest_wsl = os.path.join(WIN_TEMP_DIR, filename)
            shutil.copy2(src_path, dest_wsl)
            dest_dos = f"{WIN_TEMP_PATH_DOS}\\{filename}"
            win_paths.append(dest_dos)
        return win_paths

    def send_post_via_windows(self, image_paths: List[str], caption: str, invite_code: Optional[str] = None) -> bool:
        """Copies images to Windows clipboard, activates WhatsApp Web, and pastes."""
        code = invite_code or self.group_invite_code
        win_image_paths = self.copy_images_to_windows_temp(image_paths)

        # Create PowerShell script
        ps_script_path = os.path.join(WIN_TEMP_DIR, "send_whatsapp.ps1")
        ps_script_content = f"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName Microsoft.VisualBasic

# 1. Open or focus WhatsApp Web group
$groupUrl = "https://web.whatsapp.com/accept?code={code}"
Start-Process $groupUrl

# 2. Wait for WhatsApp Web to load/focus
Start-Sleep -Seconds 3

# 3. Copy image files to Windows clipboard
$files = New-Object System.Collections.Specialized.StringCollection
"""
        for p in win_image_paths:
            ps_script_content += f'$files.Add("{p}")\n'

        ps_script_content += f"""
[System.Windows.Forms.Clipboard]::SetFileDropList($files)

# 4. Activate WhatsApp Chrome Window and Paste
[Microsoft.VisualBasic.Interaction]::AppActivate("WhatsApp")
Start-Sleep -Milliseconds 800

# Paste images (Ctrl+V)
[System.Windows.Forms.SendKeys]::SendWait("^v")
Start-Sleep -Seconds 2

# Set Caption and Send
# [System.Windows.Forms.SendKeys]::SendWait("{{ENTER}}")
Write-Output "SUCCESS"
"""
        with open(ps_script_path, "w", encoding="utf-8") as f:
            f.write(ps_script_content)

        logger.info(f"Executing Windows WhatsApp bridge for {len(image_paths)} images...")
        try:
            cmd = [
                POWERSHELL_EXE,
                "-NoProfile",
                "-ExecutionPolicy", "Bypass",
                "-File", f"{WIN_TEMP_PATH_DOS}\\send_whatsapp.ps1"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            logger.info(f"PowerShell Output: {res.stdout.strip()}")
            return "SUCCESS" in res.stdout
        except Exception as e:
            logger.error(f"Error executing Windows bridge: {e}", exc_info=True)
            return False


windows_bridge = WindowsWhatsAppBridge()
