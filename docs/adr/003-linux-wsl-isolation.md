# ADR-003: Linux / WSL Environment Isolation & Singleton Lock

## Status
**Accepted & Mandatory**

## Context
Cross-OS automation between Linux/WSL and Windows GUI processes (e.g. running Windows `chrome.exe` via `cmd.exe` or PowerShell keystroke injection) is vulnerable to window focus stealing, UIPI session boundaries, clipboard locks, and unpredictable state transitions in background services.

## Decision
1. **100% Linux Native**: The entire application and its persistent browser session run natively inside Linux / WSL2 using Playwright Chromium with user data directory in `data/session/playwright_wa/`.
2. **Singleton Lock Discipline**: The background daemon (`./manage.sh start`, PID tracked in `data/server.pid`) holds an exclusive lock on the browser session. Standalone CLI scripts and tests must coordinate with or query the active daemon via HTTP endpoints rather than spawning duplicate browser contexts on the same profile folder.

## Consequences
- **Positive**: Zero dependency on Windows desktop state or active user login sessions.
- **Positive**: Enables clean daemonization, automated restarts, and predictable test environments.
