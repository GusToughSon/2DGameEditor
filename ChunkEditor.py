# CHUNKEDITOR.PY - Chunk Editor Suite

import tkinter as tk
from tkinter import messagebox, ttk
import os
import copy
import config
import threading
from PIL import Image, ImageTk, ImageDraw
Image_NEAREST = getattr(getattr(Image, "Resampling", Image), "NEAREST")
from EditorComponents import center_window, TilesetPalette

class ChunkEditor:
    def __init__(self, master_app, save_manager, target_chunk_id=None):
        print("[TRACE-1] Initializing ChunkEditor Base...")
        self.master_app = master_app
        self.save_manager = save_manager
        
        # --- DATA ---
        print("[TRACE-2] Requesting Chunk Loader...")
        self.chunks = self.save_manager.load_chunks()
        print(f"[TRACE-3] Chunk Data Mounted: {len(self.chunks)} entries.")
        
        self.selected_chunk_id = None
        self.tile_size = self.save_manager.project_data.get("tile_size", 16)
        
        print("[TRACE-4] Resolving Tileset Reference...")
        self.orig_tileset = self._load_tileset()
        
        # --- STATE ---
        self.zoom = 2.5 
        self.scale = 2 
        self.selected_tile_id = 0
        self.tool_mode = "PENCIL" 
        
        self.undo_stack = []
        self.redo_stack = []
        self.clipboard = None 
        self.selection_start = None
        self.selection_end = None
        self.paste_pos = None 
        self.is_drawing = False
        self.is_saving = False # Async Flag
        
        # Panning
        self.pan_x = 0
        self.pan_y = 0
        
        # Caching
        self.tile_cache = {} 
        
        # --- WINDOW SETUP ---
        print("[TRACE-5] Creating Main Toplevel...")
        self.win = tk.Toplevel(self.master_app.root)
        self.win.title("Chunk Editor")
        center_window(self.win, self.master_app.root, 1300, 950)
        self.win.configure(bg=config.COLOR_BG)
        
        self.setup_ui()
        self._setup_shortcuts()
        
        # Trigger first render once window is ready
        self.win.bind("<Configure>", self._on_v_configure)
        
        if self.chunks:
            boot_id = target_chunk_id if target_chunk_id in self.chunks else sorted(self.chunks.keys())[0]
            print(f"[TRACE-6] Auto-booting into chunk: {boot_id}")
            self._select_chunk(boot_id)

    def _on_v_configure(self, event):
        print("[TRACE-CONFIG] Viewport Re-negotiation triggered.")
        if not hasattr(self, "_config_after_id"): self._config_after_id = None
        if self._config_after_id: self.win.after_cancel(self._config_after_id)
        self._config_after_id = self.win.after(150, self.render)

    def _load_tileset(self):
        tp = os.path.join(self.save_manager.project_path, "TILESET", "World_TILESET.png")
        print(f"[TRACE-TILES] Probing Tileset: {tp}")
        if os.path.exists(tp):
            try:
                img = Image.open(tp).convert("RGBA")
                print(f"[TRACE-TILES-OK] Size: {img.width}x{img.height}")
                return img
            except Exception as e:
                print(f"[TRACE-TILES-ERR] Load failed: {e}")
        return None

    def setup_ui(self):
        print("[TRACE-UI] Building Control Surface...")
        self.toolbar = tk.Frame(self.win, bg="#111", bd=1, relief="raised", height=50)
        self.toolbar.pack(fill="x", side="top")
        self.toolbar.pack_propagate(False)

        tool_f = tk.Frame(self.toolbar, bg="#111")
        tool_f.pack(side="left", padx=10)

        self.btn_pencil = tk.Button(tool_f, text="✏️ Pencil", command=lambda: self.set_tool("PENCIL"), bg="#10b981", fg="white", bd=0, padx=10)
        self.btn_pencil.pack(side="left", padx=2)
        
        self.btn_select = tk.Button(tool_f, text="⬚ Select", command=lambda: self.set_tool("SELECT"), bg="#222", fg="white", bd=0, padx=10)
        self.btn_select.pack(side="left", padx=2)
        
        self.btn_paste = tk.Button(tool_f, text="📋 Paste", command=lambda: self.set_tool("PASTE"), bg="#222", fg="white", bd=0, padx=10, state="disabled")
        self.btn_paste.pack(side="left", padx=2)

        self.btn_fill = tk.Button(tool_f, text="🪣 Fill", command=lambda: self.set_tool("FILL"), bg="#222", fg="white", bd=0, padx=10)
        self.btn_fill.pack(side="left", padx=2)
        
        self.btn_undo = tk.Button(tool_f, text="↩ Undo", command=self.handle_undo, bg="#222", fg="white", bd=0, padx=10)
        self.btn_undo.pack(side="left", padx=2)

        self.btn_redo = tk.Button(tool_f, text="↪ Redo", command=self.handle_redo, bg="#222", fg="white", bd=0, padx=10)
        self.btn_redo.pack(side="left", padx=2)

        self.btn_rotate = tk.Button(tool_f, text="🔄 Rotate", command=self.handle_rotate, bg="#222", fg="white", bd=0, padx=10)
        self.btn_rotate.pack(side="left", padx=2)

        nav_f = tk.Frame(self.toolbar, bg="#111")
        nav_f.pack(side="left", padx=20)
        
        tk.Button(nav_f, text="◀ Prev", command=self._prev_chunk, bg="#333", fg="white", bd=0, padx=10).pack(side="left", padx=2)
        tk.Button(nav_f, text="Next ▶", command=self._next_chunk, bg="#333", fg="white", bd=0, padx=10).pack(side="left", padx=2)

        name_f = tk.Frame(self.toolbar, bg="#111")
        name_f.pack(side="left", padx=20)
        self.name_entry = tk.Entry(name_f, bg="#222", fg="white", insertbackground="white", bd=0, width=15, font=("Arial", 9))
        self.name_entry.pack(side="left", padx=2, ipady=2)
        self.name_entry.bind("<FocusOut>", self._on_name_entry_focus_out)
        self.name_entry.bind("<Key>", self._on_name_entry_keypress)
        self.name_entry.bind("<KeyRelease>", self._on_name_entry_key_release)
        self.name_entry.bind("<Return>", lambda e: self.win.focus())

        act_f = tk.Frame(self.toolbar, bg="#111")
        act_f.pack(side="right", padx=10)
        
        tk.Button(act_f, text="🗑️ Clear", command=self._clear_chunk, bg="#411", fg="#f88", bd=0, padx=10).pack(side="left", padx=5)
        self.btn_save = tk.Button(act_f, text="💾 Save All", command=self._save_all_async, bg="#141", fg="#8f8", bd=0, padx=10)
        self.btn_save.pack(side="left", padx=5)

        # --- MAGNETIC FLOATING PALETTES ---
        try:
            self._setup_floating_toolset()
        except Exception as e:
            print(f"[TRACE-UI-ERR] Palette Launch Failed: {e}")
        


        # --- VIEWPORT ---
        self.viewport = tk.Frame(self.win, bg="#0a0a0c")
        self.viewport.pack(expand=True, fill="both")
        self.canvas = tk.Canvas(self.viewport, bg="#050505", highlightthickness=0)
        self.canvas.pack(expand=True)
        
        self.canvas.bind("<Button-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.canvas.bind("<Motion>", self._on_mouse_hover)
        self.canvas.bind("<MouseWheel>", self._on_zoom)

        self.status_bar = tk.Frame(self.win, bg="#111", height=25)
        self.status_bar.pack(fill="x", side="bottom")
        self.status_label = tk.Label(self.status_bar, text="Workspace Ready", bg="#111", fg="#888", font=("Arial", 8))
        self.status_label.pack(side="left", padx=10)
        print("[TRACE-UI] Control Surface Finalized.")

    def _setup_floating_toolset(self):
        ts_path = os.path.join(self.save_manager.project_path, "TILESET", "World_TILESET.png")
        bx, by = self.win.winfo_x(), self.win.winfo_y()

        # 1. Chunk Library (4 Chunks @ 68px + 21px gutter = 293px)
        self.library_win = tk.Toplevel(self.win)
        self.library_win.title("Chunk Library")
        self.library_win.geometry(f"293x750+{bx - 310}+{by}")
        self.library_win.attributes("-topmost", True)
        self.library_win.configure(bg=config.COLOR_BG)
        
        # Header with "new chunk" button
        header_f = tk.Frame(self.library_win, bg="#222")
        header_f.pack(fill="x")
        tk.Label(header_f, text="CHUNK LIBRARY", bg="#222", fg="yellow", font=("Arial", 8, "bold")).pack(side="left", padx=5)
        new_btn = tk.Button(header_f, text="➕ New", command=self._create_new_chunk, bg="#10b981", fg="white", bd=0, padx=5, font=("Arial", 8, "bold"))
        new_btn.pack(side="right", padx=5, pady=2)

        self.chunk_palette = TilesetPalette(self.library_win, ts_path, self.tile_size, self._on_chunk_nav_selected, locked=True)
        self.chunk_palette.set_chunks(self.chunks)
        self.chunk_palette.set_mode("CHUNK")

        # 2. Tile Palette (5 Tiles @ 34px + 21px gutter + 5px buffer = 196px)
        self.palette_win = tk.Toplevel(self.win)
        self.palette_win.title("Tile Palette")
        self.palette_win.geometry(f"196x700+{bx + 1310}+{by}")
        self.palette_win.attributes("-topmost", True)
        self.palette_win.configure(bg=config.COLOR_BG)
        tk.Label(self.palette_win, text="TILE PALETTE", bg="#222", fg="cyan", font=("Arial", 8, "bold")).pack(fill="x")
        self.tile_palette = TilesetPalette(self.palette_win, ts_path, self.tile_size, self._on_tile_selected, locked=True)
        self.tile_palette.set_mode("TILE")



    def _safe_get_tile(self, cid, r, c):
        chunk = self.chunks.get(cid)
        if not chunk: return 0
        data = chunk.get("data")
        if not data: return 0
        # Layer Detection Logic
        grid = data.get("ground", data.get("layer0", data)) if isinstance(data, dict) else data
        if not grid: return 0
        if isinstance(grid, list):
            row = grid[r] if r < len(grid) else []
            if isinstance(row, list): return row[c] if c < len(row) else 0
            return 0
        elif isinstance(grid, dict):
            row = grid.get(str(r), grid.get(r))
            if not row: return 0
            if isinstance(row, list): return row[c] if c < len(row) else 0
            if isinstance(row, dict): return row.get(str(c), row.get(c, 0))
        return 0

    def _safe_set_tile(self, cid, r, c, tid):
        chunk = self.chunks.get(cid)
        if not chunk: return
        if "data" not in chunk: chunk["data"] = {}
        data = chunk["data"]
        
        if isinstance(data, dict):
            if "ground" not in data and not any(k in data for k in ["0", 0]):
                data["ground"] = [[0]*16 for _ in range(16)]
            target = data.get("ground", data)
        else: target = data

        if isinstance(target, list):
            while len(target) <= r: target.append([0]*16)
            row = target[r]
            if isinstance(row, list):
                while len(row) <= c: row.append(0)
                row[c] = tid
        elif isinstance(target, dict):
            rk = str(r) if str(r) in target else r
            if rk not in target: target[rk] = {}
            row = target[rk]
            if isinstance(row, list):
                while len(row) <= c: row.append(0)
                row[c] = tid
            else:
                ck = str(c) if str(c) in row else c
                row[ck] = tid

    def _select_chunk(self, cid):
        print(f"[TRACE-SELECT-1] Accessing Chunk ID: {cid}")
        if not cid or cid not in self.chunks:
            print(f"[TRACE-SELECT-ERR] Chunk Key Miss: {cid}")
            return
        
        self.selected_chunk_id = cid
        self.name_edited = False
        self.tile_cache.clear()
        print("[TRACE-SELECT-2] Invalidating Surface...")
        self.win.update() 
        self.render()
        self.chunk_palette.select_id(cid, "CHUNK")
        display_name = self.chunks.get(cid, {}).get("name", cid)
        if display_name.startswith("C_") and display_name[2:].isdigit():
            display_name = display_name[2:]
        self.status_label.config(text=f"Editing {display_name}")
        self.win.title(f"Chunk Editor - {display_name}")
        
        if hasattr(self, 'name_entry'):
            self.name_entry.delete(0, tk.END)
            self.name_entry.insert(0, display_name)

    def _on_name_entry_keypress(self, event):
        self.name_edited = True

    def _on_name_entry_focus_out(self, event=None):
        if not self.selected_chunk_id or not getattr(self, 'name_edited', False): return
        self.name_edited = False
        new_name = self.name_entry.get().strip()
        if not new_name: return
        
        current_name = self.chunks.get(self.selected_chunk_id, {}).get("name", self.selected_chunk_id)
        
        idx_str = self.selected_chunk_id
        if idx_str.startswith("C_") and idx_str[2:].isdigit():
            idx_num = idx_str[2:]
        else:
            idx_num = idx_str
            
        if new_name == idx_num:
            name_to_store = f"C_{idx_num}"
        else:
            name_to_store = new_name
            
        existing = False
        for other_cid, other_data in self.chunks.items():
            if other_cid == self.selected_chunk_id:
                continue
            o_name = other_data.get("name", other_cid)
            o_idx_num = other_cid[2:] if (other_cid.startswith("C_") and other_cid[2:].isdigit()) else other_cid
            o_normalized = f"C_{o_idx_num}" if o_name == o_idx_num else o_name
            
            if name_to_store == o_normalized:
                existing = True
                break
                
        if existing:
            messagebox.showerror("Error", "A chunk with this name already exists.", parent=self.win)
            def refocus():
                if self.win.winfo_exists() and hasattr(self, 'name_entry'):
                    self.name_entry.focus_set()
                    self.name_entry.select_range(0, tk.END)
            self.win.after(50, refocus)
            return
            
        if current_name != name_to_store:
            self.chunks[self.selected_chunk_id]["name"] = name_to_store
            self.chunk_palette.set_chunks(self.chunks)
            self.chunk_palette.select_id(self.selected_chunk_id, "CHUNK")
            display_name = name_to_store
            if display_name.startswith("C_") and display_name[2:].isdigit():
                display_name = display_name[2:]
            self.status_label.config(text=f"Editing {display_name}")
            self.win.title(f"Chunk Editor - {display_name}")

    def _on_name_entry_key_release(self, event=None):
        if not self.selected_chunk_id: return
        typed_name = self.name_entry.get().strip()
        if not typed_name: return
        
        idx_str = self.selected_chunk_id
        if idx_str.startswith("C_") and idx_str[2:].isdigit():
            idx_num = idx_str[2:]
        else:
            idx_num = idx_str
            
        if typed_name == idx_num:
            name_to_store = f"C_{idx_num}"
        else:
            name_to_store = typed_name
            
        existing = False
        for other_cid, other_data in self.chunks.items():
            if other_cid == self.selected_chunk_id:
                continue
            o_name = other_data.get("name", other_cid)
            o_idx_num = other_cid[2:] if (other_cid.startswith("C_") and other_cid[2:].isdigit()) else other_cid
            o_normalized = f"C_{o_idx_num}" if o_name == o_idx_num else o_name
            
            if name_to_store == o_normalized:
                existing = True
                break
                
        if existing:
            self.status_label.config(text="RENAME (try some capitals)", fg="red")
        else:
            display_name = self.chunks.get(self.selected_chunk_id, {}).get("name", self.selected_chunk_id)
            if display_name.startswith("C_") and display_name[2:].isdigit():
                display_name = display_name[2:]
            self.status_label.config(text=f"Editing {display_name}", fg="#888")

    def _next_chunk(self):
        print("[TRACE-NAV] Moving to NEXT chunk.")
        if not self.selected_chunk_id: return
        keys = sorted(self.chunks.keys(), key=lambda x: (0, int(x[2:])) if x.startswith("C_") and x[2:].isdigit() else (0, int(x)) if x.isdigit() else (1, x))
        try:
            cur_idx = keys.index(self.selected_chunk_id)
            next_idx = (cur_idx + 1) % len(keys)
            self._select_chunk(keys[next_idx])
        except: return

    def _prev_chunk(self):
        print("[TRACE-NAV] Moving to PREVIOUS chunk.")
        if not self.selected_chunk_id: return
        keys = sorted(self.chunks.keys(), key=lambda x: (0, int(x[2:])) if x.startswith("C_") and x[2:].isdigit() else (0, int(x)) if x.isdigit() else (1, x))
        try:
            cur_idx = keys.index(self.selected_chunk_id)
            prev_idx = (cur_idx - 1) % len(keys)
            self._select_chunk(keys[prev_idx])
        except: return

    def render(self):
        print("[TRACE-RENDER-1] render() call.")
        if not self.selected_chunk_id: return

        self.canvas.delete("all")
        sz = int(self.tile_size * self.zoom)
        c_size = config.CHUNK_SIZE
        
        canvas_w = max(1100, self.viewport.winfo_width())
        canvas_h = max(800, self.viewport.winfo_height())
        
        # Shifted left 4 tiles (160px) + User Pan
        offset_x = ((canvas_w - (c_size * sz)) // 2) - 160 + self.pan_x
        offset_y = ((canvas_h - (c_size * sz)) // 2) + self.pan_y
        self.offset = (offset_x, offset_y)
        
        self.canvas.config(width=canvas_w, height=canvas_h)
        
        rendered_tiles = 0
        for r in range(c_size):
            for c in range(c_size):
                tid = self._safe_get_tile(self.selected_chunk_id, r, c)
                x, y = offset_x + (c * sz), offset_y + (r * sz)
                
                img = self._get_tile_img(tid)
                if img:
                    self.canvas.create_image(x, y, image=img, anchor="nw", tags="tile")
                    rendered_tiles += 1
                else:
                    self.canvas.create_rectangle(x, y, x+sz, y+sz, fill="#1a1a1a", outline="#222", tags="tile")
                    
        print(f"[TRACE-RENDER-2] Rendered {rendered_tiles} active tiles.")
        self._render_overlays()
        self._update_library_preview()

    def _update_library_preview(self):
        if hasattr(self, 'chunk_palette') and self.selected_chunk_id:
            keys_to_del = [k for k in self.chunk_palette.chunk_thumbnails.keys() if k.startswith(f"{self.selected_chunk_id}_")]
            for k in keys_to_del:
                del self.chunk_palette.chunk_thumbnails[k]
            self.chunk_palette.update_visible()

    def _render_overlays(self):
        sz = int(self.tile_size * self.zoom)
        c_size = config.CHUNK_SIZE
        ox, oy = self.offset
        
        # Guide Grid
        for i in range(c_size + 1):
            lx, ly = ox + (i * sz), oy + (i * sz)
            self.canvas.create_line(lx, oy, lx, oy + (c_size * sz), fill="#222", width=1, tags="grid")
            self.canvas.create_line(ox, ly, ox + (c_size * sz), ly, fill="#222", width=1, tags="grid")

        # Selection Tool
        if self.selection_start and self.selection_end:
            r1, c1 = self.selection_start
            r2, c2 = self.selection_end
            min_r, max_r = min(r1, r2), max(r1, r2)
            min_c, max_c = min(c1, c2), max(c1, c2)
            x1, y1 = ox + (min_c * sz), oy + (min_r * sz)
            x2, y2 = ox + ((max_c + 1) * sz), oy + ((max_r + 1) * sz)
            self.canvas.create_rectangle(x1, y1, x2, y2, fill="#10b981", stipple="gray12", outline="")
            self.canvas.create_rectangle(x1, y1, x2, y2, outline="#10b981", width=2, dash=(4, 4))

        # Paste Preview
        if self.tool_mode == "PASTE" and self.clipboard and hasattr(self, 'mouse_grid'):
            r, c = self.mouse_grid
            if r is not None and c is not None:
                cb_rows, cb_cols = len(self.clipboard), len(self.clipboard[0])
                sr, sc = r - cb_rows//2, c - cb_cols//2
                for cr in range(cb_rows):
                    for cc in range(cb_cols):
                        tid = self.clipboard[cr][cc]
                        if tid == -1: continue
                        px, py = ox + ((sc + cc) * sz), oy + ((sr + cr) * sz)
                        img = self._get_tile_img(tid)
                        if img: self.canvas.create_image(px, py, image=img, anchor="nw", tags="preview")
                        self.canvas.create_rectangle(px, py, px+sz, py+sz, outline="white", width=1, dash=(2,2))

    def _on_mouse_down(self, event):
        r, c = self._event_to_grid(event)
        print(f"[TRACE-MOUSE] Down at: ({r}, {c})")
        if r is None: return
        if self.tool_mode == "SELECT":
            self.selection_start = (r, c)
            self.selection_end = (r, c)
            self.render()
        elif self.tool_mode == "PASTE":
            self._execute_paste(r, c)
        elif self.tool_mode == "FILL":
            self._execute_fill(r, c)
        else:
            self.push_to_undo()
            self.is_drawing = True
            self._paint_tile(r, c)

    def _on_mouse_move(self, event):
        r, c = self._event_to_grid(event)
        if r is None: return
        self.mouse_grid = (r, c)
        if self.tool_mode == "SELECT" and self.selection_start:
            self.selection_end = (r, c)
            self.render()
        elif self.is_drawing:
            self._paint_tile(r, c)

    def _on_mouse_up(self, event):
        print("[TRACE-MOUSE] Up.")
        if self.tool_mode == "SELECT" and self.selection_start:
            self._finalize_selection()
        self.is_drawing = False

    def _on_mouse_hover(self, event):
        r, c = self._event_to_grid(event)
        if r is not None:
            self.mouse_grid = (r, c)
            if self.tool_mode == "PASTE": self.render()

    def _event_to_grid(self, event):
        cx, cy = event.x, event.y
        ox, oy = self.offset
        sz = int(self.tile_size * self.zoom)
        c, r = (cx - ox) // sz, (cy - oy) // sz
        if 0 <= r < 16 and 0 <= c < 16: return int(r), int(c)
        return None, None

    def _paint_tile(self, r, c):
        if not self.selected_chunk_id: return
        if self._safe_get_tile(self.selected_chunk_id, r, c) != self.selected_tile_id:
            self._safe_set_tile(self.selected_chunk_id, r, c, self.selected_tile_id)
            self.render()

    def handle_rotate(self):
        # 1. Clipboard Rotation (Paste Mode)
        if self.tool_mode == "PASTE" and self.clipboard:
            print("[TRACE-ROTATE] Rotating Clipboard...")
            self.clipboard = self._rotate_rectangular_matrix(self.clipboard)
            self.render()
            return

        # 2. Whole Chunk Rotation
        if not self.selected_chunk_id: return
        print(f"[TRACE-ROTATE] Rotating Chunk {self.selected_chunk_id}")
        self.push_to_undo()
        
        cid = self.selected_chunk_id
        chunk = self.chunks[cid]
        data = chunk.get("data", {})
        
        # Rotate all standard layers
        if isinstance(data, dict):
            for key in ["ground", "objects", "layer0"]:
                if key in data:
                    data[key] = self._rotate_matrix(data[key])
            
            # If it's a flat row-keyed dict
            if not any(k in data for k in ["ground", "objects", "layer0"]) and any(str(k).isdigit() for k in data.keys()):
                chunk["data"] = self._rotate_matrix(data)
        elif isinstance(data, list):
            chunk["data"] = self._rotate_matrix(data)
            
        self.tile_cache.clear()
        self.render()

    def _rotate_matrix(self, matrix):
        """ Rotates a square 16x16 matrix 90 degrees CCW. """
        N = config.CHUNK_SIZE
        # Convert to 2D list if it's a dict
        grid = [[self._get_matrix_val(matrix, r, c) for c in range(N)] for r in range(N)]
        return self._rotate_rectangular_matrix(grid)

    def _rotate_rectangular_matrix(self, matrix):
        """ 
        Rotates any rectangular matrix 90 degrees Counter-Clockwise.
        Formula: new_row = (old_cols - 1) - old_col, new_col = old_row
        """
        if not matrix or not matrix[0]: return []
        rows = len(matrix)
        cols = len(matrix[0])
        
        new_grid = [[0]*rows for _ in range(cols)]
        for r in range(rows):
            for c in range(cols):
                new_grid[(cols-1)-c][r] = matrix[r][c]
        return new_grid

    def _get_matrix_val(self, matrix, r, c):
        if isinstance(matrix, list):
            if r < len(matrix):
                row = matrix[r]
                if isinstance(row, list):
                    return row[c] if c < len(row) else 0
            return 0
        elif isinstance(matrix, dict):
            rk = str(r) if str(r) in matrix else r
            row = matrix.get(rk, {})
            if isinstance(row, list):
                return row[c] if c < len(row) else 0
            ck = str(c) if str(c) in row else c
            return row.get(ck, 0)
        return 0

    def set_tool(self, mode):
        print(f"[TRACE-TOOL] Active: {mode}")
        self.tool_mode = mode
        self.selection_start = None
        self.selection_end = None
        for btn in [self.btn_pencil, self.btn_select, self.btn_paste, self.btn_fill]: btn.config(bg="#222")
        if mode == "PENCIL": self.btn_pencil.config(bg="#10b981")
        if mode == "SELECT": self.btn_select.config(bg="#10b981")
        if mode == "PASTE": self.btn_paste.config(bg="#10b981")
        if mode == "FILL": self.btn_fill.config(bg="#10b981")
        self.render()

    def _finalize_selection(self):
        if not self.selection_start or not self.selection_end: return
        r1, c1 = self.selection_start
        r2, c2 = self.selection_end
        min_r, max_r = min(r1, r2), max(r1, r2)
        min_c, max_c = min(c1, c2), max(c1, c2)
        self.clipboard = []
        for r in range(min_r, max_r + 1):
            row = [self._safe_get_tile(self.selected_chunk_id, r, c) for c in range(min_c, max_c + 1)]
            self.clipboard.append(row)
        self.btn_paste.config(state="normal")
        print(f"[TRACE-SELECT-OK] Copied {len(self.clipboard)}x{len(self.clipboard[0])} grid.")

    def _execute_paste(self, r, c):
        if not self.clipboard: return
        self.push_to_undo()
        rows, cols = len(self.clipboard), len(self.clipboard[0])
        sr, sc = r - rows//2, c - cols//2
        for cr in range(rows):
            for cc in range(cols):
                tr, tc = sr + cr, sc + cc
                if 0 <= tr < 16 and 0 <= tc < 16:
                    tid = self.clipboard[cr][cc]
                    if tid != -1: self._safe_set_tile(self.selected_chunk_id, tr, tc, tid)
        self.render()

    def _execute_fill(self, r, c):
        if not self.selected_chunk_id: return
        target_tid = self._safe_get_tile(self.selected_chunk_id, r, c)
        replacement_tid = self.selected_tile_id
        
        if target_tid == replacement_tid: return
        
        print(f"[TRACE-FILL] Replacing Tile {target_tid} with {replacement_tid}")
        self.push_to_undo()
        c_size = config.CHUNK_SIZE
        for tr in range(c_size):
            for tc in range(c_size):
                if self._safe_get_tile(self.selected_chunk_id, tr, tc) == target_tid:
                    self._safe_set_tile(self.selected_chunk_id, tr, tc, replacement_tid)
        
        self.render()

    def push_to_undo(self):
        if not self.selected_chunk_id: return
        data = self.chunks[self.selected_chunk_id].get("data")
        self.undo_stack.append(copy.deepcopy(data))
        if len(self.undo_stack) > 50: self.undo_stack.pop(0)
        self.redo_stack = []

    def handle_undo(self):
        if not self.undo_stack or not self.selected_chunk_id: return
        self.redo_stack.append(copy.deepcopy(self.chunks[self.selected_chunk_id].get("data")))
        self.chunks[self.selected_chunk_id]["data"] = self.undo_stack.pop()
        self.render()

    def handle_redo(self):
        if not self.redo_stack or not self.selected_chunk_id: return
        self.undo_stack.append(copy.deepcopy(self.chunks[self.selected_chunk_id].get("data")))
        self.chunks[self.selected_chunk_id]["data"] = self.redo_stack.pop()
        self.render()

    def _clear_chunk(self):
        if not self.selected_chunk_id: return
        if messagebox.askyesno("Clear", "Reset this chunk to Tile 0?", parent=self.win):
            self.push_to_undo()
            cid = self.selected_chunk_id
            self.chunks[cid]["data"]["ground"] = [[0]*16 for _ in range(16)]
            self.render()

    def _save_all_async(self):
        if self.is_saving: return
        print("[TRACE-SAVE-1] Initializing Async Save Thread...")
        self.is_saving = True
        self.btn_save.config(text="💾 Saving...", state="disabled", bg="#552")
        self.status_label.config(text="Writing Chunks to disk (Background)...")
        
        def save_work():
            try:
                self.save_manager.save_chunks(self.chunks)
                print("[TRACE-SAVE-2] Disk write finalized.")
                if self.win.winfo_exists():
                    self.win.after(0, self._save_complete)
            except Exception as e:
                print(f"[TRACE-SAVE-ERR] Disk Error: {e}")
                if self.win.winfo_exists():
                    def _error_ui():
                        if self.win.winfo_exists():
                            self.btn_save.config(text="💾 Save ERROR", bg="#a11", state="normal")
                    self.win.after(0, _error_ui)

        threading.Thread(target=save_work, daemon=True).start()

    def _save_complete(self):
        if not self.win.winfo_exists(): return
        self.is_saving = False
        self.btn_save.config(text="💾 Saved!", bg="#141", state="normal")
        self.status_label.config(text="All Chunks Persisted to Chunks.json", fg="#8f8")
        
        def _reset_btn():
            if self.win.winfo_exists():
                self.btn_save.config(text="💾 Save All")
        self.win.after(3000, _reset_btn)

    def _on_zoom(self, event):
        if event.state & 0x0004: # Control Key
            if event.delta > 0: self.zoom = min(12.0, self.zoom + 0.5)
            else: self.zoom = max(1.0, self.zoom - 0.5)
            self.render()
        else:
            # Vertical Scroll
            scroll_amount = (event.delta / 120) * 60
            self.pan_y += scroll_amount
            self.render()

    def _get_tile_img(self, tid):
        cache_key = (tid, self.zoom)
        if cache_key in self.tile_cache: return self.tile_cache[cache_key]
        if not self.orig_tileset or tid < 0: return None
        sz = int(self.tile_size * self.zoom)
        tw = self.orig_tileset.width // self.tile_size
        tx, ty = (tid % tw) * self.tile_size, (tid // tw) * self.tile_size
        try:
            crop = self.orig_tileset.crop((tx, ty, tx+self.tile_size, ty+self.tile_size))
            resized = crop.resize((sz, sz), Image_NEAREST)
            tk_img = ImageTk.PhotoImage(resized)
            self.tile_cache[cache_key] = tk_img
            return tk_img
        except: return None

    def _create_new_chunk(self):
        cids = set(int(cid[2:]) for cid in self.chunks.keys() if cid.startswith("C_") and cid[2:].isdigit())
        new_idx = 0
        while new_idx in cids:
            new_idx += 1
        new_cid = f"C_{new_idx}"
        
        self.chunks[new_cid] = {
            "name": new_cid,
            "data": {
                "ground": [[0]*16 for _ in range(16)],
                "objects": [[0]*16 for _ in range(16)]
            }
        }
        
        self.chunk_palette.set_chunks(self.chunks)
        self._select_chunk(new_cid)

    def _on_chunk_nav_selected(self, cid, mode):
        if mode == "NEW_CHUNK":
            self._create_new_chunk()
            return
        if mode == "RENAME_CHUNK":
            if cid == self.selected_chunk_id:
                display_name = self.chunks.get(cid, {}).get("name", cid)
                if display_name.startswith("C_") and display_name[2:].isdigit():
                    display_name = display_name[2:]
                self.status_label.config(text=f"Editing {display_name}")
                self.win.title(f"Chunk Editor - {display_name}")
            return
        if mode == "REMOVE_CHUNK":
            if cid == self.selected_chunk_id:
                keys = sorted(self.chunks.keys(), key=lambda x: (0, int(x[2:])) if x.startswith("C_") and x[2:].isdigit() else (0, int(x)) if x.isdigit() else (1, x))
                if keys:
                    self._select_chunk(keys[0])
                else:
                    self.selected_chunk_id = None
                    self.canvas.delete("all")
                    self.status_label.config(text="No Chunks Available")
                    self.win.title("Chunk Editor - No Chunk")
            else:
                self.chunk_palette.set_chunks(self.chunks)
            return
        if cid == self.selected_chunk_id: return
        self._select_chunk(cid)

    def _on_tile_selected(self, tid, mode):
        self.selected_tile_id = tid
        self.status_label.config(text=f"Paint Brush: Tile {tid}")

    def _setup_shortcuts(self):
        self.win.bind("<Button-1>", lambda e: self.win.focus() if hasattr(self, 'name_entry') and e.widget != self.name_entry else None, add="+")
        
        def guard(func, *args, **kwargs):
            if hasattr(self, 'name_entry') and self.win.focus_get() == self.name_entry:
                return
            func(*args, **kwargs)

        self.win.bind("<Control-z>", lambda e: guard(self.handle_undo))
        self.win.bind("<Control-y>", lambda e: guard(self.handle_redo))
        self.win.bind("<Escape>", lambda e: guard(self.set_tool, "PENCIL"))
        self.win.bind("<Control-s>", lambda e: guard(self._save_all_async))
        
        # Tool Shortcuts
        self.win.bind("p", lambda e: guard(self.set_tool, "PENCIL"))
        self.win.bind("s", lambda e: guard(self.set_tool, "SELECT"))
        self.win.bind("v", lambda e: guard(self.set_tool, "PASTE"))
        self.win.bind("f", lambda e: guard(self.set_tool, "FILL"))
        
        # Navigation Shortcuts
        self.win.bind("<Left>", lambda e: guard(self._prev_chunk))
        self.win.bind("<Right>", lambda e: guard(self._next_chunk))
        
        # Undo/Redo Shortcuts
        self.win.bind("u", lambda e: guard(self.handle_undo))
        self.win.bind("r", lambda e: guard(self.handle_redo))
        self.win.bind("t", lambda e: guard(self.handle_rotate))
