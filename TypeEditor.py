import tkinter as tk
from tkinter import ttk, messagebox
import os
import json
from PIL import Image, ImageTk
import config
import AnimationEditor
from TilesetSelector import TilesetSelector
import ScriptParser
from EditorComponents import center_window

class TypeEditor:
    """
    Object Property Editor (Windows 95 Style).
    Manages Types.json for object metadata.
    """
    # --- GLOBAL MAPPING TRUTH ---
    FAM_TO_TS_MAP = {
        "World": "World", "Tiles": "World", "Ground": "World",
        "Npc": "Avatars", "Monster": "Avatars",
        "Weapon": "Items", "Armor": "Items", "Consumable": "Items",
        "Item": "Items", "Trinket": "Items", "Object": "Objects",
        "Obj": "Objects", "Helm": "Items", "Gaunts": "Items",
        "Plate": "Items", "Shield": "Items", "Legs": "Items"
    }

    def _get_tileset_for_fam(self, f_name):
        """ Maps granular sub-families to their parent tilesets (Prefix-based). """
        if not f_name:
            return "Items"
        
        # Normalize input (uppercase, strip 'FAM_' prefix, replace spaces with underscores)
        s = str(f_name).upper().strip()
        if s.startswith("FAM_"):
            s = s[4:]
        s = s.replace(" ", "_")
        
        # 1. Objects tileset: family is Obj / Object
        if s == "OBJ" or s == "OBJECT" or s.startswith("OBJ_") or s.startswith("OBJECT_"):
            return "Objects"
            
        # 2. Avatars tileset: family is Monster / Npc
        if s in ["NPC", "MONSTER"] or s.startswith("NPC_") or s.startswith("MONSTER_"):
            return "Avatars"
            
        # 3. Items tileset: family is Helm / Gaunts / Plate / Shield / Legs / Trinket / Weapon / Armor / Consumable / Item
        item_families = ["HELM", "GAUNTS", "PLATE", "SHIELD", "LEGS", "TRINKET", "WEAPON", "ARMOR", "CONSUMABLE", "ITEM"]
        if s in item_families or any(s.startswith(x + "_") for x in item_families):
            return "Items"
            
        # 4. World tileset: family is World / Tiles / Ground
        world_families = ["WORLD", "TILES", "GROUND"]
        if s in world_families or any(s.startswith(x + "_") for x in world_families):
            return "World"
            
        # Fallback to exact / prefix match from FAM_TO_TS_MAP
        for key, ts in self.FAM_TO_TS_MAP.items():
            key_upper = key.upper()
            if s == key_upper or s.startswith(key_upper + "_"):
                return ts
                
        return "Items" # Default fallback


    def __init__(self, parent, save_manager, main_app=None):
        self.parent = parent
        self.save_manager = save_manager
        self.main_app = main_app
        self.project_path = save_manager.project_path
        self.types_file = os.path.join(self.project_path, "Types.json")
        
        # --- DATA ---
        self.types_data = self._load_types()
        self.selected_type_id = None
        self.tileset_props = ScriptParser.parse_tile_properties(self.project_path)
        
        # Tileset Cache for rendering Type Library icons
        self.tile_size = self.save_manager.project_data.get("tile_size", 16)
        self.tileset_cache = {}
        self.grid_zoom = 1.0
        self.pan_start_coords = (0, 0)
        self._is_saving = False # IO Lock
        self.current_tileset_img = None
        self.tileset_photo_chunks = [] # For Right Pane
        self.type_library_photos = []  # For Left Pane
        
        # Tracking child dialogs for sync-close
        self.active_dialogs = []

        # --- WINDOW SETUP ---
        self.win = tk.Toplevel(parent)
        self.win.title("Type Editor")
        
        # Standardized Centering
        center_window(self.win, parent, 1100, 700)
        
        self.win.configure(bg="#C0C0C0") # Win95 Gray
        
        # Font setup
        self.ui_font = ("Tahoma", 8)
        self.title_font = ("Tahoma", 8, "bold")

        self.setup_layout()
        self._sync_hairys_to_types()
        self.refresh_type_list()
        
        # Sync Closing logic
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)
        print(f"[DEBUG] Type Editor initialized at {self.types_file}")

    def _sync_hairys_to_types(self):
        """ 
        Synchronizes in-memory type data with disk by scanning all .hry files.
        """
        def run_sync():
            hairy_dir = os.path.join(self.project_path, "HAIRY")
            if not os.path.exists(hairy_dir): return

            print(f"[SYNC] Building Database from Scripts...")
            
            # 1. Map Names to IDs based on Types.hry (Truth #1: Identity)
            id_map = {} # {Name.lower(): ID}
            types_hry = os.path.join(hairy_dir, "Types.hry")
            if os.path.exists(types_hry):
                try:
                    with open(types_hry, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    # Find all #Define TYPE_FAM_NAME ID (or similar)
                    # We need to be careful with the suffix.
                    # Actually, ScriptParser.parse_types_use_sync already does this.
                    script_ids = ScriptParser.parse_types_use_sync(types_hry)
                    for tid, s_data in script_ids.items():
                        id_map[s_data["name"].lower()] = tid
                except: pass

            # 2. Scan every .hry for Metadata (Truth #2: Attributes)
            new_types = {}
            next_id = 9000 # Start safe for any completely un-IDed scripts
            
            system_files = {"defines.hry", "template.hry", "types.hry", "tables.hry", "skills.hry", "tiles.hry"}
            use_files = []
            for root, _, files in os.walk(hairy_dir):
                for f in files:
                    if f.lower().endswith(".hry"):
                        # Store path relative to hairy_dir for consistent processing
                        use_files.append(os.path.relpath(os.path.join(root, f), hairy_dir))
            
            processed_names = set()

            for use_file in use_files:
                if use_file.lower() in system_files: continue
                
                filepath = os.path.join(hairy_dir, use_file)
                headers = ScriptParser.parse_hairy_headers(filepath)
                
                if not headers: continue # Not a valid Object/Type script
                
                name = headers["name"]
                name_lower = name.lower()
                if name_lower in processed_names: continue
                processed_names.add(name_lower)
                
                # Find ID
                tid = id_map.get(name_lower)
                if not tid:
                    # If name isn't in Types.hry, generate a new ID
                    while str(next_id) in new_types: next_id += 1
                    tid = str(next_id)
                    print(f"[SYNC] New Discovery: '{name}' assigned dynamic ID {tid}")
                    # Registering it in Types.hry happens on save
                
                new_types[tid] = {
                    "name": name,
                    "family": headers.get("family", "FAM_OBJ"),
                    "tileset": headers.get("tileset", "World"),
                    "tile_coords": headers.get("tile_coords", [0, 0]),
                    "properties": headers.get("properties", {}),
                    "animation": headers.get("animation", {})
                }
                
            print(f"[SYNC] Discovery finished: Found {len(new_types)} Type(s) in HAIRY/")
            self.types_data = new_types
            if self.save_manager:
                self.save_manager.types_data = new_types
            if self.win.winfo_exists():
                self.win.after(0, self.refresh_type_list)

        import threading
        threading.Thread(target=run_sync, daemon=True).start()

    def _load_types(self):
        """ Loads all types from Types.hry. """
        hairy_dir = os.path.join(self.project_path, "HAIRY")
        types_hry = os.path.join(hairy_dir, "Types.hry")
        if os.path.exists(types_hry):
             return ScriptParser.parse_types_use_sync(types_hry)
        return {}

    def _load_tileset_props(self):
        """ Loads tile properties from script. """
        return ScriptParser.parse_tile_properties(self.project_path)

    def _save_tileset_props(self):
        try:
            with self.save_manager.io_lock:
                # Direct Script Sync
                ScriptParser.register_tile_define(self.project_path, self.tileset_props)
            # Sync with Main App if available
            if self.main_app:
                self.main_app.save_project(prompt=False)
            elif self.save_manager:
                self.save_manager.mark_dirty()
        except Exception as e:
            print(f"[ERROR] Failed to save TilesetTypes.json: {e}")

    def _save_types(self):
        """ Saves in-memory types data to Types.hry. """
        if self._is_saving: return
        self._is_saving = True
        try:
            with self.save_manager.io_lock:
                # Rebuild the master script from in-memory data
                ScriptParser.sync_all_types_to_hairy(self.project_path, self.types_data)
                
                # Cleanup: Delete the old Types.json to prevent confusion
                if os.path.exists(self.types_file):
                    os.remove(self.types_file)
            
            # Sync with Main App if available
            if self.main_app:
                self.main_app.save_project(prompt=False)
            elif self.save_manager:
                self.save_manager.mark_dirty()
        except Exception as e:
            print(f"[ERROR] Script Save Failed: {e}")
            messagebox.showerror("IO Error", f"Failed to save Types Database to script: {e}")
        finally:
            self._is_saving = False

    def setup_layout(self):
        # Top Toolbar
        toolbar = tk.Frame(self.win, bg="#C0C0C0", bd=1, relief="raised", height=30)
        toolbar.pack(fill="x", side="top")
        
        tk.Button(toolbar, text="New Type", command=self.create_new_type, font=self.ui_font, bg="#C0C0C0", relief="raised", bd=2).pack(side="left", padx=5, pady=2)
        tk.Button(toolbar, text="Edit Type", command=self.edit_selected_type, font=self.ui_font, bg="#C0C0C0", relief="raised", bd=2).pack(side="left", padx=5, pady=2)
        tk.Button(toolbar, text="Delete Type", command=self.delete_selected_type, font=self.ui_font, bg="#C0C0C0", relief="raised", bd=2).pack(side="left", padx=5, pady=2)
        tk.Button(toolbar, text="Save Database", command=self._save_types, font=self.ui_font, bg="#C0C0C0", relief="raised", bd=2).pack(side="left", padx=5, pady=2)
        
        # ZOOM CONTROLS (Right Side)
        tk.Button(toolbar, text="+Zoom", command=self.zoom_in, font=self.ui_font, bg="#C0C0C0", relief="raised", bd=2, width=8).pack(side="right", padx=5, pady=2)
        tk.Button(toolbar, text="-Zoom", command=self.zoom_out, font=self.ui_font, bg="#C0C0C0", relief="raised", bd=2, width=8).pack(side="right", padx=2, pady=2)

        # Main Paned Area
        self.paned = tk.PanedWindow(self.win, orient="horizontal", bg="#808080", sashwidth=4, sashrelief="sunken")
        self.paned.pack(fill="both", expand=True)

        # --- MAIN PANE: Type Library ---
        self.left_f = tk.Frame(self.paned, bg="#FFFFFF", bd=2, relief="sunken")
        tk.Label(self.left_f, text="Type Library", bg="#000080", fg="white", font=self.title_font, anchor="w").pack(fill="x")
        
        # Adding Scrollbars
        self.scroll_y = tk.Scrollbar(self.left_f, orient="vertical")
        self.scroll_y.pack(side="right", fill="y")
        self.scroll_x = tk.Scrollbar(self.left_f, orient="horizontal")
        self.scroll_x.pack(side="bottom", fill="x")

        self.type_canvas = tk.Canvas(self.left_f, bg="#dfdfdf", highlightthickness=0, 
                                     xscrollcommand=self.scroll_x.set, 
                                     yscrollcommand=self.scroll_y.set)
        self.type_canvas.pack(fill="both", expand=True)

        self.scroll_y.config(command=self.type_canvas.yview)
        self.scroll_x.config(command=self.type_canvas.xview)

        # Bindings
        # All selection/editing is now handled via tag_bind in refresh_type_list
        # to prevent double-opening windows.
        self.type_canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.type_canvas.bind("<ButtonPress-2>", self._pan_start)
        self.type_canvas.bind("<B2-Motion>", self._pan_move)
        
        self.paned.add(self.left_f, width=1100)
        
        # --- DYNAMIC RESIZING ---
        # Ensure the grid refills the width when the window or pane is resized
        self.type_canvas.bind("<Configure>", lambda e: self.refresh_type_list())

        # --- THE PANE HAS BEEN REMOVED TO PREVENT CLUTTER ---
        # The tileset browser is no longer part of the main layout.

    # Tileset Browser logic removed - No longer used.

    def _on_mousewheel(self, event):
        """ Native Scrolling behavior + Ctrl-Zoom. """
        if event.state & 0x0004: # Control Key
            if event.delta > 0: self.zoom_in()
            else: self.zoom_out()
        else:
            if event.delta:
                self.type_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def zoom_in(self):
        """ Scales the UI upwards. """
        self.grid_zoom = min(4.0, self.grid_zoom + 0.1)
        print(f"[DEBUG] Zoomed in (scale: {self.grid_zoom:.1f})")
        self.refresh_type_list()

    def zoom_out(self):
        """ Scales the UI downwards. """
        self.grid_zoom = max(0.5, self.grid_zoom - 0.1)
        print(f"[DEBUG] Zoomed out (scale: {self.grid_zoom:.1f})")
        self.refresh_type_list()

    def _pan_start(self, event):
        self.type_canvas.scan_mark(event.x, event.y)

    def _pan_move(self, event):
        self.type_canvas.scan_dragto(event.x, event.y, gain=1)

    def refresh_type_list(self):
        self.type_canvas.delete("all")
        self.type_library_photos = []
        
        # Grid settings
        sz_base = 32 # Original size
        sz = int(sz_base * self.grid_zoom)
        
        # We increase horizontal gap (was 50) to 70 to ensure labels don't overlap
        gap_h = int(70 * self.grid_zoom) # Horizontal Space
        gap_v = int(35 * self.grid_zoom) # Space for labels
        
        # Sort by family, then name (Case-insensitive)
        def type_sort_key(item):
            data = item[1]
            family = str(data.get('family', 'Tiles')).lower()
            name = str(data.get('name', 'Unnamed')).lower()
            return (family, name)

        sorted_types = sorted(self.types_data.items(), key=type_sort_key)
        
        # --- DYNAMIC WIDTH CALCULATION ---
        # We use the actual canvas width to decide how many assets fit per row.
        # This makes it 'fill the whole page' as requested.
        canvas_w = self.type_canvas.winfo_width()
        if canvas_w < 100: canvas_w = 1100 # Fallback for first-draw logic
        
        # Calculate how many items can fit. We subtract a bit for scrollbars/padding.
        items_per_row = max(1, (canvas_w - 40) // (sz + gap_h))

        # FIX: Draw a background sentinel to handle unselect clicks
        full_w = max(450, canvas_w)
        total_types = len(sorted_types)
        rows_est = (total_types + items_per_row - 1) // items_per_row
        full_h = max(700, rows_est * (sz + gap_v + sz) + 150)
        
        bg_id = self.type_canvas.create_rectangle(0, 0, full_w*2, full_h*2, fill="#dfdfdf", outline="", tags="bg_sentinel")
        self.type_canvas.tag_bind("bg_sentinel", "<Button-1>", lambda e: self.unselect_all())
        
        # Load sprites for library icons
        def get_tile(ts_name, tx, ty):
            if ts_name not in self.tiles_cache:
                path = os.path.join(self.project_path, "TILESET", f"{ts_name}_TILESET.png")
                if os.path.exists(path):
                    self.tiles_cache[ts_name] = Image.open(path).convert("RGBA")
                else: return None
            
            img = self.tiles_cache[ts_name]
            tsize = self.tile_size
            return img.crop((tx*tsize, ty*tsize, (tx+1)*tsize, (ty+1)*tsize)).resize((sz, sz), Image.NEAREST)

        self.tiles_cache = self.tileset_cache # Use the class-level cache

        for i, (tid, data) in enumerate(sorted_types):
            r, c = i // items_per_row, i % items_per_row
            x, y = c * (sz + gap_h) + 50, r * (sz + gap_v + sz) + 25
            
            tag = f"type_grp_{tid}"
            
            # Selection Rect (Encompasses tile + label)
            is_sel = (tid == self.selected_type_id)
            bg_color = "#000080" if is_sel else "#dfdfdf"
            border = "white" if is_sel else "#dfdfdf"
            
            # Box width is expanded to handle names without clipping
            # We increase the padding (was 30) to 60 to give names more room
            rect_w = sz + int(60 * self.grid_zoom)
            rect_x = x - (rect_w - sz)/2
            rect_h = sz + int(25 * self.grid_zoom)
            
            self.type_canvas.create_rectangle(rect_x, y-6, rect_x+rect_w, y+rect_h, fill=bg_color, outline=border, width=1, tags=tag)
            
            # Draw Icon
            anim = data.get("animation", {})
            frame_seq = anim.get("frame_sequence", []) if isinstance(anim, dict) else []
            if frame_seq and len(frame_seq) > 0:
                tx, ty, ts_name = frame_seq[0]
            else:
                ts_name = data.get("tileset", "World")
                tx, ty = data.get("tile_coords", [0,0])
            tile_img = get_tile(ts_name, tx, ty)
            
            if tile_img:
                tkc = ImageTk.PhotoImage(tile_img)
                self.type_library_photos.append(tkc)
                self.type_canvas.create_image(x, y, image=tkc, anchor="nw", tags=tag)
            else:
                self.type_canvas.create_rectangle(x, y, x+sz, y+sz, fill="gray", tags=tag)
            
            # Draw Label under tile
            name = data.get("name", "Unnamed")
            # Truncate only if extremely long (increased limit for readability)
            disp_name = (name[:18] + '..') if len(name) > 20 else name
            txt_color = "white" if is_sel else "#333"
            txt_size = max(6, int(7 * self.grid_zoom))
            self.type_canvas.create_text(x + sz/2, y + sz + 5, text=disp_name, 
                                        fill=txt_color, font=("Tahoma", txt_size, "bold" if is_sel else "normal"), 
                                        anchor="n", tags=tag, width=rect_w)

            # Bindings for the whole GROUP
            self.type_canvas.tag_bind(tag, "<Button-1>", lambda e, t=tid: self.select_type(t))
            self.type_canvas.tag_bind(tag, "<Double-Button-1>", lambda e, t=tid: self.open_property_editor(t))
            
        # Update scrollregion for proper panning
        self.type_canvas.config(scrollregion=(0, 0, full_w, full_h))

    def on_canvas_click(self, event):
        """ Handles selection of types in the main library grid. """
        # Convert screen coords to canvas coords (accounting for panning)
        cx = self.type_canvas.canvasx(event.x)
        cy = self.type_canvas.canvasy(event.y)
        
        # Grid settings (Must match refresh_type_list)
        sz = int(32 * self.grid_zoom)
        gap_h = int(70 * self.grid_zoom)
        gap_v = int(35 * self.grid_zoom)
        # --- DYNAMIC WIDTH SYNC ---
        canvas_w = self.type_canvas.winfo_width()
        items_per_row = max(1, (canvas_w - 40) // (sz + gap_h))

        # Back-calculate grid position
        col = int((cx - 50) // (sz + gap_h))
        row = int((cy - 25) // (sz + gap_v + sz))
        
        if col < 0 or col >= items_per_row: return
        idx = row * items_per_row + col
        
        # Get the sorted list so idx matches the visual order (Must match refresh_type_list)
        def type_sort_key(item):
            data = item[1]
            family = data.get('family', 'Tiles')
            name = data.get('name', 'Unnamed').lower()
            return (family, name)

        sorted_types = sorted(self.types_data.items(), key=type_sort_key)
        
        if 0 <= idx < len(sorted_types):
            tid = sorted_types[idx][0]
            self.select_type(tid)
        else:
            self.unselect_all()

    def unselect_all(self):
        """ Clears selection when clicking empty space. """
        print("[DEBUG] Unselected all types")
        self.selected_type_id = None
        self.refresh_type_list()

    def edit_selected_type(self):
        """ Opens property editor for currently selected type. """
        if not self.selected_type_id:
            messagebox.showwarning("Warning", "No type selected to edit.", parent=self.win)
            return
        print(f"[DEBUG] Edit Type requested for ID: {self.selected_type_id}")
        self.open_property_editor(self.selected_type_id)

    def select_type(self, tid):
        print(f"[DEBUG] Selected Type: {tid}")
        self.selected_type_id = tid
        self.refresh_type_list()

    def delete_selected_type(self):
        if not self.selected_type_id:
            messagebox.showwarning("Warning", "No type selected to delete.", parent=self.win)
            return
        
        name = self.types_data[self.selected_type_id].get("name", "Unnamed")
        if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete type '{name}' (ID: {self.selected_type_id})?", parent=self.win):
            return
            
        del self.types_data[self.selected_type_id]
        self.selected_type_id = None
        if self.save_manager:
            self.save_manager.mark_dirty()
        self.refresh_type_list()
        print(f"[DEBUG] Type deleted: {name}")

    def _get_unique_name(self, base_name, exclude_id=None):
        name = base_name
        counter = 1
        existing_names = [v["name"] for k, v in self.types_data.items() if k != exclude_id]
        while name in existing_names:
            name = f"{base_name} {counter}"
            counter += 1
        return name

    def create_new_type(self):
        # HARDENED ID GENERATION (Max-Scan instead of len-offset)
        if self.types_data:
            new_id = str(max([int(k) for k in self.types_data.keys()]) + 1)
        else:
            new_id = "100"
            
        unique_name = self._get_unique_name("NewObject")
        
        self.types_data[new_id] = {
            "name": unique_name,
            "family": "Default",
            "tileset": "Items",
            "tile_coords": [0,0],
            "properties": {
                "not_moveable": False, "solid": True, "is_container": False,
                "collectable": False, "gold_value": 0, "is_treasure": False,
                "can_reach_over": False, "illuminates": False, "editor": False,
                "weight": 0, "mass": 0, "use_delay": 0, "brightness": 0, "radius": 0
            }
        }
        if self.save_manager:
            self.save_manager.mark_dirty()
        self.refresh_type_list()
        print(f"[DEBUG] Created New Type: '{unique_name}' (ID: {new_id})")
        self.open_property_editor(new_id)

    def open_property_editor(self, tid):
        data = self.types_data[tid]
        print(f"[DEBUG] Opened Property Editor for Type ID: {tid} ({data['name']})")
        
        # Classic Win95 Dialog
        dlg = tk.Toplevel(self.win)
        dlg.title(f"Type Properties - {data['name']} - {tid}")
        
        # --- CENTER IN PARENT (Type Editor) ---
        center_window(dlg, self.win, 450, 550)
        
        dlg.configure(bg="#C0C0C0")
        dlg.resizable(False, False)
        dlg.transient(self.win)
        self.active_dialogs.append(dlg)

        # 1. Top Section: Name & ID
        top_f = tk.Frame(dlg, bg="#C0C0C0", pady=10, padx=10)
        top_f.pack(fill="x")
        
        tk.Label(top_f, text="Name:", bg="#C0C0C0", font=self.ui_font).pack(side="left")
        name_var = tk.StringVar(value=data["name"])
        tk.Entry(top_f, textvariable=name_var, bg="white", relief="sunken", bd=2).pack(side="left", padx=5, fill="x", expand=True)
        tk.Label(top_f, text=str(tid), bg="#C0C0C0", font=self.title_font, fg="#444").pack(side="right")

        # 2. Media Section
        mid_f = tk.Frame(dlg, bg="#C0C0C0", padx=10)
        mid_f.pack(fill="x")
        
        # --- TRACKING DEFS (Hoist for scope safety) ---
        check_vars = {}
        check_widgets = {}
        num_vars = {}
        
        img_box = tk.Canvas(mid_f, width=64, height=64, bg="#dfdfdf", bd=2, relief="sunken", highlightthickness=0)
        img_box.pack(side="left")
        
        def update_preview():
            img_box.delete("all")
            anim = data.get("animation", {})
            frame_seq = anim.get("frame_sequence", []) if isinstance(anim, dict) else []
            if frame_seq and len(frame_seq) > 0:
                tx, ty, ts = frame_seq[0]
            else:
                ts = data.get("tileset", "World")
                tc = data.get("tile_coords", [0,0])
                tx, ty = tc[0], tc[1]
            # Use current project tile size for crop
            tsize = self.tile_size
            path = os.path.join(self.project_path, "TILESET", f"{ts}_TILESET.png")
            if os.path.exists(path):
                img = Image.open(path).convert("RGBA")
                chunk = img.crop((tx*tsize, ty*tsize, (tx+1)*tsize, (ty+1)*tsize)).resize((64, 64), Image.NEAREST)
                self._preview_photo = ImageTk.PhotoImage(chunk) # Ref
                # Hardened Offset: Adjusted (2,2) to clear the sunken border properly. 
                img_box.create_image(2, 2, image=self._preview_photo, anchor="nw")
        
        update_preview()
        
        # --- CHILD TRACKING ---
        dlg.sub_windows = []
        def _cleanup_sub_windows(event):
            # Only trigger if the dlg itself is being destroyed
            if event.widget == dlg:
                for sw in dlg.sub_windows:
                    try:
                        if sw.winfo_exists(): sw.destroy()
                    except: pass
        dlg.bind("<Destroy>", _cleanup_sub_windows)

        btn_f = tk.Frame(mid_f, bg="#C0C0C0")
        btn_f.pack(side="left", padx=10)

        def launch_anim_editor():
            # Open Animation suite for this specific object name
            # INHERIT the tileset from the current Type's Family/Selection
            fam = fam_var.get()
            ts_key = self._get_tileset_for_fam(fam)
            print(f"[DEBUG] Launching Animation Editor for Type '{name_var.get()}' (Tileset: '{ts_key}')")
            
            def on_anim_saved(anim_data):
                data["animation"] = anim_data
                print(f"[DEBUG] Animation saved callback received for '{data['name']}': {anim_data}")
                update_preview()
            
            ae = AnimationEditor.AnimationEditor(dlg, self.save_manager, 
                                                 initial_name=name_var.get(),
                                                 initial_tileset=ts_key,
                                                 on_save_callback=on_anim_saved)
            dlg.sub_windows.append(ae.win)
            
        self.anim_button = tk.Button(btn_f, text="Select Anim", font=self.ui_font, bg="#C0C0C0", width=10, command=launch_anim_editor)
        self.anim_button.pack(pady=2)
        
        def open_tile_selector():
            # Open our sidequest utility: TilesetSelector
            fam = fam_var.get()
            ts_key = self._get_tileset_for_fam(fam)
            ts_path = os.path.join(self.project_path, "TILESET", f"{ts_key}_TILESET.png")
            print(f"[DEBUG] Opening Tile Selector for Type '{data['name']}' using tileset: '{ts_key}'")
            
            def on_picked(c, r):
                data["tileset"] = ts_key
                data["tile_coords"] = [c, r]
                print(f"[DEBUG] Selected tile coordinates [{c}, {r}] for Type '{data['name']}'")
                self._save_types()
                self.refresh_type_list()
                update_preview()
                
            ts_win = TilesetSelector(dlg, ts_path, tile_size=self.tile_size, callback=on_picked)
            dlg.sub_windows.append(ts_win.win)

        self.tile_button = tk.Button(btn_f, text="Select Tile", font=self.ui_font, bg="#C0C0C0", width=10, command=open_tile_selector)
        self.tile_button.pack(pady=2)
        
        def edit_hairy():
            """ Opens the SHARED Hairy IDE and navigates to this Type's script. """
            current_name = name_var.get().strip()
            print(f"[DEBUG] Edit Hairy requested for '{current_name}'")
            if not current_name:
                messagebox.showwarning("Warning", "Type needs a name before editing hairy.", parent=dlg)
                return
            
            use_filename = ScriptParser._hairy_filename(current_name)
            hairy_dir = os.path.join(self.project_path, "HAIRY")
            use_path = os.path.join(hairy_dir, use_filename)
            
            # Seed the .hry file from Template.hry if it doesn't exist
            if not os.path.exists(use_path):
                template_path = os.path.join(hairy_dir, "Template.hry")
                try:
                    if os.path.exists(template_path):
                        with open(template_path, 'r') as tf:
                            content = tf.read()
                    else:
                        # --- SMART INJECTION ENGINE ---
                        # Start with the Universal API Roadmap
                        roadmap = getattr(self.save_manager, "MASTER_API_ROADMAP", "// API Roadmap Missing\n")
                        content = f"{roadmap}\n"
                        content += f"// TYPE: {current_name}\n"
                        content += f"// FAMILY: {current_fam}\n"
                        content += f"// =============================================================\n\n"
                        content += f"Object \"{current_name}\"\n"
                        content += "{\n"
                        
                        # Add Family-specific baseline logic
                        if "NPC" in current_fam.upper() or "AVATAR" in current_fam.upper():
                            content += "    OnTalk\n    {\n        Say(ME, \"Greetings, traveler!\")\n    }\n\n"
                        
                        content += "    OnUse\n    {\n        Say(ME, \"You used the object.\")\n    }\n"
                        content += "}\n"
                        
                    with open(use_path, 'w') as uf:
                        uf.write(content)
                except Exception as e:
                    print(f"[ERROR] Failed to seed hairy: {e}")
            
            # Register this type in Defines.hry
            current_fam = fam_var.get()
            ScriptParser.register_type_define(self.project_path, current_fam, current_name, tid)
            
            # Use the MAIN editor's shared Hairy window
            if self.main_app:
                self.main_app.open_hairy_editor()
                # Navigate the shared editor to this specific file
                if hasattr(self.main_app, 'current_hairy_editor'):
                    self.main_app.current_hairy_editor.load_file(use_filename)
                    self.main_app.current_hairy_editor.refresh_file_list()
            else:
                # Fallback: open standalone if no main_app reference
                import Hairy
                uc = Hairy.HairyEditor(dlg, self.save_manager, initial_file=use_filename)
                dlg.sub_windows.append(uc.win)

        def edit_stats():
            """ Context-sensitive data editor launcher. """
            fam = fam_var.get().upper()
            import ArmorData, WeaponData, NPCData, UseableItemEditor, CollectableEditor, MonsterTypeEditor
            
            if fam == "FAM_ARMOR":
                ArmorData.ArmorDataEditor(dlg, self.save_manager)
            elif fam == "FAM_WEAPON":
                WeaponData.WeaponDataEditor(dlg, self.save_manager)
            elif fam == "FAM_NPC":
                NPCData.NPCDataEditor(dlg, self.save_manager)
            elif fam == "FAM_USEABLE":
                UseableItemEditor.UseableItemEditor(dlg, self.save_manager)
            elif fam == "FAM_COLLECTABLE":
                CollectableEditor.CollectableEditor(dlg, self.save_manager)
            elif fam == "FAM_MONSTER":
                MonsterTypeEditor.MonsterTypeEditor(dlg, self.save_manager)
            else:
                messagebox.showinfo("Note", f"The family '{fam}' does not have a specialized statistical editor.", parent=dlg)

        # Action Button for Logic
        logic_f = tk.Frame(mid_f, bg="#dfdfdf", pady=5)
        logic_f.pack(side="right")
        
        tk.Button(logic_f, text="Edit Hairy", font=self.ui_font, bg="#C0C0C0", width=12, height=2, command=edit_hairy).pack(side="top", pady=2)

        # 3. Type Information Group
        group = tk.LabelFrame(dlg, text="Type Information", bg="#C0C0C0", font=self.ui_font, padx=10, pady=10, relief="groove")
        group.pack(fill="both", expand=True, padx=10, pady=10)

        family_f = tk.Frame(group, bg="#C0C0C0")
        family_f.pack(fill="x", pady=5)
        tk.Label(family_f, text="Family:", bg="#C0C0C0", font=self.ui_font).pack(side="left")
        
        current_fam = data.get("family", "World")
        # Normalize: ensure we are comparing "Npc" with "Npc"
        if str(current_fam).upper().startswith("FAM_"): current_fam = current_fam[4:]
        pretty_initial = str(current_fam).lower().capitalize()
        
        fam_var = tk.StringVar(value=pretty_initial)
        # Fetch raw defines (e.g., ["FAM_GROUND", "FAM_NPC"])
        raw_fams = ScriptParser.get_defines_from_script(self.project_path, "FAM_")
        
        families = ["World"]
        for f in raw_fams:
            # Strip FAM_ prefix if it escaped from the script parser
            clean = f[4:] if f.upper().startswith("FAM_") else f
            # Pretty-ify: ARMOR_PLATE -> Armor Plate
            pretty = clean.replace("_", " ").title()
            if pretty and pretty not in families:
                families.append(pretty)
                
        families.sort()
        
        # Note: self._get_tileset_for_fam handles granular sub-families
            
        def _on_fam_change(*args):
            f = fam_var.get()
            # 1. Sync back to raw format: "Armor Plate" -> "FAM_ARMOR_PLATE"
            raw_val = f.upper().replace(" ", "_")
            data["family"] = f"FAM_{raw_val}" if f != "World" else "World"
            print(f"[DEBUG] Type family changed in UI to '{data['family']}' (Tileset: '{self._get_tileset_for_fam(f)}')")
            
            # 2. Automatic Tileset Selection
            target_ts = self._get_tileset_for_fam(f)
            data["tileset"] = target_ts
            if hasattr(self, 'current_tileset_name') and self.current_tileset_name != target_ts:
                self._on_tileset_change(target_ts)
            
            # 3. Dynamic UI Update
            if hasattr(self, '_rebuild_property_grid'):
                self._rebuild_property_grid(f)

        fam_var.trace_add("write", _on_fam_change)
        self.fam_menu = tk.OptionMenu(family_f, fam_var, *families)
        self.fam_menu.pack(side="left", padx=5)


        cols_f = tk.Frame(group, bg="#C0C0C0")
        cols_f.pack(fill="both", expand=True)

        # Left Column (Checkboxes)
        left_col = tk.Frame(cols_f, bg="#C0C0C0")
        left_col.pack(side="left", fill="both", expand=True)

        # Right Column (Numeric)
        right_col = tk.Frame(cols_f, bg="#C0C0C0")
        right_col.pack(side="right", fill="both", expand=True)

        # Numeric Fields Setup
        num_labels = [("weight", "Weight"), ("mass", "Mass"), ("use_delay", "Use delay"), ("brightness", "Brightness"), ("radius", "Illumination radius")]
        for p_key, label in num_labels:
            f = tk.Frame(right_col, bg="#C0C0C0")
            f.pack(fill="x", pady=2)
            tk.Label(f, text=f"{label}:", bg="#C0C0C0", font=self.ui_font, width=16, anchor="e").pack(side="left")
            var = tk.StringVar(value=str(data["properties"].get(p_key, 0)))
            num_vars[p_key] = var
            tk.Entry(f, textvariable=var, width=5, bg="white", relief="sunken").pack(side="left", padx=5)

        def _rebuild_property_grid(family):
            # Clear existing items in Left and Right columns
            for w in left_col.winfo_children(): w.destroy()
            for w in right_col.winfo_children(): w.destroy()
            check_vars.clear()
            num_vars.clear()

            is_gr = (family == "Ground")
            if is_gr:
                c_labels = [
                    ("block_move", "Blocked"), ("block_vis", "VisBlocked"), ("block_fly", "Can't Fly"),
                    ("block_proj", "BlockProjectiles"), ("block_magic", "BlockMagic"), ("sailable", "CanSail"),
                    ("light", "Light"), ("window", "Is Window"), ("slow", "Slow"), ("animated", "Animated"),
                    ("occlusion", "Occlusion")
                ]
                ts_k = data.get("tileset", "World")
                t_co = data.get("tile_coords", [0,0])
                # Shift to 1-indexed "Row,Col" keys for alignment with JSON schema
                tid_c = f"{t_co[1]+1},{t_co[0]+1}"
                src_props = self.tileset_props.get(ts_k, {}).get(tid_c, {})
                
                # Ground doesn't usually use numeric properties in this engine
                tk.Label(right_col, text="(Map Properties)", fg="gray", bg="#C0C0C0").pack(pady=20)
            else:
                c_labels = [
                    ("not_moveable", "Not Moveable"), ("solid", "Solid"), 
                    ("is_container", "Is Container"), ("collectable", "Collectable"),
                    ("is_treasure", "Is a Treasure"), ("can_reach_over", "Can reach over"),
                    ("illuminates", "Illuminates")
                ]
                src_props = data["properties"]
                
                # Standard numeric properties
                n_labels = [("weight", "Weight"), ("mass", "Mass"), ("use_delay", "Use delay"), ("brightness", "Brightness"), ("radius", "Illumination radius")]
                for p_key, lbl in n_labels:
                    f = tk.Frame(right_col, bg="#C0C0C0")
                    f.pack(fill="x", pady=2)
                    tk.Label(f, text=f"{lbl}:", bg="#C0C0C0", font=self.ui_font, width=16, anchor="e").pack(side="left")
                    v = tk.StringVar(value=str(src_props.get(p_key, 0)))
                    num_vars[p_key] = v
                    tk.Entry(f, textvariable=v, width=5, bg="white", relief="sunken").pack(side="left", padx=5)

            # Re-create Checkboxes
            for p_key, lbl in c_labels:
                v = tk.BooleanVar(value=src_props.get(p_key, False))
                check_vars[p_key] = v
                tk.Checkbutton(left_col, text=lbl, variable=v, bg="#C0C0C0", font=self.ui_font, activebackground="#C0C0C0").pack(anchor="w")

            # Store current context for apply_changes
            self._current_is_ground = is_gr

        self._rebuild_property_grid = _rebuild_property_grid
        _rebuild_property_grid(fam_var.get())

        # Save Button
        def apply_changes():
            new_fam = fam_var.get()
            if new_fam == "World" and not self._current_is_ground:
                # If they select World but didn't set it to use Ground properties, warn them
                pass 

            raw_name = name_var.get()
            final_name = self._get_unique_name(raw_name, exclude_id=tid)
            old_name = data.get("name", "")
            
            data["name"] = final_name
            new_fam = fam_var.get()
            data["family"] = new_fam
            
            # ATOMIC SYNC
            if self._current_is_ground:
                ts_key = data.get("tileset", "World")
                tc = data.get("tile_coords", [0,0])
                tid_coord = f"{tc[1]+1},{tc[0]+1}"
                if ts_key not in self.tileset_props: self.tileset_props[ts_key] = {}
                
                # --- ADDITIVE MERGE ---
                # Retrieve existing data or start fresh to avoid losing non-UI properties
                existing_ts_data = self.tileset_props[ts_key].get(tid_coord, {})
                for k, v in check_vars.items():
                    existing_ts_data[k] = v.get()
                
                existing_ts_data["name"] = final_name  # MIRROR THE NAME HERE
                self.tileset_props[ts_key][tid_coord] = existing_ts_data
                
                self._save_tileset_props()
            else:
                for k, v in check_vars.items(): data["properties"][k] = v.get()
                for k, v in num_vars.items():
                    try: data["properties"][k] = int(v.get())
                    except: data["properties"][k] = 0
            
            # HAIRY SYNC: Rename file if name changed, then trigger global sync via _save_types
            if old_name and old_name != final_name:
                ScriptParser.rename_hairy_file(self.project_path, old_name, final_name)
            
            # --- SCRIP-FIRST SYNC ---
            # Update the specific script file with the new metadata headers
            meta_payload = {
                "family": data.get("family", "FAM_OBJ"),
                "tileset": data.get("tileset", "World"),
                "tile_coords": data.get("tile_coords", [0, 0]),
                "solid": data.get("properties", {}).get("solid", True),
                "animation": data.get("animation", {})
            }
            ScriptParser.sync_metadata_to_hairy(self.project_path, data["name"], meta_payload)
            print(f"[DEBUG] Changes applied successfully for Type ID: {tid} ({data['name']}). Saved to Hairy script.")
            
            self._save_types()
            self.refresh_type_list()
            dlg.destroy()

        tk.Button(dlg, text="OK", command=apply_changes, width=10, bg="#C0C0C0", relief="raised", bd=2).pack(side="bottom", pady=10)

    def _on_close(self):
        print("[DEBUG] Closing Type Editor and cleaning up active dialogs")
        # Close all child property dialogs surgically
        for dlg in list(self.active_dialogs):
            try:
                if dlg.winfo_exists():
                    # Check for sub-windows inside dialogs (like Anim/Tileset selectors)
                    if hasattr(dlg, 'sub_windows'):
                        for sw in dlg.sub_windows:
                            try:
                                if sw.winfo_exists(): sw.destroy()
                            except: pass
                    dlg.destroy()
            except: pass
        self.active_dialogs.clear()
        self.win.destroy()

if __name__ == "__main__":
    # Test stub
    root = tk.Tk()
    # Dummy save manager
    class MockSM:
        project_path = "."
        def mark_dirty(self): pass
    app = TypeEditor(root, MockSM())
    root.mainloop()
