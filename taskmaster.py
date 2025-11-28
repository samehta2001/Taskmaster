import customtkinter as ctk 
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tinydb import TinyDB
from tkcalendar import Calendar 
import datetime
import os
import json
import sys
import platform

# --- 1. PATH CONFIGURATION (Mac App Fix) ---
# This ensures we save data in the User's "Application Support" folder.
# If we don't do this, the compiled .app will fail to save settings.

APP_NAME = "TaskMaster"

if platform.system() == "Darwin":
    USER_DATA_DIR = os.path.join(os.path.expanduser("~"), "Library", "Application Support", APP_NAME)
elif platform.system() == "Windows":
    USER_DATA_DIR = os.path.join(os.getenv("APPDATA"), APP_NAME)
else:
    USER_DATA_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", APP_NAME)

# Create the directory if it doesn't exist
if not os.path.exists(USER_DATA_DIR):
    os.makedirs(USER_DATA_DIR)

CONFIG_FILE = os.path.join(USER_DATA_DIR, 'todo_config.json')

# --- 2. UI CONFIGURATION ---
ctk.set_appearance_mode("Dark") 
ctk.set_default_color_theme("blue") 

# Fonts
FONT_MAIN = ("SF Pro Display", 13)
FONT_BOLD = ("SF Pro Display", 13, "bold")
FONT_HEADER = ("SF Pro Display", 26, "bold")
FONT_TITLE = ("SF Pro Display", 14, "bold")
FONT_ICON = ("SF Pro Display", 18, "bold")

# Global Variables
db = None
tasks_table = None
checked_task_ids = set()
filter_var = None  
filter_menu = None 

# --- 3. HELPER FUNCTIONS ---

