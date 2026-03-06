import customtkinter as ctk 
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tinydb import TinyDB, Query
from tkcalendar import Calendar 
import datetime
import os
import json
import sys
import platform
import csv
import threading
import anthropic
from google import genai
from google.genai import types as genai_types
import ollama

# --- 1. PATH CONFIGURATION ---
APP_NAME = "TaskMaster"

if platform.system() == "Darwin":
    USER_DATA_DIR = os.path.join(os.path.expanduser("~"), "Library", "Application Support", APP_NAME)
elif platform.system() == "Windows":
    USER_DATA_DIR = os.path.join(os.getenv("APPDATA"), APP_NAME)
else:
    USER_DATA_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", APP_NAME)

if not os.path.exists(USER_DATA_DIR):
    os.makedirs(USER_DATA_DIR)

CONFIG_FILE = os.path.join(USER_DATA_DIR, 'todo_config.json')

# --- 2. UI CONFIGURATION ---
ctk.set_appearance_mode("Dark") 
ctk.set_default_color_theme("blue") 

FONT_MAIN = ("SF Pro Display", 13)
FONT_BOLD = ("SF Pro Display", 13, "bold")
FONT_HEADER = ("SF Pro Display", 26, "bold")
FONT_TITLE = ("SF Pro Display", 14, "bold")
FONT_ICON = ("SF Pro Display", 18, "bold")
FONT_TIMER = ("SF Pro Display", 60, "bold") 

# Global Vars
db = None
tasks_table = None
checked_task_ids = set()
filter_var = None  
filter_menu = None 
hide_completed_var = None 
search_var = None
CURRENT_DB_PATH = None
_last_db_mtime = None
DB_POLL_INTERVAL_MS = 30000  # 30 seconds
ANTHROPIC_API_KEY = None
GEMINI_API_KEY = None
AI_PROVIDER = "Claude"  # "Claude", "Gemini", or "Ollama"
OLLAMA_MODEL = "llama3.1:8b"
WORKING_HOURS = "9:00 AM - 6:00 PM"
PEAK_HOURS = "9:00 AM - 12:00 PM"
WIND_DOWN_HOURS = "3:00 PM - 5:00 PM"
goals_table = None

# --- 3. HELPER FUNCTIONS ---

def send_notification(title, message):
    # macOS Native Notification
    if platform.system() == "Darwin":
        try:
            # Escape double quotes in title and message to prevent shell syntax errors
            safe_title = title.replace('"', '\\"')
            safe_message = message.replace('"', '\\"')
            os.system(f"""osascript -e 'display notification "{safe_message}" with title "{safe_title}"'""")
        except:
            pass
    else:
        # Placeholder for other OSs if needed later
        print(f"Notification: {title} - {message}")

def apply_tree_theme(mode):
    style = ttk.Style()
    style.theme_use("default")
    
    if mode == "Dark":
        bg = "#2b2b2b"
        fg = "white"
        head_bg = "#1a1a1a"
        head_fg = "white"
        sel_bg = "#1f538d"
        odd = "#2b2b2b"
        even = "#333333"
    else:
        bg = "#ffffff"
        fg = "black"
        head_bg = "#e1e1e1"
        head_fg = "black"
        sel_bg = "#007AFF"
        odd = "#ffffff"
        even = "#f0f0f0"
    
    style.configure("Treeview", background=bg, foreground=fg, fieldbackground=bg, 
                    borderwidth=0, rowheight=40, font=("SF Pro Display", 13))
    
    # Configure heading with explicit dark background for dark mode
    style.configure("Treeview.Heading", 
                    background=head_bg, 
                    foreground=head_fg, 
                    relief="flat",
                    font=("SF Pro Display", 13, "bold"),
                    borderwidth=0)
    
    # Map states to ensure dark header stays dark
    style.map("Treeview.Heading", 
              background=[('active', head_bg), ('!active', head_bg)],
              foreground=[('active', head_fg), ('!active', head_fg)])
    
    style.map("Treeview", background=[('selected', sel_bg)], foreground=[('selected', 'white')])
    
    # Try updating tags if tree exists
    try:
        tree.tag_configure('oddrow', background=odd)
        tree.tag_configure('evenrow', background=even)
    except:
        pass

def toggle_theme():
    current_mode = ctk.get_appearance_mode()
    new_mode = "Light" if current_mode == "Dark" else "Dark"
    ctk.set_appearance_mode(new_mode)
    apply_tree_theme(new_mode)

