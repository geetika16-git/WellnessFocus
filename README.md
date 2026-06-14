# Wellness Focus

A Windows-based wellness and screen time management application. Enforces break schedules, app limits, website blocking, and tracks activity. Works offline with optional cloud sync for remote admin control.

## Features
- Eye break (30s) every 20 min + Long break (5min) every 1 hour
- Pre-break notifications at 2min and 1min + 5-to-1 countdown
- Full-screen unclosable overlay with admin password bypass
- Daily screen time limits (per day of week)
- Per-app limits with schedule (allowed days)
- App blocking (process kill) + Website blocking (hosts file)
- App usage tracking + Chrome/Edge web history tracking
- Auto-start on boot, tamper-proof dual-process architecture
- Password-protected admin dashboard with reports
- All durations customizable

## Tech Stack
- **UI Client**: Python 3.11+ / PySide6 (packaged as single .exe)
- **Background Service**: C# .NET 8 Windows Service (self-contained)
- **Database**: SQLite3
- **Installer**: Inno Setup

## Build

### Prerequisites (build machine only — not needed on target laptop)
- Python 3.11+ 
- .NET 8 SDK
- Inno Setup 6 (optional, for installer)

### Windows
```
build\build_windows.bat
```

### GitHub Actions
Push to `main` branch — the CI pipeline automatically builds and uploads the installer.

## Project Structure
```
WellnessFocus/
├── main.py                # Tray icon, timer engine, break triggers
├── config_manager.py      # JSON config + SHA-256 password + user ID
├── database.py            # SQLite init + CRUD
├── notifications.py       # Toast popups
├── overlay.py             # Full-screen break overlay
├── window_monitor.py      # Active window polling
├── web_tracker.py         # Browser history reader
├── admin_panel.py         # Settings + reports dashboard
├── windows_service/       # C# Windows Service (watchdog, blocking)
├── build/                 # Build scripts + CI
└── PLAN.md                # Full development plan
```
