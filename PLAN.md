# Kids Wellness App — Complete Development Plan

## Overview
A Windows-based parental control and wellness application for laptops used by children. The app enforces eye breaks, long breaks, daily screen time limits, per-app limits, app/website blocking, and activity tracking. Admin controls are extendable to Android/iPhone/Web apps via a cloud backend.

---

## User Identification
Each user is identified by a **user ID** — this is the Windows username by default (auto-detected, zero setup), with an optional email override for cloud sync.

### Flow
1. **Auto-detect**: On startup, the app reads the current Windows username via `os.getlogin()` / `USERNAME` env var. No setup needed.
2. **Storage**: The Windows username is used as the user ID in all SQLite rows.
3. **Optional email**: Parent can set an email in Admin Settings for cloud sync. When set, the email takes priority as the user ID.
4. **Fallback**: Works completely offline with just the Windows username.

### Why this approach?
| Method | Setup needed | Works offline | Cloud-ready |
|--------|-------------|---------------|-------------|
| Windows username (auto) | None | ✅ | ❌ (not globally unique) |
| Email (manual entry) | Yes | ✅ | ✅ (globally unique) |
| **Combined (our approach)** | **None to start** | ✅ | **✅** |

Windows username is the perfect bootstrap — no friction for the user. Email is added later only when cloud features are needed.

---

