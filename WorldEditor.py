# WORLDEDITOR.PY - World map editor module

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import os
import config
from PIL import Image, ImageTk, ImageDraw
NEAREST_FILTER = getattr(getattr(Image, "Resampling", Image), "NEAREST")
from EditorComponents import center_window, TilesetPalette
import ScriptParser

class WorldEditor:
    def __init__(self, master_app, save_manager):
        self.master_app = master_app
        self.save_manager = save_manager
        
        # --- DATA ---
        self.map_list = ScriptParser.get_all_maps(self.save_manager.project_path)
        self.current_map_name = self.map_list[0] if self.map_list else "WORLD"
        
        self.world_data = self.save_manager.load_world(self.current_map_name)
        self.chunks = self.save_manager.load_chunks()
        self.tileset_img = self._load_tileset()
        self.obj_tileset_img = self._load_obj_tileset()
        self.tile_size = self.save_manager.project_data.get("tile_size", 16)
        
        # --- STATE ---
        self.pan_x, self.pan_y = 0, 0
        self.zoom = 0.5
        self.mode = "CHUNK" 
        self.selected_chunk_id = "C_0"
        self.selected_tile_id = 0
        
        self.history = []            # Stack for Undo
        self.current_stroke_tiles = [] # Track TILE modifications during a stroke
        self.redo_stack = []         # Stack for Redo
        self.mouse_img = self._load_mouse_img()
        self.is_panning = False
        self.last_grid_pos = None    # For stroke detection
        
        self.chunk_cache = {}        # cid -> PIL Image
        self.photo_cache = {}        # (cid, zoom) -> PhotoImage
        self.is_drawing = False      # Concurrency Guard
        
        # --- WINDOW SETUP ---
        self.win = tk.Toplevel(self.master_app.root)
        self.win.title("World Editor - Global Map")
        center_window(self.win, self.master_app.root, 1200, 900)
        self.win.configure(bg=config.COLOR_BG)
        
        self.setup_ui()
        self._setup_shortcuts()
        
        # UI Force Sync: Ensures winfo_width is accurate before Culling math
        self.win.update_idletasks()
        self._draw_canvas()
        
        # --- DYNAMIC SYNC ---
        self.win.protocol("WM_DELETE_WINDOW", self._on_window_close)
        self._refresh_map_list()
        
        print("[DEBUG] World Editor initialized.")

    def _on_window_close(self):
        """ Memory Flush: Break the handle-cycle and close connection. """
        self.chunk_cache.clear()
        self.photo_cache.clear()
        self.tk_chunks = []
        try:
            from DatabaseManager import DatabaseManager
            from WorldDatabaseManager import WorldDatabaseManager
            # Release DB Singletons
            DatabaseManager(self.save_manager.project_path).close()
            WorldDatabaseManager(self.save_manager.project_path).close()
        except: pass
        self.win.destroy()

    def _setup_shortcuts(self):
        self.win.bind("<Control-s>", lambda e: self.save_project_all())
        self.win.bind("<Control-z>", lambda e: self.undo())
        self.win.bind("<Control-y>", lambda e: self.redo())
        self.win.bind("<Alt-Button-1>", self._on_alt_click)

    def _load_tileset(self):
        path = os.path.join(self.save_manager.project_path, "TILESET", "World_TILESET.png")
        if os.path.exists(path):
            return Image.open(path).convert("RGBA")
        return None

    def _load_obj_tileset(self):
        path = os.path.join(self.save_manager.project_path, "TILESET", "OBJECTS_TILESET.png")
        if os.path.exists(path):
            return Image.open(path).convert("RGBA")
        return None

    def _load_mouse_img(self):
        path = os.path.join(self.save_manager.pool_root, "..", "Assets", "MouseImage.png")
        if os.path.exists(path):
            img = Image.open(path).convert("RGBA")
            img = img.resize((24, 24), NEAREST_FILTER)
            return ImageTk.PhotoImage(img)
        return None

    def setup_ui(self):
        # --- TOP TOOLBAR ---
        toolbar = tk.Frame(self.win, bg=config.COLOR_BG, bd=2, relief="raised")
        toolbar.pack(fill="x", side="top")
        
        tk.Label(toolbar, text="World Map Designer", bg=config.COLOR_BG, font=config.FONT_TITLE).pack(side="left", padx=10)
        
        # Tool Mode
        mode_f = tk.Frame(toolbar, bg=config.COLOR_BG)
        mode_f.pack(side="left", padx=20)
        
        self.mode_var = tk.StringVar(value=self.mode)
        tools = [("Chunk", "CHUNK"), ("Tile", "TILE"), ("Objects", "OBJECT"), ("Points", "POINT"), ("Sampler", "DROP")]
        for text, val in tools:
            tk.Radiobutton(mode_f, text=text, variable=self.mode_var, value=val, 
                          command=self._update_mode, bg=config.COLOR_BG).pack(side="left")

        # Map Switching
        map_f = tk.Frame(toolbar, bg=config.COLOR_BG)
        map_f.pack(side="left", padx=10)
        self.map_combo = ttk.Combobox(map_f, values=self.map_list, state="readonly", width=12)
        self.map_combo.set(self.current_map_name)
        self.map_combo.pack(side="left", padx=5)
        self.map_combo.bind("<<ComboboxSelected>>", self._on_map_changed)

        # Single Unified Save
        tk.Button(toolbar, text="💾 Save Project & Map", command=self.save_project_all, 
                  bg="#228B22", fg="white", font=("Arial", 9, "bold")).pack(side="right", padx=10)

        # --- SIDEBAR (UNIFIED PALETTE) ---
        self.right_sidebar = tk.Frame(self.win, width=250, bg=config.COLOR_BG, bd=2, relief="sunken")
        self.right_sidebar.pack(fill="y", side="right", padx=5, pady=5)
        self.right_sidebar.pack_propagate(False)

        ts_path = os.path.join(self.save_manager.project_path, "TILESET", "World_TILESET.png")
        self.tileset_palette = TilesetPalette(self.right_sidebar, ts_path, self.tile_size, self._on_asset_selected)
        self.tileset_palette.set_chunks(self.chunks)
        self.tileset_palette.set_points(self.world_data.get("points", []))
        self.tileset_palette.set_mode(self.mode)
        
        # Pre-load objects and items tilesets in a background thread to prevent startup lag
        def bg_preload():
            obj_path = os.path.join(self.save_manager.project_path, "TILESET", "OBJECTS_TILESET.png")
            items_path = os.path.join(self.save_manager.project_path, "TILESET", "ITEMS_TILESET.png")
            try:
                if os.path.exists(obj_path):
                    self.tileset_palette._tileset_cache[obj_path] = Image.open(obj_path).convert("RGBA")
                if os.path.exists(items_path):
                    self.tileset_palette._tileset_cache[items_path] = Image.open(items_path).convert("RGBA")
            except Exception as e:
                print(f"[ERROR] Background pre-load of tilesets failed: {e}")
        
        import threading
        threading.Thread(target=bg_preload, daemon=True).start()
        
        # --- HOT-SWITCH TRIPLE CLICK ---
        self.tileset_palette.canvas.bind("<Triple-Button-1>", self._on_chunk_pal_triple_click)

        # --- MAIN CANVAS ---
        self.canvas_container = tk.Frame(self.win, bg="#111", bd=2, relief="sunken")
        self.canvas_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.canvas = tk.Canvas(self.canvas_container, bg="#080808", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        # Interactions
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_click)
        self.canvas.bind("<ButtonRelease-1>", self.end_stroke)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<B3-Motion>", self.on_right_click)
        self.canvas.bind("<ButtonRelease-3>", self.end_stroke)
        self.canvas.bind("<MouseWheel>", self.on_zoom)

        
        # Inherit Global Cursor
        # GameEditor's _set_app_cursor manages this.

    def _on_chunk_pal_triple_click(self, event):
        """ The 'Master Architect' Hot-Switch gesture. """
        if self.mode == "CHUNK":
            # Determine chunk ID under mouse (TilesetPalette stores selected_id)
            cid = self.tileset_palette.selected_id
            if not cid: return
            
            print(f"[DEBUG] World Editor: Triple-click detected on {cid}. Swapping to Chunk Editor...")
            
            # 1. Save current World Layout
            self.save_world()
            
            # 2. Close this window & Cleanup DB
            self._on_window_close()
            
            # 3. Request Master App to open Chunk Editor with this ID
            if hasattr(self.master_app, "open_chunk_editor"):
                self.master_app.open_chunk_editor(target_chunk_id=cid)
        elif self.mode in ["OBJECT", "ITEMS"]:
            # Triple click on an object/item in the sidebar
            tid = self.tileset_palette.selected_id
            if not tid: return
            
            print(f"[DEBUG] World Editor: Triple-click detected on type {tid}. Opening Type Editor properties...")
            
            # 1. Open or locate the Type Editor using master_app
            if hasattr(self.master_app, "open_type_editor"):
                self.master_app.open_type_editor()
                
                # 2. Select the type in the Type Editor and open its properties
                te = self.master_app.current_type_editor
                if te and te.win.winfo_exists():
                    te.selected_type_id = tid
                    te.refresh_type_list()
                    te.open_property_editor(tid)

    def _on_asset_selected(self, asset_id, mode):
        """ Unified callback for Tiles, Chunks, and POIs. """
        if mode == "POINT_ADD":
            self.mode = "POINT_PLACEMENT"
            self.canvas.config(cursor="crosshair")
            print("[DEBUG] Move to map and click to place point.")
            return
        elif mode == "POINT_DEL":
            sel = self.tileset_palette.poi_list.selection()
            if sel:
                idx = int(sel[0])
                points = self.world_data.get("points", [])
                if 0 <= idx < len(points):
                    del points[idx]
                    self._sync_poi_to_palette()
                    self._draw_canvas()
                    self.save_manager.mark_dirty()
            return
        elif mode == "POINT_GOTO":
            idx = int(asset_id)
            points = self.world_data.get("points", [])
            if 0 <= idx < len(points):
                p = points[idx]
                win_w, win_h = self.win.winfo_width(), self.win.winfo_height()
                self.pan_x = (win_w / 2) - (p["x"] * self.zoom)
                self.pan_y = (win_h / 2) - (p["y"] * self.zoom)
                self._draw_canvas()
            return
        elif mode == "RENAME_CHUNK":
            self.save_manager.mark_dirty()
            self.chunk_cache.clear()
            self.photo_cache.clear()
            self._draw_canvas()
            return
        elif mode == "REMOVE_CHUNK":
            self.save_manager.mark_dirty()
            grid = self.world_data.get("grid", [])
            for r in range(len(grid)):
                for c in range(len(grid[r])):
                    val = grid[r][c]
                    val_str = f"C_{val}" if isinstance(val, (int, float)) or (isinstance(val, str) and val.isdigit()) else val
                    if val_str == asset_id:
                        grid[r][c] = 0
            if self.selected_chunk_id == asset_id:
                self.selected_chunk_id = "C_0"
            self.chunk_cache.clear()
            self.photo_cache.clear()
            self._draw_canvas()
            return

        if mode == "OBJECT":
            if self.mode != "OBJECT":
                obj_path = os.path.join(self.save_manager.project_path, "TILESET", "OBJECTS_TILESET.png")
                self.tileset_palette.load_tileset(obj_path)
                self.mode = "OBJECT"
                self.mode_var.set("OBJECT")
                self.tileset_palette.set_mode("OBJECT")
            if asset_id is not None:
                self.selected_tile_id = asset_id
        elif mode == "ITEMS":
            if self.mode != "ITEMS":
                items_path = os.path.join(self.save_manager.project_path, "TILESET", "ITEMS_TILESET.png")
                self.tileset_palette.load_tileset(items_path)
                self.mode = "ITEMS"
                self.mode_var.set("OBJECT")
                self.tileset_palette.set_mode("ITEMS")
            if asset_id is not None:
                self.selected_tile_id = asset_id
        elif mode == "TILE":
            if self.mode != "TILE":
                world_path = os.path.join(self.save_manager.project_path, "TILESET", "World_TILESET.png")
                self.tileset_palette.load_tileset(world_path)
                self.mode = "TILE"
                self.mode_var.set("TILE")
                self.tileset_palette.set_mode("TILE")
            if asset_id is not None:
                self.selected_tile_id = asset_id
        else:
            self.mode = mode
            self.mode_var.set(mode)
            if asset_id is not None:
                self.selected_chunk_id = asset_id
            world_path = os.path.join(self.save_manager.project_path, "TILESET", "World_TILESET.png")
            self.tileset_palette.load_tileset(world_path)

        self.canvas.config(cursor="")
        print(f"[DEBUG] Selection: {asset_id} ({self.mode})")

    def _update_mode(self):
        new_mode = self.mode_var.get()
        if self.mode == new_mode:
            return
        self.mode = new_mode
        self.canvas.config(cursor="crosshair" if self.mode == "POINT" else "")
        self.tileset_palette.set_mode(self.mode, render=False)
        if self.mode == "OBJECT":
            obj_path = os.path.join(self.save_manager.project_path, "TILESET", "OBJECTS_TILESET.png")
            self.tileset_palette.load_tileset(obj_path)
            self.tileset_palette.select_id(self.selected_tile_id, "OBJECT")
        elif self.mode == "TILE":
            world_path = os.path.join(self.save_manager.project_path, "TILESET", "World_TILESET.png")
            self.tileset_palette.load_tileset(world_path)
            self.tileset_palette.select_id(self.selected_tile_id, "TILE")
        else:
            world_path = os.path.join(self.save_manager.project_path, "TILESET", "World_TILESET.png")
            self.tileset_palette.load_tileset(world_path)
            if self.mode == "CHUNK":
                self.tileset_palette.select_id(self.selected_chunk_id, "CHUNK")
        print(f"[DEBUG] World Editor Mode: {self.mode}")

    def _sync_poi_to_palette(self):
        self.tileset_palette.set_points(self.world_data.get("points", []))



    def _draw_canvas(self):
        """ Redline Stability: Prevents recursion and handle leaks. """
        if self.is_drawing or not hasattr(self, 'canvas'): return
        self.is_drawing = True
        
        try:
            self.canvas.delete("all")
            if not self.tileset_img: return
            
            grid = self.world_data.get("grid", [])
            if not grid: return
        
            rows = len(grid)
            cols = len(grid[0])
            chunk_px = (self.tile_size * config.CHUNK_SIZE) * self.zoom
            
            self.tk_chunks = [] # Keep refs
            
            # --- ADVANCED VIEWPORT CULLING ---
            win_w = self.win.winfo_width()
            win_h = self.win.winfo_height()
            
            start_col = max(0, int(-self.pan_x // chunk_px))
            end_col = min(cols, int((-self.pan_x + win_w) // chunk_px) + 1)
            
            start_row = max(0, int(-self.pan_y // chunk_px))
            end_row = min(rows, int((-self.pan_y + win_h) // chunk_px) + 1)
            
            draw_count = 0
            for r in range(start_row, end_row):
                for c in range(start_col, end_col):
                    raw_cid = grid[r][c]
                    if not raw_cid: continue
                    
                    # Normalize ID for caching
                    cid = f"C_{raw_cid}" if isinstance(raw_cid, (int, float)) or (isinstance(raw_cid, str) and raw_cid.isdigit()) else raw_cid

                    x = self.pan_x + (c * chunk_px)
                    y = self.pan_y + (r * chunk_px)
                    
                    # 1. Render/Get Ground Chunk Image
                    ground_img = self._get_rendered_layer_chunk(cid, "ground", self.tileset_img)
                    if ground_img:
                        g_cache_key = (cid, "ground", round(self.zoom, 2))
                        if g_cache_key in self.photo_cache:
                            tk_g_img = self.photo_cache[g_cache_key]
                        else:
                            # Memory Guard
                            if len(self.photo_cache) > 600:
                                self.photo_cache.clear()
                                self.tk_chunks = []
                            
                            scaled_w = int(ground_img.width * self.zoom)
                            scaled_h = int(ground_img.height * self.zoom)
                            tk_g_img = ImageTk.PhotoImage(ground_img.resize((scaled_w, scaled_h), NEAREST_FILTER))
                            self.photo_cache[g_cache_key] = tk_g_img
                            
                        self.tk_chunks.append(tk_g_img)
                        self.canvas.create_image(x, y, image=tk_g_img, anchor="nw", tags="chunk")

                    # 2. Render/Get Object Chunk Image (overlay)
                    obj_img = self._get_rendered_layer_chunk(cid, "objects", self.obj_tileset_img)
                    if obj_img:
                        o_cache_key = (cid, "objects", round(self.zoom, 2))
                        if o_cache_key in self.photo_cache:
                            tk_o_img = self.photo_cache[o_cache_key]
                        else:
                            # Memory Guard
                            if len(self.photo_cache) > 600:
                                self.photo_cache.clear()
                                self.tk_chunks = []
                            
                            scaled_w = int(obj_img.width * self.zoom)
                            scaled_h = int(obj_img.height * self.zoom)
                            tk_o_img = ImageTk.PhotoImage(obj_img.resize((scaled_w, scaled_h), NEAREST_FILTER))
                            self.photo_cache[o_cache_key] = tk_o_img
                            
                        self.tk_chunks.append(tk_o_img)
                        self.canvas.create_image(x, y, image=tk_o_img, anchor="nw", tags="chunk")

                    if ground_img or obj_img:
                        draw_count += 1
                        
                    # Show Index if zoomed in
                    if self.zoom >= 0.4:
                        display_name = self.chunks.get(cid, {}).get("name", cid)
                        if display_name.startswith("C_") and display_name[2:].isdigit():
                            display_name = display_name[2:]
                        self.canvas.create_text(x + chunk_px/2, y + chunk_px/2, 
                                               text=str(display_name), fill="white", 
                                               font=("Arial", int(12 * self.zoom), "bold"),
                                               stipple="gray50", tags="chunk")
            print(f"[DEBUG] _draw_canvas: Finished. Draw Count: {draw_count}")

            # --- Draw Points ---
            for p in self.world_data.get("points", []):
                px = self.pan_x + (p["x"] * self.zoom)
                py = self.pan_y + (p["y"] * self.zoom)
                self.canvas.create_oval(px-5, py-5, px+5, py+5, fill=p.get("color", "lime"), outline="white", tags="chunk")
                self.canvas.create_text(px, py-10, text=p["name"], fill="white", font=("Arial", 8, "bold"), tags="chunk")

        finally:
            self.is_drawing = False

    def _normalize_cid(self, cid):
        if isinstance(cid, (int, float)):
            return f"C_{int(cid)}"
        elif not str(cid).startswith("C_"):
            return f"C_{cid}"
        return cid

    def _invalidate_cache(self, cid):
        scid = self._normalize_cid(cid)
        # Clean chunk_cache keys that match scid
        to_del_chunk = [k for k in self.chunk_cache.keys() if (isinstance(k, tuple) and len(k) > 0 and k[0] == scid) or k == scid]
        for k in to_del_chunk:
            del self.chunk_cache[k]
            
        # Clean photo_cache keys that match scid
        to_del_photo = [k for k in self.photo_cache.keys() if (isinstance(k, tuple) and len(k) > 0 and k[0] == scid) or k == scid]
        for k in to_del_photo:
            del self.photo_cache[k]

    def _get_rendered_layer_chunk(self, cid, layer_name, tileset_img):
        """ Returns a PIL image of the specific layer of the chunk. """
        if not tileset_img: return None
        scid = self._normalize_cid(cid)
        
        cache_key = (scid, layer_name)
        if cache_key in self.chunk_cache:
            return self.chunk_cache[cache_key]
            
        if len(self.chunk_cache) > 300:
            self.chunk_cache.clear()

        chunk = self.chunks.get(scid)
        if not chunk: return None
        
        full_sz = self.tile_size * config.CHUNK_SIZE
        img = Image.new("RGBA", (full_sz, full_sz), (0,0,0,0))
        
        data = chunk["data"]
        layer_grid = None
        if isinstance(data, dict):
            layer_grid = data.get(layer_name)
        elif isinstance(data, list) and layer_name == "ground":
            layer_grid = data
            
        has_any_tile = False
        if layer_grid:
            for r in range(config.CHUNK_SIZE):
                row = layer_grid.get(str(r), layer_grid.get(r)) if isinstance(layer_grid, dict) else (layer_grid[r] if r < len(layer_grid) else [])
                if not row: continue
                for c in range(config.CHUNK_SIZE):
                    tid = row.get(str(c), row.get(c, 0)) if isinstance(row, dict) else (row[c] if isinstance(row, list) and c < len(row) else 0)
                    if tid is None or tid <= 0: continue 
                    try:
                        tw = tileset_img.width // self.tile_size
                        tx = (tid % tw) * self.tile_size
                        ty = (tid // tw) * self.tile_size
                        if ty + self.tile_size <= tileset_img.height:
                            tile = tileset_img.crop((tx, ty, tx+self.tile_size, ty+self.tile_size))
                            img.paste(tile, (c * self.tile_size, r * self.tile_size), tile)
                            has_any_tile = True
                    except: continue
                    
        result_img = img if has_any_tile else None
        self.chunk_cache[cache_key] = result_img
        return result_img

    def _get_rendered_chunk(self, cid):
        """ Compatibility wrapper that flattens ground and objects. """
        scid = self._normalize_cid(cid)
        if (scid, "flattened") in self.chunk_cache:
            return self.chunk_cache[(scid, "flattened")]
            
        ground_img = self._get_rendered_layer_chunk(scid, "ground", self.tileset_img)
        obj_img = self._get_rendered_layer_chunk(scid, "objects", self.obj_tileset_img)
        
        if not ground_img and not obj_img:
            self.chunk_cache[(scid, "flattened")] = None
            return None
            
        full_sz = self.tile_size * config.CHUNK_SIZE
        img = Image.new("RGBA", (full_sz, full_sz), (0,0,0,0))
        if ground_img:
            img.paste(ground_img, (0, 0), ground_img)
        if obj_img:
            img.paste(obj_img, (0, 0), obj_img)
            
        self.chunk_cache[(scid, "flattened")] = img
        return img

    def undo(self):
        if not self.history: return
        import copy
        action = self.history.pop()
        
        if isinstance(action, tuple) and action[0] == "TILE":
            redo_tiles = []
            for target_cid, prev_data in action[1]:
                chunk = self.chunks.get(target_cid)
                if chunk:
                    redo_tiles.append((target_cid, copy.deepcopy(chunk["data"])))
                    chunk["data"] = prev_data
                    self._invalidate_cache(target_cid)
                    self.save_manager.save_chunks(self.chunks, [target_cid])
            self.redo_stack.append(("TILE", redo_tiles))
        else:
            grid_data = action[1] if isinstance(action, tuple) else action
            self.redo_stack.append(("CHUNK", copy.deepcopy(self.world_data["grid"])))
            self.world_data["grid"] = grid_data
            self.photo_cache.clear()
            
        self._draw_canvas()
        print("[DEBUG] Undo performed.")

    def redo(self):
        if not self.redo_stack: return
        import copy
        action = self.redo_stack.pop()
        
        if isinstance(action, tuple) and action[0] == "TILE":
            undo_tiles = []
            for target_cid, next_data in action[1]:
                chunk = self.chunks.get(target_cid)
                if chunk:
                    undo_tiles.append((target_cid, copy.deepcopy(chunk["data"])))
                    chunk["data"] = next_data
                    self._invalidate_cache(target_cid)
                    self.save_manager.save_chunks(self.chunks, [target_cid])
            self.history.append(("TILE", undo_tiles))
        else:
            grid_data = action[1] if isinstance(action, tuple) else action
            self.history.append(("CHUNK", copy.deepcopy(self.world_data["grid"])))
            self.world_data["grid"] = grid_data
            self.photo_cache.clear()
            
        self._draw_canvas()
        print("[DEBUG] Redo performed.")

    def end_stroke(self, event=None):
        if hasattr(self, "current_stroke_tiles") and self.current_stroke_tiles:
            self.redo_stack.clear()
            self.history.append(("TILE", self.current_stroke_tiles))
            if len(self.history) > 50: self.history.pop(0)
            
            # Persist all modified chunks during the stroke to the database at once
            modified_cids = [cid for cid, _ in self.current_stroke_tiles]
            if modified_cids:
                self.save_manager.save_chunks(self.chunks, modified_cids)
                
            self.current_stroke_tiles = []

    def _on_alt_click(self, event):
        """ Quick-switch to Sampler behavior. """
        self._execute_drop(event)

    def _execute_drop(self, event):
        """ The Eye Dropper: Grabs the asset under the mouse. """
        chunk_px = (self.tile_size * config.CHUNK_SIZE) * self.zoom
        ccol, crow = int((event.x - self.pan_x) / chunk_px), int((event.y - self.pan_y) / chunk_px)
        
        grid = self.world_data.get("grid", [])
        if 0 <= crow < len(grid) and 0 <= ccol < len(grid[ crow ]):
            cid = grid[crow][ccol]
            if cid:
                # Normalize CID
                if isinstance(cid, (int, float)):
                    target_cid = f"C_{int(cid)}"
                elif not str(cid).startswith("C_"):
                    target_cid = f"C_{cid}"
                else:
                    target_cid = cid

                if self.mode in ["CHUNK", "DROP"]:
                    self.selected_chunk_id = target_cid
                    self.tileset_palette.select_id(target_cid, "CHUNK")
                    print(f"[DEBUG] Sampler captured chunk: {target_cid}")
                else:
                    # In TILE or OBJECT/ITEMS mode, grab the specific sub-tile under the mouse!
                    chunk = self.chunks.get(target_cid)
                    if chunk:
                        world_x = (event.x - self.pan_x) / chunk_px
                        world_y = (event.y - self.pan_y) / chunk_px
                        sm_x = int((world_x - ccol) * config.CHUNK_SIZE)
                        sm_y = int((world_y - crow) * config.CHUNK_SIZE)
                        
                        if 0 <= sm_x < config.CHUNK_SIZE and 0 <= sm_y < config.CHUNK_SIZE:
                            data = chunk.get("data", {})
                            tile_id = 0
                            
                            layer_name = "objects" if self.mode in ["OBJECT", "ITEMS"] else "ground"
                            
                            if isinstance(data, dict):
                                layer_grid = data.get(layer_name)
                            elif isinstance(data, list) and layer_name == "ground":
                                layer_grid = data
                            else:
                                layer_grid = None
                                
                            if layer_grid:
                                row = layer_grid.get(str(sm_y), layer_grid.get(sm_y)) if isinstance(layer_grid, dict) else (layer_grid[sm_y] if sm_y < len(layer_grid) else [])
                                if row:
                                    tile_id = row.get(str(sm_x), row.get(sm_x, 0)) if isinstance(row, dict) else (row[sm_x] if isinstance(row, list) and sm_x < len(row) else 0)
                            
                            if tile_id is not None and tile_id >= 0:
                                if self.mode in ["OBJECT", "ITEMS"] and tile_id == 0:
                                    # Ignore empty space when sampling objects/items
                                    pass
                                else:
                                    self.selected_tile_id = tile_id
                                    self.tileset_palette.select_id(tile_id, self.mode)
                                    print(f"[DEBUG] Sampler captured {self.mode} ID: {tile_id}")

    def _execute_fill(self, event):
        """ Viewport-limited Paint Bucket. """
        chunk_px = (self.tile_size * config.CHUNK_SIZE) * self.zoom
        ccol, crow = int((event.x - self.pan_x) / chunk_px), int((event.y - self.pan_y) / chunk_px)
        
        grid = self.world_data.get("grid", [])
        if not (0 <= crow < len(grid) and 0 <= ccol < len(grid[0])): return
        
        target_id = grid[crow][ccol]
        if target_id == self.selected_chunk_id: return
        
        # Save Undo State
        import copy
        self.redo_stack.clear()
        self.history.append(("CHUNK", copy.deepcopy(grid)))
        if len(self.history) > 50: self.history.pop(0)

        # Get Viewport Bounds
        win_w, win_h = self.win.winfo_width(), self.win.winfo_height()
        sc = max(0, int(-self.pan_x // chunk_px))
        ec = min(len(grid[0]), int((-self.pan_x + win_w) // chunk_px) + 1)
        sr = max(0, int(-self.pan_y // chunk_px))
        er = min(len(grid), int((-self.pan_y + win_h) // chunk_px) + 1)

        count = 0
        for r in range(sr, er):
            for c in range(sc, ec):
                if grid[r][c] == target_id:
                    grid[r][c] = self.selected_chunk_id
                    count += 1
        
        if count > 0:
            self._draw_canvas()
            self.save_manager.mark_dirty()
            print(f"[DEBUG] Bucket filled {count} locations.")

    def on_click(self, event):
        if self.mode == "DROP":
            self._execute_drop(event)
            return
        if self.mode == "FILL":
            self._execute_fill(event)
            return
        if self.mode == "POINT_PLACEMENT" or self.mode == "POINT":
            self._execute_poi_add(event)
            return

        # Regular Click Logic (Chunk/Tile painting)
        chunk_px = (self.tile_size * config.CHUNK_SIZE) * self.zoom
        
        world_x = (event.x - self.pan_x) / chunk_px
        world_y = (event.y - self.pan_y) / chunk_px
        ccol, crow = int(world_x), int(world_y)
        
        grid = self.world_data.get("grid", [])
        if not (0 <= crow < len(grid) and 0 <= ccol < len(grid[0])): return

        # Detect Stroke Start (to save undo)
        pos = (ccol, crow)
        if event.type == tk.EventType.ButtonPress:
            import copy
            self.redo_stack.clear()
            self.current_stroke_tiles = []
            if self.mode not in ["TILE", "OBJECT", "ITEMS"]:
                self.history.append(("CHUNK", copy.deepcopy(grid)))
                if len(self.history) > 50: self.history.pop(0)
            self.last_grid_pos = pos
        elif pos == self.last_grid_pos:
            return # Don't repeat on same cell during motion

        self.last_grid_pos = pos

        if self.mode == "CHUNK":
            if grid[crow][ccol] != self.selected_chunk_id:
                grid[crow][ccol] = self.selected_chunk_id
                self._draw_canvas()
                self.save_manager.mark_dirty()
        elif self.mode in ["TILE", "OBJECT", "ITEMS"]:
            # TILE/OBJECT MODE: Direct edit of the chunk at this location
            # Normalize CID for registry lookup
            raw_cid = grid[crow][ccol]
            if not raw_cid: return
            
            if isinstance(raw_cid, (int, float)):
                target_cid = f"C_{int(raw_cid)}"
            elif not str(raw_cid).startswith("C_"):
                target_cid = f"C_{raw_cid}"
            else:
                target_cid = raw_cid

            chunk = self.chunks.get(target_cid)
            if not chunk or chunk.get("locked"):
                return # Can't touch locked chunks!
                
            # Record chunk state for undo before we modify it
            import copy
            if not any(cid == target_cid for cid, _ in self.current_stroke_tiles):
                self.current_stroke_tiles.append((target_cid, copy.deepcopy(chunk["data"])))
                
            # Get submodule coordinates (0 to CHUNK_SIZE-1)
            sm_x = int((world_x - ccol) * config.CHUNK_SIZE)
            sm_y = int((world_y - crow) * config.CHUNK_SIZE)
            
            if 0 <= sm_x < config.CHUNK_SIZE and 0 <= sm_y < config.CHUNK_SIZE:
                # Normalize CID for registry lookup
                if isinstance(target_cid, (int, float)):
                    scid = f"C_{int(target_cid)}"
                elif not str(target_cid).startswith("C_"):
                    scid = f"C_{target_cid}"
                else:
                    scid = target_cid

                # Update chunk data permanently (Robust List/Dict handling)
                data = chunk["data"]
                
                def update_layer(layer_data):
                    if isinstance(layer_data, dict):
                        row_key = str(sm_y) if str(sm_y) in layer_data else sm_y
                        if row_key not in layer_data: layer_data[row_key] = {}
                        row = layer_data[row_key]
                        col_key = str(sm_x) if isinstance(row, dict) and str(sm_x) in row else sm_x
                        if isinstance(row, dict): row[col_key] = self.selected_tile_id
                    elif isinstance(layer_data, list):
                        if sm_y < len(layer_data):
                            row = layer_data[sm_y]
                            if isinstance(row, list) and sm_x < len(row): row[sm_x] = self.selected_tile_id

                if isinstance(data, dict):
                    layer_name = "objects" if self.mode in ["OBJECT", "ITEMS"] else "ground"
                    target = data.get(layer_name)
                    if target is None:
                        data[layer_name] = [[0]*config.CHUNK_SIZE for _ in range(config.CHUNK_SIZE)]
                        target = data[layer_name]
                    update_layer(target)
                elif isinstance(data, list):
                    update_layer(data)
                
                # Invalidate cache for this chunk
                self._invalidate_cache(target_cid)
                
                self._draw_canvas()
        elif self.mode == "POINT":
            # Add a POI at coordinates
            # Screen -> World (unscaled)
            wx = (event.x - self.pan_x) / self.zoom
            wy = (event.y - self.pan_y) / self.zoom
            
            name = simpledialog.askstring("New Point", "Enter label for this location:")
            if name:
                self.world_data.get("points", []).append({
                    "name": name,
                    "x": wx,
                    "y": wy,
                    "color": "lime"
                })
                
                # --- LOGIC SYNC ---
                # Register this point in Defines.hry so scripts can reference it
                import ScriptParser
                pois = { p["name"]: i for i, p in enumerate(self.world_data.get("points", [])) }
                ScriptParser.sync_defines_block(self.save_manager.project_path, "WORLD POINTS", "POI_", pois)
                
                self._draw_canvas()
                self.save_manager.mark_dirty()

    def start_pan(self, event):
        self.start_x = event.x
        self.start_y = event.y

    def do_pan(self, event):
        self.pan_x += (event.x - self.start_x)
        self.pan_y += (event.y - self.start_y)
        self.start_x = event.x
        self.start_y = event.y
        self._draw_canvas()

    def on_zoom(self, event):
        # Check if Control is held (state & 0x0004)
        if event.state & 0x0004:
            old_zoom = self.zoom
            
            # Determine screen coordinates of the focus point (mouse position, or viewport center as fallback)
            canvas_w = self.canvas.winfo_width()
            canvas_h = self.canvas.winfo_height()
            
            focus_x = event.x if (0 <= event.x <= canvas_w) else (canvas_w / 2)
            focus_y = event.y if (0 <= event.y <= canvas_h) else (canvas_h / 2)
            
            # Translate screen focus point to world coordinates before zoom changes
            world_focus_x = (focus_x - self.pan_x) / old_zoom
            world_focus_y = (focus_y - self.pan_y) / old_zoom
            
            if event.delta > 0: 
                self.zoom = round(self.zoom * 1.15, 2)
            else: 
                self.zoom = round(self.zoom / 1.15, 2)
            
            self.zoom = max(0.05, min(self.zoom, 4.0))
            
            if self.zoom != old_zoom:
                # Adjust pan_x/pan_y so that the focused world coordinate stays at the exact same screen coordinate
                self.pan_x = focus_x - (world_focus_x * self.zoom)
                self.pan_y = focus_y - (world_focus_y * self.zoom)
                
                # Full purge on zoom-change to prevent handle stacking.
                self.photo_cache.clear()
                self.tk_chunks = []
                self._draw_canvas()
        else:
            # Vertical Scroll: Adjust pan_y
            # event.delta is usually +/- 120 on Windows
            scroll_amount = (event.delta / 120) * 80 
            self.pan_y += scroll_amount
            self._draw_canvas()


    def save_world(self):
        self.save_manager.save_world(self.world_data, self.current_map_name)


    def save_project_all(self):
        self.save_world()
        succ, err = self.save_manager.save_project()
        if succ:
            messagebox.showinfo("Success", "Entire Project and World safely archived to ZIP.")
        else:
            messagebox.showerror("Error", f"Global Save Failed: {err}")

    def _on_map_changed(self, event=None):
        """ Handles switching between different maps. """
        new_map = self.map_combo.get()
        if new_map == self.current_map_name: return
        
        # Save current state before switching
        self.save_world()
        
        self.current_map_name = new_map
        self.world_data = self.save_manager.load_world(self.current_map_name)
        
        # Clear caches
        self.photo_cache.clear()
        self._draw_canvas()
        print(f"[DEBUG] Switched to Map: {new_map}")

    def _add_new_map(self):
        """ Prompt user for a new map name and register it. """
        name = simpledialog.askstring("New Map", "Enter Map Name (e.g. Dungeons):")
        if not name: return
        
        # Sanitize name
        import re
        clean_name = re.sub(r'[^a-zA-Z0-9_]', '', name).upper()
        if clean_name in self.map_list:
            messagebox.showwarning("Warning", "Map already exists!")
            return
            
        self.map_list.append(clean_name)
        self._sync_maps_to_defines()
        
        self.map_combo["values"] = self.map_list
        self.map_combo.set(clean_name)
        self._on_map_changed()

    def _remove_current_map(self):
        """ Removes the currently selected map. """
        if len(self.map_list) <= 1:
            messagebox.showwarning("Warning", "Cannot remove the last map!")
            return
            
        if not messagebox.askyesno("Confirm Removal", f"Are you sure you want to PERMANENTLY remove '{self.current_map_name}'?"):
            return
            
        old_map = self.current_map_name
        self.map_list.remove(old_map)
        self._sync_maps_to_defines()
        
        # Switch to first available map
        new_map = self.map_list[0]
        self.map_combo.set(new_map)
        self.current_map_name = None # Force switch
        self._on_map_changed()

    def _execute_poi_add(self, event):
        """ Add a POI at coordinates. """
        # Screen -> World (unscaled)
        wx = (event.x - self.pan_x) / self.zoom
        wy = (event.y - self.pan_y) / self.zoom
        
        name = simpledialog.askstring("New Point", "Enter label for this location:")
        if name:
            points = self.world_data.setdefault("points", [])
            points.append({
                "name": name,
                "x": wx,
                "y": wy,
                "color": "lime"
            })
            
            # Reset cursor/mode if it was a one-shot add
            if self.mode == "POINT_PLACEMENT":
                self.mode = "POINT"
                self.canvas.config(cursor="")
            
            self._sync_poi_to_palette()
            self._draw_canvas()
            self.save_manager.mark_dirty()
            print(f"[DEBUG] Point added: {name} at ({wx:.1f}, {wy:.1f})")

    def _sync_maps_to_defines(self):
        """ Updates Defines.hry with the new map list. """
        map_dict = { name: i for i, name in enumerate(self.map_list) }
        ScriptParser.sync_maps(self.save_manager.project_path, map_dict)
        self.save_manager.mark_dirty()

    def _refresh_map_list(self):
        """ Re-scans Defines.hry for maps and updates the dropdown. """
        new_list = ScriptParser.get_all_maps(self.save_manager.project_path)
        if new_list != self.map_list:
            print(f"[DEBUG] World Editor: Map list synced from script ({len(new_list)} maps).")
            self.map_list = new_list
            self.map_combo["values"] = self.map_list
            
            # If our current map was deleted in code, switch to safe fallback
            if self.current_map_name not in self.map_list and self.map_list:
                self.map_combo.set(self.map_list[0])
                self._on_map_changed()


    def on_close(self):
        self.win.destroy()

    def on_right_click(self, event):
        if self.mode in ["OBJECT", "ITEMS"]:
            self.erase_object_at(event)
        else:
            if event.type == tk.EventType.ButtonPress:
                self.start_pan(event)
            else:
                self.do_pan(event)

    def erase_object_at(self, event):
        chunk_px = (self.tile_size * config.CHUNK_SIZE) * self.zoom
        world_x = (event.x - self.pan_x) / chunk_px
        world_y = (event.y - self.pan_y) / chunk_px
        ccol, crow = int(world_x), int(world_y)
        
        grid = self.world_data.get("grid", [])
        if not (0 <= crow < len(grid) and 0 <= ccol < len(grid[0])): return

        pos = (ccol, crow)
        if event.type == tk.EventType.ButtonPress:
            self.redo_stack.clear()
            self.current_stroke_tiles = []
            self.last_grid_pos = pos
        elif pos == self.last_grid_pos:
            return
        self.last_grid_pos = pos

        raw_cid = grid[crow][ccol]
        if not raw_cid: return
        target_cid = self._normalize_cid(raw_cid)
        
        chunk = self.chunks.get(target_cid)
        if not chunk or chunk.get("locked"): return

        # Record undo
        import copy
        if not any(cid == target_cid for cid, _ in self.current_stroke_tiles):
            self.current_stroke_tiles.append((target_cid, copy.deepcopy(chunk["data"])))

        sm_x = int((world_x - ccol) * config.CHUNK_SIZE)
        sm_y = int((world_y - crow) * config.CHUNK_SIZE)

        if 0 <= sm_x < config.CHUNK_SIZE and 0 <= sm_y < config.CHUNK_SIZE:
            data = chunk["data"]
            if isinstance(data, dict):
                layer_name = "objects"
                target = data.get(layer_name)
                if target is not None:
                    if isinstance(target, dict):
                        row_key = str(sm_y) if str(sm_y) in target else sm_y
                        if row_key in target:
                            row = target[row_key]
                            col_key = str(sm_x) if isinstance(row, dict) and str(sm_x) in row else sm_x
                            if isinstance(row, dict) and col_key in row:
                                row[col_key] = 0
                    elif isinstance(target, list):
                        if sm_y < len(target):
                            row = target[sm_y]
                            if isinstance(row, list) and sm_x < len(row):
                                row[sm_x] = 0

            # Invalidate cache and redraw
            self._invalidate_cache(target_cid)
            self._draw_canvas()
