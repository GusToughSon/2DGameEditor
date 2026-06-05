# ==============================================================================
# WORLDEDITOR.PY - THE CARTOGRAPHER'S COMPASS
# ==============================================================================
# This module handles large-scale map editing and world grid stitching.
# Supports Tile/Chunk tool modes with direct passthrough to chunk data.
# ==============================================================================

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import os
import config
from PIL import Image, ImageTk, ImageDraw
try:
    NEAREST_FILTER = Image.Resampling.NEAREST
except AttributeError:
    NEAREST_FILTER = Image.NEAREST
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
        tools = [("Chunk", "CHUNK"), ("Tile", "TILE"), ("Points", "POINT"), ("Sampler", "DROP"), ("Bucket", "FILL")]
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
        self.canvas.bind("<Button-3>", self.start_pan)
        self.canvas.bind("<B3-Motion>", self.do_pan)
        self.canvas.bind("<MouseWheel>", self.on_zoom)

        
        # Inherit Global Cursor
        # GameEditor's _set_app_cursor manages this.

    def _on_chunk_pal_triple_click(self, event):
        """ The 'Master Architect' Hot-Switch gesture. """
        if self.mode != "CHUNK": return
        
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
                # Center camera on P (World -> Screen)
                # target_x = pan_x + p.x * zoom
                # We want: 0 + win_w/2 = pan_x + p.x * zoom
                # pan_x = win_w/2 - p.x * zoom
                win_w, win_h = self.win.winfo_width(), self.win.winfo_height()
                self.pan_x = (win_w / 2) - (p["x"] * self.zoom)
                self.pan_y = (win_h / 2) - (p["y"] * self.zoom)
                self._draw_canvas()
            return

        self.mode = mode
        self.mode_var.set(mode) # Sync toolbar radiobuttons
        self.canvas.config(cursor="")
        
        if mode == "TILE":
            self.selected_tile_id = asset_id
        else:
            self.selected_chunk_id = asset_id
        
        print(f"[DEBUG] Selection: {asset_id} ({mode})")

    def _update_mode(self):
        self.mode = self.mode_var.get()
        self.canvas.config(cursor="crosshair" if self.mode == "POINT" else "")
        self.tileset_palette.set_mode(self.mode)
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
                    
                    # Render/Get Chunk Image
                    img = self._get_rendered_chunk(cid)
                    if img:
                        cache_key = (cid, round(self.zoom, 2))
                        if cache_key in self.photo_cache:
                            tk_img = self.photo_cache[cache_key]
                        else:
                            # Memory Guard
                            if len(self.photo_cache) > 400:
                                self.photo_cache.clear()
                                self.tk_chunks = []
                            
                            scaled_w = int(img.width * self.zoom)
                            scaled_h = int(img.height * self.zoom)
                            tk_img = ImageTk.PhotoImage(img.resize((scaled_w, scaled_h), Image.NEAREST))
                            self.photo_cache[cache_key] = tk_img
                            
                        self.tk_chunks.append(tk_img)
                        self.canvas.create_image(x, y, image=tk_img, anchor="nw", tags="chunk")
                        draw_count += 1
                        
                    # Show Index if zoomed in
                    if self.zoom >= 0.4:
                        self.canvas.create_text(x + chunk_px/2, y + chunk_px/2, 
                                              text=str(cid), fill="white", 
                                              font=("Arial", int(14 * self.zoom), "bold"),
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

    def _get_rendered_chunk(self, cid):
        """ Returns a PIL image of the chunk, cached with a strict 150-item limit. """
        # Normalize CID to string with 'C_' prefix if it's a raw number
        if isinstance(cid, (int, float)):
            scid = f"C_{int(cid)}"
        elif not str(cid).startswith("C_"):
            scid = f"C_{cid}"
        else:
            scid = cid

        if scid in self.chunk_cache:
            return self.chunk_cache[scid]
            
        # L1 EVICTION: Prevent RAM ballooning
        if len(self.chunk_cache) > 150:
            self.chunk_cache.clear()

        chunk = self.chunks.get(scid)
        if not chunk: return None
        
        full_sz = self.tile_size * config.CHUNK_SIZE
        img = Image.new("RGBA", (full_sz, full_sz), (0,0,0,0))
        
        data = chunk["data"]
        layers = []
        if isinstance(data, dict):
            if "ground" in data: layers.append(data["ground"])
            if "objects" in data: layers.append(data["objects"])
        elif isinstance(data, list):
            layers.append(data)

        for layer in layers:
            for r in range(config.CHUNK_SIZE):
                row = layer.get(str(r), layer.get(r, [])) if isinstance(layer, dict) else (layer[r] if r < len(layer) else [])
                for c in range(config.CHUNK_SIZE):
                    tid = row.get(str(c), row.get(c, 0)) if isinstance(row, dict) else (row[c] if c < len(row) else 0)
                    if tid <= 0: continue 
                    try:
                        tw = self.tileset_img.width // self.tile_size
                        tx = (tid % tw) * self.tile_size
                        ty = (tid // tw) * self.tile_size
                        if ty + self.tile_size <= self.tileset_img.height:
                            tile = self.tileset_img.crop((tx, ty, tx+self.tile_size, ty+self.tile_size))
                            img.paste(tile, (c * self.tile_size, r * self.tile_size), tile)
                    except: continue
                
        self.chunk_cache[scid] = img
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
                    if target_cid in self.chunk_cache:
                        del self.chunk_cache[target_cid]
                    to_del = [k for k in self.photo_cache.keys() if k[0] == target_cid]
                    for k in to_del: del self.photo_cache[k]
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
                    if target_cid in self.chunk_cache:
                        del self.chunk_cache[target_cid]
                    to_del = [k for k in self.photo_cache.keys() if k[0] == target_cid]
                    for k in to_del: del self.photo_cache[k]
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
                self.selected_chunk_id = cid
                self.tileset_palette.select_id(cid, "CHUNK")
                print(f"[DEBUG] Sampler captured: {cid}")

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
            if self.mode != "TILE":
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
        elif self.mode == "TILE":
            # TILE MODE: Direct edit of the chunk at this location
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
                    target = data.get("ground", data.get("layer0"))
                    if target is not None: update_layer(target)
                elif isinstance(data, list):
                    update_layer(data)
                
                # Invalidate cache for this chunk
                if scid in self.chunk_cache:
                    del self.chunk_cache[scid]
                # Clear photo cache for this chunk only
                to_del = [k for k in self.photo_cache.keys() if k[0] == scid or k[0] == target_cid]
                for k in to_del: del self.photo_cache[k]
                
                self._draw_canvas()
                self.save_manager.save_chunks(self.chunks, [scid])
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
            if event.delta > 0: self.zoom = round(self.zoom * 1.15, 2)
            else: self.zoom = round(self.zoom / 1.15, 2)
            
            self.zoom = max(0.05, min(self.zoom, 4.0))
            
            if self.zoom != old_zoom:
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
        self.save_manager.save_world(self.world_data)
        messagebox.showinfo("Success", "World Layout cached in memory pool.")

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
        
        self.map_combo.config(values=self.map_list)
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
            self.map_combo.config(values=self.map_list)
            
            # If our current map was deleted in code, switch to safe fallback
            if self.current_map_name not in self.map_list and self.map_list:
                self.map_combo.set(self.map_list[0])
                self._on_map_changed()

    def save_world(self):
        self.save_manager.save_world(self.world_data, self.current_map_name)
        # We don't show the messagebox here to keep map switching fluid.

    def on_close(self):
        self.win.destroy()