## Status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Core Database & Config | ✅ Completed |
| 2 | UI Client — Notifications & Overlays | ✅ Completed |
| 3 | Active Window Monitoring & Web Tracking | ✅ Completed |
| 4 | App/Website Blocking (C# Service) | ✅ Completed |
| 5 | Admin Dashboard (Local) | ✅ Completed |
| 6 | Installer & Auto-Start | ✅ Completed |
| 7 | Cloud Sync & Mobile App (Future) | ⬜ Not started |

---

## Features

### 1. Break Schedule & Rules
- **Eye Break**: 30-second break every 20 minutes of continuous screen time.
- **Long Break**: 5-minute break every 1 hour of continuous screen time.
- **Pre-reminders**: Notification at 2 minutes before break, and at 1 minute before break.
- **Countdown**: On-screen countdown from 5 to 1 seconds immediately before the overlay locks the screen.
- **Parent Override**: Admin can bypass/end any break by entering a password.

### 2. Screen Time Limits
- **Daily Device Limit**: Configurable per day of week (e.g., 120 min weekdays, 180 min weekends).
- **Per-App Limits & Schedule**: Max daily time per app, with allowed days of week (e.g., Minecraft only on Sat/Sun).
- When a limit is reached, the app/game is blocked (process killed or overlay shown).

### 3. App & Website Blocking
- **App Blocking**: Blacklist of process names. Blocked apps are killed instantly if launched.
- **Website Blocking**: Blacklist of domains. Blocked sites are redirected to 127.0.0.1 via Windows hosts file.

### 4. Activity Tracking & Reporting
- **App Usage**: Tracks active window (process name + window title), duration per session, logged to SQLite.
- **Web Tracking**: Reads URL bar from Chrome & Edge using Windows UI Automation API (no browser extensions needed).
- **Daily Reports**: Total screen time, per-app breakdown, web history, breaks taken.

### 5. Anti-Tamper & Auto-Start
- Starts automatically on Windows boot.
- **Dual-process architecture**:
  - **C# Windows Service (LocalSystem)**: Runs the background monitor, enforces blocks, and acts as a watchdog. Cannot be killed by a standard user.
  - **Python PyQt6 UI Client**: Shows notifications, countdowns, overlays, and admin settings panel. If the UI client process is killed, the C# Service instantly restarts it.
- Uninstall requires admin password.

### 6. Mobile/Web Admin (Future)
- Android app (and later iPhone / Web) to view reports and change settings.
- Cloud sync layer (Supabase/Firebase) for real-time config push and activity upload.

---

## Architecture

```
 ┌──────────────────────────────────────────────────────┐
 │              Windows Service (C# .NET)               │
 │  • Starts on boot (LocalSystem account)              │
 │  • Runs background timer for breaks                  │
 │  • Polls active window every 1-2 seconds             │
 │  • Logs app usage to SQLite                          │
 │  • Kills blocked apps when limit is reached          │
 │  • Manages hosts file for website blocking           │
 │  • Watchdog: monitors UI Client, restarts if killed  │
 └──────────────┬───────────────────────────────────────┘
                │ IPC
                ▼
 ┌──────────────────────────────────────────────────────┐
 │           UI Overlay Client (Python PyQt6)           │
 │  • Runs in user session (SystemTray + fullscreen)    │
 │  • Shows pre-break notifications (2min, 1min)        │
 │  • Shows 5-to-1 countdown overlay                    │
 │  • Shows full-screen break overlay (eye/long)        │
 │  • Reads Chrome & Edge URL bar with UI Automation     │
 │  • Admin settings panel (password-protected)          │
 └──────────────────────────────────────────────────────┘
```

### Communication between Service and UI Client
- **Named Pipe (IPC)**: C# service sends commands to UI Client (show overlay, end break, show notification).
- **Shared SQLite DB**: Both processes read/write to `%ProgramData%\KidsWellnessApp\activity.db`.

---

## Tech Stack

| Component          | Technology                  |
|--------------------|-----------------------------|
| Background Service | C# .NET 8 (Windows Service) |
| UI Client          | Python 3.11+ / PySide6      |
| Local Database     | SQLite3                     |
| Configuration      | JSON file (local, schedule-based per day) |
| Web Tracking       | Windows UI Automation API   |
| Installer          | Inno Setup / NSIS (setup.exe) |
| Cloud Backend      | Supabase or Firebase (future) |
| Mobile/Web Admin   | Flutter / Kotlin / iOS / Web (future) |

---

## File Structure

```
WellnessFocus/
├── windows_service/           # C# .NET Windows Service
│   ├── Service.cs             # Timer, process monitor, watchdog
│   ├── Program.cs             # Entry point, service registration
│   ├── WellnessService.csproj
│   └── ServiceInstaller.cs    # Install/uninstall logic
│
├── ui_client/                 # Python PyQt6 UI Client
│   ├── main.py                # Entry point: tray icon + event loop
│   ├── overlay.py             # Full-screen break overlay window
│   ├── notifications.py       # Toast notification popups
│   ├── web_tracker.py         # UI Automation URL reader for Chrome/Edge
│   ├── admin_panel.py         # Password-protected settings dashboard
│   ├── config_manager.py      # Load/save config.json
│   ├── database.py            # SQLite init + CRUD operations
│   └── requirements.txt       # PySide6, pyinstaller
│
├── cloud_sync/                # Future: Cloud backend integration
│   └── sync_client.py         # REST API client for Supabase/Firebase
│
├── build/                     # Build scripts & CI/CD
│   ├── build_windows.bat      # One-click build script for Windows
│   ├── build_installer.iss    # Inno Setup installer script
│   └── github_actions.yml     # CI pipeline for automated builds
│
├── android_app/               # Future: Android/Kotlin admin app
│
├── config.json                # Default config (created at first run)
├── requirements.txt           # Python dependencies
├── PLAN.md                    # This file
└── README.md                  # User-facing documentation
```

---

## Development Phases

### Phase 1: Core Database & Config (Windows) — ✅ Completed
**Files**: `config_manager.py`, `database.py`
- Set up `%ProgramData%\KidsWellnessApp\` directory.
- SQLite tables: `app_usage_log`, `web_usage_log`, `break_log`.
- JSON configuration manager with defaults.
- Password hashing (SHA-256) support.

### Phase 2: UI Client — Notifications & Overlays — ✅ Completed
**Files**: `main.py`, `overlay.py`, `notifications.py`
- System tray icon (PyQt6).
- Pre-break toast notifications (2min, 1min warnings).
- Full-screen frameless overlay for eye break (30s) and long break (5min).
- 5-to-1 countdown before overlay locks.
- Overlay blocks Alt+F4, Alt+Tab, Win+D, Ctrl+Alt+Del (via low-level hooks).
- Password bypass to dismiss overlay.

### Phase 3: Active Window Monitoring & Web Tracking — ✅ Completed
**Files**: `window_monitor.py`, `web_tracker.py`
- Poll `GetForegroundWindow()` + `GetWindowText()` every 1-2 seconds.
- Log active process name + duration to SQLite.
- UI Automation: read URL from Chrome/Edge address bar.
- Log visited URLs/domains to `web_usage_log`.

### Phase 4: App/Website Blocking (C# Windows Service) — ✅ Completed
**Files**: `windows_service/Service.cs`, `windows_service/Program.cs`
- C# service runs as LocalSystem.
- Reads blocklist from config.
- Kills blocked processes via `Process.Kill()`.
- Manages hosts file (`C:\Windows\System32\drivers\etc\hosts`) for domain blocking.
- Watchdog: monitors Python `ui_client.exe` process; restarts if terminated.
- Communicates with UI Client via Named Pipe for overlay commands.

### Phase 5: Admin Dashboard (Local) — ✅ Completed
**Files**: `admin_panel.py`
- Password-protected settings window.
- View daily reports (app usage chart, web history).
- Modify limits, blocklists, breaks.
- Change admin password.

### Phase 6: Installer & Auto-Start — ✅ Completed
**Files**: `build/build_windows.bat`, `build/build_installer.iss`, `build/github_actions.yml`
- Build scripts for Windows.
- Inno Setup to create a single `.exe` installer.
- Registers C# service, installs Python, sets up auto-start.
- GitHub Actions: automated cloud build for public distribution.

### Phase 7: Cloud Sync & Mobile App (Future) — ⬜ Not started
**Files**: `cloud_sync/sync_client.py`, `android_app/`
- REST API client to Sync config to/fro cloud.
- Upload logs to cloud database.
- Android/Kotlin app for remote admin control.
- Real-time config push via WebSocket / Supabase Realtime.

---

## Security & Anti-Tamper Design

| Threat | Mitigation |
|--------|-----------|
| User kills UI client | C# Service watchdog restarts it immediately |
| User kills Windows Service | Requires admin privileges; standard user cannot |
| User blocks startup | Service is auto-started by Windows SCM |
| User closes overlay | Overlay is frameless, topmost, blocks keyboard hooks |
| User uninstalls | Uninstaller requires admin password |
| User disables WiFi (to bypass sync) | Last known config is enforced locally |
| User opens Task Manager | Overlay can be configured to block/hide Task Manager |

---

## Data Storage

| Data | Location |
|------|----------|
| Configuration | `%ProgramData%\WellnessFocus\config.json` |
| SQLite Database | `%ProgramData%\WellnessFocus\activity.db` |
| Logs | `%ProgramData%\WellnessFocus\logs\` |

---

## Public Distribution (Future)

- Host code on GitHub (private → public).
- GitHub Actions builds `.exe` installer automatically.
- Each release creates a downloadable `.exe` file.
- Zero configuration secrets: all URLs/keys configurable via environment variables.
- Clean, separate modules: easy for community to contribute (Web/iPhone admin apps).