def export_to_csv():
    if tasks_table is None: return
    
    file_path = filedialog.asksaveasfilename(
        title="Export Tasks to CSV",
        defaultextension=".csv",
        filetypes=[("CSV Files", "*.csv")],
        initialfile=f"tasks_export_{datetime.date.today()}.csv",
        parent=app
    )
    
    if file_path:
        try:
            all_tasks = tasks_table.all()
            with open(file_path, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                # Header
                writer.writerow(["ID", "Title", "Category", "Priority", "Status", "Deadline", "Impact", "Urgent", "Notes", "Created At"])
                # Rows
                for task in all_tasks:
                    writer.writerow([
                        task.doc_id,
                        task.get('title', ''),
                        task.get('category', ''),
                        task.get('priority', ''),
                        task.get('status', ''),
                        task.get('deadline', ''),
                        task.get('impact', ''),
                        task.get('is_urgent', ''),
                        task.get('notes', ''),
                        task.get('created_at', '')
                    ])
            messagebox.showinfo("Success", "Tasks exported successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {e}")

def center_window_to_parent(window, width, height):
    app.update_idletasks()
    main_x = app.winfo_x()
    main_y = app.winfo_y()
    main_w = app.winfo_width()
    main_h = app.winfo_height()
    x_pos = main_x + (main_w // 2) - (width // 2)
    y_pos = main_y + (main_h // 2) - (height // 2)
    window.geometry(f"{width}x{height}+{x_pos}+{y_pos}")

def get_priority(impact, is_urgent):
    if impact == "High": return "Critical" if is_urgent else "Planned"
    elif impact == "Medium": return "Important" if is_urgent else "Review"
    else: return "Delegate" if is_urgent else "Trivial"

def get_all_categories():
    if tasks_table is None: return ["All Categories"]
    cats = set(task.get('category', 'General') for task in tasks_table.all())
    cats.add("General") 
    sorted_cats = sorted(list(cats))
    return ["All Categories"] + sorted_cats

def _get_ollama_models():
    try:
        response = ollama.list()
        return [m.model for m in response.models] if response.models else []
    except Exception:
        return []

# --- 4. POMODORO LOGIC (UPDATED: CENTERED) ---

class PomodoroWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Focus Mode")
        
        # --- CENTERING LOGIC ---
        width = 300
        height = 250
        
        # Ensure parent geometry is up to date
        parent.update_idletasks()
        
        main_x = parent.winfo_x()
        main_y = parent.winfo_y()
        main_w = parent.winfo_width()
        main_h = parent.winfo_height()
        
        x_pos = main_x + (main_w // 2) - (width // 2)
        y_pos = main_y + (main_h // 2) - (height // 2)
        
        self.geometry(f"{width}x{height}+{x_pos}+{y_pos}")
        self.attributes("-topmost", True) 

        self.time_left = 25 * 60 
        self.running = False
        self.timer_id = None
        self.mode = "Work" 

        # UI
        self.lbl_mode = ctk.CTkLabel(self, text="🔥 Focus Time", font=FONT_TITLE, text_color="#FF3B30")
        self.lbl_mode.pack(pady=(20, 5))

        self.lbl_timer = ctk.CTkLabel(self, text="25:00", font=FONT_TIMER)
        self.lbl_timer.pack(pady=10)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10)

        self.btn_start = ctk.CTkButton(btn_frame, text="Start", width=80, command=self.toggle_timer, fg_color="#34C759", hover_color="#28a745")
        self.btn_start.pack(side="left", padx=5)

        self.btn_reset = ctk.CTkButton(btn_frame, text="Reset", width=80, command=self.reset_timer, fg_color="#FF3B30", hover_color="#d32f2f")
        self.btn_reset.pack(side="left", padx=5)

        self.btn_mode = ctk.CTkButton(self, text="Switch to Break (5m)", command=self.switch_mode, fg_color="transparent", border_width=1, text_color="white")
        self.btn_mode.pack(pady=10)

    def toggle_timer(self):
        if self.running:
            self.running = False
            self.btn_start.configure(text="Resume", fg_color="#34C759")
            if self.timer_id:
                self.after_cancel(self.timer_id)
        else:
            self.running = True
            self.btn_start.configure(text="Pause", fg_color="#FFCC00", text_color="black")
            self.countdown()

    def countdown(self):
        if self.running and self.time_left > 0:
            mins, secs = divmod(self.time_left, 60)
            self.lbl_timer.configure(text=f"{mins:02d}:{secs:02d}")
            self.time_left -= 1
            self.timer_id = self.after(1000, self.countdown)
        elif self.time_left == 0:
            self.running = False
            self.lbl_timer.configure(text="00:00")
            self.btn_start.configure(text="Start", fg_color="#34C759")
            
            msg = f"{self.mode} session finished!"
            send_notification("TaskMaster Focus", msg)
            
            # Bring window to front
            self.deiconify()
            self.lift()
            self.attributes("-topmost", True)
            
            tk.messagebox.showinfo("Timer", msg, parent=self)

    def reset_timer(self):
        self.running = False
        if self.timer_id: self.after_cancel(self.timer_id)
        self.btn_start.configure(text="Start", fg_color="#34C759")
        
        if self.mode == "Work":
            self.time_left = 25 * 60
            self.lbl_timer.configure(text="25:00")
        else:
            self.time_left = 5 * 60
            self.lbl_timer.configure(text="05:00")

    def switch_mode(self):
        self.reset_timer()
        if self.mode == "Work":
            self.mode = "Break"
            self.lbl_mode.configure(text="☕️ Take a Break", text_color="#34C759")
            self.btn_mode.configure(text="Switch to Focus (25m)")
            self.time_left = 5 * 60
            self.lbl_timer.configure(text="05:00")
        else:
            self.mode = "Work"
            self.lbl_mode.configure(text="🔥 Focus Time", text_color="#FF3B30")
            self.btn_mode.configure(text="Switch to Break (5m)")
            self.time_left = 25 * 60
            self.lbl_timer.configure(text="25:00")

def open_pomodoro():
    PomodoroWindow(app)
    
def open_settings():
    global ANTHROPIC_API_KEY, GEMINI_API_KEY, AI_PROVIDER, OLLAMA_MODEL
    set_win = ctk.CTkToplevel(app)
    set_win.title("Settings")
    center_window_to_parent(set_win, 500, 700)
    set_win.grab_set()
    set_win.attributes("-topmost", True)

    scrollable = ctk.CTkScrollableFrame(set_win)
    scrollable.pack(fill="both", expand=True, padx=0, pady=0)

    ctk.CTkLabel(scrollable, text="Settings", font=FONT_HEADER).pack(pady=(20, 10))

    # Database Path
    ctk.CTkLabel(scrollable, text="Database Path:", font=FONT_TITLE).pack(pady=(10, 0))

    path_frame = ctk.CTkFrame(scrollable, fg_color="transparent")
    path_frame.pack(pady=5, padx=20, fill="x")

    entry_path = ctk.CTkEntry(path_frame, font=FONT_MAIN)
    if CURRENT_DB_PATH:
        entry_path.insert(0, CURRENT_DB_PATH)
    else:
        entry_path.insert(0, "Not Loaded")
    entry_path.configure(state="readonly")
    entry_path.pack(side="left", fill="x", expand=True, padx=(0, 10))

    def change_db():
        new_path = filedialog.asksaveasfilename(
            title="Select or Create Database File",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json")],
            initialfile="my_tasks.json",
            parent=set_win
        )
        if new_path:
            save_config_and_start(new_path)
            entry_path.configure(state="normal")
            entry_path.delete(0, "end")
            entry_path.insert(0, new_path)
            entry_path.configure(state="readonly")
            messagebox.showinfo("Success", "Database switched successfully!", parent=set_win)

    btn_change = ctk.CTkButton(path_frame, text="Change", width=80, command=change_db)
    btn_change.pack(side="right")

    # AI Provider Selector
    ctk.CTkLabel(scrollable, text="AI Provider:", font=FONT_TITLE).pack(pady=(15, 0))

    def on_provider_change(value):
        global AI_PROVIDER
        AI_PROVIDER = value
        _save_all_settings()

    provider_seg = ctk.CTkSegmentedButton(scrollable, values=["Claude", "Gemini", "Ollama"],
                                           command=on_provider_change, font=FONT_BOLD)
    provider_seg.set(AI_PROVIDER)
    provider_seg.pack(pady=5, padx=20)

    # Anthropic API Key
    ctk.CTkLabel(scrollable, text="Anthropic API Key:", font=FONT_TITLE).pack(pady=(15, 0))

    api_frame = ctk.CTkFrame(scrollable, fg_color="transparent")
    api_frame.pack(pady=5, padx=20, fill="x")

    entry_api = ctk.CTkEntry(api_frame, font=FONT_MAIN, show="*", placeholder_text="sk-ant-...")
    if ANTHROPIC_API_KEY:
        entry_api.insert(0, ANTHROPIC_API_KEY)
    entry_api.pack(side="left", fill="x", expand=True, padx=(0, 10))

    def save_anthropic_key():
        global ANTHROPIC_API_KEY
        key = entry_api.get().strip()
        ANTHROPIC_API_KEY = key if key else None
        _save_all_settings()
        messagebox.showinfo("Success", "Anthropic API key saved!", parent=set_win)

    ctk.CTkButton(api_frame, text="Save Key", width=80, command=save_anthropic_key,
                   fg_color="#5856D6", hover_color="#4e4cb8").pack(side="right")

    # Gemini API Key
    ctk.CTkLabel(scrollable, text="Gemini API Key:", font=FONT_TITLE).pack(pady=(15, 0))

    gemini_frame = ctk.CTkFrame(scrollable, fg_color="transparent")
    gemini_frame.pack(pady=5, padx=20, fill="x")

    entry_gemini = ctk.CTkEntry(gemini_frame, font=FONT_MAIN, show="*", placeholder_text="AIza...")
    if GEMINI_API_KEY:
        entry_gemini.insert(0, GEMINI_API_KEY)
    entry_gemini.pack(side="left", fill="x", expand=True, padx=(0, 10))

    def save_gemini_key():
        global GEMINI_API_KEY
        key = entry_gemini.get().strip()
        GEMINI_API_KEY = key if key else None
        _save_all_settings()
        messagebox.showinfo("Success", "Gemini API key saved!", parent=set_win)

    ctk.CTkButton(gemini_frame, text="Save Key", width=80, command=save_gemini_key,
                   fg_color="#34A853", hover_color="#2d8f47").pack(side="right")

    # Ollama Model Selector
    ctk.CTkLabel(scrollable, text="Ollama Model:", font=FONT_TITLE).pack(pady=(15, 0))

    ollama_frame = ctk.CTkFrame(scrollable, fg_color="transparent")
    ollama_frame.pack(pady=5, padx=20, fill="x")

    available_models = _get_ollama_models()
    ollama_combo = ctk.CTkComboBox(ollama_frame, values=available_models, font=FONT_MAIN, height=35)
    ollama_combo.set(OLLAMA_MODEL if OLLAMA_MODEL in available_models else (available_models[0] if available_models else ""))
    ollama_combo.pack(side="left", fill="x", expand=True, padx=(0, 10))

    def save_ollama_model():
        global OLLAMA_MODEL
        OLLAMA_MODEL = ollama_combo.get().strip()
        _save_all_settings()
        messagebox.showinfo("Success", f"Ollama model set to '{OLLAMA_MODEL}'.", parent=set_win)

    ctk.CTkButton(ollama_frame, text="Save", width=80, command=save_ollama_model,
                   fg_color="#FF9500", hover_color="#e08600").pack(side="right")

    def refresh_ollama_list():
        models = _get_ollama_models()
        ollama_combo.configure(values=models)
        if models:
            ollama_combo.set(models[0])

    ctk.CTkButton(scrollable, text="Refresh Ollama Models", command=refresh_ollama_list,
                   fg_color="#FF9500", hover_color="#e08600", font=FONT_BOLD, width=180).pack(pady=(5, 0))

    # Productivity Schedule
    ctk.CTkLabel(scrollable, text="Productivity Schedule:", font=FONT_TITLE).pack(pady=(20, 0))

    ctk.CTkLabel(scrollable, text="Your overall working window",
                 font=FONT_MAIN, text_color="#A0A0A0").pack(pady=(5, 2))
    work_frame = ctk.CTkFrame(scrollable, fg_color="transparent")
    work_frame.pack(pady=5, padx=20, fill="x")
    ctk.CTkLabel(work_frame, text="Working Hours:", font=FONT_MAIN, width=130, anchor="w").pack(side="left")
    entry_work = ctk.CTkEntry(work_frame, font=FONT_MAIN, placeholder_text="e.g. 9:00 AM - 6:00 PM")
    entry_work.insert(0, WORKING_HOURS)
    entry_work.pack(side="left", fill="x", expand=True)

    ctk.CTkLabel(scrollable, text="High-focus blocks (comma-separate multiple)",
                 font=FONT_MAIN, text_color="#A0A0A0").pack(pady=(5, 2))
    peak_frame = ctk.CTkFrame(scrollable, fg_color="transparent")
    peak_frame.pack(pady=5, padx=20, fill="x")
    ctk.CTkLabel(peak_frame, text="Peak Hours:", font=FONT_MAIN, width=130, anchor="w").pack(side="left")
    entry_peak = ctk.CTkEntry(peak_frame, font=FONT_MAIN, placeholder_text="e.g. 9 AM - 11 AM, 2 PM - 3 PM")
    entry_peak.insert(0, PEAK_HOURS)
    entry_peak.pack(side="left", fill="x", expand=True)

    ctk.CTkLabel(scrollable, text="Lower energy periods for lighter tasks",
                 font=FONT_MAIN, text_color="#A0A0A0").pack(pady=(5, 2))
    wind_frame = ctk.CTkFrame(scrollable, fg_color="transparent")
    wind_frame.pack(pady=5, padx=20, fill="x")
    ctk.CTkLabel(wind_frame, text="Wind-Down Hours:", font=FONT_MAIN, width=130, anchor="w").pack(side="left")
    entry_wind = ctk.CTkEntry(wind_frame, font=FONT_MAIN, placeholder_text="e.g. 3:00 PM - 5:00 PM")
    entry_wind.insert(0, WIND_DOWN_HOURS)
    entry_wind.pack(side="left", fill="x", expand=True)

    def save_schedule():
        global WORKING_HOURS, PEAK_HOURS, WIND_DOWN_HOURS
        WORKING_HOURS = entry_work.get().strip() or "9:00 AM - 6:00 PM"
        PEAK_HOURS = entry_peak.get().strip() or "9:00 AM - 12:00 PM"
        WIND_DOWN_HOURS = entry_wind.get().strip() or "3:00 PM - 5:00 PM"
        _save_all_settings()
        messagebox.showinfo("Success", "Productivity schedule saved!", parent=set_win)

    ctk.CTkButton(scrollable, text="Save Schedule", command=save_schedule,
                   fg_color="#007AFF", hover_color="#0062cc", font=FONT_BOLD, width=150).pack(pady=(5, 0))

    # Theme Toggle
    ctk.CTkLabel(scrollable, text="Appearance:", font=FONT_TITLE).pack(pady=(20, 0))
    btn_theme = ctk.CTkButton(scrollable, text="Toggle Light/Dark Mode", command=toggle_theme,
                              fg_color="#555555", hover_color="#666666", font=FONT_BOLD)
    btn_theme.pack(pady=10)

    ctk.CTkButton(scrollable, text="Close", command=set_win.destroy, fg_color="#FF3B30", hover_color="#d32f2f").pack(pady=(20, 20))

# --- 5. DATABASE & SETUP ---

def check_deadlines():
    if tasks_table is None: return
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    Task = Query()
    due_tasks = tasks_table.search(Task.deadline == today)
    due_tasks = [t for t in due_tasks if t.get('status') != 'Completed']
    
    if due_tasks:
        count = len(due_tasks)
        send_notification("TaskMaster", f"You have {count} task(s) due today!")

def initialize_db(path):
    global db, tasks_table, goals_table, CURRENT_DB_PATH, _last_db_mtime
    try:
        if db is not None:
            db.close()
        db = TinyDB(path)
        tasks_table = db.table('tasks')
        goals_table = db.table('category_goals')
        CURRENT_DB_PATH = path
        _last_db_mtime = _get_db_mtime()
        refresh_task_list()
        update_filter_options()
        app.after(2000, check_deadlines)
        _start_db_poll()
    except Exception as e:
        messagebox.showerror("Error", f"Could not load database: {e}")

def _get_db_mtime():
    try:
        return os.path.getmtime(CURRENT_DB_PATH) if CURRENT_DB_PATH else None
    except OSError:
        return None

_db_poll_id = None

def _start_db_poll():
    global _db_poll_id
    if _db_poll_id is not None:
        app.after_cancel(_db_poll_id)
    _db_poll_id = app.after(DB_POLL_INTERVAL_MS, _poll_db_for_changes)

def _poll_db_for_changes():
    global _last_db_mtime, db, tasks_table, goals_table, _db_poll_id
    if CURRENT_DB_PATH is None:
        _db_poll_id = app.after(DB_POLL_INTERVAL_MS, _poll_db_for_changes)
        return
    current_mtime = _get_db_mtime()
    if current_mtime is not None and current_mtime != _last_db_mtime:
        _last_db_mtime = current_mtime
        try:
            if db is not None:
                db.close()
            db = TinyDB(CURRENT_DB_PATH)
            tasks_table = db.table('tasks')
            goals_table = db.table('category_goals')
            refresh_task_list()
            update_filter_options()
        except Exception:
            pass
    _db_poll_id = app.after(DB_POLL_INTERVAL_MS, _poll_db_for_changes)

def _save_all_settings():
    config = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
        except:
            pass
    config.pop('api_key', None)
    if ANTHROPIC_API_KEY:
        config['anthropic_api_key'] = ANTHROPIC_API_KEY
    else:
        config.pop('anthropic_api_key', None)
    if GEMINI_API_KEY:
        config['gemini_api_key'] = GEMINI_API_KEY
    else:
        config.pop('gemini_api_key', None)
    config['ai_provider'] = AI_PROVIDER
    config['ollama_model'] = OLLAMA_MODEL
    config['working_hours'] = WORKING_HOURS
    config['peak_hours'] = PEAK_HOURS
    config['wind_down_hours'] = WIND_DOWN_HOURS
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def save_config_and_start(path):
    config = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
        except:
            pass
    config['db_path'] = path
    config.pop('api_key', None)
    if ANTHROPIC_API_KEY:
        config['anthropic_api_key'] = ANTHROPIC_API_KEY
    if GEMINI_API_KEY:
        config['gemini_api_key'] = GEMINI_API_KEY
    config['ai_provider'] = AI_PROVIDER
    config['ollama_model'] = OLLAMA_MODEL
    config['working_hours'] = WORKING_HOURS
    config['peak_hours'] = PEAK_HOURS
    config['wind_down_hours'] = WIND_DOWN_HOURS
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)
    initialize_db(path)

def open_setup_wizard():
    setup_win = ctk.CTkToplevel(app)
    setup_win.title("Welcome")
    center_window_to_parent(setup_win, 400, 250)
    setup_win.grab_set()
    setup_win.attributes("-topmost", True)
    
    def on_close():
        app.destroy()
        sys.exit()
    setup_win.protocol("WM_DELETE_WINDOW", on_close)

    ctk.CTkLabel(setup_win, text="Welcome to TaskMaster", font=FONT_HEADER).pack(pady=(30, 10))
    ctk.CTkLabel(setup_win, text="To get started, please create or select\na location to save your tasks.", 
                 font=FONT_MAIN, text_color="#A0A0A0").pack(pady=(0, 20))

    def browse_file():
        setup_win.withdraw() 
        file_path = filedialog.asksaveasfilename(
            title="Create Database File",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json")],
            initialfile="my_tasks.json",
            parent=app
        )
        setup_win.deiconify() 
        if file_path:
            save_config_and_start(file_path)
            setup_win.destroy()

    ctk.CTkButton(setup_win, text="Select Save Location", command=browse_file, 
                  height=45, font=FONT_BOLD).pack(pady=10, padx=40, fill="x")

def check_config_on_startup():
    global ANTHROPIC_API_KEY, GEMINI_API_KEY, AI_PROVIDER, OLLAMA_MODEL
    global WORKING_HOURS, PEAK_HOURS, WIND_DOWN_HOURS
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                path = config.get('db_path', '')
                ANTHROPIC_API_KEY = config.get('anthropic_api_key', None)
                GEMINI_API_KEY = config.get('gemini_api_key', None)
                AI_PROVIDER = config.get('ai_provider', 'Claude')
                OLLAMA_MODEL = config.get('ollama_model', 'llama3.1:8b')
                WORKING_HOURS = config.get('working_hours', '9:00 AM - 6:00 PM')
                PEAK_HOURS = config.get('peak_hours', '9:00 AM - 12:00 PM')
                WIND_DOWN_HOURS = config.get('wind_down_hours', '3:00 PM - 5:00 PM')
                # Backward compat: migrate old api_key
                if not ANTHROPIC_API_KEY and config.get('api_key'):
                    ANTHROPIC_API_KEY = config['api_key']
                    _save_all_settings()
                if path:
                    initialize_db(path)
                    return
        except:
            pass
    open_setup_wizard()

# --- 6. CORE UI LOGIC ---

def update_filter_options():
    if filter_menu is None: return
    opts = get_all_categories()
    filter_menu.configure(values=opts)
    if filter_var.get() not in opts:
        filter_var.set("All Categories")

def refresh_task_list(event=None):
    if tasks_table is None: return

    checked_task_ids.clear()
    for item in tree.get_children():
        tree.delete(item)

    all_tasks = tasks_table.all()
    
    # 1. Category Filter
    current_filter = filter_var.get()
    if current_filter != "All Categories":
        all_tasks = [t for t in all_tasks if t.get('category', 'General') == current_filter]

    # 2. Hide Completed Filter
    if hide_completed_var.get(): 
        all_tasks = [t for t in all_tasks if t.get('status') != 'Completed']

    # 3. Search Filter
    search_txt = search_var.get().lower()
    if search_txt:
        all_tasks = [t for t in all_tasks if search_txt in t['title'].lower()]

    # Sort Logic
    priority_order = {"Critical": 0, "Important": 1, "Planned": 2, "Review": 3, "Delegate": 4, "Trivial": 5}
    all_tasks.sort(key=lambda x: priority_order.get(x['priority'], 99))

    count = 0
    for task in all_tasks:
        row_id = task.doc_id
        tag = 'evenrow' if count % 2 == 0 else 'oddrow'
        cat_display = task.get('category', 'General')

        tree.insert("", "end", iid=row_id, values=(
            "☐", 
            task['title'], 
            cat_display,
            task['priority'], 
            task.get('status', 'Pending'), 
            task['deadline']
        ), tags=(tag,))
        count += 1
    
    if filter_menu:
        filter_menu.configure(values=get_all_categories())

def delete_selected_tasks():
    if tasks_table is None: return
    if not checked_task_ids:
        messagebox.showwarning("No Selection", "Please check the box next to tasks to delete.")
        return

    confirm = messagebox.askyesno("Confirm Delete", f"Delete {len(checked_task_ids)} selected task(s)?")
    if confirm:
        tasks_table.remove(doc_ids=list(checked_task_ids))
        refresh_task_list()
        update_filter_options() 

def toggle_check(event):
    region = tree.identify("region", event.x, event.y)
    if region != "cell": return
    col = tree.identify_column(event.x)
    row_id = tree.identify_row(event.y)
    
    if col == "#1" and row_id:
        current_vals = list(tree.item(row_id, "values"))
        sym = current_vals[0]
        doc_id = int(row_id)

        if sym == "☐":
            current_vals[0] = "☑"
            checked_task_ids.add(doc_id)
        else:
            current_vals[0] = "☐"
            if doc_id in checked_task_ids: checked_task_ids.remove(doc_id)
        
        tree.item(row_id, values=current_vals)
        return "break" 

# --- 7. POPUP WINDOWS ---

def open_category_goal_window():
    selected_cat = filter_var.get()
    if selected_cat == "All Categories":
        messagebox.showinfo("Select Category",
                            "Please select a specific category from the filter dropdown first.",
                            parent=app)
        return
    if goals_table is None:
        return

    goal_win = ctk.CTkToplevel(app)
    goal_win.title(f"Goal — {selected_cat}")
    center_window_to_parent(goal_win, 480, 320)
    goal_win.grab_set()
    goal_win.attributes("-topmost", True)

    ctk.CTkLabel(goal_win, text=f"{selected_cat} — Long-Term Goal",
                 font=FONT_HEADER).pack(pady=(20, 5))
    ctk.CTkLabel(goal_win, text="Describe the overarching vision or objective for this category.",
                 font=FONT_MAIN, text_color="#A0A0A0").pack(pady=(0, 10))

    txt_goal = ctk.CTkTextbox(goal_win, font=FONT_MAIN, height=120, wrap="word")
    txt_goal.pack(fill="x", padx=20, pady=(0, 10))

    existing = goals_table.get(Query().category == selected_cat)
    if existing and existing.get('goal', ''):
        txt_goal.insert("1.0", existing['goal'])

    def save_goal():
        goal_text = txt_goal.get("1.0", "end-1c").strip()
        if existing:
            goals_table.update({'goal': goal_text}, Query().category == selected_cat)
        else:
            goals_table.insert({'category': selected_cat, 'goal': goal_text})
        goal_win.destroy()

    btn_frame = ctk.CTkFrame(goal_win, fg_color="transparent")
    btn_frame.pack(fill="x", padx=20, pady=(0, 20))
    ctk.CTkButton(btn_frame, text="Save", command=save_goal, height=40,
                   font=FONT_BOLD, fg_color="#34C759", hover_color="#28a745").pack(side="left", expand=True, fill="x", padx=(0, 5))
    ctk.CTkButton(btn_frame, text="Cancel", command=goal_win.destroy, height=40,
                   font=FONT_BOLD, fg_color="#FF3B30", hover_color="#d32f2f").pack(side="right", expand=True, fill="x", padx=(5, 0))

def open_calendar_picker(parent_window, set_date_callback):
    cal_win = ctk.CTkToplevel(parent_window)
    cal_win.title("Pick Date")
    center_window_to_parent(cal_win, 300, 280)
    cal_win.grab_set() 
    cal_win.attributes("-topmost", True)

    cal = Calendar(cal_win, selectmode='day', date_pattern='y-mm-dd', 
                   background="black", foreground="white", headersbackground="#1f538d",
                   font=("SF Pro Display", 10))
    cal.pack(pady=20, padx=20, fill="both", expand=True)

    def on_select():
        set_date_callback(cal.get_date())
        cal_win.destroy()

    ctk.CTkButton(cal_win, text="Confirm", command=on_select, font=FONT_BOLD).pack(pady=(0, 20), padx=20)

def open_task_window(task_id=None, task_data=None):
    if tasks_table is None: return 
    is_edit = task_id is not None
    win = ctk.CTkToplevel(app)
    win.title("Edit Task" if is_edit else "Add New Task")
    center_window_to_parent(win, 420, 650) 
    win.grab_set() 
    win.attributes("-topmost", True)
    
    date_var = tk.StringVar(value=datetime.datetime.now().strftime("%Y-%m-%d"))

    def save_or_update():
        title = entry_title.get()
        impact = combo_impact.get()
        category = combo_category.get() 
        is_urgent = switch_urgent.get() == 1
        deadline = date_var.get()
        status = combo_status.get() 
        notes = txt_notes.get("1.0", "end-1c")

        if not title: return
        if not category.strip(): category = "General"

        calculated_priority = get_priority(impact, is_urgent)
        record = {
            'title': title, 'impact': impact, 'category': category, 
            'is_urgent': is_urgent, 'priority': calculated_priority, 'deadline': deadline,
            'status': status,
            'notes': notes,
            'created_at': datetime.datetime.now().strftime("%Y-%m-%d") if not is_edit else task_data['created_at']
        }

        if is_edit:
            tasks_table.update(record, doc_ids=[task_id])
        else:
            tasks_table.insert(record)

        refresh_task_list()
        update_filter_options()
        win.destroy()

    frame = ctk.CTkFrame(win, corner_radius=15)
    frame.pack(fill="both", expand=True, padx=20, pady=20)

    # 1. Title
    ctk.CTkLabel(frame, text="Task Description", font=FONT_TITLE, text_color="#A0A0A0").pack(anchor="w", padx=15, pady=(5,5))
    entry_title = ctk.CTkEntry(frame, placeholder_text="Details...", font=FONT_MAIN, height=35)
    entry_title.pack(fill="x", padx=15, pady=(0, 10))

    # 2. Notes
    ctk.CTkLabel(frame, text="Notes", font=FONT_TITLE, text_color="#A0A0A0").pack(anchor="w", padx=15, pady=(0,5))
    txt_notes = ctk.CTkTextbox(frame, font=FONT_MAIN, height=80)
    txt_notes.pack(fill="x", padx=15, pady=(0, 10))

    # 3. Category
    ctk.CTkLabel(frame, text="Category", font=FONT_TITLE, text_color="#A0A0A0").pack(anchor="w", padx=15, pady=(0,5))
    existing_cats = get_all_categories()
    if "All Categories" in existing_cats: existing_cats.remove("All Categories")
    defaults = ["Work", "Personal", "Health", "Finance"]
    combo_values = sorted(list(set(defaults + existing_cats)))
    
    combo_category = ctk.CTkComboBox(frame, values=combo_values, font=FONT_MAIN, height=35)
    combo_category.set("General") 
    combo_category.pack(fill="x", padx=15, pady=(0, 10))

    # 4. Status
    ctk.CTkLabel(frame, text="Status", font=FONT_TITLE, text_color="#A0A0A0").pack(anchor="w", padx=15, pady=(0,5))
    combo_status = ctk.CTkComboBox(frame, values=["Pending", "In Progress", "Completed", "On Hold"], state="readonly", font=FONT_MAIN, height=35)
    combo_status.set("Pending")
    combo_status.pack(fill="x", padx=15, pady=(0, 10))

    # 5. Impact
    ctk.CTkLabel(frame, text="Impact", font=FONT_TITLE, text_color="#A0A0A0").pack(anchor="w", padx=15, pady=(0,5))
    combo_impact = ctk.CTkComboBox(frame, values=["High", "Medium", "Low"], state="readonly", font=FONT_MAIN, height=35)
    combo_impact.set("High")
    combo_impact.pack(fill="x", padx=15, pady=(0, 10))

    # 6. Urgent
    switch_urgent = ctk.CTkSwitch(frame, text="Mark as Urgent", font=FONT_MAIN)
    switch_urgent.pack(anchor="w", padx=15, pady=(0, 10))

    # 7. Deadline
    ctk.CTkLabel(frame, text="Deadline", font=FONT_TITLE, text_color="#A0A0A0").pack(anchor="w", padx=15, pady=(0,5))
    date_frame = ctk.CTkFrame(frame, fg_color="transparent")
    date_frame.pack(fill="x", padx=15, pady=(0, 15))
    ctk.CTkLabel(date_frame, textvariable=date_var, font=("SF Pro Display", 16), width=100, anchor="w").pack(side="left")
    ctk.CTkButton(date_frame, text="Select", width=80, 
                  command=lambda: open_calendar_picker(win, lambda d: date_var.set(d))).pack(side="right")

    if is_edit and task_data:
        entry_title.insert(0, task_data['title'])
        if task_data.get('notes'):
            txt_notes.insert("1.0", task_data['notes'])
        combo_impact.set(task_data['impact'])
        combo_category.set(task_data.get('category', 'General'))
        combo_status.set(task_data.get('status', 'Pending'))
        if task_data.get('is_urgent', False): switch_urgent.select()
        date_var.set(task_data['deadline'])

    ctk.CTkButton(frame, text="Update" if is_edit else "Save", command=save_or_update, height=45, font=FONT_BOLD).pack(fill="x", padx=15, pady=10)

def on_double_click(event):
    if tree.identify_column(event.x) == "#1": return
    sel = tree.selection()
    if not sel: return
    doc_id = int(sel[0])
    task_data = tasks_table.get(doc_id=doc_id)
    if task_data: open_task_window(task_id=doc_id, task_data=task_data)

# --- 8. PLAN MY DAY (CLAUDE AI) ---

PLAN_CHATS_DIR = os.path.join(USER_DATA_DIR, "plan_chats")
if not os.path.exists(PLAN_CHATS_DIR):
    os.makedirs(PLAN_CHATS_DIR)

class PlanChatWindow(ctk.CTkToplevel):
    def __init__(self, parent, system_prompt, messages):
        super().__init__(parent)
        self.title("Plan My Day")
        width, height = 650, 600
        center_window_to_parent(self, width, height)

        self.system_prompt = system_prompt
        self.messages = list(messages)
        self.chat_file = os.path.join(
            PLAN_CHATS_DIR,
            f"plan_{datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json"
        )

        ctk.CTkLabel(self, text="Plan My Day", font=FONT_HEADER).pack(pady=(15, 5))

        self.chat_display = ctk.CTkTextbox(self, font=FONT_MAIN, wrap="word", state="disabled")
        self.chat_display.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.pack(fill="x", padx=15, pady=(0, 10))

        self.entry = ctk.CTkEntry(input_frame, font=FONT_MAIN,
                                   placeholder_text="e.g. Add a 1-hour lunch break at 12:30...")
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry.bind("<Return>", lambda e: self._send_message())

        self.btn_send = ctk.CTkButton(input_frame, text="Send", width=80,
                                       command=self._send_message, font=FONT_BOLD,
                                       fg_color="#007AFF", hover_color="#0062cc")
        self.btn_send.pack(side="right")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(0, 15))
        ctk.CTkButton(btn_frame, text="Close", command=self.destroy,
                       fg_color="#FF3B30", hover_color="#d32f2f", font=FONT_BOLD,
                       width=100).pack(side="right")

        for msg in self.messages:
            self._append_to_display(msg["role"], msg["content"])

        self._save_chat()

    def _append_to_display(self, role, content):
        self.chat_display.configure(state="normal")
        if self.chat_display.get("1.0", "end-1c"):
            self.chat_display.insert("end", "\n\n")
        label = "You" if role == "user" else "Planner"
        self.chat_display.insert("end", f"--- {label} ---\n")
        self.chat_display.insert("end", content)
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")

    def _send_message(self):
        user_text = self.entry.get().strip()
        if not user_text:
            return
        self.entry.delete(0, "end")
        self.messages.append({"role": "user", "content": user_text})
        self._append_to_display("user", user_text)

        self.btn_send.configure(state="disabled", text="...")
        self.entry.configure(state="disabled")

        def call_api():
            try:
                response_text = _call_ai(self.system_prompt, self.messages)
                self.after(0, lambda: self._on_response(response_text))
            except Exception as e:
                self.after(0, lambda: self._on_error(str(e)))

        threading.Thread(target=call_api, daemon=True).start()

    def _on_response(self, response_text):
        self.messages.append({"role": "assistant", "content": response_text})
        self._append_to_display("assistant", response_text)
        self.btn_send.configure(state="normal", text="Send")
        self.entry.configure(state="normal")
        self.entry.focus()
        self._save_chat()

    def _on_error(self, error_msg):
        self.messages.pop()
        self._append_to_display("assistant", f"[Error: {error_msg}]")
        self.btn_send.configure(state="normal", text="Send")
        self.entry.configure(state="normal")

    def _save_chat(self):
        data = {
            "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "provider": AI_PROVIDER,
            "model": OLLAMA_MODEL if AI_PROVIDER == "Ollama" else AI_PROVIDER,
            "messages": self.messages,
        }
        try:
            with open(self.chat_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

def _call_claude(system_prompt, messages):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=system_prompt,
        messages=messages,
    )
    return response.content[0].text

def _call_gemini(system_prompt, messages):
    client = genai.Client(api_key=GEMINI_API_KEY)
    contents = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(genai_types.Content(role=role, parts=[genai_types.Part(text=msg["content"])]))
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=contents,
        config=genai_types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=2048,
        ),
    )
    return response.text

