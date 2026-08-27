#!/usr/bin/env bash
# ==============================================================================
# Baba Quran Bot & Web Admin Control CLI
#
# Commands:
#   ./manage.sh start             - Start background bot and web dashboard
#   ./manage.sh stop              - Stop background daemon cleanly
#   ./manage.sh restart           - Restart service with latest updates
#   ./manage.sh status            - Check running status and active PID
#   ./manage.sh logs              - Stream live application logs
#   ./manage.sh post-now          - Proactively publish today's Quran reading
#   ./manage.sh set-page <number> - Slide/set the upcoming schedule start page (1-604)
#   ./manage.sh sync-members      - Sync group roster & real phone numbers
#   ./manage.sh download-pages    - Download full Madinah Mushaf (Pages 1-604)
# ==============================================================================

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Prefer Virtual Environment Python
if [ -f "${PROJECT_DIR}/.venv/bin/python" ]; then
    PYTHON_EXEC="${PROJECT_DIR}/.venv/bin/python"
else
    PYTHON_EXEC="python3"
fi

COMMAND="$1"
shift || true

case "${COMMAND}" in
    start|stop|restart|status)
        "${PYTHON_EXEC}" "${PROJECT_DIR}/scripts/manage_server.py" "${COMMAND}" "$@"
        ;;
    logs)
        LOG_FILE="${PROJECT_DIR}/logs/web_server.log"
        mkdir -p "${PROJECT_DIR}/logs"
        touch "${LOG_FILE}"
        echo "📄 Streaming live logs from ${LOG_FILE} (Ctrl+C to exit)..."
        tail -f -n 50 "${LOG_FILE}"
        ;;
    post-now)
        echo "📖 Publishing today's Quran reading proactively..."
        "${PYTHON_EXEC}" "${PROJECT_DIR}/scripts/post_now.py" "$@"
        ;;
    set-page)
        if [ -z "$1" ]; then
            echo "❌ Usage: ./manage.sh set-page <page_number (1-604)>"
            exit 1
        fi
        "${PYTHON_EXEC}" "${PROJECT_DIR}/scripts/set_page.py" "$1"
        ;;
    sync-members)
        echo "👥 Syncing family group roster from WhatsApp..."
        "${PYTHON_EXEC}" "${PROJECT_DIR}/scripts/sync_members.py" "$@"
        ;;
    download-pages)
        echo "📥 Downloading Mushaf page images..."
        "${PYTHON_EXEC}" "${PROJECT_DIR}/scripts/download_pages.py" "$@"
        ;;
    help|--help|-h|"")
        echo "======================================================="
        echo "  📖 BABA QURAN BOT MANAGEMENT CLI"
        echo "======================================================="
        echo "Usage: ./manage.sh <command> [arguments]"
        echo ""
        echo "Service Lifecycle:"
        echo "  start             Start background daemon & web dashboard"
        echo "  stop              Stop background daemon"
        echo "  restart           Restart background daemon"
        echo "  status            Check active PID and running state"
        echo "  logs              Tail live application logs"
        echo ""
        echo "Quran & Member Operations:"
        echo "  post-now          Proactively publish today's reading"
        echo "  set-page <1-604>  Slide upcoming Khatmah start page"
        echo "  sync-members      Sync group roster & phone numbers"
        echo "  download-pages    Download 604 Madinah Quran page images"
        echo "======================================================="
        ;;
    *)
        echo "❌ Unknown command: '${COMMAND}'"
        echo "Run './manage.sh help' for a list of available commands."
        exit 1
        ;;
esac
