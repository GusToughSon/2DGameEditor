import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import os
import config
import math
import threading
from PIL import Image, ImageTk
import ScriptParser
Image_NEAREST = getattr(getattr(Image, "Resampling", Image), "NEAREST")

class GameStatusBar:
    """
    A compartmentalized Status Bar component.
    Handles its own lights, labels, and state updates.
    """
    def __init__(self, parent):
        self.frame = tk.Frame(parent, relief="sunken", bd=1, bg=config.COLOR_BG)
        self.frame.pack(side="bottom", fill="x")

        # The little colored circle dot (Green/Yellow/Red)
        self.icon_canvas = tk.Canvas(self.frame, width=12, height=12, bg=config.COLOR_BG, highlightthickness=0)
        self.icon_canvas.pack(side="left", padx=(5, 2))
        self.icon_dot = self.icon_canvas.create_oval(1, 1, 11, 11, fill="lime", outline="black")

        self.label = tk.Label(self.frame, text="Ready", bg=config.COLOR_BG, font=config.FONT_UI)
        self.label.pack(side="left", padx=2)

        # Keyboard Lock Indicators (NUM, CAPS)
        self.caps_label = tk.Label(self.frame, text="CAPS", bg=config.COLOR_BG, fg="gray", font=("Arial", 7, "bold"), width=6)
        self.caps_label.pack(side="right", padx=5)
        self.num_label = tk.Label(self.frame, text="NUM", bg=config.COLOR_BG, fg="gray", font=("Arial", 7, "bold"), width=6)
        self.num_label.pack(side="right", padx=2)

    def set_status(self, text, color="lime"):
        self.label.config(text=text)
        self.icon_canvas.itemconfig(self.icon_dot, fill=color)

    def update_locks(self, caps, num):
        self.caps_label.config(fg="white" if caps else "gray")
        self.num_label.config(fg="white" if num else "gray")

def show_about_dialog(parent):
    """ Centered About Dialog with Personalized Information. """
    win = tk.Toplevel(parent)
    win.title("About")
    
    # Standardized Centering
    center_window(win, parent, 320, 220)
    
    win.configure(bg=config.COLOR_BG)
    win.resizable(False, False)
    win.transient(parent)
    win.grab_set()
    
    # Content
    content = tk.Frame(win, bg=config.COLOR_BG, padx=25, pady=20)
    content.pack(fill="both", expand=True)
    
    tk.Label(content, text=config.APP_TITLE, font=("Arial", 11, "bold"), bg=config.COLOR_BG).pack(pady=(0, 2))
    tk.Label(content, text=f"Version: {config.VERSION}", font=("Arial", 9), bg=config.COLOR_BG).pack(pady=(0, 10))
    
    tk.Label(content, text="A professional 2D Game Editor suite.", font=("Arial", 8), bg=config.COLOR_BG).pack()
    tk.Label(content, text="Created with Irritation, Frustration, and Perplexity.", font=("Arial", 8, "italic"), bg=config.COLOR_BG).pack(pady=(5, 10))
    
    tk.Label(content, text="© 2026 Macro is Fun LLC.", font=("Arial", 8, "bold"), bg=config.COLOR_BG).pack()
    
    # Action
    tk.Button(win, text="OK", width=12, command=win.destroy, bg=config.COLOR_BG, relief="raised", bd=2).pack(pady=15)