def _call_ollama(system_prompt, messages):
    ollama_messages = [{"role": "system", "content": system_prompt}] + messages
    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=ollama_messages,
    )
    return response["message"]["content"]

def _call_ai(system_prompt, messages):
    if AI_PROVIDER == "Ollama":
        return _call_ollama(system_prompt, messages)
    elif AI_PROVIDER == "Gemini":
        return _call_gemini(system_prompt, messages)
    else:
        return _call_claude(system_prompt, messages)

def plan_my_day():
    if AI_PROVIDER == "Claude" and not ANTHROPIC_API_KEY:
        messagebox.showwarning("API Key Missing",
                               "Please set your Anthropic API key in Settings first.",
                               parent=app)
        return
    if AI_PROVIDER == "Gemini" and not GEMINI_API_KEY:
        messagebox.showwarning("API Key Missing",
                               "Please set your Gemini API key in Settings first.",
                               parent=app)
        return
    if AI_PROVIDER == "Ollama" and not OLLAMA_MODEL:
        messagebox.showwarning("No Model",
                               "Please select an Ollama model in Settings first.",
                               parent=app)
        return

    if tasks_table is None:
        messagebox.showwarning("No Database", "Please set up a database first.",
                               parent=app)
        return

    all_tasks = tasks_table.all()
    incomplete = [t for t in all_tasks if t.get('status') != 'Completed']

    if not incomplete:
        messagebox.showinfo("No Tasks", "You have no incomplete tasks to plan around.",
                            parent=app)
        return

    # Build task list text
    task_lines = []
    for t in incomplete:
        line = (f"- {t['title']} | Priority: {t['priority']} | Status: {t.get('status', 'Pending')} "
                f"| Category: {t.get('category', 'General')} | Deadline: {t['deadline']}")
        if t.get('notes', '').strip():
            line += f" | Notes: {t['notes'].strip()}"
        task_lines.append(line)
    task_text = "\n".join(task_lines)

    today = datetime.datetime.now().strftime("%A, %B %d, %Y")

    # Collect per-category goals for categories present in incomplete tasks
    goals_section = ""
    if goals_table is not None:
        categories_in_play = set(t.get('category', 'General') for t in incomplete)
        goal_lines = []
        for cat in sorted(categories_in_play):
            goal_doc = goals_table.get(Query().category == cat)
            if goal_doc and goal_doc.get('goal', '').strip():
                goal_lines.append(f"- {cat}: {goal_doc['goal']}")
        if goal_lines:
            goals_section = "\n\nLong-term goals by category:\n" + "\n".join(goal_lines)

    system_prompt = (
        "You are a productivity planner. The user will give you their current task list. "
        "Create a practical, time-blocked daily plan for today. Prioritize by deadline and priority level.\n\n"
        "STRICT RULES:\n"
        "1. NEVER schedule any task outside the user's Working Hours. This is a hard constraint.\n"
        "2. Schedule demanding, high-priority tasks during the user's Peak Hours.\n"
        "3. Reserve lighter tasks, reviews, and admin work for Wind-Down Hours.\n"
        "4. Align daily task prioritization with the user's long-term goals for each category.\n"
        "5. Do NOT assume breaks; only include breaks if the user requests them.\n"
        "6. Reference actual task titles in your plan.\n\n"
        "Format the plan as follows:\n"
        "- Start with a one-line summary of the day\n"
        "- Use time blocks in the format 'HH:MM AM - HH:MM AM/PM: Task Title'\n"
        "- Group tasks under headers: MORNING, AFTERNOON, EVENING\n"
        "- End with a 'KEY FOCUS AREAS' bullet list\n\n"
        "When the user sends follow-up messages, revise the plan accordingly and output the full updated plan."
    )
    user_message = (
        f"Today is {today}.\n\n"
        f"My Working Hours: {WORKING_HOURS}\n"
        f"My Peak Hours (high focus): {PEAK_HOURS}\n"
        f"My Wind-Down Hours (lower energy): {WIND_DOWN_HOURS}\n\n"
        f"Here are my current tasks:\n\n{task_text}"
        f"{goals_section}\n\n"
        "Please create a daily plan for me. "
        f"IMPORTANT: All tasks MUST be scheduled between {WORKING_HOURS} only. "
        "Do NOT schedule anything outside these working hours."
    )

    # Show loading window
    loading_win = ctk.CTkToplevel(app)
    loading_win.title("Planning...")
    center_window_to_parent(loading_win, 300, 120)
    provider_label = f"{AI_PROVIDER} ({OLLAMA_MODEL})" if AI_PROVIDER == "Ollama" else AI_PROVIDER
    ctk.CTkLabel(loading_win, text=f"Generating plan via {provider_label}...", font=FONT_TITLE).pack(pady=(30, 5))
    ctk.CTkLabel(loading_win, text="This may take a few seconds.", font=FONT_MAIN, text_color="#A0A0A0").pack()

    initial_messages = [{"role": "user", "content": user_message}]

    def call_api():
        try:
            plan_text = _call_ai(system_prompt, initial_messages)
            app.after(0, lambda: on_success(plan_text))
        except Exception as e:
            err_msg = str(e)
            app.after(0, lambda: on_error(err_msg))

    def on_success(plan_text):
        loading_win.destroy()
        initial_messages.append({"role": "assistant", "content": plan_text})
        PlanChatWindow(app, system_prompt, initial_messages)

    def on_error(error_msg):
        loading_win.destroy()
        messagebox.showerror("Error", f"Failed to generate plan:\n{error_msg}", parent=app)

    threading.Thread(target=call_api, daemon=True).start()

