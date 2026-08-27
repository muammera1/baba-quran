#!/usr/bin/env bash
# ==============================================================================
# Baba Quran Web Admin Server Control Script
# Usage:
#   ./manage.sh start     - Start server in background
#   ./manage.sh stop      - Stop background server
#   ./manage.sh restart   - Restart server
#   ./manage.sh status    - Check server status
#   ./manage.sh logs      - Follow live server logs
# ==============================================================================

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_EXEC="python3"

if [ "$1" == "logs" ]; then
    LOG_FILE="${PROJECT_DIR}/logs/web_server.log"
    mkdir -p "${PROJECT_DIR}/logs"
    touch "${LOG_FILE}"
    echo "📄 Viewing live server logs (Ctrl+C to exit)..."
    tail -f "${LOG_FILE}"
else
    ${PYTHON_EXEC} "${PROJECT_DIR}/scripts/manage_server.py" "$@"
fi