def center_window(win, parent, width, height):
    """ Centers 'win' (Toplevel) relative to its 'parent' window. """
    win.withdraw()
    win.update_idletasks()
    
    # 1. Get Parent Geometry
    parent.update_idletasks()
    pw = parent.winfo_width()
    ph = parent.winfo_height()
    px = parent.winfo_x()
    py = parent.winfo_y()
    
    if pw < 100 or ph < 100:
        pw = win.winfo_screenwidth()
        ph = win.winfo_screenheight()
        px, py = 0, 0

    x = px + (pw // 2) - (width // 2)
    y = py + (ph // 2) - (height // 2)
    
    win.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")
    win.deiconify()

import random

class LoginNotification:
    """
    Internal Snarky Notification (Frame-based).
    Strictly contained within the main editor boundaries.
    """
    def __init__(self, parent, msg_path):
        self.parent = parent # This is the main root window
        self.msg_path = msg_path
        self.messages = self._load_messages()
        self._after_id = None
        self._hide_after_id = None
        
        # --- TIMER STATE ---
        self.base_min = 45000
        self.base_max = 90000
        self.current_delay = random.randint(self.base_min, self.base_max)
        
        # --- UI FRAME (Internal to parent) ---
        self.bg_color = "#1A1A1A"
        self.accent_color = "#00FF00"
        self.text_color = "#FFFFFF"
        
        # Create directly as a child of root to allow clipping
        self.frame = tk.Frame(parent, bg=self.bg_color, relief="raised", bd=1,
                              highlightbackground=self.accent_color, highlightthickness=1)
        
        # Header with Close Button
        header = tk.Frame(self.frame, bg=self.bg_color)
        header.pack(fill="x", side="top", padx=2, pady=2)
        
        tk.Label(header, text="SYSTEM MESSAGE", fg=self.accent_color, bg=self.bg_color,
                 font=("Arial", 7, "bold")).pack(side="left")
        
        close_btn = tk.Label(header, text="X", fg="#AA0000", bg=self.bg_color, 
                             font=("Arial", 8, "bold"), cursor="hand2")
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda e: self.on_manual_close())
        
        # Content Area
        self.label = tk.Label(self.frame, text="", fg=self.text_color, bg=self.bg_color, 
                              font=("Arial", 9), padx=10, pady=5, wraplength=200, justify="left")
        self.label.pack()
        
        # Initial State: Hidden
        self.frame.place(relx=1.0, rely=1.0, x=500, y=500, anchor="se") 
        
        self.show_next_message()
        
    def _load_messages(self):
        if os.path.exists(self.msg_path):
            try:
                with open(self.msg_path, "r", encoding="utf-8") as f:
                    return [line.strip() for line in f if line.strip()]
            except: pass
        return ["Authentication confirmed."]

    def hide(self, manual=False):
        self.frame.place_forget()
        if self._hide_after_id:
            try: self.parent.after_cancel(self._hide_after_id)
            except: pass
            self._hide_after_id = None
            
        if not manual:
            # User "left it" - grow timer by 25% (Cap at 5 minutes)
            self.current_delay = int(self.current_delay * 1.25)
            self.current_delay = min(self.current_delay, 300000)

    def on_manual_close(self):
        """ Clicking X halves the next notification time. """
        self.hide(manual=True)
        self.current_delay //= 2
        self.current_delay = max(self.current_delay, 5000) # Cap at 5 seconds
        
        # Re-queue immediately with new faster delay
        if self._after_id:
            try: self.parent.after_cancel(self._after_id)
            except: pass
        self._after_id = self.parent.after(self.current_delay, self.show_next_message)

    def show_next_message(self):
        try:
            if not self.parent.winfo_exists(): return
            if self.parent.state() == "iconic": return 
        except: return

        if not self.messages: return
        msg = random.choice(self.messages)
        self.label.config(text=msg)
        
        # Layering: We go up, but status bar goes higher
        self.frame.lift()
        try:
            if hasattr(self.parent, 'status_bar_comp'):
                self.parent.status_bar_comp.frame.lift()
        except: pass
        
        target_x = -15
        target_y = -30 
        start_y = 50
        
        self.frame.place(relx=1.0, rely=1.0, x=target_x, y=start_y, anchor="se")
        self._animate_slide(target_x, start_y, target_y)
        
        # Auto-hide in 15 seconds
        self._hide_after_id = self.parent.after(15000, lambda: self.hide() if self.parent.winfo_exists() else None)
        
        # Queue next normally
        self._after_id = self.parent.after(self.current_delay, self.show_next_message)

    def _animate_slide(self, x, current_y, target_y):
        """ Smooth slide for internal frame inside parent container. """
        if not self.parent.winfo_exists(): return
        
        dist = current_y - target_y
        step = max(1, dist // 12) 
        
        new_y = current_y - step
        if new_y <= target_y:
            self.frame.place(relx=1.0, rely=1.0, x=x, y=target_y, anchor="se")
            return
            
        self.frame.place(relx=1.0, rely=1.0, x=x, y=new_y, anchor="se")
        self.parent.after(15, lambda: self._animate_slide(x, new_y, target_y))

from PIL import Image, ImageTk

class TilesetPalette:
    """
    A reusable UI palette that displays a tileset and allowing selection
    of both individual tiles and pre-built chunks via Tabs.
    """
    def __init__(self, parent, tileset_path, tile_size, callback, locked=False):
        self.parent = parent
        self.tile_size = tile_size
        self.callback = callback
        self.selected_id = 0
        self.mode = "TILE"  # "TILE" or "CHUNK"
        self.locked = locked # If True, hide tabs and stay on TILE
        self.chunks_data = {}
        self.chunk_thumbnails = {}
        self.persist_refs = []
        self.chunk_zoom = 48 # Display size for chunk thumbnails
        
        # Load Tileset for rendering
        self._tileset_cache = {}
        self._tileset_tk_cache = {}
        self.current_tileset_source = tileset_path
        
        self.orig_img = None
        if os.path.exists(tileset_path):
            try:
                self.orig_img = Image.open(tileset_path).convert("RGBA")
                self._tileset_cache[tileset_path] = self.orig_img
            except: pass
            
        # UI Container
        self.frame = tk.Frame(parent, bg=config.COLOR_BG, bd=2, relief="sunken")
        self.frame.pack(fill="both", expand=True)
        
        self.canvas_container = tk.Frame(self.frame, bg="#222")
        self.canvas_container.pack(fill="both", expand=True, side="bottom")

        # POI List (Hidden by default)
        self.poi_frame = tk.Frame(self.canvas_container, bg=config.COLOR_BG)
        self.poi_list = ttk.Treeview(self.poi_frame, columns=("name"), show="headings", selectmode="browse")
        self.poi_list.heading("name", text="Point of Interest Name")
        self.poi_list.pack(fill="both", expand=True)
        self.poi_list.bind("<Double-1>", self._on_poi_dbl_click)

        self.canvas = tk.Canvas(self.canvas_container, bg="#111", highlightthickness=0)
        self.v_scroll = tk.Scrollbar(self.canvas_container, orient="vertical", command=self._on_scroll)
        self.canvas.configure(yscrollcommand=self.v_scroll.set)
        
        self.v_scroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # TABS
        self.tab_f = tk.Frame(self.frame, bg=config.COLOR_BG)
        if not self.locked:
            self.tab_f.pack(fill="x", side="top")
        
        self.b_tile = tk.Button(self.tab_f, text="Tiles", command=lambda: self._tab_click("TILE"), 
                                relief="sunken", bg="#eee", font=("Arial", 8))
        self.b_tile.pack(side="left", expand=True, fill="x")
        
        self.b_obj = tk.Button(self.tab_f, text="Objects", command=lambda: self._tab_click("OBJECT"), 
                               relief="raised", bg="#eee", font=("Arial", 8))
        self.b_obj.pack(side="left", expand=True, fill="x")
        
        self.b_chunk = tk.Button(self.tab_f, text="Chunks", command=lambda: self._tab_click("CHUNK"), 
                                 relief="raised", bg="#eee", font=("Arial", 8))
        self.b_chunk.pack(side="left", expand=True, fill="x")

        # SEARCH BAR
        self.search_f = tk.Frame(self.frame, bg=config.COLOR_BG)
        self.search_f.pack(fill="x", side="top")
        tk.Label(self.search_f, text="🔍", bg=config.COLOR_BG).pack(side="left")
        
        self.ent = tk.Entry(self.search_f, font=("Arial", 8))
        self.ent.pack(side="left", fill="x", expand=True, padx=2)
        self.ent.bind("<Return>", lambda e: self.on_search(self.ent.get()))
        
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<MouseWheel>", self.on_wheel)
        self.frame.bind("<Configure>", self.update_visible)
        self.canvas.bind("<Configure>", self.update_visible)
        
        if self.orig_img:
            self.render_view()

    def on_wheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.update_visible()
        
        if self.orig_img:
            self.render_view()

    def _on_scroll(self, *args):
        self.canvas.yview(*args)
        self.update_visible()

    def select_id(self, asset_id, mode):
        """ Used by Eye Dropper to sync the palette. """
        self.mode = mode
        if mode in ["OBJECT", "ITEMS"]:
            if isinstance(asset_id, int):
                found_tid = None
                if hasattr(self, "types_data") and self.types_data:
                    ts_name = "OBJECTS" if mode == "OBJECT" else "ITEMS"
                    ts_path = os.path.join(self.project_path, "TILESET", f"{ts_name}_TILESET.png")
                    ts_width = 16
                    if os.path.exists(ts_path):
                        try:
                            with Image.open(ts_path) as img:
                                ts_width = img.width // self.tile_size
                        except: pass
                    
                    for tid, data in self.types_data.items():
                        anim = data.get("animation", {})
                        frame_seq = anim.get("frame_sequence", []) if isinstance(anim, dict) else []
                        if frame_seq and len(frame_seq) > 0:
                            tx, ty, ts_src = frame_seq[0]
                        else:
                            tx, ty = data.get("tile_coords", [0, 0])
                        
                        type_tile_id = ty * ts_width + tx
                        if type_tile_id == asset_id:
                            found_tid = tid
                            break
                if found_tid:
                    self.selected_id = found_tid
                else:
                    self.selected_id = asset_id
            else:
                self.selected_id = asset_id
        else:
            self.selected_id = asset_id
        self.select_and_center(self.selected_id)

    def select_and_center(self, asset_id):
        """ Instantly scroll the library to focus on this asset ONLY if it's not fully visible. """
        raw_ids = self._get_full_ids()
        try:
            idx = raw_ids.index(asset_id)
        except: return

        # Mode-Aware Geometric calculation
        if self.mode in ["OBJECT", "ITEMS"]:
            sz = 32
            gap = 28 + 10 # gap_v + 10
            gap_h = 24
            cw = self.frame.winfo_width()
            if cw < 50: cw = 200
            cols = max(1, cw // (sz + gap_h))
        elif self.mode == "TILE":
            ds = 2 # Display Scale
            sz = self.tile_size * ds
            gap = 0
            if not self.orig_img: return
            cols = self.orig_img.width // self.tile_size
        else:
            sz = self.chunk_zoom
            gap = 4
            cw = self.frame.winfo_width()
            if cw < 50: cw = 200
            cols = max(1, cw // (sz + gap))

        row = idx // cols
        target_y = row * (sz + gap)
        
        # Current Viewport State
        view_h = self.canvas.winfo_height()
        if view_h < 50: view_h = 600 # Fallback
        
        v_start = self.canvas.canvasy(0)
        v_end = v_start + view_h
        
        # Only scroll if the asset is off-screen or partially clipped
        if target_y < v_start or (target_y + sz) > v_end:
            # Calculate REAL total height based on all possible rows
            rows_total = math.ceil(len(raw_ids) / cols)
            total_h = rows_total * (sz + gap) + 40
            
            if total_h > 0:
                # Center in viewport
                scroll_pos = (target_y - view_h/2 + sz/2) / total_h
                self.canvas.yview_moveto(max(0, scroll_pos))
        
        self.render_view()

    def on_search(self, term):
        """ Search centers the item rather than filtering the list. """
        if not term: return
        term = term.lower()
        
        full_ids = self._get_full_ids()
        
        # Mode-Aware Search logic
        if self.mode == "TILE":
            try:
                target_id = int(term)
                if 0 <= target_id < len(full_ids):
                    self.selected_id = target_id
                    if self.callback: self.callback(target_id, "TILE")
                    self.select_and_center(target_id)
                    return
            except: pass
            
        # Chunk Searching (Subtitle/ID matching)
        match = next((cid for cid in full_ids if term in str(cid).lower()), None)
        if match:
            self.selected_id = match
            if self.callback: self.callback(match, self.mode)
            self.select_and_center(match)

    def _get_full_ids(self):
        """ Returns the contextually relevant ID list for current mode. """
        if self.mode in ["OBJECT", "ITEMS"]:
            sorted_types = []
            if hasattr(self, "types_data") and self.types_data:
                for tid, data in self.types_data.items():
                    fam = data.get("family", "").upper()
                    ts = data.get("tileset", "")
                    
                    is_match = False
                    if self.mode == "OBJECT":
                        is_match = (ts == "Objects") or fam.startswith("FAM_OBJ")
                    elif self.mode == "ITEMS":
                        item_prefixes = ["FAM_ARMOR", "FAM_GAUNT", "FAM_HELM", "FAM_LEG", "FAM_PLATE", "FAM_SHIELD", "FAM_TRINKET", "FAM_WEAPON", "FAM_CONSUMABLE", "FAM_ITEM"]
                        is_match = (ts == "Items") or any(fam.startswith(p) for p in item_prefixes)
                    
                    if is_match:
                        sorted_types.append((tid, data))
            sorted_types.sort(key=lambda x: x[1].get("name", "").lower())
            return [t[0] for t in sorted_types]
        elif self.mode == "TILE":
            if not self.orig_img: return []
            tw = self.orig_img.width // self.tile_size
            th = self.orig_img.height // self.tile_size
            return list(range(tw * th))
            
        def natural_sort_key(cid):
            try:
                if str(cid).startswith("C_"): return int(cid[2:])
                if str(cid).isdigit(): return int(cid)
            except: pass
            return str(cid)
        return sorted(self.chunks_data.keys(), key=natural_sort_key)

    def set_chunks(self, chunks_data):
        """ Update the palette with current project chunks. """
        self.chunks_data = chunks_data
        self.chunk_thumbnails.clear()
        if self.mode == "CHUNK":
            self.render_view()

    def load_tileset(self, tileset_source):
        self.current_tileset_source = tileset_source

        if isinstance(tileset_source, Image.Image):
            self.orig_img = tileset_source
        elif tileset_source in self._tileset_cache:
            self.orig_img = self._tileset_cache[tileset_source]
        else:
            self.orig_img = None
            if os.path.exists(tileset_source):
                try:
                    self.orig_img = Image.open(tileset_source).convert("RGBA")
                    self._tileset_cache[tileset_source] = self.orig_img
                except: pass
        self.render_view()

    def set_mode(self, mode, render=True):
        self.mode = mode
        if mode == "POINT":
            self.b_tile.config(text="+ Add", relief="raised", command=lambda: self.callback(None, "POINT_ADD"))
            self.b_chunk.config(text="- Remove", relief="raised", command=lambda: self.callback(None, "POINT_DEL"))
            self.b_obj.pack_forget()
            self.poi_frame.pack(fill="both", expand=True)
            self.canvas.pack_forget()
            self.v_scroll.pack_forget()
        else:
            self.b_tile.pack_forget()
            self.b_obj.pack_forget()
            self.b_chunk.pack_forget()
            
            self.b_tile.config(text="Tiles", relief="sunken" if mode == "TILE" else "raised", command=lambda: self._tab_click("TILE"))
            self.b_obj.config(text="Items" if mode == "ITEMS" else "Objects", relief="sunken" if mode in ["OBJECT", "ITEMS"] else "raised", command=lambda: self._tab_click("OBJECT"))
            self.b_chunk.config(text="Chunks", relief="sunken" if mode == "CHUNK" else "raised", command=lambda: self._tab_click("CHUNK"))
            
            self.b_tile.pack(side="left", expand=True, fill="x")
            self.b_obj.pack(side="left", expand=True, fill="x")
            self.b_chunk.pack(side="left", expand=True, fill="x")
            self.poi_frame.pack_forget()
            
            # Restore Canvas UI
            self.v_scroll.pack(side="right", fill="y")
            self.canvas.pack(side="left", fill="both", expand=True)
            if render:
                self.render_view()

    def _tab_click(self, mode):
        if mode == "OBJECT":
            if self.mode == "OBJECT":
                mode = "ITEMS"
            elif self.mode == "ITEMS":
                mode = "OBJECT"
        self.set_mode(mode)
        if self.callback: self.callback(None, mode)

    def set_points(self, points):
        """ Update the POI list. """
        self.poi_list.delete(*self.poi_list.get_children())
        for i, p in enumerate(points):
            self.poi_list.insert("", "end", iid=str(i), values=(p["name"],))

    def _on_poi_dbl_click(self, event):
        sel = self.poi_list.selection()
        if sel and self.callback:
            self.callback(int(sel[0]), "POINT_GOTO")

    def on_wheel(self, event):
        if self.mode == "CHUNK":
            # Control + Wheel = Zoom
            if event.state & 0x4: # Control mask
                if event.delta > 0: self.chunk_zoom = min(128, self.chunk_zoom + 8)
                else: self.chunk_zoom = max(32, self.chunk_zoom - 8)
                self.render_view()
            else:
                self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
                self.update_visible()
        else:
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            self.update_visible()

    def _load_types(self):
        self.project_path = os.path.dirname(os.path.dirname(self.current_tileset_source))
        if hasattr(self, "save_manager") and hasattr(self.save_manager, "types_data") and self.save_manager.types_data:
            self.types_data = self.save_manager.types_data
        else:
            if not getattr(self, "_loading_types", False):
                self._loading_types = True
                def bg():
                    try:
                        types = ScriptParser.load_all_types_with_metadata(self.project_path)
                        if hasattr(self, "save_manager"):
                            self.save_manager.types_data = types
                        self.types_data = types
                        
                        # Resolve integer selected_id to type ID (tid)
                        if isinstance(self.selected_id, int) and self.mode in ["OBJECT", "ITEMS"]:
                            found_tid = None
                            ts_name = "OBJECTS" if self.mode == "OBJECT" else "ITEMS"
                            ts_path = os.path.join(self.project_path, "TILESET", f"{ts_name}_TILESET.png")
                            ts_width = 16
                            if os.path.exists(ts_path):
                                try:
                                    with Image.open(ts_path) as img:
                                        ts_width = img.width // self.tile_size
                                except: pass
                            
                            for tid, data in self.types_data.items():
                                anim = data.get("animation", {})
                                frame_seq = anim.get("frame_sequence", []) if isinstance(anim, dict) else []
                                if frame_seq and len(frame_seq) > 0:
                                    tx, ty, ts_src = frame_seq[0]
                                else:
                                    tx, ty = data.get("tile_coords", [0, 0])
                                
                                type_tile_id = ty * ts_width + tx
                                if type_tile_id == self.selected_id:
                                    found_tid = tid
                                    break
                            if found_tid:
                                self.selected_id = found_tid

                        if self.canvas.winfo_exists():
                            self.canvas.after(0, self.update_visible)
                    except Exception as e:
                        print(f"[ERROR] bg type load failed: {e}")
                    finally:
                        self._loading_types = False
                import threading
                threading.Thread(target=bg, daemon=True).start()

    def render_view(self):
        self.canvas.delete("all")
        self.persist_refs = []
        self.chunk_thumbnails.clear() # Optional: clear old thumbnails to save memory
        
        if self.mode == "TILE":
            self._render_tileset()
        elif self.mode in ["OBJECT", "ITEMS"]:
            self._load_types()
            self.update_visible()
        else:
            self.update_visible()

    def _render_tileset(self):
        if not self.orig_img: return
        
        source_key = self.current_tileset_source
        
        # Check PhotoImage cache
        if source_key and source_key in self._tileset_tk_cache:
            self.tk_img = self._tileset_tk_cache[source_key]
            scaled_w = self.tk_img.width()
            scaled_h = self.tk_img.height()
        else:
            # Display at 2x scale
            display_scale = 2
            sz = self.tile_size * display_scale
            scaled_w = self.orig_img.width * display_scale
            scaled_h = self.orig_img.height * display_scale
            
            self.tk_img = ImageTk.PhotoImage(self.orig_img.resize((scaled_w, scaled_h), Image_NEAREST))
            if source_key:
                self._tileset_tk_cache[source_key] = self.tk_img
        
        self.canvas.create_image(0, 0, image=self.tk_img, anchor="nw")
        self.persist_refs.append(self.tk_img)
        
        self.canvas.config(scrollregion=(0, 0, scaled_w, scaled_h))
        self.draw_selection()
    def update_visible(self, event=None):
        """ The Core Virtualization Engine: Optimized for 4000+ items. """
        if self.mode == "TILE":
            return # No virtualization/grid layout needed for continuous tileset image
        if hasattr(self, "_updating_visible") and self._updating_visible: return
        self._updating_visible = True
        
        try:
            if self.mode == "CHUNK":
                self._update_visible_chunks()
            elif self.mode in ["OBJECT", "ITEMS"]:
                self._update_visible_types()
        finally:
            self._updating_visible = False

    def _update_visible_types(self):
        self.canvas.delete("all")
        self.persist_refs = []
        
        # Sort types by name for stable display
        sorted_types = []
        if hasattr(self, "types_data") and self.types_data:
            for tid, data in self.types_data.items():
                fam = data.get("family", "").upper()
                ts = data.get("tileset", "")
                
                is_match = False
                if self.mode == "OBJECT":
                    is_match = (ts == "Objects") or fam.startswith("FAM_OBJ")
                elif self.mode == "ITEMS":
                    item_prefixes = ["FAM_ARMOR", "FAM_GAUNT", "FAM_HELM", "FAM_LEG", "FAM_PLATE", "FAM_SHIELD", "FAM_TRINKET", "FAM_WEAPON", "FAM_CONSUMABLE", "FAM_ITEM"]
                    is_match = (ts == "Items") or any(fam.startswith(p) for p in item_prefixes)
                
                if is_match:
                    sorted_types.append((tid, data))
        
        sorted_types.sort(key=lambda x: x[1].get("name", "").lower())
        
        sz = 32
        gap_h = 24
        gap_v = 28
        cw = self.frame.winfo_width()
        if cw < 50: cw = 200
        
        cols = max(1, cw // (sz + gap_h))
        rows_total = math.ceil(len(sorted_types) / cols)
        total_h = rows_total * (sz + gap_v) + 40
        
        new_sr = (0, 0, cw, total_h)
        if self.canvas.cget("scrollregion") != " ".join(map(str, new_sr)):
            self.canvas.config(scrollregion=new_sr)
            
        v_start = self.canvas.canvasy(0)
        v_end = v_start + max(600, self.canvas.winfo_height())
        
        row_start = max(0, int(v_start // (sz + gap_v)))
        row_end = min(rows_total, int(v_end // (sz + gap_v)) + 1)
        
        idx_start = row_start * cols
        idx_end = min(len(sorted_types), row_end * cols)
        
        # Keep track of coordinates of each displayed type so on_click can hit-test them!
        self._displayed_types = []  # List of tuples: (rect_x, rect_y, rect_w, rect_h, tid, tile_id)
        
        # Cache for tileset images to avoid reloading them per tile
        tiles_cache = {}
        
        def get_tile(ts_name, tx, ty):
            if ts_name not in tiles_cache:
                path = os.path.join(self.project_path, "TILESET", f"{ts_name}_TILESET.png")
                if os.path.exists(path):
                    tiles_cache[ts_name] = Image.open(path).convert("RGBA")
                else:
                    return None
            img = tiles_cache[ts_name]
            tsize = self.tile_size
            try:
                return img.crop((tx*tsize, ty*tsize, (tx+1)*tsize, (ty+1)*tsize)).resize((sz, sz), Image_NEAREST)
            except:
                return None

        # Pre-load tileset width to calculate 1D tile ID
        ts_name = "OBJECTS" if self.mode == "OBJECT" else "ITEMS"
        ts_path = os.path.join(self.project_path, "TILESET", f"{ts_name}_TILESET.png")
        ts_width = 16 # fallback
        if os.path.exists(ts_path):
            try:
                with Image.open(ts_path) as img:
                    ts_width = img.width // self.tile_size
            except:
                pass

        for i in range(idx_start, idx_end):
            tid, data = sorted_types[i]
            r, c = i // cols, i % cols
            x, y = c * (sz + gap_h) + 12, r * (sz + gap_v + 10) + 15
            
            # Draw preview
            anim = data.get("animation", {})
            frame_seq = anim.get("frame_sequence", []) if isinstance(anim, dict) else []
            if frame_seq and len(frame_seq) > 0:
                tx, ty, ts_src = frame_seq[0]
            else:
                ts_src = data.get("tileset", "World")
                tx, ty = data.get("tile_coords", [0, 0])
                
            tile_img = get_tile(ts_src, tx, ty)
            
            # Selection Highlight
            type_tile_id = ty * ts_width + tx
            is_sel = (self.selected_id == tid)
            
            box_w = sz + 16
            box_h = sz + 20
            rx, ry = x - 8, y - 4
            
            self._displayed_types.append((rx, ry, box_w, box_h, tid, type_tile_id))
            
            tag = f"type_item_{tid}"
            if is_sel:
                self.canvas.create_rectangle(rx, ry, rx + box_w, ry + box_h, fill="#000080", outline="yellow", width=3, tags=tag)
            else:
                self.canvas.create_rectangle(rx, ry, rx + box_w, ry + box_h, fill="#111", outline="#333", width=1, tags=tag)
                
            if tile_img:
                photo = ImageTk.PhotoImage(tile_img)
                self.canvas.create_image(x, y, image=photo, anchor="nw", tags=tag)
                self.persist_refs.append(photo)
            else:
                self.canvas.create_rectangle(x, y, x + sz, y + sz, fill="gray", tags=tag)
                
            name = data.get("name", "Unnamed")
            disp_name = (name[:8] + "..") if len(name) > 10 else name
            txt_color = "white" if is_sel else "#ccc"
            self.canvas.create_text(x + sz//2, y + sz + 2, text=disp_name, fill=txt_color, font=("Arial", 7), anchor="n", tags=tag)

    def _update_visible_chunks(self, event=None):
        full_ids = self._get_full_ids()
        total_items = len(full_ids) + 1
        
        # Absolute Purge: Remove everything before virtualization
        self.canvas.delete("all")
        self.persist_refs = []
        
        sz = self.chunk_zoom
        gap = 4
        cw = self.frame.winfo_width()
        if cw < 50: cw = 200 
        
        cols = max(1, cw // (sz + gap))
        rows_total = math.ceil(total_items / cols)
        total_h = rows_total * (sz + gap) + 40
        
        new_sr = (0, 0, cw, total_h)
        if self.canvas.cget("scrollregion") != " ".join(map(str, new_sr)):
            self.canvas.config(scrollregion=new_sr)
        
        v_start = self.canvas.canvasy(0)
        v_end = v_start + max(600, self.canvas.winfo_height())
        
        row_start = max(0, int(v_start // (sz + gap)))
        row_end = min(rows_total, int(v_end // (sz + gap)) + 1)
        
        idx_start = row_start * cols
        idx_end = min(total_items, row_end * cols)
        
        for i in range(idx_start, idx_end):
            r, c = i // cols, i % cols
            x, y = c * (sz + gap) + 10, r * (sz + gap) + 10
            if i < len(full_ids):
                cid = full_ids[i]
                p = self._get_chunk_photo(cid, sz)
                if p:
                    self.canvas.create_image(x, y, image=p, anchor="nw", tags=(cid, "chunk_thumb"))
                    self.persist_refs.append(p)
                    display_name = self.chunks_data.get(cid, {}).get("name", cid)
                    if display_name.startswith("C_") and display_name[2:].isdigit():
                        display_name = display_name[2:]
                    if len(display_name) > 10:
                        display_name = display_name[:8] + ".."
                    self.canvas.create_text(x+2, y+2, text=str(display_name), fill="yellow", font=("Arial", 7), anchor="nw", tags="chunk_label")
            else:
                self.canvas.create_rectangle(x, y, x + sz, y + sz, fill="#1e1e24", outline="#444", width=2, tags=("NEW_CHUNK_BUTTON", "chunk_thumb"))
                self.canvas.create_text(x + sz//2, y + sz//2, text="+", fill="#10b981", font=("Arial", 18, "bold"), anchor="center", tags="new_chunk_plus")
        self.draw_selection()

    def _update_visible_tiles(self, event=None):
        """ Virtual Tile Renderer: Purges surface and redraws visible viewport range. """
        if not self.orig_img: return
        
        # Absolute Purge
        self.canvas.delete("all")
        self.persist_refs = []
        
        ds = 2 # Display Scale
        sz = self.tile_size * ds
        gap = 2
        cw = self.frame.winfo_width()
        if cw < 50: cw = 200 
        
        # Calculate Grid
        cols = max(1, cw // (sz + gap))
        tw = self.orig_img.width // self.tile_size
        th = self.orig_img.height // self.tile_size
        total_tiles = tw * th
        
        rows_total = math.ceil(total_tiles / cols)
        total_h = rows_total * (sz + gap) + 20
        
        new_sr = (0, 0, cw, total_h)
        if self.canvas.cget("scrollregion") != " ".join(map(str, new_sr)):
            self.canvas.config(scrollregion=new_sr)
            
        v_start = self.canvas.canvasy(0)
        v_end = v_start + max(600, self.canvas.winfo_height())
        
        row_start = max(0, int(v_start // (sz + gap)))
        row_end = min(rows_total, int(v_end // (sz + gap)) + 1)
        
        idx_start = row_start * cols
        idx_end = min(total_tiles, row_end * cols)
        
        for i in range(idx_start, idx_end):
            tx = (i % tw) * self.tile_size
            ty = (i // tw) * self.tile_size
            
            r, c = i // cols, i % cols
            x, y = c * (sz + gap) + 5, r * (sz + gap) + 5
            
            tile_img = self.orig_img.crop((tx, ty, tx + self.tile_size, ty + self.tile_size))
            photo = ImageTk.PhotoImage(tile_img.resize((sz, sz), Image_NEAREST))
            self.canvas.create_image(x, y, image=photo, anchor="nw", tags=("tile_thumb", str(i)))
            self.persist_refs.append(photo)
            
        self.draw_selection()

    def _get_chunk_photo(self, cid, sz):
        key = f"{cid}_{sz}"
        if key in self.chunk_thumbnails: return self.chunk_thumbnails[key]
        
        if not self.orig_img: return None
        chunk = self.chunks_data.get(cid)
        if not chunk: return None
        
        try:
            # Reconstruct chunk from tileset
            full_res = config.CHUNK_SIZE * self.tile_size
            img = Image.new("RGBA", (full_res, full_res), (0,0,0,0))
            
            data = chunk.get("data", {})
            layers = []
            if isinstance(data, dict):
                # Try standard layer names
                if "ground" in data: layers.append(data["ground"])
                if "objects" in data: layers.append(data["objects"])
                # If no layers found, check if the dict itself is the grid (row-keyed)
                if not layers and any(str(k).isdigit() for k in data.keys()):
                    layers.append(data)
            elif isinstance(data, list):
                layers.append(data)
            
            tw = self.orig_img.width // self.tile_size
            ts = self.tile_size
            
            for layer in layers:
                if not layer: continue
                # Support both 2D (list of lists or dict of dicts/lists) and 1D arrays
                if isinstance(layer, dict):
                    # Dict of Rows
                    for r_idx in range(config.CHUNK_SIZE):
                        rk = str(r_idx) if str(r_idx) in layer else r_idx
                        row = layer.get(rk, [])
                        if isinstance(row, dict):
                            for c_idx in range(config.CHUNK_SIZE):
                                ck = str(c_idx) if str(c_idx) in row else c_idx
                                tid = row.get(ck, 0)
                                if tid > 0:
                                    tx, ty = (tid % tw) * ts, (tid // tw) * ts
                                    tile = self.orig_img.crop((tx, ty, tx+ts, ty+ts))
                                    img.paste(tile, (c_idx*ts, r_idx*ts), tile)
                        elif isinstance(row, list):
                            for c_idx, tid in enumerate(row):
                                if c_idx < config.CHUNK_SIZE and tid > 0:
                                    tx, ty = (tid % tw) * ts, (tid // tw) * ts
                                    tile = self.orig_img.crop((tx, ty, tx+ts, ty+ts))
                                    img.paste(tile, (c_idx*ts, r_idx*ts), tile)
                elif len(layer) > 0 and isinstance(layer[0], list):
                    # 2D List
                    for r in range(min(len(layer), config.CHUNK_SIZE)):
                        for itm in range(min(len(layer[r]), config.CHUNK_SIZE)):
                            tid = layer[r][itm]
                            if tid > 0:
                                tx, ty = (tid % tw) * ts, (tid // tw) * ts
                                tile = self.orig_img.crop((tx, ty, tx+ts, ty+ts))
                                img.paste(tile, (itm*ts, r*ts), tile)
                else:
                    # 1D List
                    for i, tid in enumerate(layer):
                        if tid > 0:
                            r, itm = i // config.CHUNK_SIZE, i % config.CHUNK_SIZE
                            if r < config.CHUNK_SIZE:
                                tx, ty = (tid % tw) * ts, (tid // tw) * ts
                                tile = self.orig_img.crop((tx, ty, tx+ts, ty+ts))
                                img.paste(tile, (itm*ts, r*ts), tile)
            
            # Scale to thumbnail
            photo = ImageTk.PhotoImage(img.resize((sz, sz), Image_NEAREST))
            self.chunk_thumbnails[key] = photo
            return photo
        except Exception as e:
            print(f"[ERROR] Palette: Thumbnail failed for {cid}: {e}")
            return None

    def draw_selection(self):
        self.canvas.delete("selection_rect")
        self.canvas.delete("sel")
        if self.selected_id is None: return

        if self.mode == "TILE":
            if not self.orig_img: return
            try:
                sel_id = int(self.selected_id)  # type: ignore
            except (ValueError, TypeError):
                return
            
            ds = 2
            sz = self.tile_size * ds
            cols = self.orig_img.width // self.tile_size
            
            grid_c = sel_id % cols
            grid_r = sel_id // cols
            x, y = grid_c * sz, grid_r * sz
            self.canvas.create_rectangle(x, y, x + sz, y + sz, outline="yellow", width=2, tags="selection_rect")
        elif self.mode in ["OBJECT", "ITEMS"]:
            # Selection highlight is handled during type list rendering.
            pass
        else:
            full_ids = self._get_full_ids()
            if self.selected_id not in full_ids: return
            try: idx = full_ids.index(self.selected_id)
            except: return
            
            sz = self.chunk_zoom
            gap = 4
            cw = self.frame.winfo_width()
            if cw < 50: cw = 200 
            cols = max(1, cw // (sz + gap))
            
            r, c = idx // cols, idx % cols
            x, y = c * (sz + gap) + 10, r * (sz + gap) + 10
            self.canvas.create_rectangle(x, y, x+sz, y+sz, outline="#10b981", width=3, tags="sel")

    def on_click(self, event):
        vx, vy = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        
        if self.mode == "TILE":
            if not self.orig_img: return
            ds = 2
            sz = self.tile_size * ds
            cols = self.orig_img.width // self.tile_size
            
            grid_c = int(vx // sz)
            grid_r = int(vy // sz)
            
            if grid_c < 0 or grid_c >= cols: return
            
            idx = grid_r * cols + grid_c
            tw = self.orig_img.width // self.tile_size
            th = self.orig_img.height // self.tile_size
            if 0 <= idx < (tw * th):
                self.selected_id = idx
                self.draw_selection()
                if self.callback: self.callback(self.selected_id, self.mode)
        elif self.mode in ["OBJECT", "ITEMS"]:
            for rx, ry, w, h, tid, type_tile_id in getattr(self, "_displayed_types", []):
                if rx <= vx <= rx + w and ry <= vy <= ry + h:
                    self.selected_id = tid
                    self.render_view()
                    if self.callback: self.callback(type_tile_id, self.mode)
                    break
        else:
            # Deterministic Grid Math for Chunks
            sz = self.chunk_zoom
            gap = 4
            cw = self.frame.winfo_width()
            if cw < 50: cw = 200 
            cols = max(1, cw // (sz + gap))
            
            # Reversed logic from update_visible: (x, y) -> index
            grid_c = int((vx - 10) // (sz + gap))
            grid_r = int((vy - 10) // (sz + gap))
            
            if grid_c < 0 or grid_c >= cols: return
            
            idx = grid_r * cols + grid_c
            full_ids = self._get_full_ids()
            
            if 0 <= idx < len(full_ids):
                cid = full_ids[idx]
                self.selected_id = cid
                self.draw_selection()
                if self.callback: self.callback(self.selected_id, "CHUNK")
            elif idx == len(full_ids):
                if self.callback: self.callback(None, "NEW_CHUNK")

    def on_right_click(self, event):
        if self.mode != "CHUNK": return
        vx, vy = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        sz = self.chunk_zoom
        gap = 4
        cw = self.frame.winfo_width()
        if cw < 50: cw = 200 
        cols = max(1, cw // (sz + gap))
        
        grid_c = int((vx - 10) // (sz + gap))
        grid_r = int((vy - 10) // (sz + gap))
        
        if grid_c < 0 or grid_c >= cols: return
        
        idx = grid_r * cols + grid_c
        full_ids = self._get_full_ids()
        
        if 0 <= idx < len(full_ids):
            cid = full_ids[idx]
            self.show_context_menu(event, cid)

    def show_context_menu(self, event, cid):
        menu = tk.Menu(self.parent, tearoff=0)
        menu.add_command(label="✏️ Rename Chunk", command=lambda: self.trigger_rename(cid))
        menu.add_command(label="🗑️ Remove Chunk", command=lambda: self.trigger_remove(cid))
        menu.post(event.x_root, event.y_root)

    def trigger_rename(self, cid):
        current_name = self.chunks_data.get(cid, {}).get("name", cid)
        while True:
            new_name = simpledialog.askstring("Rename Chunk", f"Enter new visual name for {cid}:", initialvalue=current_name, parent=self.parent)
            if new_name is None:
                return
            new_name = new_name.strip()
            if not new_name:
                return
            
            idx_num = cid[2:] if (cid.startswith("C_") and cid[2:].isdigit()) else cid
            normalized_proposed = f"C_{idx_num}" if new_name == idx_num else new_name
            
            existing = False
            for other_cid, other_data in self.chunks_data.items():
                if other_cid == cid:
                    continue
                o_name = other_data.get("name", other_cid)
                o_idx_num = other_cid[2:] if (other_cid.startswith("C_") and other_cid[2:].isdigit()) else other_cid
                o_normalized = f"C_{o_idx_num}" if o_name == o_idx_num else o_name
                
                if normalized_proposed == o_normalized:
                    existing = True
                    break
                    
            if existing:
                messagebox.showerror("Error", "A chunk with this name already exists.", parent=self.parent)
            else:
                if cid in self.chunks_data:
                    self.chunks_data[cid]["name"] = new_name
                self.render_view()
                if self.callback:
                    self.callback(cid, "RENAME_CHUNK")
                break

    def trigger_remove(self, cid):
        display_name = self.chunks_data.get(cid, {}).get("name", cid)
        if display_name.startswith("C_") and display_name[2:].isdigit():
            display_name = display_name[2:]
            
        ans1 = messagebox.askyesno("Confirm Delete (Level 1)", f"Are you sure you want to delete chunk '{display_name}'?", parent=self.parent)
        if not ans1: return
        ans2 = messagebox.askyesno("Confirm Delete (Level 2) - WARNING", f"WARNING: Deleting '{display_name}' is permanent and will clear it from the world grid. Proceed?", parent=self.parent)
        if not ans2: return
        
        if cid in self.chunks_data:
            del self.chunks_data[cid]
        self.render_view()
        if self.callback:
            self.callback(cid, "REMOVE_CHUNK")
