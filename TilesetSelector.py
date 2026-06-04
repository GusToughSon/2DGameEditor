import tkinter as tk
from PIL import Image, ImageTk
import os
import config
from EditorComponents import center_window

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
        self.win.title(f"Select Tile - {os.path.basename(tileset_path)}")
        
        # Standardized Centering
        center_window(self.win, parent, 400, 550)
        
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
        
        # --- DYNAMIC RESIZING ---
        self.canvas.bind("<Configure>", lambda e: self._render_grid())

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
            return

        try:
            self.full_img = Image.open(self.tileset_path).convert("RGBA")
            self._render_grid()
        except Exception as e:
            print(f"[ERROR] TilesetSelector failed to load: {e}")

    def _render_grid(self):
        self.canvas.delete("all")
        self.photo_chunks.clear()
        
        tw, th = self.full_img.size
        ts = self.tile_size
        cols, rows = tw // ts, th // ts
        
        display_sz = 32 # Visual scaling for easier picking
        gap = 4
        
        # Calculate items per row based on ACTUAL window width
        canvas_w = self.canvas.winfo_width()
        if canvas_w < 100: canvas_w = 380 # Fallback for initial render
        
        items_per_row = max(1, (canvas_w - 20) // (display_sz + gap))
        total_rows = (cols * rows + items_per_row - 1) // items_per_row
        
        full_h = total_rows * (display_sz + gap) + 20
        self.canvas.config(scrollregion=(0, 0, canvas_w, full_h))

        for i in range(cols * rows):
            sc, sr = i % cols, i // cols
            grid_x = (i % items_per_row) * (display_sz + gap) + 10
            grid_y = (i // items_per_row) * (display_sz + gap) + 10
            
            chunk = self.full_img.crop((sc*ts, sr*ts, (sc+1)*ts, (sr+1)*ts)).resize((display_sz, display_sz), Image.NEAREST)
            tkc = ImageTk.PhotoImage(chunk)
            self.photo_chunks.append(tkc)
            
            self.canvas.create_image(grid_x, grid_y, image=tkc, anchor="nw", tags=f"tile_{sc}_{sr}")
            
        # Selection info
        self.items_per_row = items_per_row
        self.display_sz = display_sz
        self.gap = gap
        self.cols_in_source = cols

    def _on_click(self, event):
        cx, cy = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        
        grid_c = int((cx - 10) // (self.display_sz + self.gap))
        grid_r = int((cy - 10) // (self.display_sz + self.gap))
        
        if grid_c < 0 or grid_c >= self.items_per_row: return
        
        idx = grid_r * self.items_per_row + grid_c
        total_tiles = (self.full_img.width // self.tile_size) * (self.full_img.height // self.tile_size)
        if idx < 0 or idx >= total_tiles: return
        
        # Convert back to source tileset coords
        self.selected_c = idx % self.cols_in_source
        self.selected_r = idx // self.cols_in_source
        
        # Draw Selection Rectangle
        self.canvas.delete("selector")
        gx = grid_c * (self.display_sz + self.gap) + 10
        gy = grid_r * (self.display_sz + self.gap) + 10
        self.canvas.create_rectangle(gx-2, gy-2, gx+self.display_sz+2, gy+self.display_sz+2, 
                                     outline="yellow", width=2, tags="selector")
        
        # Enable OK button
        self.ok_btn.config(state="normal")
        print(f"[DEBUG] TilesetSelector focus: ({self.selected_c}, {self.selected_r})")

    def _on_ok(self):
        if hasattr(self, 'selected_c'):
            if self.callback:
                self.callback(self.selected_c, self.selected_r)
            self.win.destroy()

    def _on_double_click(self, event):
        self._on_click(event) # Ensure it's selected
        self._on_ok()