# --- 9. MAIN APP RENDER ---
app = ctk.CTk()
app.title("TaskMaster")
app.geometry("1000x700") 

# Initialize Global UI Vars
search_var = tk.StringVar()
filter_var = tk.StringVar(value="All Categories")
hide_completed_var = ctk.BooleanVar(value=True)

# Header
header_frame = ctk.CTkFrame(app, height=100, corner_radius=0, fg_color="transparent")
header_frame.pack(fill="x", padx=30, pady=(20, 10))

# Top Row: Title | Theme | Focus
top_row = ctk.CTkFrame(header_frame, fg_color="transparent")
top_row.pack(fill="x", pady=(0, 15))

ctk.CTkLabel(top_row, text="Tasks", font=FONT_HEADER).pack(side="left")

btn_settings = ctk.CTkButton(top_row, text="⚙️", width=40, height=32, 
                          command=open_settings, fg_color="transparent", hover_color="#444444", 
                          font=("SF Pro Display", 20), text_color="#FFFFFF")
btn_settings.pack(side="right", padx=(5, 0))

btn_focus = ctk.CTkButton(top_row, text="Focus Mode 🍅", width=120, height=32,
                          command=open_pomodoro, fg_color="#34C759", hover_color="#28a745", font=FONT_BOLD)
