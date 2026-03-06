# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TaskMaster is a Python desktop task management app using the Eisenhower Matrix for priority calculation. Single-file application (`taskmaster.py`, ~740 lines) with CustomTkinter UI, TinyDB for local JSON storage, and a built-in Pomodoro timer.

## Commands

```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install customtkinter tinydb tkcalendar

# Run
python3 taskmaster.py

# Build macOS (.app bundle + DMG)
pip install pyinstaller pillow
python3 build.py

# Build Windows (.exe)
python build_win.py
```

There are no automated tests or linting configured.

## Architecture

The entire application lives in `taskmaster.py`, organized into 8 sequential sections:

1. **Path Configuration** (lines 13-26) — Platform-specific app data dirs (macOS/Windows/Linux)
2. **UI Configuration** (lines 28-46) — CustomTkinter theme, font constants, global state variables
3. **Helper Functions** (lines 49-173) — Notifications, theme toggling, CSV export, priority calculation, category management
4. **Pomodoro Logic** (lines 175-335) — `PomodoroWindow` class (CTkToplevel), settings dialog
5. **Database & Setup** (lines 336-411) — TinyDB init, config persistence, first-run setup wizard
6. **Core UI Logic** (lines 413-499) — Task list filtering/sorting/rendering, checkbox toggle, deletion
7. **Popup Windows** (lines 501-629) — Calendar picker, add/edit task dialog
8. **Main App Render** (lines 631-740) — Root window, header, search bar, TreeView, event bindings

### Key Patterns

- **Procedural style** with global state (`db`, `tasks_table`, `checked_task_ids`, etc.). Only `PomodoroWindow` uses a class.
- **Priority is calculated, not user-selected**: `get_priority(impact, is_urgent)` maps Impact (High/Medium/Low) + Urgency (bool) to priorities: Critical, Planned, Important, Review, Delegate, Trivial.
- **Task list refreshes fully** on every change — `refresh_task_list()` clears and re-renders the TreeView with current filters (category, search text, hide-completed).
- **Tasks sort by priority order**: Critical → Important → Planned → Review → Delegate → Trivial.
- **Modal windows** use `grab_set()` + `attributes("-topmost", True)` + custom centering via `center_window_to_parent()`.

### Task Schema (TinyDB)

```python
{
    'title': str, 'impact': str, 'category': str, 'is_urgent': bool,
    'priority': str, 'deadline': str,  # YYYY-MM-DD
    'status': str,  # Pending | In Progress | Completed | On Hold
    'notes': str, 'created_at': str  # YYYY-MM-DD
}
```

### Config

Stored at platform-specific paths (e.g., `~/Library/Application Support/TaskMaster/todo_config.json` on macOS). Contains `{"db_path": "/path/to/tasks.json"}`.

## Platform Considerations

- macOS notifications use `osascript`; other platforms fall back to console output
- Build scripts: `build.py` (macOS with ad-hoc codesigning + DMG creation), `build_win.py` (Windows single .exe with icon conversion)
- Font: SF Pro Display throughout — may not render on non-Apple platforms
