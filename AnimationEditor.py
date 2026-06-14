import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import config
from EditorComponents import center_window

_IMAGE_CACHE = {}

class AnimationEditor:
    """
    A professional, Win95-style Animation Editor for 2D assets.
    Provides frame-by-frame management and real-time playback simulation.
    """
    def __init__(self, parent, save_manager=None, initial_tile=None, initial_name=None, initial_tileset="World", on_save_callback=None):
        self.parent = parent
        self.save_manager = save_manager
        self.on_save_callback = on_save_callback
        
        self.win = tk.Toplevel(parent)
        self.win.title(f"Animation Editor - {initial_name if initial_name else '[Untitled]'}")
        
        # Standardized Centering
        center_window(self.win, parent, 520, 450)
        
        self.win.configure(bg=config.COLOR_BG)
        self.win.resizable(False, False)
        
        # --- STATE ---
        self.frame_data = [ [0, 0, initial_tileset] for _ in range(8) ]
        self.speed = tk.IntVar(value=100)
        self.frame_count = tk.IntVar(value=1)
        self.anim_name = tk.StringVar(value=initial_name if initial_name else "NewAnim_01")
        self.loop_mode = tk.StringVar(value="Cycle")
        self.random_speed = tk.BooleanVar(value=False)
        
        self.current_frame_idx = 0
        self.preview_job = None
        self.photo_cache = {} # For UI icons
        self.preview_photos = [] # Store references to prevent GC
        
        self.setup_ui()
        self.sync_slots_to_count() # Initial lock state
        self.start_preview() # Start playback loop
        
        # Load existing if available
        self.load_existing_anim_data()
        
        # Focus management
        self.win.transient(parent)
        self.win.grab_set()
        self.win.protocol("WM_DELETE_WINDOW", self.on_close)
        self.win.bind("<Destroy>", lambda e: self.cleanup() if e.widget == self.win else None)

    def on_close(self):
        self.win.destroy()

    def cleanup(self):
        """ Hard stop for the playback heartbeat. """
        if hasattr(self, 'preview_job') and self.preview_job:
            try: self.win.after_cancel(self.preview_job)
            except: pass
            self.preview_job = None

    def setup_ui(self):
        # --- TOP SECTION: NAME ---
        top_f = tk.Frame(self.win, bg=config.COLOR_BG, padx=10, pady=10)
        top_f.pack(fill="x")
        
        tk.Label(top_f, text="Animation:", bg=config.COLOR_BG, font=config.FONT_TITLE).pack(side="left")
        self.name_entry = tk.Entry(top_f, textvariable=self.anim_name, width=30, relief="sunken", bd=2)
        self.name_entry.pack(side="left", padx=10)
        
        # --- PREVIEW STRIP (8 SLOTS) ---
        strip_f = tk.LabelFrame(self.win, text="Frame Sequence", bg=config.COLOR_BG, padx=5, pady=5, relief="groove")
        strip_f.pack(fill="x", padx=10, pady=5)
        
        self.slots = []
        for i in range(8):
            slot_container = tk.Frame(strip_f, bg=config.COLOR_BG, bd=2, relief="sunken", width=50, height=50)
            slot_container.pack_propagate(False)
            slot_container.pack(side="left", padx=4, pady=2)
            
            canvas = tk.Canvas(slot_container, bg="#444", highlightthickness=0)
            canvas.pack(fill="both", expand=True)
            # Dotted line placeholder for empty slot
            canvas.create_rectangle(5, 5, 45, 45, outline="#666", dash=(2, 2))
            tk.Label(canvas, text=str(i+1), fg="#888", bg="#444", font=("Arial", 7)).place(relx=1.0, rely=1.0, anchor="se")
            
            canvas.bind("<Double-Button-1>", lambda e, idx=i: self.select_tile_for_frame(idx))
            self.slots.append(canvas)

        # Trace count for reactive UI
        self.frame_count.trace_add("write", lambda *a: self.sync_slots_to_count())

        # --- CENTER SECTION: SAMPLE WINDOW & CONTROLS ---
        mid_f = tk.Frame(self.win, bg=config.COLOR_BG, padx=10, pady=5)
        mid_f.pack(fill="both", expand=True)
        
        # Left: Sample Display
        sample_group = tk.LabelFrame(mid_f, text="Sample", bg=config.COLOR_BG, padx=10, pady=10, relief="groove")
        sample_group.pack(side="left", fill="both", expand=True)
        
        self.sample_canvas = tk.Canvas(sample_group, bg="#222", relief="sunken", bd=2, width=128, height=128)
        self.sample_canvas.pack(pady=10)
        
        # Right: Controls
        ctrl_group = tk.LabelFrame(mid_f, text="Animation Controls", bg=config.COLOR_BG, padx=10, pady=10, relief="groove")
        ctrl_group.pack(side="right", fill="both", expand=True, padx=(10, 0))
        
        # Mode Dropdown
        tk.Label(ctrl_group, text="Mode:", bg=config.COLOR_BG, font=("Arial", 8)).grid(row=0, column=0, sticky="w", pady=2)
        modes = ["None", "Cycle", "Ping-Pong", "Random Frame", "Static-Masked", "Static-Scroll"]
        self.mode_menu = ttk.Combobox(ctrl_group, textvariable=self.loop_mode, values=modes, state="readonly", width=15)
        self.mode_menu.grid(row=0, column=1, pady=2, sticky="w")
        
        # Speed
        tk.Label(ctrl_group, text="Speed (ms):", bg=config.COLOR_BG, font=("Arial", 8)).grid(row=1, column=0, sticky="w", pady=2)
        self.speed_entry = tk.Entry(ctrl_group, textvariable=self.speed, width=8, relief="sunken", bd=2)
        self.speed_entry.grid(row=1, column=1, pady=2, sticky="w")
        
        # Total Frames
        tk.Label(ctrl_group, text="Frames:", bg=config.COLOR_BG, font=("Arial", 8)).grid(row=2, column=0, sticky="w", pady=2)
        self.frame_count_entry = tk.Entry(ctrl_group, textvariable=self.frame_count, width=8, relief="sunken", bd=2)
        self.frame_count_entry.grid(row=2, column=1, pady=2, sticky="w")
        
        # Frame Slider (Added for better UX)
        self.frame_slider = tk.Scale(ctrl_group, from_=1, to=8, orient="horizontal", 
                                     variable=self.frame_count, showvalue=0, 
                                     bg=config.COLOR_BG, highlightthickness=0,
                                     troughcolor="#444", activebackground="lime")
        self.frame_slider.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 5))
        
        # Random Speed Toggle
        self.rand_cb = tk.Checkbutton(ctrl_group, text="Random Speed", variable=self.random_speed, bg=config.COLOR_BG, 
                                      activebackground=config.COLOR_BG, font=("Arial", 8))
        self.rand_cb.grid(row=4, column=0, columnspan=2, sticky="w", pady=10)

        # --- BOTTOM ACTION BAR ---
        bot_f = tk.Frame(self.win, bg=config.COLOR_BG, pady=10)
        bot_f.pack(fill="x")
        
        tk.Button(bot_f, text="Save Animation", command=self.save_anim, width=15, bg=config.COLOR_BG, relief="raised", bd=2).pack(side="right", padx=10)
        tk.Button(bot_f, text="Cancel", command=self.win.destroy, width=10, bg=config.COLOR_BG, relief="raised", bd=2).pack(side="right")

    def sync_slots_to_count(self):
        """ Greys out slots that are beyond the current frame count. """
        try: count = int(self.frame_count.get())
        except: count = 1
        count = max(1, min(8, count))
        
        for i, canvas in enumerate(self.slots):
            if i < count:
                canvas.config(bg="#444")
            else:
                canvas.config(bg="#222")
                canvas.delete("img") # Clear image for locked frames

    def select_tile_for_frame(self, idx):
        """ Opens TilesetSelector for a specific keyframe. """
        try: count = int(self.frame_count.get())
        except: count = 1
        if idx >= count: return # Locked
        
        from TilesetSelector import TilesetSelector
        # Default to World for now
        ts_path = os.path.join(self.save_manager.project_path, "TILESET", f"{self.frame_data[idx][2]}_TILESET.png")
        
        def callback(tx, ty):
            self.frame_data[idx] = [tx, ty, self.frame_data[idx][2]]
            self.refresh_slot_icon(idx)
            
        tile_sz = getattr(self.save_manager, 'tile_size', 16)
        TilesetSelector(self.win, ts_path, tile_size=tile_sz, callback=callback)

    def refresh_slot_icon(self, idx):
        """ UI Refresh for a single frame slot. """
        tx, ty, ts = self.frame_data[idx]
        canvas = self.slots[idx]
        canvas.delete("img")
        
        # Load small preview
        ts_path = os.path.join(self.save_manager.project_path, "TILESET", f"{ts}_TILESET.png")
        if os.path.exists(ts_path):
            from PIL import Image, ImageTk
            mtime = os.path.getmtime(ts_path)
            if ts_path in _IMAGE_CACHE and _IMAGE_CACHE[ts_path]["mtime"] == mtime:
                full = _IMAGE_CACHE[ts_path]["img"]
            else:
                full = Image.open(ts_path).convert("RGBA")
                _IMAGE_CACHE[ts_path] = {"mtime": mtime, "img": full}
            
            tile_sz = getattr(self.save_manager, 'tile_size', 16)
            crop = full.crop((tx*tile_sz, ty*tile_sz, (tx+1)*tile_sz, (ty+1)*tile_sz)).resize((40,40), Image.NEAREST)
            photo = ImageTk.PhotoImage(crop)
            self.photo_cache[f"slot_{idx}"] = photo # Prevent GC
            canvas.create_image(25, 25, image=photo, tags="img")

    def start_preview(self):
        """ Initiation of the playback loop. """
        if self.preview_job: 
            self.win.after_cancel(self.preview_job)
        
        try: ms = int(self.speed.get())
        except: ms = 100
        ms = max(50, ms)
        
        self.animate()
        self.preview_job = self.win.after(ms, self.start_preview)

    def animate(self):
        """ Draws the current frame in the sample window. """
        try: count = int(self.frame_count.get())
        except: count = 1
        
        if count == 0: return
        self.current_frame_idx = (self.current_frame_idx + 1) % count
        
        # Draw frame to sample canvas
        tx, ty, ts = self.frame_data[self.current_frame_idx]
        ts_path = os.path.join(self.save_manager.project_path, "TILESET", f"{ts}_TILESET.png")
        
        if os.path.exists(ts_path):
            from PIL import Image, ImageTk
            mtime = os.path.getmtime(ts_path)
            if ts_path in _IMAGE_CACHE and _IMAGE_CACHE[ts_path]["mtime"] == mtime:
                full = _IMAGE_CACHE[ts_path]["img"]
            else:
                full = Image.open(ts_path).convert("RGBA")
                _IMAGE_CACHE[ts_path] = {"mtime": mtime, "img": full}
                
            tile_sz = getattr(self.save_manager, 'tile_size', 16)
            crop = full.crop((tx*tile_sz, ty*tile_sz, (tx+1)*tile_sz, (ty+1)*tile_sz)).resize((128,128), Image.NEAREST)
            photo = ImageTk.PhotoImage(crop)
            self.preview_photos = [photo] # Keep reference
            self.sample_canvas.delete("all")
            self.sample_canvas.create_image(64, 64, image=photo)


    def load_existing_anim_data(self):
        """ Hydrates the editor if called from an existing type. """
        if not self.save_manager or not self.save_manager.project_path: return
        
        hairy_dir = os.path.join(self.save_manager.project_path, "HAIRY")
        import ScriptParser
        filename = ScriptParser._hairy_filename(self.anim_name.get())
        filepath = os.path.join(hairy_dir, filename)
        
        if os.path.exists(filepath):
            headers = ScriptParser.parse_hairy_headers(filepath)
            if headers and "animation" in headers:
                anim = headers["animation"]
                if anim:
                    self.frame_count.set(anim.get("frames", 1))
                    self.speed.set(anim.get("speed", 100))
                    self.loop_mode.set(anim.get("mode", "Cycle"))
                    self.random_speed.set(anim.get("random_speed", False))
                    
                    # If we had saved frame data (tile mappings), load them here
                    frames = anim.get("frame_sequence", [])
                    for i, f in enumerate(frames[:8]):
                        if len(f) >= 3: self.frame_data[i] = f
                        self.refresh_slot_icon(i)

    def save_anim(self):
        """ Modified Save to include the Frame Sequence. """
        if not self.save_manager or not self.save_manager.project_path:
            messagebox.showerror("Error", "No active project!")
            return

        raw_name = self.anim_name.get().strip()
        import re
        name = re.sub(r'[^a-zA-Z0-9_ ]', '', raw_name)
        
        try:
            speed = int(self.speed.get())
            count = int(self.frame_count.get())
        except: speed, count = 100, 1

        # EXPORT THE MAPPED FRAMES
        anim_data = {
            "mode": self.loop_mode.get(),
            "speed": speed,
            "frames": count,
            "random_speed": self.random_speed.get(),
            "frame_sequence": self.frame_data[:count] # [ [x,y,ts], [x,y,ts]... ]
        }

        # Invoke callback if provided to update parent's state
        if self.on_save_callback:
            self.on_save_callback(anim_data)

        # Write directly to the Hairy file
        import ScriptParser
        ScriptParser.sync_metadata_to_hairy(self.save_manager.project_path, name, {"animation": anim_data})

        self.save_manager.mark_dirty()
        self.win.destroy()

if __name__ == "__main__":
    # Test Standalone
    root = tk.Tk()
    root.withdraw()
    app = AnimationEditor(root)
    root.mainloop()
