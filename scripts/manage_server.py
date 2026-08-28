#!/usr/bin/env python3
"""Cross-platform Server Lifecycle Manager for Baba Quran Web Admin."""

import argparse
import os
import signal
import subprocess
import sys
import time

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PID_FILE = os.path.join(PROJECT_DIR, "data", "server.pid")
LOG_FILE = os.path.join(PROJECT_DIR, "logs", "web_server.log")
SERVER_SCRIPT = os.path.join(PROJECT_DIR, "src", "web", "server.py")
PORT = 8080


def get_running_pid() -> int:
    """Returns PID if process is actually running our server, otherwise 0."""
    if not os.path.exists(PID_FILE):
        return 0
    try:
        with open(PID_FILE, "r", encoding="utf-8") as f:
            pid = int(f.read().strip())
        
        # Verify that the process actually exists and is running our server
        cmdline_path = f"/proc/{pid}/cmdline"
        if os.path.exists(cmdline_path):
            with open(cmdline_path, "rb") as f:
                cmdline = f.read().decode("utf-8", errors="ignore")
                if "server.py" in cmdline or "src.web.server" in cmdline:
                    return pid
                else:
                    # Stale PID belonging to another system process
                    if os.path.exists(PID_FILE):
                        os.remove(PID_FILE)
                    return 0

        os.kill(pid, 0)
        return pid
    except (OSError, ValueError):
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        return 0


def start_server() -> None:
    pid = get_running_pid()
    if pid:
        print(f"⚠️  Server is ALREADY RUNNING (PID: {pid}) at http://localhost:{PORT}")
        return

    os.makedirs(os.path.join(PROJECT_DIR, "data"), exist_ok=True)
    os.makedirs(os.path.join(PROJECT_DIR, "logs"), exist_ok=True)

    log_fd = open(LOG_FILE, "a", encoding="utf-8")
    env = os.environ.copy()
    proc = subprocess.Popen(
        [sys.executable, SERVER_SCRIPT, "--port", str(PORT)],
        stdout=log_fd,
        stderr=log_fd,
        cwd=PROJECT_DIR,
        env=env,
        start_new_session=True,
    )

    with open(PID_FILE, "w", encoding="utf-8") as f:
        f.write(str(proc.pid))

    time.sleep(1.5)
    if get_running_pid():
        print(f"✅ Server successfully started in background!")
        print(f"🌐 URL: http://localhost:{PORT}")
        print(f"🔢 PID: {proc.pid}")
        print(f"📄 Logs: {LOG_FILE}")
    else:
        print(f"❌ Server failed to start. Check {LOG_FILE} for details.")


def stop_server() -> None:
    pid = get_running_pid()
    if not pid:
        print("ℹ️  Server is NOT running.")
        return

    print(f"🛑 Stopping Baba Quran Web Admin Server (PID: {pid})...")
    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(10):
            time.sleep(0.5)
            try:
                os.kill(pid, 0)
            except OSError:
                break
        else:
            os.kill(pid, signal.SIGKILL)
    except OSError:
        pass

    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)
    print("✅ Server stopped successfully.")


def status_server() -> None:
    pid = get_running_pid()
    if pid:
        print(f"🟢 Baba Quran Web Admin Server is RUNNING")
        print(f"   • PID: {pid}")
        print(f"   • URL: http://localhost:{PORT}")
        print(f"   • Log File: {LOG_FILE}")
    else:
        print("🔴 Baba Quran Web Admin Server is STOPPED")


def main() -> None:
    parser = argparse.ArgumentParser(description="Baba Quran Server Manager")
    parser.add_argument("action", choices=["start", "stop", "restart", "status"], help="Action to perform")
    args = parser.parse_args()

    if args.action == "start":
        start_server()
    elif args.action == "stop":
        stop_server()
    elif args.action == "restart":
        stop_server()
        time.sleep(1)
        start_server()
    elif args.action == "status":
        status_server()


if __name__ == "__main__":
    main()
