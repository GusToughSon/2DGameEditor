import tkinter as tk
from PIL import Image, ImageTk
import os
import config
from EditorComponents import center_window

# Global cache for preloaded/resized tileset images to avoid slow loading on subsequent opens
_IMAGE_CACHE = {}

class TilesetSelector:
    """
    A standalone tileset selection window.
    Used for picking tiles for Types, Chunks, and Map objects.
    """
    def __init__(self, parent, tileset_path, tile_size=16, callback=None):
        self.parent = parent
        self.tileset_path = tileset_path
        self.tile_size = tile_size
        self.callback = callback
        
        self.win = tk.Toplevel(parent)
        self.win.withdraw() # Hide window immediately to prevent blank white popup while loading
        self.win.title(f"Select Tile - {os.path.basename(tileset_path)}")
        self.win.configure(bg=config.COLOR_BG)
        self.win.transient(parent)
        self.win.grab_set() # Force interaction
        
        self.selected_tile = None
        self.photo_chunks = []
        
        self._setup_ui()
        self._load_tileset()

    def _setup_ui(self):
        # 1. Title bar
        header = tk.Frame(self.win, bg="#333", pady=5)
        header.pack(fill="x")
        tk.Label(header, text="Click a tile to focus, double-click to select", fg="white", bg="#333", font=("Arial", 9, "bold")).pack()

        # 2. Scrollable Canvas
        self.canvas_container = tk.Frame(self.win, bg=config.COLOR_BG)
        self.canvas_container.pack(fill="both", expand=True)
        
        self.scroll_y = tk.Scrollbar(self.canvas_container, orient="vertical", command=self._on_scroll_y)
        self.scroll_y.pack(side="right", fill="y")
        
        self.canvas = tk.Canvas(self.canvas_container, bg=config.COLOR_BG, highlightthickness=0, yscrollcommand=self.scroll_y.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Double-Button-1>", self._on_double_click)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<ButtonPress-2>", self._pan_start)
        self.canvas.bind("<B2-Motion>", self._pan_move)
        
        # 3. Action Buttons (Bottom)
        btn_f = tk.Frame(self.win, bg=config.COLOR_BG, pady=10)
        btn_f.pack(fill="x")
        
        self.ok_btn = tk.Button(btn_f, text="OK", width=12, bg=config.COLOR_BG, relief="raised", bd=2, 
                                 command=self._on_ok, state="disabled")
        self.ok_btn.pack(side="right", padx=10)
        
        cancel_btn = tk.Button(btn_f, text="Cancel", width=12, bg=config.COLOR_BG, relief="raised", bd=2,
                               command=self.win.destroy)
        cancel_btn.pack(side="right")

    def _on_scroll_y(self, *args): self.canvas.yview(*args)
    
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _load_tileset(self):
        if not os.path.exists(self.tileset_path):
            tk.Label(self.canvas, text="Tileset not found!", fg="red").pack()
            self.win.deiconify()
            return

        try:
            mtime = os.path.getmtime(self.tileset_path)
            ts = self.tile_size
            display_scale = 2
            sz = ts * display_scale
            
            # Check global cache first
            if self.tileset_path in _IMAGE_CACHE and _IMAGE_CACHE[self.tileset_path]["mtime"] == mtime and _IMAGE_CACHE[self.tileset_path]["tile_size"] == ts:
                entry = _IMAGE_CACHE[self.tileset_path]
                self.full_img = entry["full_img"]
                self.tk_img = entry["tk_img"]
                self.display_sz = entry["display_sz"]
                self.cols_in_source = entry["cols_in_source"]
            else:
                self.full_img = Image.open(self.tileset_path).convert("RGBA")
                tw, th = self.full_img.size
                cols = tw // ts
                scaled_w = tw * display_scale
                scaled_h = th * display_scale
                
                resized = self.full_img.resize((scaled_w, scaled_h), Image.NEAREST)
                self.tk_img = ImageTk.PhotoImage(resized)
                
                self.display_sz = sz
                self.cols_in_source = cols
                
                # Cache it
                _IMAGE_CACHE[self.tileset_path] = {
                    "mtime": mtime,
                    "tile_size": ts,
                    "full_img": self.full_img,
                    "tk_img": self.tk_img,
                    "display_sz": self.display_sz,
                    "cols_in_source": self.cols_in_source
                }
            
            tw, th = self.full_img.size
            cols = tw // ts
            
            calc_w = cols * sz + 40
            screen_w = self.win.winfo_screenwidth()
            w_width = min(max(calc_w, 400), int(screen_w * 0.9))
            
            center_window(self.win, self.parent, w_width, 550)
            
            self._render_grid()
            
            # Pre-render completely and then reveal the window to prevent flashing/white screens
            self.win.update_idletasks()
            self.win.deiconify()
        except Exception as e:
            print(f"[ERROR] TilesetSelector failed to load: {e}")
            self.win.deiconify()

    def _render_grid(self):
        self.canvas.delete("all")
        self.photo_chunks.clear()
        
        tw, th = self.full_img.size
        ts = self.tile_size
        cols, rows = tw // ts, th // ts
        
        display_scale = 2
        sz = ts * display_scale
        scaled_w = tw * display_scale
        scaled_h = th * display_scale
        
        self.photo_chunks.append(self.tk_img) # keep ref
        
        self.canvas.create_image(10, 10, image=self.tk_img, anchor="nw")
        
        # Draw boundaries grid
        for c in range(cols + 1):
            x = c * sz + 10
            self.canvas.create_line(x, 10, x, scaled_h + 10, fill="#444", width=1)
        for r in range(rows + 1):
            y = r * sz + 10
            self.canvas.create_line(10, y, scaled_w + 10, y, fill="#444", width=1)
            
        full_h = scaled_h + 40
        self.canvas.config(scrollregion=(0, 0, scaled_w + 20, full_h))


    def _on_click(self, event):
        cx, cy = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        
        grid_c = int((cx - 10) // self.display_sz)
        grid_r = int((cy - 10) // self.display_sz)
        
        if grid_c < 0 or grid_c >= self.cols_in_source: return
        if grid_r < 0 or grid_r >= (self.full_img.height // self.tile_size): return
        
        self.selected_c = grid_c
        self.selected_r = grid_r
        
        self.canvas.delete("selector")
        gx = grid_c * self.display_sz + 10
        gy = grid_r * self.display_sz + 10
        self.canvas.create_rectangle(gx-1, gy-1, gx+self.display_sz+1, gy+self.display_sz+1, 
                                     outline="yellow", width=2, tags="selector")
        
        self.ok_btn.config(state="normal")
        print(f"[DEBUG] TilesetSelector focus: ({self.selected_c}, {self.selected_r})")

    def _on_ok(self):
        if hasattr(self, 'selected_c'):
            if self.callback:
                self.callback(self.selected_c, self.selected_r)
            self.win.destroy()

    def _on_double_click(self, event):
        self._on_click(event)
        self._on_ok()