def center_window_to_parent(window, width, height):
    """Centers a child window relative to the main app."""
    app.update_idletasks()
    main_x = app.winfo_x()
    main_y = app.winfo_y()
    main_w = app.winfo_width()
    main_h = app.winfo_height()
    x_pos = main_x + (main_w // 2) - (width // 2)
    y_pos = main_y + (main_h // 2) - (height // 2)
    window.geometry(f"{width}x{height}+{x_pos}+{y_pos}")

def get_priority(impact, is_urgent):
    """Eisenhower Matrix Logic."""
    if impact == "High": 
        return "Critical" if is_urgent else "Planned"
    elif impact == "Medium": 
        return "Important" if is_urgent else "Review"
    else: 
        return "Delegate" if is_urgent else "Trivial"

def get_all_categories():
    """Returns list of unique categories found in DB."""
    if tasks_table is None: return ["All Categories"]
    cats = set(task.get('category', 'General') for task in tasks_table.all())
    cats.add("General") 
    sorted_cats = sorted(list(cats))
    return ["All Categories"] + sorted_cats

# --- 4. DATABASE & SETUP LOGIC ---

def initialize_db(path):
    global db, tasks_table
    try:
        db = TinyDB(path)
        tasks_table = db.table('tasks')
        refresh_task_list()
        update_filter_options()
    except Exception as e:
        messagebox.showerror("Error", f"Could not load database: {e}")

def save_config_and_start(path):
    with open(CONFIG_FILE, 'w') as f:
        json.dump({'db_path': path}, f)
    initialize_db(path)

def open_setup_wizard():
    """First Run Modal Window."""
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
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                path = config.get('db_path', '')
                if path:
                    initialize_db(path)
                    return
        except:
            pass 
    open_setup_wizard()

# --- 5. CORE UI LOGIC ---

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
    
    # Filter
    current_filter = filter_var.get()
    if current_filter != "All Categories":
        all_tasks = [t for t in all_tasks if t.get('category', 'General') == current_filter]

    # Sort
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
            task['status'], 
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

# --- 6. POPUP WINDOWS ---

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
    center_window_to_parent(win, 420, 500) 
    win.grab_set() 
    win.attributes("-topmost", True)
    
    date_var = tk.StringVar(value=datetime.datetime.now().strftime("%Y-%m-%d"))

    def save_or_update():
        title = entry_title.get()
        impact = combo_impact.get()
        category = combo_category.get() 
        is_urgent = switch_urgent.get() == 1
        deadline = date_var.get()

        if not title: return
        if not category.strip(): category = "General"

        calculated_priority = get_priority(impact, is_urgent)
        record = {
            'title': title, 'impact': impact, 'category': category, 
            'is_urgent': is_urgent, 'priority': calculated_priority, 'deadline': deadline,
            'status': 'Pending' if not is_edit else task_data['status'],
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

    # Inputs
    ctk.CTkLabel(frame, text="Task Description", font=FONT_TITLE, text_color="#A0A0A0").pack(anchor="w", padx=15, pady=(10,5))
    entry_title = ctk.CTkEntry(frame, placeholder_text="Details...", font=FONT_MAIN, height=35)
    entry_title.pack(fill="x", padx=15, pady=(0, 10))

    ctk.CTkLabel(frame, text="Category", font=FONT_TITLE, text_color="#A0A0A0").pack(anchor="w", padx=15, pady=(0,5))
    existing_cats = get_all_categories()
    if "All Categories" in existing_cats: existing_cats.remove("All Categories")
    defaults = ["Work", "Personal", "Health", "Finance"]
    combo_values = sorted(list(set(defaults + existing_cats)))
    
    combo_category = ctk.CTkComboBox(frame, values=combo_values, font=FONT_MAIN, height=35)
    combo_category.set("General") 
    combo_category.pack(fill="x", padx=15, pady=(0, 10))

    ctk.CTkLabel(frame, text="Impact", font=FONT_TITLE, text_color="#A0A0A0").pack(anchor="w", padx=15, pady=(0,5))
    combo_impact = ctk.CTkComboBox(frame, values=["High", "Medium", "Low"], state="readonly", font=FONT_MAIN, height=35)
    combo_impact.set("High")
    combo_impact.pack(fill="x", padx=15, pady=(0, 10))

    switch_urgent = ctk.CTkSwitch(frame, text="Mark as Urgent", font=FONT_MAIN)
    switch_urgent.pack(anchor="w", padx=15, pady=(0, 10))

    ctk.CTkLabel(frame, text="Deadline", font=FONT_TITLE, text_color="#A0A0A0").pack(anchor="w", padx=15, pady=(0,5))
    date_frame = ctk.CTkFrame(frame, fg_color="transparent")
    date_frame.pack(fill="x", padx=15, pady=(0, 20))
    ctk.CTkLabel(date_frame, textvariable=date_var, font=("SF Pro Display", 16), width=100, anchor="w").pack(side="left")
    ctk.CTkButton(date_frame, text="Select", width=80, 
                  command=lambda: open_calendar_picker(win, lambda d: date_var.set(d))).pack(side="right")

    if is_edit and task_data:
        entry_title.insert(0, task_data['title'])
        combo_impact.set(task_data['impact'])
        combo_category.set(task_data.get('category', 'General'))
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

# --- 7. MAIN APP RENDER ---
app = ctk.CTk()
app.title("TaskMaster")
app.geometry("950x650") 

# Header
header_frame = ctk.CTkFrame(app, height=70, corner_radius=0, fg_color="transparent")
header_frame.pack(fill="x", padx=30, pady=(30, 20))

ctk.CTkLabel(header_frame, text="Tasks", font=FONT_HEADER).pack(side="left")

# Filter
filter_var = tk.StringVar(value="All Categories")
filter_menu = ctk.CTkComboBox(
    header_frame, 
    values=["All Categories"], 
    command=refresh_task_list, 
    variable=filter_var,
    width=150,
    font=FONT_MAIN
)
filter_menu.pack(side="left", padx=(20, 0))

# Buttons
btn_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
btn_frame.pack(side="right")
btn_del = ctk.CTkButton(btn_frame, text="-", width=40, height=40, corner_radius=10,
    font=FONT_ICON, fg_color="#FF3B30", hover_color="#D70015", command=delete_selected_tasks)
btn_del.pack(side="left", padx=(0, 10))
btn_add = ctk.CTkButton(btn_frame, text="+", width=40, height=40, corner_radius=10,
    font=FONT_ICON, fg_color="#007AFF", hover_color="#0062cc", command=lambda: open_task_window())
btn_add.pack(side="left")

# List Area
list_frame = ctk.CTkFrame(app, corner_radius=12)
list_frame.pack(fill="both", expand=True, padx=30, pady=(0, 30))

style = ttk.Style()
style.theme_use("default")
bg_color = "#2b2b2b"
selected_color = "#1f538d"
style.configure("Treeview", background=bg_color, foreground="white", fieldbackground=bg_color,
                borderwidth=0, rowheight=40, font=("SF Pro Display", 13))
style.configure("Treeview.Heading", background="#1a1a1a", foreground="white", relief="flat",
                font=("SF Pro Display", 13, "bold"))
style.map("Treeview", background=[('selected', selected_color)])
style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])

columns = ("select", "title", "category", "priority", "status", "deadline")
tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")

tree.heading("select", text="✓", anchor="center")
tree.heading("title", text="Task Description", anchor="w")
tree.heading("category", text="Category", anchor="w") 
tree.heading("priority", text="Priority", anchor="center")
tree.heading("status", text="Status", anchor="center")
tree.heading("deadline", text="Deadline", anchor="center")

tree.column("select", width=40, anchor="center", stretch=False)
tree.column("title", width=400, anchor="w")
tree.column("category", width=120, anchor="w") 
tree.column("priority", width=100, anchor="center")
tree.column("status", width=90, anchor="center")
tree.column("deadline", width=100, anchor="center")

scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
tree.configure(yscroll=scrollbar.set)
tree.pack(side="left", fill="both", expand=True, padx=15, pady=15)
scrollbar.pack(side="right", fill="y", pady=15, padx=(0,15))

tree.bind("<Button-1>", toggle_check) 
tree.bind("<Double-1>", on_double_click) 
tree.tag_configure('oddrow', background='#2b2b2b')
tree.tag_configure('evenrow', background='#333333') 

# Start
app.after(150, check_config_on_startup)
app.mainloop()