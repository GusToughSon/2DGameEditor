import tkinter as tk
from tkinter import messagebox, colorchooser, filedialog
import os
import config
from PIL import Image, ImageTk, ImageDraw
import collections
import re
from DebugUtils import DebugUtils

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev, PyInstaller, and Nuitka """
    import sys
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    base_path = os.path.dirname(os.path.abspath(__file__))
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        test_path = os.path.join(base_path, relative_path)
        if not os.path.exists(test_path):
            return os.path.join(exe_dir, relative_path)
    return os.path.join(base_path, relative_path)

from EditorComponents import center_window

class PixelEditor:
    """
    Advanced Pixel Art Suite.
    Features: Resizable Tile Sidebar, Flood Fill, Marquee, and Atomic Transforms.
    """
    def __init__(self, parent, tile_img=None, col=0, row=0, callback=None, tileset_dir=None, save_manager=None, **kwargs):
        self.parent = parent
        self.callback = callback 
        self.col, self.row = col, row
        self.tileset_dir = tileset_dir
        self.save_manager = save_manager
        
        # --- DATA ---
        if tile_img:
            self.image = tile_img.convert("RGBA")
            self.tile_size = self.image.width
        else:
            # FIX: Properly fetch tile size from project metadata for empty tiles
            self.tile_size = self.save_manager.project_data.get("tile_size", 16) if self.save_manager else 16
            self.image = Image.new("RGBA", (self.tile_size, self.tile_size), (0,0,0,0))
        self.zoom = 20
        self.brush_size = 1
        self.active_tool = "PENCIL"
        self.current_color = "#FFFFFF" # Left Click (Primary)
        self.secondary_color = "#000000" # Right Click (Secondary)
        self.recent_colors = collections.deque(["#000000", "#FFFFFF"], maxlen=8)
        self.palette_colors = ["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF", "#00FFFF", "#000000", "#FFFFFF"]
        self.selection = None 
        self.clipboard = None 
        self.is_locked = False # Editing Lock
        
        # Sidebar state
        self.sidebar_zoom = 3.0
        self.sidebar_width = 250
        self.tileset_photo_chunks = [] # Keep refs to avoid GC
        self.tileset_map = {} # Will be populated dynamically
        self.initial_tileset = kwargs.get("initial_tileset", "World")

        # --- HISTORY ENGINE ---
        self.undo_stack = []
        self.redo_stack = []
        self.max_history = 50
        
        # --- WINDOW ---
        self.win = tk.Toplevel(parent)
        self.win.title("Pixel Editor")
        
        # Standardized Centering
        center_window(self.win, parent, 1100, 800)
        
        # --- WINDOW ICON FIX ---
        icon_path = resource_path(os.path.join("Assets", "PixelIcon.png"))
        if os.path.exists(icon_path):
            try:
                self._win_icon = ImageTk.PhotoImage(Image.open(icon_path))
                self.win.iconphoto(False, self._win_icon)
            except: pass
            
        self.win.configure(bg="#1A1A1A")
        # --- UI LAYOUT ---
        self.setup_layout()
        self.setup_menus()
        
        # Initial Sidebar Load
        self.current_tileset_path = None
        if self.tileset_dir:
            self._refresh_dropdown()
            name = self.initial_tileset if self.initial_tileset in self.tileset_map else "World"
            if name not in self.tileset_map and self.tileset_map:
                name = list(self.tileset_map.keys())[0]
            
            self.ts_var.set(name)
            self._on_tileset_change(name)
            
        self.refresh_workspace()
        
        # Security & Memory: Bind cleanup
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)
        self.win.bind("<Destroy>", self._on_destroy)
        print(f"[DEBUG] Pixel Editor initialized for tile ({self.col}, {self.row})")
        
    def setup_layout(self):
        # 1. Main PanedWindow for Resizable Sidebar
        self.paned = tk.PanedWindow(self.win, orient="horizontal", bg="#222", sashwidth=4, sashrelief="raised")
        self.paned.pack(fill="both", expand=True)

        # --- LEFT SIDEBAR (The Asset Browser) ---
        self.sidebar_f = tk.Frame(self.paned, bg="#222", width=self.sidebar_width)
        
        # Tileset Navigator Dropdown
        nav_f = tk.Frame(self.sidebar_f, bg="#333", pady=5)
        nav_f.pack(fill="x", side="top")
        self.ts_var = tk.StringVar(value="World")
        self.ts_drop_frame = tk.Frame(nav_f, bg="#333") # Container for dynamic replacement
        self.ts_drop_frame.pack(fill="x", padx=10)
        
        self.ts_drop = tk.OptionMenu(self.ts_drop_frame, self.ts_var, "World", command=self._on_tileset_change)
        self.ts_drop.config(bg="#444", fg="white", font=("Arial", 8))
        self.ts_drop.pack(fill="x")

        # Tile Grid Canvas with Scrollbars (Outer container for centering +/- buttons)
        side_outer = tk.Frame(self.sidebar_f, bg="#111")
        side_outer.pack(fill="both", expand=True)

        # Grid setup for anchors
        side_outer.grid_rowconfigure(0, weight=1)
        side_outer.grid_columnconfigure(0, weight=1)

        side_container = tk.Frame(side_outer, bg="#111")
        side_container.grid(row=0, column=0, sticky="nsew")
        
        self.side_scroll_x = tk.Scrollbar(side_container, orient="horizontal", command=self._on_sidebar_scroll_x)
        self.side_scroll_x.pack(side="bottom", fill="x")
        self.side_scroll_y = tk.Scrollbar(side_container, orient="vertical", command=self._on_sidebar_scroll_y)
        self.side_scroll_y.pack(side="right", fill="y")
        
        self.side_canvas = tk.Canvas(side_container, bg="#111", highlightthickness=0, 
                                     xscrollcommand=self.side_scroll_x.set, 
                                     yscrollcommand=self.side_scroll_y.set)
        self.side_canvas.pack(side="left", fill="both", expand=True)
        self.side_canvas.bind("<MouseWheel>", self._on_sidebar_zoom)
        self.side_canvas.bind("<Button-1>", self._on_sidebar_click)

        # --- DYNAMIC RESIZE ANCHORS ---
        # Right Side (Columns)
        col_ctrl = tk.Frame(side_outer, bg="#222", width=25)
        col_ctrl.grid(row=0, column=1, sticky="ns")
        tk.Button(col_ctrl, text="+", command=lambda: self._modify_tileset_size(1, 0),
                  bg="#333", fg="lime", relief="flat", font=("Arial", 10, "bold"), height=2).pack(expand=True, side="top", fill="x")
        tk.Button(col_ctrl, text="-", command=lambda: self._modify_tileset_size(-1, 0),
                  bg="#333", fg="red", relief="flat", font=("Arial", 10, "bold"), height=2).pack(expand=True, side="top", fill="x")

        # Bottom Side (Rows)
        row_ctrl = tk.Frame(side_outer, bg="#222", height=25)
        row_ctrl.grid(row=1, column=0, sticky="ew")
        tk.Button(row_ctrl, text="+", command=lambda: self._modify_tileset_size(0, 1),
                  bg="#333", fg="lime", relief="flat", font=("Arial", 10, "bold"), width=4).pack(expand=True, side="left", fill="y")
        tk.Button(row_ctrl, text="-", command=lambda: self._modify_tileset_size(0, -1),
                  bg="#333", fg="red", relief="flat", font=("Arial", 10, "bold"), width=4).pack(expand=True, side="left", fill="y")
        
        self.paned.add(self.sidebar_f)

        # --- CENTRAL WORKSPACE ---
        self.work_f = tk.Frame(self.paned, bg="#1A1A1A")
        self.paned.add(self.work_f)
        
        # --- WORKSPACE DASHBOARD (Tools + Palette) ---
        self.dash_f = tk.Frame(self.work_f, bg="#333", pady=5)
        self.dash_f.pack(fill="x", side="top")
        
        # Tools Bar
        tool_bar = tk.Frame(self.dash_f, bg="#333")
        tool_bar.pack(fill="x")
        
        tools = [
            ("Pencil", "PENCIL"), ("Eraser", "ERASER"), 
            ("Fill", "FILL"), ("Color Copy", "DROPPER"), 
            ("Copy", "COPY_SELECT")
        ]
        self.tool_btns = {}
        for name, cmd in tools:
            btn = tk.Button(tool_bar, text=name, width=9 if name == "Color Copy" else 6, bg="#444", fg="white", 
                            command=lambda c=cmd, n=name: self.set_tool(c, n))
            btn.pack(side="left", padx=2)
            self.tool_btns[cmd] = btn
            
            # Special binding for Color Copy right-click
            if cmd == "DROPPER":
                btn.bind("<Button-3>", lambda e: self.set_tool("DROPPER", "Color Copy", primary=False))
            
        tk.Label(tool_bar, text="| Size:", bg="#333", fg="gray").pack(side="left", padx=5)
        for s in [1, 2, 4]:
            btn = tk.Button(tool_bar, text=f"{s}px", width=3, bg="#444", fg="white",
                            command=lambda sz=s: self.set_brush(sz))
            btn.pack(side="left", padx=1)

        # Transform & History Block
        trans_f = tk.Frame(tool_bar, bg="#333")
        trans_f.pack(side="left", padx=10)
        
        # Row 1: The Transform buttons
        row1 = tk.Frame(trans_f, bg="#333")
        row1.pack(side="top")
        tk.Button(row1, text="Rot90", command=self.rotate_data, bg="#444", fg="white", width=5, font=("Arial", 7)).pack(side="left", padx=1)
        tk.Button(row1, text="FlipH", command=self.flip_h, bg="#444", fg="white", width=5, font=("Arial", 7)).pack(side="left", padx=1)
        tk.Button(row1, text="FlipV", command=self.flip_v, bg="#444", fg="white", width=5, font=("Arial", 7)).pack(side="left", padx=1)
        
        # Row 2: The History buttons (Undo/Redo)
        row2 = tk.Frame(trans_f, bg="#333")
        row2.pack(side="top", pady=(2, 0))
        tk.Button(row2, text="↩ Undo", command=self.undo, bg="#444", fg="#AFA", width=8, font=("Arial", 7, "bold")).pack(side="left", padx=1)
        tk.Button(row2, text="Redo ↪", command=self.redo, bg="#444", fg="#AAF", width=8, font=("Arial", 7, "bold")).pack(side="left", padx=1)
        
        # --- LOCK BUTTON (Right Side) ---
        self.lock_btn = tk.Button(tool_bar, text="🔓", command=self.toggle_lock,
                                  bg="#444", fg="#AAA", font=("Arial", 12), width=3, relief="raised", bd=2)
        self.lock_btn.pack(side="right", padx=10)

        # Palette Bar (Now Under Tools)
        self.palette_f = tk.Frame(self.work_f, bg="#333", pady=5)
        self.palette_f.pack(fill="x", side="top")
        
        # Color Preview (Left/Right)
        self.preview_f = tk.Frame(self.palette_f, bg="#2a2a2a", padx=5)
        self.preview_f.pack(side="left")
        
        self.palette_swatches = [] # Cache for persistent SWATCHES
        self.rebuild_palette()

        # Workspace Canvas with Scrollbars
        self.canvas_container = tk.Frame(self.work_f, bg="#111", bd=2, relief="sunken")
        self.canvas_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.scroll_x = tk.Scrollbar(self.canvas_container, orient="horizontal", command=self._on_scroll_x)
        self.scroll_x.pack(side="bottom", fill="x")
        self.scroll_y = tk.Scrollbar(self.canvas_container, orient="vertical", command=self._on_scroll_y)
        self.scroll_y.pack(side="right", fill="y")
        
        self.canvas = tk.Canvas(self.canvas_container, bg="#000", highlightthickness=0,
                                xscrollcommand=self.scroll_x.set, yscrollcommand=self.scroll_y.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.bind("<MouseWheel>", self._on_main_zoom)
        
        # Debounced Resize Logic
        self._resize_job = None
        self.win.bind("<Configure>", self._on_window_resize)

        self.canvas.bind("<Button-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        
        self.canvas.bind("<Button-3>", self.on_press) # Right Click
        self.canvas.bind("<B3-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-3>", self.on_release)

    def _on_window_resize(self, event):
        if self._resize_job: self.win.after_cancel(self._resize_job)
        self._resize_job = self.win.after(100, self._perform_full_refresh)

    def _perform_full_refresh(self):
        self._resize_job = None
        # Track the actual width of the sidebar from the paned window
        try:
            self.sidebar_width = self.sidebar_f.winfo_width()
        except: pass
        self._refresh_sidebar()
        self.refresh_workspace()

    def setup_menus(self):
        m = tk.Menu(self.win)
        
        # 1. FILE MENU (Cleaned up)
        f = tk.Menu(m, tearoff=0)
        f.add_command(label="Export THIS Tile as PNG...", command=self._export_png)
        f.add_separator()
        f.add_command(label="Exit", command=self.win.destroy)
        m.add_cascade(label="File", menu=f)
        
        # 2. TOP-LEVEL SAVE (Instant Actuation)
        m.add_command(label="Save", command=self._commit_project)
        
        self.win.config(menu=m)

    def rebuild_palette(self):
        """ Creates the palette UI elements once. """
        for w in self.palette_f.winfo_children(): w.destroy()
        self.palette_swatches = []
        
        # 1. Color Previews (Current Primary / Secondary)
        self.l_prev_canvas = tk.Canvas(self.palette_f, width=24, height=24, bg=self.current_color, highlightthickness=2, highlightbackground="#555")
        self.l_prev_canvas.pack(side="left", padx=2)
        
        self.r_prev_canvas = tk.Canvas(self.palette_f, width=24, height=24, bg=self.secondary_color, highlightthickness=2, highlightbackground="#555")
        self.r_prev_canvas.pack(side="left", padx=2)

        # 2. Main Palette Swatches
        swatch_f = tk.Frame(self.palette_f, bg="#2a2a2a", padx=10)
        swatch_f.pack(side="left")

        for i in range(len(self.palette_colors)):
            c = self.palette_colors[i]
            btn = tk.Canvas(swatch_f, width=22, height=22, bg=c, highlightthickness=1)
            btn.pack(side="left", padx=2)
            
            # Left Click: Set Primary
            btn.bind("<Button-1>", lambda e, idx=i: self.set_color_by_index(idx, primary=True))
            # Right Click: Set Secondary
            btn.bind("<Button-3>", lambda e, idx=i: self.set_color_by_index(idx, primary=False))
            # Double Click: Edit this slot
            btn.bind("<Double-Button-1>", lambda e, idx=i: self._pick_new_color_by_index(idx))
            
            self.palette_swatches.append(btn)
        
        # Instruction Label
        tk.Label(self.palette_f, text="Double click to change colors", fg="#777", bg="#2a2a2a", font=("Arial", 8, "italic")).pack(side="left", padx=10)
        
        self.update_palette_ui()

    def update_palette_ui(self):
        """ Updates existing widgets without destroying them (Preserves Double-Clicks). """
        self.l_prev_canvas.config(bg=self.current_color)
        self.r_prev_canvas.config(bg=self.secondary_color)
        
        for i, btn in enumerate(self.palette_swatches):
            c = self.palette_colors[i]
            border = "#444"
            if c == self.current_color: border = "white"
            elif c == self.secondary_color: border = "#AAA"
            btn.config(bg=c, highlightbackground=border)

    def refresh_workspace(self):
        self.canvas.delete("all")
        grid_pix = self.tile_size * self.zoom
        off_x, off_y = 50, 50
        
        # --- 1. OPTIMIZED CHECKERBOARD BG (Low Object Count) ---
        # Draw one big dark base
        self.canvas.create_rectangle(off_x, off_y, off_x + grid_pix, off_y + grid_pix, fill="#111", outline="")
        # Draw a single grid of subtle larger 'transparency blocks'
        bs = self.zoom 
        for y in range(self.tile_size):
            for x in range(self.tile_size):
                if (x + y) % 2 == 0:
                    px, py = off_x + x * bs, off_y + y * bs
                    self.canvas.create_rectangle(px, py, px + bs, py + bs, fill="#181818", outline="")

        # --- 2. PIXEL DATA ---
        for y in range(self.tile_size):
            for x in range(self.tile_size):
                r, g, b, a = self.image.getpixel((x, y))
                if a > 0:
                    px, py = off_x + x * self.zoom, off_y + y * self.zoom
                    hex_c = '#{:02x}{:02x}{:02x}'.format(r, g, b)
                    self.canvas.create_rectangle(px, py, px + self.zoom, py + self.zoom, fill=hex_c, outline="")

        # --- 3. PRECISION GRID OVERLAY (0.5px Style) ---
        grid_color = "#2a2a2a"
        for i in range(self.tile_size + 1):
            lx = off_x + i * self.zoom
            self.canvas.create_line(lx, off_y, lx, off_y + grid_pix, fill=grid_color, width=1)
            ly = off_y + i * self.zoom
            self.canvas.create_line(off_x, ly, off_x + grid_pix, ly, fill=grid_color, width=1)
            
        # Update Scrollregion
        self.canvas.config(scrollregion=(0, 0, grid_pix + 100, grid_pix + 100))

    def _on_scroll_x(self, *args): self.canvas.xview(*args)
    def _on_scroll_y(self, *args): self.canvas.yview(*args)

    def _on_main_zoom(self, event):
        if event.state & 0x0004: # Control Key
            old_zoom = self.zoom
            mx, my = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
            
            self.zoom = min(80, max(5, self.zoom + (2 if event.delta > 0 else -2)))
            if old_zoom == self.zoom: return
            
            self.refresh_workspace()
            
            # Center zoom logic - must account for 50px offset (off_x/off_y)
            stride = self.tile_size * self.zoom + 100
            ratio = self.zoom / old_zoom
            
            # Corrected formula: offset + (original_rel_pos * ratio)
            new_mx = 50 + (mx - 50) * ratio
            new_my = 50 + (my - 50) * ratio
            
            self.canvas.xview_moveto((new_mx - event.x) / stride)
            self.canvas.yview_moveto((new_my - event.y) / stride)
        else:
            # Vertical Scroll
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # --- TOOLS LOGIC ---
    def set_tool(self, t, name=None, primary=True): 
        print(f"[DEBUG] Tool switched to: {name or t} (Primary: {primary})")
        self.active_tool = t
        self.dropper_target_primary = primary # Track if dropper is for L or R
        
        # Reset all button reliefs
        for cmd, btn in self.tool_btns.items():
            btn.config(relief="raised", bg="#444")
            
        # Set active relief
        if t in self.tool_btns:
            self.tool_btns[t].config(relief="sunken", bg="#666")

        if t == "COPY_SELECT":
            self.canvas.config(cursor="crosshair")
            print("[DEBUG] Copy Tool: Select a region to copy.")
        elif t == "PASTE":
            self.canvas.config(cursor="plus")
            print("[DEBUG] Paste Tool: Click to place the copied pixels.")
        else:
            self.canvas.config(cursor="")
            self.side_canvas.config(cursor="")
            
    def set_brush(self, s): 
        print(f"[DEBUG] Brush size set to: {s}px")
        self.brush_size = s
    def set_color_by_index(self, idx, primary=True):
        c = self.palette_colors[idx]
        self.set_color(c, primary)

    def set_color(self, c, primary=True): 
        if primary:
            self.current_color = c
        else:
            self.secondary_color = c
        self.update_palette_ui()

    def _push_undo(self):
        """ Captures a deep copy of the current state for the undo stack. """
        # We push a copy of the image
        self.undo_stack.append(self.image.copy())
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)
        # Redo stack is cleared on ANY new interaction
        self.redo_stack.clear()
        
    def undo(self):
        if not self.undo_stack: return
        # Push current to redo
        self.redo_stack.append(self.image.copy())
        # Pop from undo
        self.image = self.undo_stack.pop()
        self.refresh_workspace()
        self._soft_save()
        self._hard_save()
        if self.callback: self.callback(self.image)
        DebugUtils.log("Undo performed.")

    def redo(self):
        if not self.redo_stack: return
        # Push current back to undo
        self.undo_stack.append(self.image.copy())
        # Restore from redo
        self.image = self.redo_stack.pop()
        self.refresh_workspace()
        self._soft_save()
        self._hard_save()
        if self.callback: self.callback(self.image)
        DebugUtils.log("Redo performed.")

    def _soft_save(self):
        """ Instantly updates the sidebar to reflect edits in memory. """
        if hasattr(self, 'full_tileset_img'):
            # Paste our current 16x16 edit back into the master sheet in memory
            self.full_tileset_img.paste(self.image, (self.col*16, self.row*16))
            self._refresh_sidebar()

    def _hard_save(self):
        """ Flushes the memory buffer to the physical PNG file on disk. """
        if hasattr(self, 'full_tileset_img') and self.current_tileset_path:
            try:
                # --- THREAD SYNCHRONIZATION ---
                # We acquire the central project lock to prevent the Tileset Editor
                # and this Pixel Suite from trampling on each other's I/O.
                lock = self.save_manager.io_lock if self.save_manager else None
                if lock: lock.acquire()

                # --- ATOMIC DISPLACEMENT ---
                # We save to a sidecar (.tmp) and perform an OS swap.
                # This ensures the master PNG never ends up as a 0-byte corrupted mess.
                temp = self.current_tileset_path + ".tmp"
                self.full_tileset_img.save(temp, format="PNG")
                os.replace(temp, self.current_tileset_path)

                if lock: lock.release()
                print(f"[DEBUG] Auto-saved tileset: {os.path.basename(self.current_tileset_path)}")
                if self.save_manager:
                    self.save_manager.mark_dirty()
            except Exception as e:
                print(f"[ERROR] Auto-save failed: {e}")

    def toggle_lock(self):
        """ Toggles the editing lock. """
        self.is_locked = not self.is_locked
        if self.is_locked:
            self.lock_btn.config(text="🔒", bg="#600", fg="white", relief="sunken")
            print("[DEBUG] Editor LOCKED. Interaction disabled.")
        else:
            self.lock_btn.config(text="🔓", bg="#444", fg="#AAA", relief="raised")
            print("[DEBUG] Editor UNLOCKED.")

    def on_press(self, event):
        if self.is_locked:
            if self.active_tool not in ["DROPPER", "MARQUEE", "COPY_SELECT"]:
                return
        # FIX: Store start position in CANVAS coordinates so marquee stays put during scroll/zoom
        self.start_x = self.side_canvas.canvasx(event.x) if event.widget == self.side_canvas else self.canvas.canvasx(event.x)
        self.start_y = self.side_canvas.canvasy(event.y) if event.widget == self.side_canvas else self.canvas.canvasy(event.y)
        
        if self.active_tool in ["PENCIL", "ERASER", "FILL", "DROPPER", "PASTE"]:
            if self.active_tool not in ["DROPPER", "PASTE"]: self._push_undo()
            self.on_drag(event)

    def on_drag(self, event):
        if self.is_locked:
            # Only allow non-editing tools if locked
            if self.active_tool not in ["DROPPER", "MARQUEE"]:
                return
        ox, oy = 50, 50
        # FIX: Use canvasx/y to account for scrolling!
        cx, cy = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        tx, ty = int((cx - ox) // self.zoom), int((cy - oy) // self.zoom)
        
        # Determine color based on mouse button (1=Left, 3=Right)
        is_right_click = (event.num == 3) or (event.state & 0x400) 
        
        active_color = self.current_color if not is_right_click else self.secondary_color
        
        if 0 <= tx < self.tile_size and 0 <= ty < self.tile_size:
            if self.active_tool == "PENCIL":
                self._draw_pixel(tx, ty, active_color)
            elif self.active_tool == "ERASER":
                self._draw_pixel(tx, ty, None)
            elif self.active_tool == "FILL":
                self._flood_fill(tx, ty, active_color)
            elif self.active_tool == "DROPPER":
                r,g,b,a = self.image.getpixel((tx, ty))
                if a > 0: 
                    new_c = '#{:02x}{:02x}{:02x}'.format(r,g,b)
                    self.set_color(new_c, primary=getattr(self, 'dropper_target_primary', True))
                    # Auto-reset to pencil after picking
                    self.set_tool("PENCIL", "Pencil")
            elif self.active_tool == "MARQUEE" or self.active_tool == "COPY_SELECT":
                self._draw_marquee(event.x, event.y)
            elif self.active_tool == "PASTE":
                self._paste_clipboard(tx, ty)
        
    def on_release(self, event):
        if self.active_tool == "MARQUEE" or self.active_tool == "COPY_SELECT":
            ox, oy = 50, 50
            # FIX: Translate release pos to canvas space
            ex, ey = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
            
            x1, y1 = int((self.start_x - ox) // self.zoom), int((self.start_y - oy) // self.zoom)
            x2, y2 = int((ex - ox) // self.zoom), int((ey - oy) // self.zoom)
            self.selection = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
            
            if self.active_tool == "COPY_SELECT":
                self.copy_selection()
                self.set_tool("PASTE", "Paste")
        
        # --- AUTO-SAVE ON RELEASE ---
        self._hard_save()
        if self.callback: self.callback(self.image)
        self.refresh_workspace()

    def _draw_pixel(self, x, y, color):
        rgb = tuple(int(color[i:i+2], 16) for i in (1, 3, 5)) if color else (0,0,0,0)
        draw = ImageDraw.Draw(self.image)
        rad = self.brush_size - 1
        draw.rectangle([x, y, x+rad, y+rad], fill=rgb)
        self.refresh_workspace()
        self._soft_save()

    def _flood_fill(self, x, y, color):
        if self.is_locked: return
        target = self.image.getpixel((x, y))
        rgb = tuple(int(color[i:i+2], 16) for i in (1, 3, 5)) + (255,)
        if target == rgb: return
        
        q = collections.deque([(x, y)])
        while q:
            cx, cy = q.popleft()
            if self.image.getpixel((cx, cy)) == target:
                self.image.putpixel((cx, cy), rgb)
                for nx, ny in [(cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)]:
                    if 0 <= nx < self.tile_size and 0 <= ny < self.tile_size:
                        q.append((nx, ny))
        self.refresh_workspace()
        self._soft_save()
        self._hard_save()
        if self.callback: self.callback(self.image)

    # --- TRANSFORMS ---
    def rotate_data(self): 
        if self.is_locked: return
        self._push_undo()
        self.image = self.image.rotate(-90)
        self.refresh_workspace()
        self._soft_save()
        self._hard_save()
        if self.callback: self.callback(self.image)
        
    def flip_h(self): 
        if self.is_locked: return
        self._push_undo()
        self.image = self.image.transpose(Image.FLIP_LEFT_RIGHT)
        self.refresh_workspace()
        self._soft_save()
        self._hard_save()
        if self.callback: self.callback(self.image)
        
    def flip_v(self): 
        if self.is_locked: return
        self._push_undo()
        self.image = self.image.transpose(Image.FLIP_TOP_BOTTOM)
        self.refresh_workspace()
        self._soft_save()
        self._hard_save()
        if self.callback: self.callback(self.image)

    # --- CLIPBOARD ---
    def copy_selection(self):
        if self.selection:
            self.clipboard = self.image.crop(self.selection)
            print("[DEBUG] Selection copied.")

    def _paste_clipboard(self, x, y):
        if self.is_locked: return
        if self.clipboard:
            self._push_undo()
            # Center the paste relative to the click
            px = x - self.clipboard.width // 2
            py = y - self.clipboard.height // 2
            self.image.paste(self.clipboard, (px, py))
            self.refresh_workspace()
            self._soft_save()
            self._hard_save()
            if self.callback: self.callback(self.image)

    def _draw_marquee(self, ex, ey):
        self.canvas.delete("marquee")
        # ex/ey passed here are widget coords; convert to canvas for drawing
        cx, cy = self.canvas.canvasx(ex), self.canvas.canvasy(ey)
        self.canvas.create_rectangle(self.start_x, self.start_y, cx, cy, outline="white", dash=(4,4), tags="marquee")

    # --- SIDEBAR LOGIC ---
    def _on_sidebar_scroll_x(self, *args): self.side_canvas.xview(*args)
    def _on_sidebar_scroll_y(self, *args): self.side_canvas.yview(*args)

    def _on_sidebar_zoom(self, event):
        if event.state & 0x0004: # Control Key
            old_zoom = self.sidebar_zoom
            mx = self.side_canvas.canvasx(event.x)
            my = self.side_canvas.canvasy(event.y)
            
            self.sidebar_zoom = min(4.0, max(0.2, self.sidebar_zoom + (0.1 if event.delta > 0 else -0.1)))
            
            if old_zoom == self.sidebar_zoom: return
            
            # Redraw sidebar to update scrollregion
            self._refresh_sidebar()
            
            # Centering Logic
            sr = self.side_canvas.cget("scrollregion").split()
            if len(sr) == 4:
                full_w, full_h = float(sr[2]), float(sr[3])
                ratio = self.sidebar_zoom / old_zoom
                if full_w > 0 and full_h > 0:
                    self.side_canvas.xview_moveto((mx * ratio - event.x) / full_w)
                    self.side_canvas.yview_moveto((my * ratio - event.y) / full_h)
        else:
            # Vertical Scroll
            self.side_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_sidebar_click(self, event):
        if not hasattr(self, 'full_tileset_img'): return
        tw, th = self.full_tileset_img.size
        ts_cols = tw // 16
        ts_rows = th // 16

        cx, cy = self.side_canvas.canvasx(event.x), self.side_canvas.canvasy(event.y)
        
        gap = 4
        sz = int(16 * self.sidebar_zoom)
        
        # FIX: Align click math with visual grid (use actual columns, not window width)
        items_per_row = ts_cols
        
        grid_c = int((cx - 5) // (sz + gap))
        grid_r = int((cy - 5) // (sz + gap))
        
        if grid_c < 0 or grid_c >= items_per_row: return
        idx = grid_r * items_per_row + grid_c
        
        if 0 <= idx < (ts_cols * ts_rows):
            src_c = idx % ts_cols
            src_r = idx // ts_cols
            
            # --- COPY/PASTE LOGIC ---
            if self.active_tool == "COPY_TILE" and self.clipboard:
                # Paste clipboard into the master sheet at THIS clicked location
                self.full_tileset_img.paste(self.clipboard, (src_c*16, src_r*16))
                print(f"[DEBUG] Stamped tile to ({src_c}, {src_r})")
                self.set_tool("PENCIL")
                self._refresh_sidebar()
                self._hard_save() # Save the stamp immediately
            else:
                # Normal Switch
                self.image = self.full_tileset_img.crop((src_c*16, src_r*16, (src_c+1)*16, (src_r+1)*16))
                self.col, self.row = src_c, src_r
                self.refresh_workspace()
                self._refresh_sidebar()

    def _refresh_dropdown(self):
        """ Bidirectional Sync: script defines <-> disk files. """
        self.tileset_map = {}
        if not self.tileset_dir or not os.path.exists(self.tileset_dir): return

        project_path = self.save_manager.project_path if self.save_manager else None
        if not project_path: return

        import ScriptParser
        # 1. Get definitions from script
        script_names = ScriptParser.get_all_tilesets(project_path)
        
        # 2. Scan physical disk
        disk_files = [f for f in os.listdir(self.tileset_dir) if f.lower().endswith(".png")]
        
        # 3. Create Bidirectional Map
        for name in script_names:
            # Standard mapping: World -> World_TILESET.png or World.png
            possible = [f"{name}_TILESET.png", f"{name}.png"]
            found = False
            for p in possible:
                # Case-insensitive match on disk
                for df in disk_files:
                    if df.lower() == p.lower():
                        self.tileset_map[name.capitalize()] = df
                        found = True
                        break
                if found: break
            if not found:
                # Definition exists but file is missing? Map to default guess.
                self.tileset_map[name.capitalize()] = f"{name}_TILESET.png"

        # 4. Auto-Register new files found on disk but not in script
        needs_def = False
        for df in disk_files:
            # Reverse map: "World_TILESET.png" -> "WORLD"
            core_name = df.replace("_TILESET.png", "").replace(".png", "").upper()
            if core_name not in script_names:
                DebugUtils.log(f"Auto-registering tileset define: {core_name}")
                self._register_tileset_define(core_name)
                needs_def = True
        
        if needs_def:
            # Re-read if we just added some
            script_names = ScriptParser.get_all_tilesets(project_path)
            for name in script_names:
                self.tileset_map[name.capitalize()] = f"{name}_TILESET.png"

        # --- REBUILD DROPDOWN ---
        if hasattr(self, 'ts_drop_frame'):
            for w in self.ts_drop_frame.winfo_children(): w.destroy()
            options = sorted(list(self.tileset_map.keys())) if self.tileset_map else ["World"]
            
            # Use current if valid, else pick first or World
            current = self.ts_var.get()
            if not current or current not in options:
                self.ts_var.set(options[0])

            self.ts_drop = tk.OptionMenu(self.ts_drop_frame, self.ts_var, *options, command=self._on_tileset_change)
            self.ts_drop.config(bg="#444", fg="white", font=("Arial", 8), width=15)
            self.ts_drop.pack(fill="x")

    def _register_tileset_define(self, name):
        """ Appends a new TILESET_ define to Defines.hry. """
        if not self.save_manager: return
        path = os.path.join(self.save_manager.project_path, "HAIRY", "Defines.hry")
        if os.path.exists(path):
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"DEFINE GLOBAL TILESET_{name.upper()} 0 // Auto-Registered\n")

    def _on_tileset_change(self, val):
        if not self.tileset_dir: return
        if not val or val not in self.tileset_map:
            # Fallback to case-insensitive or first available
            matched = None
            for k in self.tileset_map.keys():
                if k.lower() == str(val).lower():
                    matched = k
                    break
            if matched:
                val = matched
            elif self.tileset_map:
                val = list(self.tileset_map.keys())[0]
            else:
                return

        self.current_tileset_path = os.path.join(self.tileset_dir, self.tileset_map[val])
        if os.path.exists(self.current_tileset_path):
            lock = self.save_manager.io_lock if self.save_manager else None
            try:
                if lock: lock.acquire()
                with Image.open(self.current_tileset_path) as img:
                    self.full_tileset_img = img.convert("RGBA")
            finally:
                if lock: lock.release()
            self._refresh_sidebar()

    def _refresh_sidebar(self):
        if not hasattr(self, 'full_tileset_img'): return
        self.side_canvas.delete("all")
        self.tileset_photo_chunks.clear()
        
        sw = self.win.winfo_width() / 4 
        gap = 4
        sz = int(16 * self.sidebar_zoom)
        
        tw, th = self.full_tileset_img.size
        cols, rows = tw // 16, th // 16
        total_items = cols * rows
        
        # FIX: Hold the actual dimensions of the tileset, do not wrap/continue past
        items_per_row = cols 
        total_rows = rows
        
        # 1. Update Scroll Region
        # Full content width is now the ACTUAL cols * zoom
        content_w = items_per_row * (sz + gap) + 20
        full_w = max(self.sidebar_width, content_w)
        full_h = total_rows * (sz + gap) + 20
        self.side_canvas.config(scrollregion=(0, 0, full_w, full_h))
        
        # 2. Virtualization: Find visible rows
        ch = self.side_canvas.winfo_height()
        if ch <= 1: ch = 600
        vy1, vy2 = self.side_canvas.canvasy(0), self.side_canvas.canvasy(ch)
        
        row_start = max(0, int(vy1 // (sz + gap)))
        row_end = min(total_rows, int(vy2 // (sz + gap)) + 1)

        # 3. Only render visible tiles
        for r_idx in range(row_start, row_end):
            for c_idx in range(items_per_row):
                i = r_idx * items_per_row + c_idx
                if i >= total_items: break
                
                # Logical source coords from full_tileset_img
                src_c = i % cols
                src_r = i // cols
                
                x, y = c_idx * (sz + gap) + 5, r_idx * (sz + gap) + 5
                
                # VISUAL GRID: Draw a subtle slot even if tile is transparent
                self.side_canvas.create_rectangle(x, y, x+sz, y+sz, outline="#222", fill="#0a0a0a", tags="tile")

                # Crop & Size
                chunk = self.full_tileset_img.crop((src_c*16, src_r*16, (src_c+1)*16, (src_r+1)*16))
                if self.sidebar_zoom != 1.0:
                    chunk = chunk.resize((sz, sz), Image.NEAREST)
                
                tkc = ImageTk.PhotoImage(chunk)
                self.tileset_photo_chunks.append(tkc)
                
                # Highlight Active
                if src_c == self.col and src_r == self.row:
                    self.side_canvas.create_rectangle(x-2, y-2, x+sz+2, y+sz+2, fill="#446", outline="yellow", tags="tile")
                
                self.side_canvas.create_image(x, y, image=tkc, anchor="nw", tags="tile")

    def _modify_tileset_size(self, d_cols, d_rows):
        """ Dynamically expand or shrink the tileset image (16px steps). """
        if not hasattr(self, 'full_tileset_img') or not self.current_tileset_path: return
        
        tw, th = self.full_tileset_img.size
        cols, rows = tw // 16, th // 16
        
        new_cols = max(1, cols + d_cols)
        new_rows = max(1, rows + d_rows)
        
        if new_cols == cols and new_rows == rows: return
        
        # Destruction Guard: Confirm before deleting data
        if new_cols < cols or new_rows < rows:
            if not messagebox.askyesno("Shrink Tileset?", 
                                       "This will permanently remove tiles from the edge. Continue?", 
                                       parent=self.win):
                return

        # Perform atomic resize in memory
        new_w, new_h = new_cols * 16, new_rows * 16
        new_img = Image.new("RGBA", (new_w, new_h), (0,0,0,0))
        new_img.paste(self.full_tileset_img, (0, 0))
        self.full_tileset_img = new_img
        
        # Follow the Growth: Snap selection to the new edge if we expanded
        if d_cols > 0: self.col = new_cols - 1
        if d_rows > 0: self.row = new_rows - 1

        # Correct active selection bounds (Clamping)
        self.col = max(0, min(self.col, new_cols - 1))
        self.row = max(0, min(self.row, new_rows - 1))
        
        # Flush to disk & update UI
        self._hard_save()
        self.win.update_idletasks() # Force UI to catch up
        self._refresh_sidebar()
        self.refresh_workspace() # Load the newly selected tile data
        print(f"[DEBUG] Tileset successfully resized to {new_cols}x{new_rows} tiles.")

    def _pick_new_color_by_index(self, index):
        old = self.palette_colors[index]
        # Attach the color wheel to 'self.win' (Pixel Editor) so it doesn't pull the main window to front
        c = colorchooser.askcolor(initialcolor=old, parent=self.win, title="Modify Palette Color")[1]
        if c:
            self.palette_colors[index] = c
            self.set_color(c, primary=True)
            self.update_palette_ui()
            # Update the permanent palette if an index was provided
            if index is not None:
                self.palette_colors[index] = c
            # Also add to recent
            if c not in self.recent_colors:
                self.recent_colors.appendleft(c)
            self.rebuild_palette()

    def _commit_project(self):
        """ Hard Save to disk and update parent if alive """
        self._hard_save()
        if self.callback: 
            # If we are expanded, we might need the parent to reload the whole sheet
            if hasattr(self.parent, 'refresh_view'):
                self.parent.refresh_view()
            else:
                self.callback(self.image)
        print("[DEBUG] Manual save triggered: Disk flush complete.")

    def _export_png(self):
        """ Exports only the individual tile currently being edited """
        p = filedialog.asksaveasfilename(defaultextension=".png", title="Export Individual Tile")
        if p: 
            self.image.save(p)
            print(f"[DEBUG] Exported tile to {p}")

    def _on_close(self):
        """ Explicit shutdown handler """
        print(f"[DEBUG] Closing Pixel Editor...")
        self.win.destroy()

    def _on_destroy(self, event):
        """ Memory Management: Release large asset references """
        if event.widget == self.win:
            print("[DEBUG] Releasing Pixel Editor resources...")
            self.image = None
            self.full_tileset_img = None
            self.tileset_photo_chunks.clear()
            self.clipboard = None
