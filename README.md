# TaskMaster ✅

<div align="center">
  <img src="logo.png" alt="TaskMaster Logo" width="120" height="120">
  <br>
  <b>A modern, distraction-free task manager built for focus.</b>
  <br><br>
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/UI-CustomTkinter-blue?style=flat" />
  <img src="https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-lightgrey?style=flat" />
</div>

---

## 📖 About
**TaskMaster** is a Python-based desktop application designed to help you organize tasks using the **Eisenhower Matrix** logic. Unlike standard to-do lists, TaskMaster automatically calculates the priority of your tasks ("Critical," "Planned," "Delegate") based on the Impact and Urgency you select.

It features a native Mac-like Dark Mode interface, local JSON storage (no cloud required), and a built-in Pomodoro timer to help you get work done.

## ✨ Key Features

* **🧠 Smart Priority Logic:** Automatically categorizes tasks based on Impact (High/Medium/Low) and Urgency.
* **🍅 Focus Mode:** Built-in **Pomodoro Timer** (25m Work / 5m Break) with a floating window that stays on top.
* **🎨 Modern Dark UI:** Built with `CustomTkinter` and SF Pro fonts for a sleek, native macOS feel.
* **📂 Categories & Filters:** Organize tasks by category (Work, Personal, etc.) and filter the view.
* **🙈 Hide Completed:** Toggle switch to instantly clean up your view by hiding finished tasks.
* **🔒 Local & Private:** All data is stored in a local JSON file. You choose the storage location on the first run.
* **📅 Calendar Integration:** Visual date picker for setting deadlines.

---

## 📸 Screenshots

*(Add screenshots of your app here. e.g. Main Window, Add Task Window, Focus Mode)*

| Main Dashboard | Focus Mode |
|:---:|:---:|
| <img src="assets/screenshot_main.png" width="400" alt="Main View"> | <img src="assets/screenshot_focus.png" width="400" alt="Focus View"> |

---

## 🚀 Installation

### For macOS Users
1.  Go to the [Releases](../../releases) page.
2.  Download `TaskMaster_Installer.dmg`.
3.  Drag the app to your **Applications** folder.
4.  **Note:** Since this app is not signed by Apple, you may need to Right-Click the app and select **Open** the first time you run it.

### For Windows Users
1.  Download `TaskMaster.exe` from Releases.
2.  Run the executable directly (No installation required).

---

## 🛠️ Development Setup

If you want to run the code source or contribute:

### 1. Clone the Repository
```bash
git clone [https://github.com/YOUR_USERNAME/TaskMaster.git](https://github.com/YOUR_USERNAME/TaskMaster.git)
cd TaskMaster