btn_focus.pack(side="right")

btn_plan = ctk.CTkButton(top_row, text="Plan My Day", width=120, height=32,
                          command=plan_my_day, fg_color="#5856D6", hover_color="#4e4cb8", font=FONT_BOLD)
btn_plan.pack(side="right", padx=(0, 10))


# Bottom Row: Search | Filter | Hide | Export | Del | Add
bottom_row = ctk.CTkFrame(header_frame, fg_color="transparent")
bottom_row.pack(fill="x")

# Search
entry_search = ctk.CTkEntry(bottom_row, textvariable=search_var, placeholder_text="Search tasks...", width=200, font=FONT_MAIN)
entry_search.pack(side="left", padx=(0, 10))
search_var.trace_add("write", lambda *args: refresh_task_list()) 

# Filter
filter_menu = ctk.CTkComboBox(
    bottom_row, 
    values=["All Categories"], 
    command=refresh_task_list, 
    variable=filter_var,
    width=140,
    font=FONT_MAIN
)
filter_menu.pack(side="left")

btn_goal = ctk.CTkButton(bottom_row, text="🎯 Goal", width=70, height=32,
    command=open_category_goal_window, fg_color="#5856D6", hover_color="#4e4cb8", font=FONT_BOLD)
btn_goal.pack(side="left", padx=(10, 0))

