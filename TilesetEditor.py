import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import os
import shutil
import config
import threading
from PIL import Image, ImageTk, ImageDraw
import PixelEditor # NEW Module
import AnimationEditor
import ScriptParser
import sys
import json
from PIL import ImageChops
import re
from DebugUtils import DebugUtils

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev, PyInstaller, and Nuitka """
    import sys
    import os
    
    # 1. Check for PyInstaller temp folder
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
        
    # 2. Check for Frozen execution (Nuitka / Other)
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), relative_path)
        
    # 3. Default to current working directory (Dev mode)
    return os.path.join(os.path.abspath("."), relative_path)

from EditorComponents import center_window

class TilesetEditor:
    """
    A standalone Toplevel window for managing tileset assets.
    Optimized for multi-threaded performance and UI stability.
    Hardened for atomic data integrity and concurrent I/O.
    """
    def __init__(self, parent, save_manager):
        print("[DEBUG] Initializing Tileset Editor window...")
        self.parent = parent
        self.save_manager = save_manager
        
        self.win = tk.Toplevel(parent)
        self.win.title(f"{config.APP_TITLE} [Active Engine] - Tileset Editor")
        
        # Standardized Centering
        center_window(self.win, parent, 950, 650)
        
        self.win.configure(bg=config.COLOR_BG)
        
        # --- ICON ---
        icon_path = resource_path(os.path.join("Assets", "TileIcon.png"))
        if os.path.exists(icon_path):
            try:
                self._win_icon = ImageTk.PhotoImage(Image.open(icon_path))
                self.win.iconphoto(False, self._win_icon)
            except: pass
        
        # --- DATA ---
        if not self.save_manager.project_path:
            messagebox.showerror("Error", "No project active.", parent=self.win)
            self.win.destroy()
            return

        self.tileset_dir = os.path.join(self.save_manager.project_path, "TILESET")
        self.tile_size = self.save_manager.project_data.get("tile_size", 16)
        self.active_file = None
        self.zoom = 3.0
        self.base_image = None
        self._zoom_job = None
        self._last_load_id = 0
        self.tk_image_chunks = []
        self.selection_rect = None
        self.selected_tile = (0, 0)
        
        # --- PROPERTIES ENGINE (Pure-Script Architecture) ---
        self.all_props = ScriptParser.parse_tile_properties(self.save_manager.project_path)
        
        # --- TOOL ENGINE ---
        self.active_tool = "SELECT"
        self.clipboard_img = None
        self.tileset_map = {} # Master registry initialized before UI
        
        # --- SECURITY & CONCURRENCY ---
        self.io_lock = self.save_manager.io_lock # Shared project lock
        
        # Setup UI
        self.setup_ui()
        
        # Bindings
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Double-Button-1>", lambda e: self.open_pixel_editor())
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<Shift-MouseWheel>", self.on_mouse_wheel_x)
        self.canvas.bind("<ButtonPress-2>", self.pan_start)
        self.canvas.bind("<B2-Motion>", self.pan_move)
        
        # Throttling
        self._redraw_job = None
        
        self.win.update_idletasks()
        
        # Memory & Security
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)
        self.win.bind("<Destroy>", self._on_destroy)
        if self.tileset_dir:
            self._refresh_dropdown()
        self._refresh_prop_ui() # Ensure default tile (0,0) properties show on start

    def setup_ui(self):
        # --- 1. TOP HEADER (Command Hub) ---
        top_frame = tk.Frame(self.win, bg=config.COLOR_TITLE_BAR, pady=8)
        top_frame.pack(fill="x", side="top")
        self.top_f_ref = top_frame # Ref for layout positioning
        
        tk.Button(top_frame, text="💾 Save Project", command=self.hard_save_project, 
                  bg="#1a1", fg="white", font=config.FONT_TITLE, relief="raised", bd=1).pack(side="left", padx=(10, 20))

        tk.Label(top_frame, text="Active Tileset:", bg=config.COLOR_TITLE_BAR, fg=config.COLOR_TITLE_TEXT, font=config.FONT_TITLE).pack(side="left", padx=5)
        self.selected_name = tk.StringVar()
        self.dropdown_frame = tk.Frame(top_frame, bg=config.COLOR_TITLE_BAR)
        self.dropdown_frame.pack(side="left")

        tk.Frame(top_frame, width=20, bg=config.COLOR_TITLE_BAR).pack(side="left")
        tk.Button(top_frame, text="📥 New Tileset...", command=self.add_new_tileset, bg="#444", fg="lime", relief="raised", bd=1).pack(side="left", padx=5)
        tk.Button(top_frame, text="🔄 Import/Swap...", command=self.import_tileset, bg=config.COLOR_BG, relief="raised", bd=1).pack(side="left", padx=5)
        tk.Button(top_frame, text="📤 Export PNG...", command=self.export_tileset, bg=config.COLOR_BG, relief="raised", bd=1).pack(side="left", padx=5)
        
        self.zoom_label = tk.Label(top_frame, text="Zoom: 180%", bg=config.COLOR_TITLE_BAR, fg="white", font=config.FONT_UI)
        self.zoom_label.pack(side="right", padx=20)

        # --- 2. BOTTOM TOOLBAR (Tactical Hub) ---
        bot_frame = tk.Frame(self.win, bg=config.COLOR_BG, pady=10, relief="sunken", bd=1)
        bot_frame.pack(fill="x", side="bottom")

        grid_f = tk.LabelFrame(bot_frame, text="Grid", bg=config.COLOR_BG, fg="white", font=("Arial", 8))
        grid_f.pack(side="left", padx=5)
        tk.Button(grid_f, text="+C", width=3, command=self.add_column, bg="#444", fg="white").pack(side="left", padx=2)
        tk.Button(grid_f, text="-C", width=3, command=self.remove_column, bg="#444", fg="white").pack(side="left", padx=2)
        tk.Button(grid_f, text="+R", width=3, command=self.add_row, bg="#444", fg="white").pack(side="left", padx=10)
        tk.Button(grid_f, text="-R", width=3, command=self.remove_row, bg="#444", fg="white").pack(side="left", padx=2)
        
        clip_f = tk.LabelFrame(bot_frame, text="Clipboard", bg=config.COLOR_BG, fg="white", font=("Arial", 8))
        clip_f.pack(side="left", padx=15)
        tk.Button(clip_f, text="Copy", width=6, command=self.copy_tile, bg=config.COLOR_BG).pack(side="left", padx=2)
        tk.Button(clip_f, text="Swap", width=6, command=self.start_swap, bg=config.COLOR_BG).pack(side="left", padx=2)
        
        trans_f = tk.LabelFrame(bot_frame, text="Transform", bg=config.COLOR_BG, fg="white", font=("Arial", 8))
        trans_f.pack(side="left", padx=5)
        tk.Button(trans_f, text="FlipH", width=6, command=self.flip_h, bg=config.COLOR_BG).pack(side="left", padx=2)
        tk.Button(trans_f, text="FlipV", width=6, command=self.flip_v, bg=config.COLOR_BG).pack(side="left", padx=2)
        tk.Button(trans_f, text="Rot90", width=6, command=self.rotate_tile, bg=config.COLOR_BG).pack(side="left", padx=2)
        
        misc_f = tk.LabelFrame(bot_frame, text="Misc", bg=config.COLOR_BG, fg="white", font=("Arial", 8))
        misc_f.pack(side="left", padx=15)
        tk.Button(misc_f, text="Pixel Edit", width=8, command=self.open_pixel_editor, bg="#446", fg="white").pack(side="left", padx=2)
        tk.Button(misc_f, text="CLEAR", width=6, command=self.clear_tile, bg="#933", fg="white").pack(side="left", padx=2)

        self.status_label = tk.Label(bot_frame, text="Ready", bg=config.COLOR_BG, font=("Arial", 8, "italic"), fg="#444")
        self.status_label.pack(side="right", padx=10)
        # --- 3. PROPERTIES PANE (Ultra-Thin Ribbon) ---
        self.prop_f = tk.Frame(self.win, bg="#333", pady=0, bd=1, relief="sunken")
        self.prop_f.pack(fill="x", side="top")
        self.prop_target_h = 40 # ULTRA-THIN
        self.prop_f.pack_propagate(False)
        self.prop_f.config(height=self.prop_target_h)
        self._anim_job = None
        
        self.prop_keys = [
            ("Blocked", "block_move"), ("VisBlocked", "block_vis"), ("Can't Fly", "block_fly"),
            ("BlockProjectiles", "block_proj"), ("BlockMagic", "block_magic"), ("CanSail", "sailable"),
            ("Light", "light"), ("Is Window", "window"), ("Slow", "slow"), ("Anim", "animated"),
            ("Occ", "occlusion")
        ]
        self.prop_vars = {}
        
        # --- SINGLE HORIZONTAL RIBBON ---
        ribbon = tk.Frame(self.prop_f, bg="#333", padx=5)
        ribbon.pack(fill="both", expand=True)
        
        # Part A: Identity (Left)
        id_f = tk.Frame(ribbon, bg="#333")
        id_f.pack(side="left", padx=(0, 15))
        
        tk.Label(id_f, text="Name:", bg="#333", fg="white", font=("Arial", 7, "bold")).pack(side="left")
        self.tile_name_var = tk.StringVar()
        self.tile_name_entry = tk.Entry(id_f, textvariable=self.tile_name_var, bg="#222", fg="lime", 
                                         insertbackground="white", width=12, bd=0, font=("Arial", 8))
        self.tile_name_entry.pack(side="left", padx=5)
        self.tile_name_entry.bind("<Return>", lambda e: self._commit_name_change())
        
        # OK Button for manual commit as requested
        self.ok_btn = tk.Button(id_f, text="OK", command=self._commit_name_change,
                              bg="#353", fg="white", font=("Arial", 6, "bold"), width=3, relief="flat")
        self.ok_btn.pack(side="left", padx=(0, 5))
        
        self.hairy_btn = tk.Button(id_f, text="Hairy", command=self.open_hairy_editor, 
                  bg="#000080", fg="white", font=("Arial", 6, "bold"), width=8, relief="flat")
        self.hairy_btn.pack(side="left")
        
        # Part B: Preview (Left-ish)
        self.preview_f = tk.Frame(ribbon, bg="#333", padx=10)
        self.preview_f.pack(side="left")
        self.preview_canvas = tk.Canvas(self.preview_f, width=32, height=32, bg="#222", highlightthickness=1, highlightbackground="#555")
        self.preview_canvas.pack(side="left")

        # Part C: Sync Feedback (Right-aligned in Ribbon)
        self.type_link_label = tk.Label(ribbon, text="", bg="#333", fg="gray", font=("Arial", 7, "italic"))
        self.type_link_label.pack(side="right", padx=10)

        # Part D: Switches (Center)
        check_container = tk.Frame(ribbon, bg="#333")
        check_container.pack(side="left", fill="x", expand=True)
        
        for i, (label, key) in enumerate(self.prop_keys):
            var = tk.BooleanVar()
            self.prop_vars[key] = var
            cb = tk.Checkbutton(check_container, text=label, variable=var, bg="#333", fg="white", 
                               selectcolor="#222", activebackground="#333", font=("Arial", 7),
                               padx=0, pady=0, command=self._save_current_props)
            cb.grid(row=0, column=i*2, padx=2, sticky="w")
            
            if key == "occlusion":
                self.occlu_menu = ttk.Combobox(check_container, values=["-", "Std", "Dp"], width=4, state="disabled", font=("Arial", 7))
                self.occlu_menu.set("-")
                self.occlu_menu.grid(row=0, column=i*2+1, padx=1)
                self.occlu_menu.bind("<<ComboboxSelected>>", self._save_current_props)
                var.trace_add("write", self._on_occlu_toggle)
            
            if key == "animated":
                self.anim_btn = tk.Button(check_container, text="⚙", bg=config.COLOR_BG, font=("Arial", 6), width=2, 
                                        command=self.open_animation_editor, relief="flat")
                self.anim_btn.grid(row=0, column=i*2+1, padx=1)

        # --- 4. CENTRAL VIEWPORT (Main Stage) ---
        self.canvas_container = tk.Frame(self.win, bg="darkgray", bd=2, relief="sunken")
        self.canvas_container.pack(fill="both", expand=True, padx=10, pady=10)
        self.scroll_x = tk.Scrollbar(self.canvas_container, orient="horizontal", command=self._on_scroll_x)
        self.scroll_x.pack(side="bottom", fill="x")
        self.scroll_y = tk.Scrollbar(self.canvas_container, orient="vertical", command=self._on_scroll_y)
        self.scroll_y.pack(side="right", fill="y")
        self.canvas = tk.Canvas(self.canvas_container, bg="#333333", xscrollcommand=self.scroll_x.set, yscrollcommand=self.scroll_y.set, highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.win.bind("<Configure>", lambda e: self.draw_canvas())

    def _trigger_redraw(self):
        """ Debounced/Throttled redraw to keep UI snappy """
        if self._redraw_job:
            self.win.after_cancel(self._redraw_job)
        self._redraw_job = self.win.after(5, self.draw_canvas)

    def _on_scroll_x(self, *args):
        self.canvas.xview(*args)
        self._trigger_redraw()

    def _on_scroll_y(self, *args):
        self.canvas.yview(*args)
        self._trigger_redraw()

    def _refresh_dropdown(self):
        # --- BIDIRECTIONAL ASSET SYNC ---
        self.tileset_map = {}
        if self.save_manager.project_path:
            import ScriptParser
            # 1. Get from Script
            script_names = ScriptParser.get_all_tilesets(self.save_manager.project_path)
            
            # 2. Get from Disk
            disk_files = [f for f in os.listdir(self.tileset_dir) if f.lower().endswith(".png")]
            
            for name in script_names:
                found = False
                for df in disk_files:
                    if df.lower().startswith(name.lower()):
                        self.tileset_map[name.capitalize()] = df
                        found = True
                        break
                if not found:
                    self.tileset_map[name.capitalize()] = f"{name}_TILESET.png"

            # 3. Auto-Register new disk files
            for df in disk_files:
                core = df.replace("_TILESET.png", "").replace(".png", "").upper()
                if core not in script_names:
                    self._register_tileset_define(core)
                    self.tileset_map[core.capitalize()] = df

        for widget in self.dropdown_frame.winfo_children(): widget.destroy()
        options = sorted(list(self.tileset_map.keys())) if self.tileset_map else ["World"]
        
        current = self.selected_name.get()
        if not current or current not in options:
            self.selected_name.set("World" if "World" in options else options[0])
            
        self.dropdown = tk.OptionMenu(self.dropdown_frame, self.selected_name, *options, command=self.on_select)
        self.dropdown.config(bg=config.COLOR_BG, font=config.FONT_UI, width=12)
        self.dropdown.pack()
        self.on_select(self.selected_name.get())

    def import_tileset(self):
        label = self.selected_name.get()
        if label not in self.tileset_map: return
        src = filedialog.askopenfilename(title=f"Import {label}", filetypes=[("PNG", "*.png")], parent=self.win)
        if not src: return
        dest = os.path.join(self.tileset_dir, self.tileset_map[label])
        if not messagebox.askyesno("Confirm", f"Replace {label}?", parent=self.win): return
        try:
            with self.io_lock: # PROTECT I/O
                with Image.open(src) as img:
                    img_data = img.convert("RGBA")
                    # No cleaning needed for raw import replacement usually, 
                    # but we keep it safe.
                
                temp_file = dest + ".tmp"
                img_data.save(temp_file, format="PNG")
                os.replace(temp_file, dest)
            
            # Refresh to ensure any name changes or script defines are updated
            self._refresh_dropdown()
            self._on_asset_changed()
        except Exception as e: 
            messagebox.showerror("Security Error", f"Hardened Import Failed: {e}", parent=self.win)

    def add_new_tileset(self):
        """ Allows the user to import a COMPLETELY NEW tileset to the project. """
        src = filedialog.askopenfilename(title="Select PNG to Import as New Tileset", 
                                         filetypes=[("PNG", "*.png")], parent=self.win)
        if not src: return
        
        name = simpledialog.askstring("New Tileset Name", "Enter a unique name for this tileset (e.g. Cave):", parent=self.win)
        if not name: return
        
        # Safe Naming
        safe_name = re.sub(r'[^A-Za-z0-9]', '_', name).strip()
        filename = f"{safe_name.upper()}_TILESET.png"
        dest = os.path.join(self.tileset_dir, filename)
        
        if os.path.exists(dest):
            messagebox.showerror("Error", f"Tileset '{filename}' already exists!", parent=self.win)
            return

        try:
            with self.io_lock:
                shutil.copy2(src, dest)
            
            # This triggers the 'Auto-Register' logic in _refresh_dropdown
            self._refresh_dropdown()
            
            # Switch to it
            self.selected_name.set(safe_name.capitalize())
            self._on_asset_changed()
            
            messagebox.showinfo("Success", f"Tileset '{safe_name}' registered and imported!", parent=self.win)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add tileset: {e}", parent=self.win)

    def export_tileset(self):
        if not self.active_file or not os.path.exists(self.active_file): return
        label = self.selected_name.get()
        export_dir = os.path.join(os.getcwd(), "Exports")
        if not os.path.exists(export_dir): os.makedirs(export_dir, exist_ok=True)
        import re
        pattern = re.compile(rf"{label}_(\d+)\.(\d+)\.png$")
        maj, mino = 1, -1
        for f in os.listdir(export_dir):
            match = pattern.match(f)
            if match:
                m_maj, m_mino = int(match.group(1)), int(match.group(2))
                if m_maj > maj: maj, mino = m_maj, m_mino
                elif m_maj == maj: mino = max(mino, m_mino)
        dest = filedialog.asksaveasfilename(title="Export", initialdir=export_dir, initialfile=f"{label}_{maj}.{mino+1}.png", parent=self.win)
        if dest: shutil.copy(self.active_file, dest)

    def pan_start(self, event): 
        self.canvas.scan_mark(event.x, event.y)
        
    def pan_move(self, event): 
        self.canvas.scan_dragto(event.x, event.y, gain=1)
        self._trigger_redraw() # MUST update while panning

    def on_mouse_wheel(self, event):
        if event.state & 0x0004: # Control Key
            # 1. Capture world coordinates before zoom
            mx = self.canvas.canvasx(event.x)
            my = self.canvas.canvasy(event.y)
            old_zoom = self.zoom

            # 2. Update Zoom
            self.zoom = min(4.0, max(0.1, self.zoom + (0.1 if event.delta > 0 else -0.1)))
            if self.zoom == old_zoom: return
            
            self.zoom_label.config(text=f"Zoom: {int(self.zoom * 100)}%")
            
            # 3. Redraw immediately to get new scrollregion
            self.draw_canvas()
            
            # 4. Calculate new scroll position to keep (mx, my) under the mouse
            w, h = self.base_image.size
            stride = max(1, int(self.tile_size * self.zoom)) + config.UI_GRID_GAP
            cols, rows = w // self.tile_size, h // self.tile_size
            full_w, full_h = cols * stride, rows * stride
            
            if full_w > 0 and full_h > 0:
                new_scale_mx = mx * (self.zoom / old_zoom)
                new_scale_my = my * (self.zoom / old_zoom)
                
                new_left = (new_scale_mx - event.x) / full_w
                new_top = (new_scale_my - event.y) / full_h
                
                self.canvas.xview_moveto(new_left)
                self.canvas.yview_moveto(new_top)
                
            self._trigger_redraw()
        else:
            # Vertical Scroll
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            self._trigger_redraw()

    def on_mouse_wheel_x(self, event):
        # Shift + Wheel can still scroll or zoom, but we'll stick to horizontal scroll for utility
        self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
        self._trigger_redraw()

    def on_canvas_click(self, event):
        if not self.base_image: return
        w, h = self.base_image.size
        max_cols, max_rows = w // self.tile_size, h // self.tile_size
        
        gap, sz = config.UI_GRID_GAP, max(1, int(self.tile_size * self.zoom))
        cx, cy = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        col, row = int(cx // (sz + gap)), int(cy // (sz + gap))
        
        # --- BOUNDARY ENFORCEMENT ---
        # Don't let the user select tiles that don't exist yet!
        if col < 0 or col >= max_cols or row < 0 or row >= max_rows:
            return
            
        # --- TOOL ENGINE ---
        if self.active_tool == "PASTE" and self.clipboard_img:
            self._paste_at(col, row, self.clipboard_img)
            self.set_tool("SELECT")
            return
            
        if self.active_tool == "SWAP":
            if self.clipboard_img and hasattr(self, 'swap_source'):
                # Destination img
                tile_b_img = self._get_tile_img(col, row)
                # Atomic swap! Target gets ClipboardA, Source gets ImgB
                sc, sr = self.swap_source
                self._paste_twice(col, row, self.clipboard_img, sc, sr, tile_b_img)
                self.set_tool("SELECT")
            return

        # ATOMIC GUARD: Save previous tile props BEFORE switching selection (World Only)
        if self.selected_name.get() == "World":
            if hasattr(self, 'selected_tile') and self.selected_tile:
                 self._save_current_props()

        # Normal selection
        if self.selection_rect: self.canvas.delete(self.selection_rect)
        x1, y1 = col * (sz + gap), row * (sz + gap)
        self.selection_rect = self.canvas.create_rectangle(x1, y1, x1+sz, y1+sz, outline="yellow", width=2)
        self.selected_tile = (col, row)
        self._refresh_prop_ui()

    def _on_occlu_toggle(self, *args):
        if self.prop_vars["occlusion"].get():
            self.occlu_menu.config(state="readonly")
        else:
            self.occlu_menu.config(state="disabled")

    def _load_props(self):
        """ DEPRECATED: Uses ScriptParser.parse_tile_properties instead. """
        return ScriptParser.parse_tile_properties(self.save_manager.project_path)

    def _commit_name_change(self):
        """ Explicitly commits the name change to the registry. """
        if not hasattr(self, 'selected_tile') or not self.selected_tile: return
        
        import re
        raw_name = self.tile_name_var.get().strip()
        clean_name = re.sub(r'[^a-zA-Z0-9_]', '', raw_name.replace(" ", "_"))[:32]
        self.tile_name_var.set(clean_name)
        
        ts = self.selected_name.get()
        tid = f"{self.selected_tile[1]+1},{self.selected_tile[0]+1}"
        
        if ts not in self.all_props: self.all_props[ts] = {}
        if tid not in self.all_props[ts]: self.all_props[ts][tid] = {}
        
        # Update the STASHED name
        self.all_props[ts][tid]["name"] = clean_name
        
        # Now trigger a full save to write to disk
        self._save_current_props()

    def _save_current_props(self):
        """ Saves all properties, using the STASHED name for safety. """
        if self.selected_name.get() != "World": return 
        if not hasattr(self, 'selected_tile') or not self.selected_tile: return

        ts = self.selected_name.get()
        if ts not in self.all_props: self.all_props[ts] = {}
        
        try:
            with self.io_lock:
                tid = f"{self.selected_tile[1]+1},{self.selected_tile[0]+1}"
                # 1. Get current toggle states
                data = {k: v.get() for k, v in self.prop_vars.items()}
                data["occlusion_type"] = self.occlu_menu.get()
                
                # 2. Re-acquire the STASHED name (ignoring uncommitted entry changes)
                stashed = self.all_props[ts].get(tid, {}).get("name", "")
                data["name"] = stashed
                
                self.all_props[ts][tid] = data
                
                # --- PURE-SCRIPT SYNC ---
                ScriptParser.register_tile_define(self.save_manager.project_path, self.all_props)
                self.save_manager.mark_dirty()
                self._update_preview()
        except Exception as e:
            print(f"[ERROR] Failed to save props: {e}")

    def _refresh_prop_ui(self):
        """ Context-Aware Refresh: Only processes properties for the World tileset. """
        ts = self.selected_name.get()
        if ts != "World": return 

        # Shift to 1-indexed "Row,Col" keys for alignment with JSON schema
        tid = f"{self.selected_tile[1]+1},{self.selected_tile[0]+1}"
        data = self.all_props.get(ts, {}).get(tid, {})
        for k, var in self.prop_vars.items():
            var.set(data.get(k, False))
        
        # Refresh Name & UI
        self.tile_name_var.set(data.get("name", ""))
        self.occlu_menu.set(data.get("occlusion_type", "-"))
        
        # Visual hint for Type linkage
        tname = data.get("name", "")
        if tname:
            self.type_link_label.config(text=f"Linked to: {tname}", fg="lime")
        else:
            self.type_link_label.config(text="[No Type Link]", fg="gray")
            
        self._on_occlu_toggle()
        self._update_preview()

    def _update_preview(self):
        """ Plays animation or shows static tile in the ribbon preview. """
        if self._anim_job:
            self.win.after_cancel(self._anim_job)
            self._anim_job = None

        ts = self.selected_name.get()
        sc, sr = self.selected_tile
        
        # 1. Check if animated
        tid = f"{sr+1},{sc+1}"
        data = self.all_props.get(ts, {}).get(tid, {})
        is_animated = data.get("animated", False)
        name = data.get("name", "").strip()

        if is_animated and name:
            # Try to find animation data in Types.json
            types_path = os.path.join(self.save_manager.project_path, "Types.json")
            if os.path.exists(types_path):
                try:
                    with open(types_path, 'r') as f:
                        types_data = json.load(f)
                    
                    anim_data = None
                    for tid_t, tdata in types_data.items():
                        if tdata.get("name") == name:
                            anim_data = tdata.get("animation")
                            break
                    
                    if anim_data and anim_data.get("frame_sequence"):
                        self._play_anim_preview(anim_data)
                        return
                except: pass

        # Fallback: Static Preview
        self.preview_canvas.delete("all")
        img = self._get_tile_img(sc, sr)
        if img:
            photo = ImageTk.PhotoImage(img.resize((32, 32), Image.NEAREST))
            self._static_preview_photo = photo # Ref
            self.preview_canvas.create_image(16, 16, image=photo)

    def _play_anim_preview(self, anim_data):
        sequence = anim_data.get("frame_sequence", [])
        if not sequence: return
        
        speed = anim_data.get("speed", 100)
        self._anim_frame_idx = 0
        self._anim_photos = [] # Cache

        def next_frame():
            if not self.win.winfo_exists(): return
            
            frame = sequence[self._anim_frame_idx]
            tx, ty, tset = frame[0], frame[1], frame[2]
            
            # Load frame img
            img = None
            if tset == self.selected_name.get() and self.base_image:
                img = self.base_image
            else:
                ts_path = os.path.join(self.tileset_dir, f"{tset}_TILESET.png")
                if os.path.exists(ts_path):
                    try:
                        img = Image.open(ts_path).convert("RGBA")
                    except: pass
            
            if img:
                try:
                    tile = img.crop((tx*self.tile_size, ty*self.tile_size, (tx+1)*self.tile_size, (ty+1)*self.tile_size))
                    photo = ImageTk.PhotoImage(tile.resize((32, 32), Image.NEAREST))
                    self.preview_canvas.delete("all")
                    self.preview_canvas.create_image(16, 16, image=photo)
                    self._current_anim_photo = photo # Keep ref
                except: pass
            
            self._anim_frame_idx = (self._anim_frame_idx + 1) % len(sequence)
            self._anim_job = self.win.after(speed, next_frame)

        next_frame()

    def open_hairy_editor(self):
        """ IDE Integration: Opens or creates a .hry script for the selected tile. """
        name = self.tile_name_var.get().strip()
        if not name:
            self.status_label.config(text="Warning: Tile must have a NAME to open Hairy.", fg="red")
            return
        
        filename = f"{name}.hry"
        hairy_dir = os.path.join(self.save_manager.project_path, "HAIRY")
        full_path = os.path.join(hairy_dir, filename)
        
        # Auto-Create from Template if missing
        if not os.path.exists(full_path):
            template_path = os.path.join(hairy_dir, "Template.hry")
            # Fallback content if Template.hry is completely missing
            content = f"// New Script for Tile: {name}\n\nObject \"{name}\"\n{{\n    OnUse\n    {{\n        Print \"You used {name}!\"\n    }}\n}}\n"
            
            if os.path.exists(template_path):
                try:
                    with open(template_path, 'r') as f:
                        content = f.read()
                        # Customization: Replace template class name with actual tile name
                        content = content.replace("My_Template_Object", name)
                except: pass
            
            try:
                os.makedirs(hairy_dir, exist_ok=True)
                with open(full_path, 'w') as f:
                    f.write(content)
                # Refresh file list in Hairy if it's already open by someone else
                print(f"[DEBUG] Created new script: {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create script file: {e}")
                return

        # Explicit Launch
        import Hairy
        # We pass initial_file to start the editor directly on this tile's logic
        Hairy.HairyEditor(self.win, self.save_manager, initial_file=filename)
        self.status_label.config(text=f"Editing Logic: {filename}", fg="blue")

    # --- TILE OPERATIONS ---
    def set_tool(self, tool):
        self.active_tool = tool
        if tool == "PASTE": self.canvas.config(cursor="plus")
        elif tool == "SWAP": self.canvas.config(cursor="exchange")
        elif tool == "CLEAR": self.canvas.config(cursor="X_cursor")
        else: self.canvas.config(cursor="")
        print(f"[DEBUG] Tileset Tool: {tool}")

    def _get_tile_img(self, c, r):
        if not self.base_image: return None
        left, top = c * self.tile_size, r * self.tile_size
        return self.base_image.crop((left, top, left+self.tile_size, top+self.tile_size))

    def _paste_at(self, c, r, img):
        if not self.base_image or not img: return
        with self.io_lock:
            # We copy base_image so we don't modify the currently rendered one until save is done
            new_img = self.base_image.copy()
            new_img.paste(img, (c * self.tile_size, r * self.tile_size))
            
            # Atomic Save
            temp = self.active_file + ".tmp"
            new_img.save(temp, format="PNG")
            os.replace(temp, self.active_file)
            
        self.save_manager.mark_dirty()
        self._on_asset_changed()

    def _paste_twice(self, c1, r1, img1, c2, r2, img2):
        """ Hardened atomic double-paste for swaps """
        if not self.base_image: return
        with self.io_lock:
            # Modify off-screen clone first
            new_img = self.base_image.copy()
            new_img.paste(img1, (c1 * self.tile_size, r1 * self.tile_size))
            new_img.paste(img2, (c2 * self.tile_size, r2 * self.tile_size))
            
            # Atomic displacement
            temp = self.active_file + ".tmp"
            new_img.save(temp, format="PNG")
            os.replace(temp, self.active_file)
        self.save_manager.mark_dirty()
        self._on_asset_changed()

    def copy_tile(self, silent=False):
        if not hasattr(self, 'selected_tile'): return
        sc, sr = self.selected_tile
        self.clipboard_img = self._get_tile_img(sc, sr)
        if not silent: 
            self.set_tool("PASTE")
            print("[DEBUG] Tile Copied to Clipboard.")

    def flip_h(self):
        if not hasattr(self, 'selected_tile'): return
        sc, sr = self.selected_tile
        img = self._get_tile_img(sc, sr)
        if img: self._paste_at(sc, sr, img.transpose(Image.FLIP_LEFT_RIGHT))

    def flip_v(self):
        if not hasattr(self, 'selected_tile'): return
        sc, sr = self.selected_tile
        img = self._get_tile_img(sc, sr)
        if img: self._paste_at(sc, sr, img.transpose(Image.FLIP_TOP_BOTTOM))

    def rotate_tile(self):
        if not hasattr(self, 'selected_tile'): return
        sc, sr = self.selected_tile
        img = self._get_tile_img(sc, sr)
        if img: self._paste_at(sc, sr, img.rotate(-90))

    def clear_tile(self):
        if not hasattr(self, 'selected_tile'): return
        sc, sr = self.selected_tile
        # Resets to a grey box with white outline
        blank = Image.new("RGBA", (self.tile_size, self.tile_size), (100,100,100,255))
        draw = ImageDraw.Draw(blank)
        draw.rectangle([0,0,self.tile_size-1,self.tile_size-1], outline="white")
        self._paste_at(sc, sr, blank)

    def start_swap(self):
        """ Instant Capture: Click Tile A -> Click SWAP -> Click Tile B """
        if not hasattr(self, 'selected_tile'): 
            print("[DEBUG] No tile selected to swap!")
            return
        sc, sr = self.selected_tile
        self.clipboard_img = self._get_tile_img(sc, sr)
        self.swap_source = (sc, sr) # Store source position
        self.set_tool("SWAP")

    def open_pixel_editor(self):
        """ Launches the Surgical Pixel Suite for the current selection """
        if not hasattr(self, 'selected_tile'): return
        sc, sr = self.selected_tile
        tile_img = self._get_tile_img(sc, sr)
        if not tile_img: return
        
        # Open the new window with the project directory for the sidebar!
        PixelEditor.PixelEditor(self.win, tile_img, sc, sr, 
                                callback=lambda new_img: self._paste_at(sc, sr, new_img),
                                tileset_dir=self.tileset_dir,
                                save_manager=self.save_manager,
                                initial_tileset=self.selected_name.get())

    def open_animation_editor(self):
        """ Launches the Animation Suite for the current selection """
        if not hasattr(self, 'selected_tile'): return
        sc, sr = self.selected_tile
        tile_img = self._get_tile_img(sc, sr)
        if not tile_img: return
        
        # Open animation tool with the current tile as the first frame seed
        name = self.tile_name_var.get().strip()
        AnimationEditor.AnimationEditor(self.win, self.save_manager, initial_tile=tile_img, initial_name=name)

    def _register_tileset_define(self, name):
        """ Appends a new TILESET_ define to Defines.hry. """
        if not self.save_manager: return
        path = os.path.join(self.save_manager.project_path, "HAIRY", "Defines.hry")
        if os.path.exists(path):
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"DEFINE GLOBAL TILESET_{name.upper()} 0 // Auto-Registered\n")

    def on_select(self, value):
        if value not in self.tileset_map: return
        
        # --- SMOOTH UI: Animated Panel Transition ---
        # If we are NOT on 'World', we completely hide the pane and its border.
        is_world = (value == "World")
        target = self.prop_target_h if is_world else 0
        
        if not is_world:
            self.prop_f.config(bd=0)
            self.prop_f.pack_forget() # COMPLETELY REMOVE FROM LAYOUT
        else:
            self.prop_f.pack(fill="x", side="top", after=self.top_f_ref) # Restore position
            self.prop_f.config(bd=1)
        
        self._animate_prop_pane(target)
            
        file_path = os.path.join(self.tileset_dir, self.tileset_map[value])
        if file_path == self.active_file and self.base_image is not None: return
        self.active_file = file_path
        print(f"[DEBUG] Tileset changed to: {value}")
        self._on_asset_changed()

    def _animate_prop_pane(self, target):
        """ Smooth Vertical Slide (Hydraulic Motion) """
        if self._anim_job: self.win.after_cancel(self._anim_job)
        
        current_h = self.prop_f.winfo_height()
        step = 15 # Pixels per frame
        
        if abs(current_h - target) < step:
            self.prop_f.config(height=target)
            # Final Polish: Hide border if target is 0
            if target == 0: self.prop_f.config(bd=0)
            else: self.prop_f.config(bd=1)
            return
            
        new_h = current_h + step if target > current_h else current_h - step
        self.prop_f.config(height=new_h)
        self._anim_job = self.win.after(10, lambda: self._animate_prop_pane(target))


    def _on_asset_changed(self):
        """ TRIGGERS BACKGROUND LOAD WITH RACE-CONDITION PREVENTION """
        self._last_load_id += 1
        self.status_label.config(text=f"Loading asset: {self.selected_name.get()}...", fg="blue")
        self._trigger_load(self.active_file, self._last_load_id)

    def hard_save_project(self):
        """ COMPREHENSIVE FLUSH TO HARDWARE (ZIP ARCHIVE) """
        self.status_label.config(text="Backing up project to .sav... please wait...", fg="#111")
        self.win.update_idletasks()
        
        # 1. Flush Tile Metadata
        self._save_current_props()
        
        # 2. Trigger global SaveLogic zip
        succ, err = self.save_manager.save_project()
        if succ:
            self.status_label.config(text="Backup Successful! Project Secured.", fg="#151")
        else:
            self.status_label.config(text=f"SAVE FAILED: {err}", fg="red")
            messagebox.showerror("Error", f"Hardware Level Save Failed: {err}")

    def _trigger_load(self, target_file, run_id):
        """ Hardened: Background worker for heavy I/O """
        self.canvas.delete("all")
        self.tk_image_chunks.clear()
        self.selection_rect = None
        
        cw, ch = self.win.winfo_width(), self.win.winfo_height()
        mid_x, mid_y = self.canvas.canvasx(cw//2) if cw > 1 else 450, self.canvas.canvasy(ch//2) if ch > 1 else 300
        self.canvas.create_text(mid_x, mid_y, text="⚡ PROCESSING ASSETS...", fill="white", font=("Arial", 14, "bold"))
        self.win.update_idletasks()
        
        def bg_worker(r_id, path):
            result = self._perform_heavy_load(path)
            if r_id == self._last_load_id:
                if self.win.winfo_exists():
                    self.win.after(0, lambda: self._finalize_load(result) if self.win.winfo_exists() else None)
            else:
                print(f"[DEBUG] Selection changed while loading, discarding ID {r_id}")
        
        threading.Thread(target=bg_worker, args=(run_id, target_file), daemon=True).start()

    def _perform_heavy_load(self, path):
        """ Hardened Load: Uses Lock and isolates data. """
        if not path or not os.path.exists(path): return None
        try:
            with self.io_lock:
                with Image.open(path) as img:
                    img_data = img.convert("RGBA")
                    w, h = img_data.size
                    tw = self.tile_size
                    pw, ph = (tw - (w % tw)) % tw, (tw - (h % tw)) % tw
                    if pw > 0 or ph > 0:
                        padded = Image.new("RGBA", (w+pw, h+ph), (0,0,0,0))
                        padded.paste(img_data, (0,0))
                        img_data = padded
                    return self._clean_magic_pink(img_data)
        except: return None

    def _finalize_load(self, img):
        self.base_image = img
        self.draw_canvas()

    def refresh_view(self): self._on_asset_changed()

    def _clean_magic_pink(self, img):
        r, g, b, a = img.split()
        l_hit, l_miss, l_inv = [255 if i == 255 else 0 for i in range(256)], [255 if i == 0 else 0 for i in range(256)], [255-i for i in range(256)]
        mask = ImageChops.darker(r.point(l_hit), ImageChops.darker(g.point(l_miss), b.point(l_hit)))
        return Image.merge("RGBA", (r, g, b, ImageChops.darker(a, mask.point(l_inv))))

    def draw_canvas(self):
        self._redraw_job = None
        if not self.base_image: 
            # If we are loading, don't clear the "PROCESSING" text
            # but still check if we need to draw something else
            return
            
        try:
            # 1. Update Layout Constants
            w, h = self.base_image.size
            gap, sz = config.UI_GRID_GAP, max(1, int(self.tile_size * self.zoom))
            cols, rows = w // self.tile_size, h // self.tile_size
            stride = sz + gap
            
            # 2. Update Scroll Region (Only if needed or on zoom)
            full_w, full_h = cols * stride, rows * stride
            current_sr = self.canvas.cget("scrollregion")
            new_sr = (0, 0, full_w, full_h)
            if current_sr != f"0 0 {full_w} {full_h}":
                self.canvas.config(scrollregion=new_sr)
            
            # 3. Calculate Viewport
            ww, wh = self.canvas.winfo_width(), self.canvas.winfo_height()
            if ww <= 1: ww, wh = 1200, 800
            
            vx1, vy1 = self.canvas.canvasx(0), self.canvas.canvasy(0)
            vx2, vy2 = self.canvas.canvasx(ww), self.canvas.canvasy(wh)
            
            # Boundary expansion for smooth scrolling (1 tile buffer)
            cs = max(0, int(vx1 // stride) - 1)
            ce = min(cols, int(vx2 // stride) + 2)
            rs = max(0, int(vy1 // stride) - 1)
            re = min(rows, int(vy2 // stride) + 2)
            
            # 4. Atomic Redraw
            self.canvas.delete("all")
            self.tk_image_chunks.clear()
            self.selection_rect = None

            # --- A. CHECKERBOARD & TILES ---
            # To improve performance, we combine loops and only draw what's needed
            for r in range(rs, re):
                for c in range(cs, ce):
                    x, y = c * stride, r * stride
                    
                    # Checker Background
                    self.canvas.create_rectangle(x, y, x+sz, y+sz, fill="#222", outline="")
                    sub = sz // 2
                    if sub > 2:
                        self.canvas.create_rectangle(x+sub, y, x+sz, y+sub, fill="#2a2a2a", outline="")
                        self.canvas.create_rectangle(x, y+sub, x+sub, y+sz, fill="#2a2a2a", outline="")

                    # The Tile
                    chunk = self.base_image.crop((c*self.tile_size, r*self.tile_size, (c+1)*self.tile_size, (r+1)*self.tile_size))
                    if self.zoom != 1.0: 
                        chunk = chunk.resize((sz, sz), Image.NEAREST)
                    
                    tkc = ImageTk.PhotoImage(chunk, master=self.win)
                    self.tk_image_chunks.append(tkc)
                    self.canvas.create_image(x, y, image=tkc, anchor="nw")

            # --- B. PRECISION GRID OVERLAY ---
            grid_color = "#333333"
            # Optimization: Only draw lines through the visible area
            for c in range(cs, ce + 1):
                lx = c * stride
                self.canvas.create_line(lx, vy1, lx, vy2, fill=grid_color)
            for r in range(rs, re + 1):
                ly = r * stride
                self.canvas.create_line(vx1, ly, vx2, ly, fill=grid_color)

            # --- C. SELECTION RECT ---
            if hasattr(self, 'selected_tile'):
                sc, sr = self.selected_tile
                if sc < cols and sr < rows:
                    sx, sy = sc * stride, sr * stride
                    self.selection_rect = self.canvas.create_rectangle(sx, sy, sx+sz, sy+sz, outline="yellow", width=2)
                    
        except Exception as e: 
            print(f"[RENDER ERROR] {e}")
            import traceback
            traceback.print_exc()

    def add_column(self): self._resize_tileset(1, 0)
    def add_row(self): self._resize_tileset(0, 1)
    def remove_column(self): self._resize_tileset(-1, 0)
    def remove_row(self): self._resize_tileset(0, -1)

    def _resize_tileset(self, ac, ar):
        if not self.active_file: return
        try:
            with self.io_lock:
                with Image.open(self.active_file) as img:
                    img.load()
                    ow, oh = img.size
                    ic = img.copy()
            
                nw, nh = ow+(ac*self.tile_size), oh+(ar*self.tile_size)
                if nw < self.tile_size or nh < self.tile_size: return
                ni = Image.new("RGBA", (nw, nh), (100, 100, 100, 255))
                ni.paste(ic, (0, 0))
                if ac > 0 or ar > 0:
                    draw = ImageDraw.Draw(ni)
                    # Use existing columns/rows to avoid drawing over old art
                    oc, orw = ow//self.tile_size, oh//self.tile_size
                    for r in range(nh//self.tile_size):
                        for c in range(nw//self.tile_size):
                            if c >= oc or r >= orw:
                                box = [c*self.tile_size, r*self.tile_size, (c+1)*self.tile_size-1, (r+1)*self.tile_size-1]
                                draw.rectangle(box, outline="white")
                
                # --- ATOMIC DISPLACEMENT ---
                temp_file = self.active_file + ".tmp"
                ni.save(temp_file, format="PNG")
                os.replace(temp_file, self.active_file)
                
                # --- INSTANT UI UPDATE ---
                self.save_manager.mark_dirty()
                # Instead of re-reading from disk, we hand the new image directly to the UI
                self.base_image = ni 
                self.win.after(0, self.draw_canvas)
                
            print(f"[DEBUG] Tileset Resized to {nw}x{nh}. Instant render triggered.")
        except Exception as e: 
            messagebox.showerror("Error", f"Instant Resize Failed: {e}")
    def _on_close(self):
        """ Secure Shutdown: Kills BG workers and animations. """
        if hasattr(self, '_anim_job') and self._anim_job:
            self.win.after_cancel(self._anim_job)
        self._anim_job = None
        self.win.destroy()

    def _on_destroy(self, event):
        """ Memory Management: Surgical cleanup of large assets """
        if event.widget == self.win:
            print("[DEBUG] Releasing Tileset Editor resources...")
            self.base_image = None
            self.tk_image_chunks.clear()
            self.clipboard_img = None
