# GAMEEDITOR.PY - Main application entry point and controller

import tkinter as tk                 # The toolbox for making windows/buttons
from tkinter import messagebox, filedialog # Pop-up boxes and file seekers
import os                            # Tools for talking to computer folders
import sys                           # Tool for checking the Operating System (Win/Linux)
from importlib import util
import importlib

Image = None
ImageTk = None
pystray = None
item = None

if util.find_spec("PIL") is not None:
    try:
        from PIL import Image, ImageTk
    except ImportError:
        Image = None
        ImageTk = None

if util.find_spec("pystray") is not None:
    pystray = importlib.import_module("pystray")
    item = getattr(pystray, "MenuItem", None)

import ctypes                         # Windows API for Taskbar Icons

# Import project modules
import config                        # Colors and Fonts
from SaveLogic import SaveLogic      # Saving and Loading files
from TilesetEditor import TilesetEditor # The art-sheet editor window
import NPCData
from TypeEditor import TypeEditor
import Hairy
from EditorComponents import GameStatusBar, show_about_dialog, LoginNotification
from TilesetSelector import TilesetSelector
import WorldEditor
import AnimationEditor
import ChunkEditor
import SkillEditor
import ShopEditor
import MonsterSpawnEditor
import ObjectSheetEditor
import PixelEditor
import collections
import threading
from DebugUtils import DebugUtils

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev, PyInstaller, and Nuitka """
    # 1. Check for PyInstaller/Nuitka temp extraction folder
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        return os.path.join(meipass, relative_path)
        
    # 2. For Nuitka onefile, the resources are extracted to a temp folder 
    # reachable via the directory of the script file.
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    # Check if we are running from a frozen EXE
    if getattr(sys, 'frozen', False):
        # Fallback to EXE dir if __file__ is unreliable
        exe_dir = os.path.dirname(sys.executable)
        test_path = os.path.join(base_path, relative_path)
        if not os.path.exists(test_path):
            return os.path.join(exe_dir, relative_path)

    return os.path.join(base_path, relative_path)


def load_image(path):
    """Load an image for Tkinter, using PIL if available."""
    if Image is not None and ImageTk is not None:
        return ImageTk.PhotoImage(Image.open(path))
    try:
        return tk.PhotoImage(file=path)
    except Exception:
        return None

class GameEditor:
    """
    This is the manager of the whole show. 
    It creates the menus and decides which screen to show on the monitor.
    """
    def __init__(self, root):
        DebugUtils.log("Booting up 2DGameEditor engine...")
        
        # --- TASKBAR & WINDOW ICON FIX (AGGRESSIVE) ---
        icon_png = resource_path(os.path.join("Assets", "EditorIcon.png"))
        icon_ico = resource_path(os.path.join("Assets", "EditorIcon.ico"))
        if sys.platform == "win32":
            try:
                myappid = f"GusToughSon.2DGameEditor.v{config.VERSION.replace('.','')}"
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            except: pass

        # 'root' is the Big Window that holds everything
        self.root = root
        
        # Apply icons to root
        if os.path.exists(icon_png):
            try:
                self._brand_img = load_image(icon_png)
                if self._brand_img:
                    self.root.iconphoto(True, self._brand_img)
                if os.path.exists(icon_ico) and sys.platform == "win32":
                    self.root.iconbitmap(icon_ico)
                DebugUtils.log("Application Branding Hardened.")
            except Exception as e: 
                print(f"[ERROR] Icon branding failed: {e}")
        
        self.root.title(f"{config.APP_TITLE} [Active Engine]")
        
        # --- CENTER IN SCREEN ---
        self.root.withdraw() # Hide while calculating
        self.root.update_idletasks()
        win_w, win_h = 800, 600
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        start_x = (screen_w // 2) - (win_w // 2)
        start_y = (screen_h // 2) - (win_h // 2)
        self.root.geometry(f"{win_w}x{win_h}+{start_x}+{start_y}")
        self.root.deiconify() # Reveal
        self.root.configure(bg=config.COLOR_BG)
        
        # Initialize save manager
        self.save_manager = SaveLogic()
        self.state = "Welcome" # We start at the 'Welcome' screen
        self.active_editors = [] # Track open PixelEditor windows
        self.current_tileset_editor = None
        
        # Create the UI pieces
        self.setup_menu()        # Restore the menu!
        # We now use the modular component!
        self.status_bar_comp = GameStatusBar(self.root)
        self.update_statusbar() # Start the blinking heartbeat
        self.update_keyboard_locks() # Start the lock monitor
        
        # --- TRAY INTEGRATION ---
        self.setup_tray()
        self.root.bind("<Unmap>", self._on_unmap)
        self.root.bind("<Map>", self._on_map)

        # DEFERRED STARTUP: Let the window render its frame first to avoid 'White Lag'
        self.root.after(100, self._deferred_startup)

    def _deferred_startup(self):
        """ Handles heavy lifting after the main window is successfully mapped. """
        # --- AUTO-LOAD LOGIC ---
        last_project = getattr(config, "LAST_PROJECT", "MyNewProject")
        saves_dir = os.path.join(self.save_manager._script_dir, config.SAVES_DIR)
        
        # Always show welcome screen as an anchor
        self.show_welcome()
        
        # Path Detection Logic (Native Folder Mapping)
        default_path = os.path.join(saves_dir, last_project)
        
        if os.path.exists(default_path):
            print(f"[DEBUG] Auto-loading project: {default_path}")
            # Update status if auto-loading
            self._sync_load_handler(default_path)

        # Final UI Notifications
        msg_p = resource_path(os.path.join("Assets", "LoginMsg.txt"))
        self.login_notify = LoginNotification(self.root, msg_p)
        self.status_bar_comp.frame.lift()

    def setup_menu(self):
        """ Creates the File, Editors, and Help menus using standard Native Menus. """
        if hasattr(self, 'menubar'):
            try:
                self.root.config(menu="")
                self.menubar.destroy()
            except: pass
        
        self.menubar = tk.Menu(self.root)
        
        # --- FILE MENU ---
        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.file_menu.add_command(label="New Project...", command=self.new_project)
        self.file_menu.add_command(label="Open Project Folder...", command=self.open_project)
        self.file_menu.add_separator()
        
        if self.state == "Loaded":
            self.file_menu.add_command(label="Save Project", command=lambda: self.save_project(prompt=False))
            self.file_menu.add_command(label="Save Project As...", command=lambda: self.save_project(prompt=True))
            self.file_menu.add_separator()
            
        self.file_menu.add_command(label="Exit", command=self.on_app_close)
        
        # --- EDITORS MENU ---
        if self.state == "Loaded":
            self.editors_menu = tk.Menu(self.menubar, tearoff=0)
            self.editors_menu.add_command(label="Tileset Editor", command=self.open_tileset_editor)
            self.editors_menu.add_command(label="Pixel Editor", command=self.open_pixel_editor)
            self.editors_menu.add_command(label="Chunk Editor", command=self.open_chunk_editor)
            self.editors_menu.add_command(label="World Editor", command=self.open_world_editor)
            self.editors_menu.add_command(label="Type Editor", command=self.open_type_editor)
            self.editors_menu.add_command(label="Hairy Editor", command=self.open_hairy_editor)
            self.editors_menu.add_command(label="Skills Editor", command=self.open_skill_editor)
            self.editors_menu.add_command(label="Shop Editor", command=self.open_shop_editor)
            self.editors_menu.add_command(label="Monster Spawn Editor", command=self.open_spawn_editor)
            self.editors_menu.add_command(label="Monster Type Editor", command=self.open_monster_type_editor)
            self.editors_menu.add_command(label="ObjectSheet Editor", command=self.open_object_sheet_editor)
            self.editors_menu.add_command(label="Safe Zone Editor", command=self.open_safe_zone_editor)
            self.editors_menu.add_command(label="NPC Spawn Editor", command=self.open_npc_spawn_editor)
            self.editors_menu.add_command(label="GM Control Console", command=self.open_admin_tool_editor)
            self.editors_menu.add_separator()
            self.editors_menu.add_command(label="Weapon Data Editor", command=self.open_weapon_data_editor)
            self.editors_menu.add_command(label="Armor Data Editor", command=self.open_armor_data_editor)
            self.editors_menu.add_command(label="Useable Item Editor", command=self.open_useable_item_editor)
            self.editors_menu.add_command(label="Collectable Item Editor", command=self.open_collectable_item_editor)

        # Attach everything to the bar
        self.menubar.add_cascade(label="File", menu=self.file_menu)
        if self.state == "Loaded":
            self.menubar.add_cascade(label="Editors", menu=self.editors_menu)
        
        self.menubar.add_command(label="About", command=self.show_about)
        self.root.config(menu=self.menubar)

    def show_about(self):
        show_about_dialog(self.root)

    def _update_config_last_project(self, name):
        """ Surgical + Additive update of the LAST_PROJECT variable in config.py """
        try:
            config_path = os.path.join(self.save_manager._script_dir, "config.py")
            lines = []
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    lines = f.readlines()
            
            import re
            pattern = re.compile(r"^LAST_PROJECT\s*=")
            found = False
            
            with open(config_path, "w") as f:
                for line in lines:
                    if pattern.match(line):
                        f.write(f'LAST_PROJECT = "{name}"\n')
                        found = True
                    else:
                        f.write(line)
                if not found:
                    f.write(f'\nLAST_PROJECT = "{name}"\n')
                    
            # Update the in-memory object too
            config.LAST_PROJECT = name
            DebugUtils.log(f"Session Saved: {name}")
        except Exception as e:
            print(f"[ERROR] Session Persistence Failed: {e}")

    def _setup_custom_titlebar(self):
        """ Creates a professional, draggable title bar. """
        self.title_bar = tk.Frame(self.root, bg=config.COLOR_TITLE_BAR, height=30, bd=0)
        self.title_bar.pack(fill="x", side="top")
        
        # App Title & Icon
        icon_label = None
        if hasattr(self, "_brand_img") and self._brand_img is not None:
            icon_label = tk.Label(self.title_bar, image=self._brand_img, bg=config.COLOR_TITLE_BAR)
            icon_label.pack(side="left", padx=5)
        
        tk.Label(self.title_bar, text=f"{config.APP_TITLE}", bg=config.COLOR_TITLE_BAR, 
                 fg=config.COLOR_TITLE_TEXT, font=config.FONT_TITLE).pack(side="left")
        
        # Window Controls
        tk.Button(self.title_bar, text="✕", bg=config.COLOR_TITLE_BAR, fg="white", bd=0, 
                  command=self.on_app_close, font=("Arial", 12)).pack(side="right", padx=5)
        tk.Button(self.title_bar, text="🗗", bg=config.COLOR_TITLE_BAR, fg="white", bd=0, 
                  command=self._toggle_maximize, font=("Arial", 12)).pack(side="right", padx=5)
        tk.Button(self.title_bar, text="—", bg=config.COLOR_TITLE_BAR, fg="white", bd=0, 
                  command=self._minimize_window, font=("Arial", 12)).pack(side="right", padx=5)
        
        # Draggable Logic
        self.title_bar.bind("<Button-1>", self._start_window_drag)
        self.title_bar.bind("<B1-Motion>", self._do_window_drag)
        self._drag_start_x = 0
        self._drag_start_y = 0

    def _start_window_drag(self, event):
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def _do_window_drag(self, event):
        x = self.root.winfo_x() + (event.x - self._drag_start_x)
        y = self.root.winfo_y() + (event.y - self._drag_start_y)
        self.root.geometry(f"+{x}+{y}")

    def _minimize_window(self):
        # On Windows overrideredirect(True) windows don't minimize to taskbar easily
        # We use withdraw/iconify trick
        self.root.state('withdrawn')
        self.root.overrideredirect(False)
        self.root.iconify()
        self.root.bind("<Map>", self._restore_after_minimize)

    def _restore_after_minimize(self, event):
        self.root.overrideredirect(True)
        self.root.unbind("<Map>")

    def _toggle_maximize(self):
        # For now, simple fixed size toggling or full screen
        pass

    def _setup_window_edges(self):
        """ Adds thick borders that serve as resizing handles. """
        self.resizer = tk.Frame(self.root, bg=config.COLOR_TITLE_BAR, cursor="size_nw_se", width=10, height=10)
        self.resizer.place(relx=1.0, rely=1.0, anchor="se")
        self.resizer.bind("<B1-Motion>", self._do_resize)
        
        # We also add a visual border around the whole app
        self.root.config(highlightbackground="#444", highlightcolor="#444", highlightthickness=2)

    def _do_resize(self, event):
        x = self.root.winfo_pointerx() - self.root.winfo_x()
        y = self.root.winfo_pointery() - self.root.winfo_y()
        # Minimum size 800x600
        nw, nh = max(800, x), max(600, y)
        self.root.geometry(f"{nw}x{nh}")
        # Redraw background if needed
        if hasattr(self, "bg_label"):
            self.bg_label.config(width=nw, height=nh)

    def set_status(self, text, color="lime"):
        """ Wrapper for the modular status bar """
        self.status_bar_comp.set_status(text, color)

    def setup_background(self):
        """ Loads the custom editor skin and locks it to the top-left. """
        bg_path = os.path.join("Assets", "EDITOR_BACKGROUND.png")
        if os.path.exists(bg_path):
            try:
                if Image is None or ImageTk is None:
                    raise RuntimeError("PIL is required to load the editor background.")
                img = Image.open(bg_path)
                self.bg_photo = ImageTk.PhotoImage(img)
                
                # Place as a background label
                self.bg_label = tk.Label(self.root, image=self.bg_photo, bg=config.COLOR_BG, bd=0)
                self.bg_label.place(x=0, y=0, anchor="nw")
                self.bg_label.lower() # Push to back of Z-order
            except Exception as e:
                print(f"[DEBUG] Background image failed to load: {e}")


    def update_statusbar(self):
        """ Continuous loop that updates the status bar colors. """
        if self.state == "Loaded":
            if self.save_manager.is_dirty:
                self.set_status("Unsaved Changes", "yellow")
            else:
                self.set_status("Ready", "lime")
        else:
            self.set_status("Ready", "lime")

        # Re-run this check in 250ms
        self.root.after(250, self.update_statusbar)

    def update_keyboard_locks(self):
        """ Continuous loop that updates the lock keys. """
        # Check Caps/Num/Ins locks on Windows
        if sys.platform == "win32":
            try:
                import ctypes
                hllDll = ctypes.WinDLL("User32.dll")
                caps = hllDll.GetKeyState(0x14) & 0x0001
                num = hllDll.GetKeyState(0x90) & 0x0001
                
                self.status_bar_comp.update_locks(caps, num)
            except: pass

        # Re-run this check in 500ms
        self.root.after(500, self.update_keyboard_locks)

    def show_welcome(self):
        """ Shows the 'Project Launcher' dialogue box in the middle. """
        if self.state == "Loaded": return
        if hasattr(self, 'welcome_frame') and self.welcome_frame.winfo_exists(): return

        self.welcome_frame = tk.Frame(self.root, bg=config.COLOR_BG, bd=2, relief="raised")
        self.welcome_frame.place(relx=0.5, rely=0.5, anchor="center", width=340, height=220)

        title_bar = tk.Frame(self.welcome_frame, bg=config.COLOR_TITLE_BAR, height=25)
        title_bar.pack(fill="x")
        tk.Label(title_bar, text="New/Open", bg=config.COLOR_TITLE_BAR, fg=config.COLOR_TITLE_TEXT, font=config.FONT_TITLE).pack(side="left", padx=5)

        content = tk.Frame(self.welcome_frame, bg=config.COLOR_BG, padx=20, pady=20)
        content.pack(fill="both")
        tk.Button(content, text="New Project...", command=self.new_project, width=25, bg=config.COLOR_BG, relief="raised", bd=2).pack(pady=5)
        tk.Button(content, text="Open Project Folder...", command=self.open_project, width=25, bg=config.COLOR_BG, relief="raised", bd=2).pack(pady=5)

    def new_project(self):
        """ Starts the 'Create New' flow. """
        if hasattr(self, 'new_win') and self.new_win.winfo_exists():
            self.new_win.lift(); return
        
        if not self.check_save_dialog(): return
            
        self.new_win = tk.Toplevel(self.root)
        self.new_win.title("New Project")
        
        # --- WINDOW ICON FIX ---
        icon_path = resource_path(os.path.join("Assets", "NewIcon.png"))
        if os.path.exists(icon_path):
            try:
                self._new_win_icon = load_image(icon_path)
                if self._new_win_icon:
                    self.new_win.iconphoto(False, self._new_win_icon)
            except: pass
        
        # --- CENTER IN PARENT ---
        self.new_win.withdraw() # Hide while calculating
        self.new_win.update_idletasks()
        w, h = 320, 240
        px, py = self.root.winfo_x(), self.root.winfo_y()
        pw, ph = self.root.winfo_width(), self.root.winfo_height()
        x = px + (pw // 2) - (w // 2)
        y = py + (ph // 2) - (h // 2)
        self.new_win.geometry(f"{w}x{h}+{x}+{y}")
        self.new_win.deiconify() # Reveal
        
        self.new_win.configure(bg=config.COLOR_BG)
        self.new_win.resizable(False, False)
        self.new_win.transient(self.root)
        self.new_win.grab_set() # Lock focus

        tk.Label(self.new_win, text="Project Name:", bg=config.COLOR_BG).pack(pady=5)
        name_var = tk.StringVar(value="MyNewProject")
        tk.Entry(self.new_win, textvariable=name_var, width=30).pack(padx=20)

        tk.Label(self.new_win, text="Tile Size (16, 32, 64):", bg=config.COLOR_BG).pack(pady=5)
        size_var = tk.StringVar(value="32")
        tk.Entry(self.new_win, textvariable=size_var, width=10).pack(padx=20)

        def confirm():
            # Extract and sanitize the name
            import re
            raw_name = name_var.get().strip()
            name = re.sub(r'[^a-zA-Z0-9_ ]', '', raw_name)
            if not name:
                messagebox.showwarning("Warning", "Project name must be alpha-numeric!")
                return

            try: tsize = int(size_var.get())
            except: tsize = 32
            
            # Check if this zip already exists in Saves/
            zip_check = os.path.join(self.save_manager._script_dir, config.SAVES_DIR, f"{name}.zip")
            if os.path.exists(zip_check):
                if not messagebox.askyesno("Overwrite?", f"The project '{name}' already exists in Saves. Overwrite it?", parent=self.new_win):
                    return
            
            # Prepare the new data in the editing pool
            print(f"[DEBUG] Creating new project '{name}' with tile size {tsize}px")
            self.save_manager.new_project(name, tsize)
            
            # Save it immediately to the ZIP
            success, err = self.save_manager.save_project()
            if success:
                self.enter_loaded_state(name)
                self.new_win.destroy()
            else: messagebox.showerror("Error", err, parent=self.new_win)

        tk.Button(self.new_win, text="OK", command=confirm, width=10).pack(pady=10)

    def open_project(self):
        """ Custom 'Open Project' window with OpenIcon applied. """
        if hasattr(self, 'open_win') and self.open_win.winfo_exists():
            self.open_win.lift(); return
            
        if not self.check_save_dialog(): return

        self.open_win = tk.Toplevel(self.root)
        self.open_win.title("Open Project")
        
        # --- WINDOW ICON FIX (SPECIFIC TO OPEN) ---
        icon_path = resource_path(os.path.join("Assets", "OpenIcon.png"))
        if os.path.exists(icon_path):
            try:
                self._open_icon = load_image(icon_path)
                if self._open_icon:
                    self.open_win.iconphoto(False, self._open_icon)
            except: pass
        
        # --- CENTER IN PARENT ---
        self.open_win.withdraw()
        self.open_win.update_idletasks()
        w, h = 350, 300
        px, py = self.root.winfo_x(), self.root.winfo_y()
        pw, ph = self.root.winfo_width(), self.root.winfo_height()
        x = px + (pw // 2) - (w // 2)
        y = py + (ph // 2) - (h // 2)
        self.open_win.geometry(f"{w}x{h}+{x}+{y}")
        self.open_win.deiconify()
        
        self.open_win.configure(bg=config.COLOR_BG)
        self.open_win.resizable(False, False)
        self.open_win.transient(self.root)
        self.open_win.grab_set() # Lock focus

        tk.Label(self.open_win, text="Select Project to Open:", bg=config.COLOR_BG, font=config.FONT_TITLE).pack(pady=10)
        
        list_f = tk.Frame(self.open_win, bg=config.COLOR_BG)
        list_f.pack(padx=20, fill="both", expand=True)
        
        sb = tk.Scrollbar(list_f)
        sb.pack(side="right", fill="y")
        
        lb = tk.Listbox(list_f, yscrollcommand=sb.set, relief="sunken", bd=2, activestyle="none", highlightthickness=0)
        lb.pack(side="left", fill="both", expand=True)
        sb.config(command=lb.yview)
        
        # Populate projects from the Saves folder
        saves_dir = os.path.join(self.save_manager._script_dir, config.SAVES_DIR)
        os.makedirs(saves_dir, exist_ok=True)
        def refresh_list():
            lb.delete(0, "end")
            # --- NATIVE WORKSPACE DISCOVERY ---
            # List only directories in the Saves folder
            items = sorted([f for f in os.listdir(saves_dir) if os.path.isdir(os.path.join(saves_dir, f))], key=str.lower)
            for name in items:
                lb.insert("end", name)

        refresh_list()
        
        # Ensure the listbox is focused initially so clicks register immediately
        lb.focus_set()

        # Double click to open
        lb.bind("<Double-Button-1>", lambda e: confirm())

        def delete_selected():
            selection = lb.curselection()
            if not selection: return
            name = lb.get(selection[0])
            # Check for both (prioritize .sav)
            path = os.path.join(saves_dir, f"{name}{config.PROJECT_EXT}")
            if not os.path.exists(path):
                path = os.path.join(saves_dir, f"{name}.zip")
            
            if messagebox.askyesno("Delete Project?", f"Are you sure you want to PERMANENTLY delete '{name}'?\nThis cannot be undone.", parent=self.open_win):
                try:
                    # Comprehensive Cleanup: Delete both extensions if present
                    deleted = False
                    for ext in [config.PROJECT_EXT, ".zip"]:
                        p = os.path.join(saves_dir, f"{name}{ext}")
                        if os.path.exists(p):
                            os.remove(p)
                            deleted = True
                    
                    if deleted:
                        refresh_list()
                        DebugUtils.log(f"Deleted project: {name}")
                except Exception as e:
                    messagebox.showerror("Error", f"Could not delete: {e}", parent=self.open_win)

        def confirm(e=None):
            selection = lb.curselection()
            if not selection: 
                # Fallback: If nothing selected, treat like a quick "New Project" jump
                self.new_project()
                self.open_win.destroy()
                return
            name = lb.get(selection[0])
            path = os.path.join(saves_dir, name)
            
            # Heartbeat-Synch Load to prevent UI hang with massive chunks
            with DebugUtils.benchmark(f"Full Project Load: {name}"):
                self._sync_load_handler(path)
            self.open_win.destroy()

        def browse():
            # Modern Directory Picker for Native Workspaces
            # Modern Directory Picker for Native Workspaces
            path = filedialog.askdirectory(
                initialdir=saves_dir,
                title="Select Project Workspace Folder",
                parent=self.open_win
            )
            refresh_list() # Sync list even if cancelled
            if not path: return
            self._sync_load_handler(path)
            self.open_win.destroy()

        btn_f = tk.Frame(self.open_win, bg=config.COLOR_BG, pady=10)
        btn_f.pack(fill="x")
        
        tk.Button(btn_f, text="Open", command=confirm, width=10).pack(side="left", padx=5)
        tk.Button(btn_f, text="Delete", command=delete_selected, width=10, fg="red").pack(side="left", padx=5)
        tk.Button(btn_f, text="Browse...", command=browse, width=10).pack(side="left", padx=5)
        tk.Button(btn_f, text="Cancel", command=self.open_win.destroy, width=10).pack(side="right", padx=5)

    def _sync_load_handler(self, path):
        """ The Heartbeat Pump: Runs on main thread but pumps UI events to stay fluid. """
        self.set_status("Macerating Project Data...", "blue")
        try:
            if self.root.winfo_exists(): self.root.update()
        except: pass
        
        data, err = self.save_manager.load_project(path, progress_callback=self._on_load_progress)
        
        if data:
            # Use the folder name (basename) for persistence to ensure the path remains valid
            folder_name = os.path.basename(path.rstrip(os.sep))
            self.enter_loaded_state(folder_name)
        else:
            messagebox.showerror("Forge Error", f"The Data Forge failed: {err}")

    def _on_load_progress(self, msg):
        """ Pumps the UI event loop during heavy I/O to prevent 'Not Responding' hangs. """
        try:
            if not self.root.winfo_exists(): return
            self.set_status(msg, "blue")
            self.root.update()
        except: pass

    def enter_loaded_state(self, name):
        self.state = "Loaded"
        self._update_config_last_project(name) # Record session memory
        if hasattr(self, 'welcome_frame') and self.welcome_frame.winfo_exists():
            self.welcome_frame.destroy()
        self.root.title(f"{config.APP_TITLE} [Active Engine] - {name}")
        DebugUtils.log(f"App State: Loaded Project ({name})")
        self.setup_menu()
        self.setup_background()

    def open_tileset_editor(self):
        """ Opens the art-sheet window. Ensures only one is open at a time! """
        try:
            if self.current_tileset_editor and self.current_tileset_editor.win.winfo_exists():
                self.current_tileset_editor.win.lift()
                self.current_tileset_editor.win.focus_force()
                return
        except: pass
            
        self.current_tileset_editor = TilesetEditor(self.root, self.save_manager)

    def check_save_dialog(self):
        """ Asks the user if they want to save changes before leaving. """
        if self.state != "Loaded" or not self.save_manager.is_dirty: return True
        ans = messagebox.askyesnocancel("Wait!", "Do you want to save changes?")
        if ans is True: return self.save_project()
        return ans is False # True if 'No', False if 'Cancel'

    def save_as_project_dialog(self):
        """ Custom 'Save As' window with SaveIcon applied. """
        if hasattr(self, 'save_as_win') and self.save_as_win.winfo_exists():
            self.save_as_win.lift(); return
            
        self.save_as_win = tk.Toplevel(self.root)
        self.save_as_win.title("Save Project As...")
        
        # --- WINDOW ICON FIX (SPECIFIC TO SAVE) ---
        icon_path = resource_path(os.path.join("Assets", "SaveIcon.png"))
        if os.path.exists(icon_path):
            try:
                self._save_as_icon = load_image(icon_path)
                if self._save_as_icon:
                    self.save_as_win.iconphoto(False, self._save_as_icon)
            except: pass
        
        # --- CENTER IN PARENT ---
        self.save_as_win.withdraw()
        self.save_as_win.update_idletasks()
        w, h = 320, 180
        px, py = self.root.winfo_x(), self.root.winfo_y()
        pw, ph = self.root.winfo_width(), self.root.winfo_height()
        x = px + (pw // 2) - (w // 2)
        y = py + (ph // 2) - (h // 2)
        self.save_as_win.geometry(f"{w}x{h}+{x}+{y}")
        self.save_as_win.deiconify()
        
        self.save_as_win.configure(bg=config.COLOR_BG)
        self.save_as_win.resizable(False, False)
        self.save_as_win.transient(self.root)
        self.save_as_win.grab_set() # Lock focus

        tk.Label(self.save_as_win, text="New Project Name:", bg=config.COLOR_BG).pack(pady=10)
        name_var = tk.StringVar(value=self.save_manager.project_name)
        entry = tk.Entry(self.save_as_win, textvariable=name_var, width=30)
        entry.pack(padx=20)
        entry.focus_set()
        entry.selection_range(0, "end")

        def confirm():
            new_name = name_var.get().strip()
            if not new_name: return
            
            # Extract just the filename without path or extension
            import re
            base_name = re.sub(r'[^a-zA-Z0-9_ ]', '', new_name)
            
            # Check if this zip already exists in Saves/
            zip_check = os.path.join(self.save_manager._script_dir, config.SAVES_DIR, f"{base_name}.zip")
            if os.path.exists(zip_check) and base_name != self.save_manager.project_name:
                if not messagebox.askyesno("Overwrite?", f"The project '{base_name}' already exists in Saves. Overwrite it?", parent=self.save_as_win):
                    return

            # Use the modular rename logic
            self.close_sub_editors()
            success, err = self.save_manager.rename_project(base_name)
            if not success:
                messagebox.showerror("Rename Failed", err, parent=self.save_as_win)
                return

            # Update the window title and config persistence
            self.root.title(f"{config.APP_TITLE} [Active Engine] - {base_name}")
            self._update_config_last_project(base_name)

            # Perform actual disk save
            success, err = self.save_manager.save_project()
            if success:
                print(f"[DEBUG] Project '{base_name}' saved via custom dialog.")
                self.save_as_win.destroy()
            else:
                messagebox.showerror("Error", err, parent=self.save_as_win)

        tk.Button(self.save_as_win, text="Save As", command=confirm, width=15).pack(pady=20)
        entry.bind("<Return>", lambda e: confirm())

    def save_project(self, prompt=False):
        """ Atomic save: Compresses the editing pool into a single ZIP in Saves/ """
        if prompt:
            return self.save_as_project_dialog()

        success, err = self.save_manager.save_project()
        if success: 
            # Update config with the last saved name
            self._update_config_last_project(self.save_manager.project_name)
            return True
        else:
            messagebox.showerror("Error", err)
            return False



    def open_pixel_editor(self):
        """ Opens the Pixel Editor in Standalone Mode. """
        ts_dir = None
        project_path = getattr(self.save_manager, 'project_path', None)
        if self.state == "Loaded" and isinstance(project_path, str):
            ts_dir = os.path.join(project_path, "TILESET")
        pe = PixelEditor.PixelEditor(self.root, tileset_dir=ts_dir, save_manager=self.save_manager)
        
        # --- MEMORY PROTECTION ---
        # We track open editors to close them on exit, but we MUST remove them
        # if the user closes them manually to prevent memory leakage!
        self.active_editors.append(pe)
        pe.win.bind("<Destroy>", lambda e: self._remove_active_editor(pe), add="+")
        print("[DEBUG] Pixel Editor launched.")

    def _remove_active_editor(self, editor):
        """ Safely purges closed windows from the master tracker. """
        if editor in self.active_editors:
            try:
                self.active_editors.remove(editor)
            except ValueError: pass

    def open_type_editor(self):
        """ Launches the Windows 95-style Type Editor. """
        try:
            if self.current_type_editor and self.current_type_editor.win.winfo_exists():
                self.current_type_editor.win.lift()
                return
        except: pass
            
        self.current_type_editor = TypeEditor(self.root, self.save_manager, main_app=self)
        print("[DEBUG] Type Editor launched.")

    def open_anim_editor(self):
        """ Launches the Standalone Animation Suite. """
        try:
            if self.current_anim_editor and self.current_anim_editor.win.winfo_exists():
                self.current_anim_editor.win.lift()
                return
        except: pass
        self.current_anim_editor = AnimationEditor.AnimationEditor(self.root, self.save_manager)
        print("[DEBUG] Animation Editor launched.")


    def open_shop_editor(self):
        """ Launches the Windows 95-style Shop Editor. """
        try:
            if hasattr(self, 'current_shop_editor') and self.current_shop_editor.win.winfo_exists():
                self.current_shop_editor.win.lift()
                return
        except: pass
            
        self.current_shop_editor = ShopEditor.ShopEditor(self.root, self.save_manager, main_app=self)
        print("[DEBUG] Shop Editor launched.")

    def open_hairy_editor(self):
        """ IDE Module: Direct Script Editor for .hry logic. """
        try:
            if self.current_hairy_editor and self.current_hairy_editor.win.winfo_exists():
                self.current_hairy_editor.win.lift(); return
        except: pass
            
        self.current_hairy_editor = Hairy.HairyEditor(self.root, self.save_manager)
        print("[DEBUG] Hairy Editor launched (Modular).")

    def open_world_editor(self):
        """ Launches the World Map Editor. """
        try:
            if self.current_world_editor and self.current_world_editor.win.winfo_exists():
                self.current_world_editor.win.lift()
                return
        except: pass
        self.current_world_editor = WorldEditor.WorldEditor(self, self.save_manager)
        print("[DEBUG] World Editor launched.")

    def open_chunk_editor(self, target_chunk_id=None):
        """ Launches the Chunk Designer. Supports targeted boot. """
        try:
            if self.current_chunk_editor and self.current_chunk_editor.win.winfo_exists():
                if target_chunk_id:
                    self.current_chunk_editor._select_chunk(target_chunk_id)
                self.current_chunk_editor.win.lift()
                return
        except: pass
        self.current_chunk_editor = ChunkEditor.ChunkEditor(self, self.save_manager, target_chunk_id=target_chunk_id)
        print(f"[DEBUG] Chunk Editor launched (Target: {target_chunk_id}).")

    def open_skill_editor(self):
        """ Launches the Database for stats and level attributes. """
        try:
            if self.current_skill_editor and self.current_skill_editor.win.winfo_exists():
                self.current_skill_editor.win.lift(); return
        except: pass
        self.current_skill_editor = SkillEditor.SkillEditor(self.root, self.save_manager)
        print("[DEBUG] Skill Editor launched.")


    def open_spawn_editor(self):
        """ Launches the Monster Spawn Editor. """
        try:
            if hasattr(self, 'current_spawn_editor') and self.current_spawn_editor.win.winfo_exists():
                self.current_spawn_editor.win.lift(); return
        except: pass
        self.current_spawn_editor = MonsterSpawnEditor.MonsterSpawnEditor(self.root, self.save_manager)
        print("[DEBUG] Monster Spawn Editor launched.")

    def open_monster_type_editor(self):
        """ Launches the Monster Type Definition Editor. """
        try:
            if hasattr(self, 'current_monster_type_editor') and self.current_monster_type_editor and self.current_monster_type_editor.win.winfo_exists():
                self.current_monster_type_editor.win.lift(); return
        except: pass
        import MonsterTypeEditor
        self.current_monster_type_editor = MonsterTypeEditor.MonsterTypeDataEditor(self.root, self.save_manager)
        print("[DEBUG] Monster Type Editor launched.")

    def open_safe_zone_editor(self):
        """ Launches the Safe Zone Configurator. """
        try:
            if hasattr(self, 'current_safe_zone_editor') and self.current_safe_zone_editor.win.winfo_exists():
                self.current_safe_zone_editor.win.lift(); return
        except: pass
        import SafeZoneEditor
        self.current_safe_zone_editor = SafeZoneEditor.SafeZoneEditor(self.root, self.save_manager)
        print("[DEBUG] Safe Zone Editor launched.")

    def open_npc_spawn_editor(self):
        """ Launches the NPC Spawn Point Configurator. """
        try:
            if hasattr(self, 'current_npc_spawn_editor') and self.current_npc_spawn_editor and self.current_npc_spawn_editor.win.winfo_exists():
                self.current_npc_spawn_editor.win.lift(); return
        except: pass
        import NPCSpawnEditor
        self.current_npc_spawn_editor = NPCSpawnEditor.NPCSpawnEditor(self.root, self.save_manager)
        print("[DEBUG] NPC Spawn Editor launched.")

    def open_npc_data_editor(self):
        """ Launches the NPC/Creature Stat Editor. """
        try:
            if self.current_npc_editor and self.current_npc_editor.win.winfo_exists():
                self.current_npc_editor.win.lift(); return
        except: pass
        self.current_npc_editor = NPCData.NPCDataEditor(self.root, self.save_manager)
        print("[DEBUG] NPC Data Editor launched.")

    def open_armor_data_editor(self):
        """ Launches the Armor/Equipment Stat Editor. """
        try:
            if self.current_armor_editor and self.current_armor_editor.win.winfo_exists():
                self.current_armor_editor.win.lift(); return
        except: pass
        import ArmorData
        self.current_armor_editor = ArmorData.ArmorDataEditor(self.root, self.save_manager)
        print("[DEBUG] Armor Data Editor launched.")

    def open_weapon_data_editor(self):
        """ Launches the Weapon/Equipment Stat Editor. """
        try:
            if self.current_weapon_editor and self.current_weapon_editor.win.winfo_exists():
                self.current_weapon_editor.win.lift(); return
        except: pass
        import WeaponData
        self.current_weapon_editor = WeaponData.WeaponDataEditor(self.root, self.save_manager)
        print("[DEBUG] Weapon Data Editor launched.")

    def open_useable_item_editor(self):
        """ Launches the Useable Item Stat Editor. """
        try:
            if hasattr(self, 'current_useable_editor') and self.current_useable_editor and self.current_useable_editor.win.winfo_exists():
                self.current_useable_editor.win.lift(); return
        except: pass
        import UseableItemEditor
        self.current_useable_editor = UseableItemEditor.UseableItemDataEditor(self.root, self.save_manager)
        print("[DEBUG] Useable Item Editor launched.")

    def open_collectable_item_editor(self):
        """ Launches the Collectable Item Stat Editor. """
        try:
            if hasattr(self, 'current_collectable_editor') and self.current_collectable_editor and self.current_collectable_editor.win.winfo_exists():
                self.current_collectable_editor.win.lift(); return
        except: pass
        import CollectableEditor
        self.current_collectable_editor = CollectableEditor.CollectableItemDataEditor(self.root, self.save_manager)
        print("[DEBUG] Collectable Item Editor launched.")

    def open_admin_tool_editor(self):
        """ Launches the Admin/GM Control Console. """
        try:
            if hasattr(self, 'current_admin_tool_editor') and self.current_admin_tool_editor and self.current_admin_tool_editor.win.winfo_exists():
                self.current_admin_tool_editor.win.lift(); return
        except: pass
        import AdminToolEditor
        self.current_admin_tool_editor = AdminToolEditor.AdminToolEditor(self.root, self.save_manager, main_app=self)
        print("[DEBUG] GM Control Console launched.")

    def open_object_sheet_editor(self):
        """ Launches the Bulk Metadata Spreadsheet. """
        try:
            if hasattr(self, 'current_object_sheet_editor') and self.current_object_sheet_editor.win.winfo_exists():
                self.current_object_sheet_editor.win.lift(); return
        except: pass
        self.current_object_sheet_editor = ObjectSheetEditor.ObjectSheetEditor(self.root, self.save_manager)
        print("[DEBUG] ObjectSheet Editor launched.")

    def close_sub_editors(self):
        """ Hardened Lifecycle Manager: Clears resources and forces GC. """
        import gc
        # Surgical termination of all child modules
        editors_to_clear = [
            'current_tileset_editor', 'current_type_editor', 
            'current_anim_editor', 'current_npc_editor', 
            'current_armor_editor', 'current_weapon_editor',
            'current_useable_editor', 'current_collectable_editor',
            'current_monster_type_editor',
            'current_hairy_editor', 'current_world_editor', 
            'current_chunk_editor', 'current_skill_editor', 
            'current_shop_editor', 'current_spawn_editor', 
            'current_object_sheet_editor', 'tileset_selector',
            'current_safe_zone_editor', 'current_npc_spawn_editor',
            'current_admin_tool_editor'
        ]
        
        for attr in editors_to_clear:
            if hasattr(self, attr):
                obj = getattr(self, attr)
                if obj:
                    try:
                        # Case 1: Complex Editor with .win attribute
                        if hasattr(obj, 'win') and obj.win.winfo_exists():
                            obj.win.destroy()
                        # Case 2: Primitive Tkinter windows
                        elif hasattr(obj, 'winfo_exists') and obj.winfo_exists():
                            obj.destroy()
                    except: pass
                setattr(self, attr, None) # Nullify to invite GC
        
        # Drain the floating editor pool (e.g. PixelEditor instances)
        for pe in list(self.active_editors):
            try:
                if pe.win.winfo_exists(): pe.win.destroy()
            except: pass
        self.active_editors.clear()
        
        gc.collect() # Force immediate reclamation of GDI handles
        print("[SECURITY] Resource sweep complete. System hardened.")

    def setup_tray(self):
        """ System Tray initialization. """
        try:
            icon_path = resource_path(os.path.join("Assets", "EditorIcon.png"))
            if not os.path.exists(icon_path): return
            
            if pystray is None or item is None or Image is None:
                return
            image = Image.open(icon_path)
            # We must use lambda or a wrapper to call deiconify safely
            menu = (
                item('Restore', self.restore_from_tray, default=True),
                item('Exit', self.on_app_close)
            )
            self.tray_icon = pystray.Icon("2DGameEditor", image, "2DGameEditor", menu)
            
            # Tray loop must run in a background thread to keep Tkinter responsive
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
            self.tray_icon.visible = False
        except Exception as e:
            print(f"[DEBUG] Tray system failed: {e}")

    def _on_unmap(self, event):
        """ Detects minimization and hides to tray. """
        if self.root.state() == 'iconic':
            self.root.withdraw()
            if hasattr(self, 'tray_icon'):
                self.tray_icon.visible = True

    def _on_map(self, event):
        """ Detects window restoration. """
        if hasattr(self, 'tray_icon'):
            self.tray_icon.visible = False

    def restore_from_tray(self, icon=None, item=None):
        """ Soft restore from tray menu or click. """
        if hasattr(self, 'tray_icon'):
            self.tray_icon.visible = False
        self.root.after(0, self.root.deiconify)
        self.root.after(100, self.root.lift)
        self.root.after(200, self.root.focus_force)

    def on_app_close(self, icon=None, item=None):
        """ Safely closes everything when you click the X. """
        if hasattr(self, 'tray_icon'):
            self.tray_icon.stop()
        if self.check_save_dialog():
            self.close_sub_editors()
            # Clean up the secret editing folder before leaving!
            self.save_manager.cleanup_pool()
            self.root.destroy()

if __name__ == "__main__":
    app = None
    try:
        root = tk.Tk()
        app = GameEditor(root)
        root.mainloop()
    except KeyboardInterrupt:
        print("\n[DEBUG] Interrupted by user. Shutting down gracefully...")
        # If the app was initialized, we should try to clean up
        if app is not None:
            app.on_app_close()
        else:
            sys.exit(0)