# Hide Completed
switch_hide = ctk.CTkSwitch(
    bottom_row, 
    text="Hide Done", 
    command=refresh_task_list, 
    variable=hide_completed_var,
    onvalue=True, offvalue=False,
    font=FONT_MAIN
)
switch_hide.pack(side="left", padx=15)

# Buttons Right
btn_frame = ctk.CTkFrame(bottom_row, fg_color="transparent")
btn_frame.pack(side="right")

btn_export = ctk.CTkButton(btn_frame, text="Export CSV", width=90, height=32, 
                           command=export_to_csv, fg_color="#5856D6", hover_color="#4e4cb8", font=FONT_BOLD)
btn_export.pack(side="left", padx=(0, 10))

btn_del = ctk.CTkButton(btn_frame, text="-", width=40, height=40, corner_radius=10,
    font=FONT_ICON, fg_color="#FF3B30", hover_color="#D70015", command=delete_selected_tasks)
btn_del.pack(side="left", padx=(0, 10))

btn_add = ctk.CTkButton(btn_frame, text="+", width=40, height=40, corner_radius=10,
    font=FONT_ICON, fg_color="#007AFF", hover_color="#0062cc", command=lambda: open_task_window())
btn_add.pack(side="left")

list_frame = ctk.CTkFrame(app, corner_radius=12)
list_frame.pack(fill="both", expand=True, padx=30, pady=(0, 30))

# Treeview setup
columns = ("select", "title", "category", "priority", "status", "deadline")
tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")

tree.heading("select", text="✓", anchor="center")
tree.heading("title", text="Task Description", anchor="w")
tree.heading("category", text="Category", anchor="w") 
tree.heading("priority", text="Priority", anchor="center")
tree.heading("status", text="Status", anchor="center")
tree.heading("deadline", text="Deadline", anchor="center")

tree.column("select", width=40, anchor="center", stretch=False)
tree.column("title", width=380, anchor="w")
tree.column("category", width=120, anchor="w") 
tree.column("priority", width=100, anchor="center")
tree.column("status", width=110, anchor="center")
tree.column("deadline", width=100, anchor="center")

scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
tree.configure(yscroll=scrollbar.set)
tree.pack(side="left", fill="both", expand=True, padx=15, pady=15)
scrollbar.pack(side="right", fill="y", pady=15, padx=(0,15))

tree.bind("<Button-1>", toggle_check) 
tree.bind("<Double-1>", on_double_click) 

# Apply initial theme (Dark by default per line 29)
apply_tree_theme("Dark")

app.after(150, check_config_on_startup)
app.mainloop()