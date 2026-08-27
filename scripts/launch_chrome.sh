#!/usr/bin/env bash
# ==============================================================================
# Launch Google Chrome with Profile 2 (WhatsApp) and Remote Debugging Enabled
# ==============================================================================

CHROME_EXE="/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"
PROFILE="Profile 2"
PORT=9222

if [ ! -f "${CHROME_EXE}" ]; then
    echo "❌ Google Chrome executable not found at: ${CHROME_EXE}"
    exit 1
fi

echo "🚀 Launching Google Chrome (${PROFILE}) on Remote Debugging Port ${PORT}..."
"${CHROME_EXE}" --remote-debugging-port=${PORT} --profile-directory="${PROFILE}" "https://web.whatsapp.com" >/dev/null 2>&1 &

echo "✅ Chrome launched! WhatsApp Web is opening in Profile 2."
echo "🔗 CDP Endpoint: http://127.0.0.1:${PORT}"
