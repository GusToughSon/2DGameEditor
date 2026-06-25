# e:\2DGameEditor\SafeZoneEditor.py
import tkinter as tk
from tkinter import messagebox, ttk
import os
import json
from EditorComponents import center_window

class SafeZoneEditor:
    """
    Safe Zone Coordinates Configuration Dialog.
    Reads and writes to Maps/SafeZones.json.
    """
    def __init__(self, parent, save_manager=None):
        self.parent = parent
        self.save_manager = save_manager
        
        self.win = tk.Toplevel(parent)
        self.win.title("Safe Zone Configurator")
        
        center_window(self.win, parent, 500, 400)
        self.win.configure(bg="#dfdfdf")
        self.win.resizable(False, False)
        self.win.transient(parent)
        
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)
        self.ui_font = ("MS Sans Serif", 8)
        self.title_font = ("MS Sans Serif", 8, "bold")
        
        self.safe_zones_list = []
        self.load_safe_zones()
        self.setup_ui()
        
    def load_safe_zones(self):
        if not self.save_manager or not self.save_manager.project_path:
            return
        path = os.path.join(self.save_manager.project_path, "Maps", "SafeZones.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.safe_zones_list = data.get("safe_zones", [])
            except Exception as e:
                print(f"[ERROR] Failed to load SafeZones.json: {e}")

    def save_safe_zones(self):
        if not self.save_manager or not self.save_manager.project_path:
            return
        os.makedirs(os.path.join(self.save_manager.project_path, "Maps"), exist_ok=True)
        path = os.path.join(self.save_manager.project_path, "Maps", "SafeZones.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"safe_zones": self.safe_zones_list}, f, indent=4)
            if self.save_manager:
                self.save_manager.mark_dirty()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save safe zones: {e}")

    def setup_ui(self):
        # Left side: list of defined safe zones
        main_frame = tk.Frame(self.win, bg="#dfdfdf", padx=10, pady=10)
        main_frame.pack(fill="both", expand=True)

        left_frame = tk.Frame(main_frame, bg="#dfdfdf")
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        tk.Label(left_frame, text="Configured Safe Zone Chunks:", bg="#dfdfdf", font=self.title_font).pack(anchor="w", pady=(0, 5))
        
        list_container = tk.Frame(left_frame)
        list_container.pack(fill="both", expand=True)

        self.zone_listbox = tk.Listbox(list_container, font=self.ui_font, selectbackground="#0000A0")
        self.zone_listbox.pack(side="left", fill="both", expand=True)
        
        sb = tk.Scrollbar(list_container, command=self.zone_listbox.yview)
        sb.pack(side="right", fill="y")
        self.zone_listbox.config(yscrollcommand=sb.set)

        self.refresh_listbox()

        btn_f_left = tk.Frame(left_frame, bg="#dfdfdf", pady=5)
        btn_f_left.pack(fill="x")
        tk.Button(btn_f_left, text="Delete Selected", command=self.delete_zone, bg="#C0C0C0", font=self.ui_font).pack(fill="x")

        # Right side: Add zone fields
        right_frame = tk.LabelFrame(main_frame, text="Add Safe Zone", bg="#dfdfdf", font=self.title_font, padx=10, pady=10)
        right_frame.pack(side="right", fill="both", padx=(10, 0))

        self.stat_vars = {}
        fields = [
            ("min_x", "Min Chunk X:"),
            ("min_y", "Min Chunk Y:"),
            ("max_x", "Max Chunk X:"),
            ("max_y", "Max Chunk Y:")
        ]
        
        for k, label in fields:
            lf = tk.Frame(right_frame, bg="#dfdfdf")
            lf.pack(fill="x", pady=4)
            tk.Label(lf, text=label, bg="#dfdfdf", font=self.ui_font, width=12, anchor="w").pack(side="left")
            v = tk.StringVar(value="0")
            self.stat_vars[k] = v
            tk.Entry(lf, textvariable=v, width=8, relief="sunken", bd=2).pack(side="right", padx=5)

        tk.Button(right_frame, text="Add Range", command=self.apply, bg="#C0C0C0", width=12, relief="raised", bd=2, font=self.ui_font).pack(pady=15)
        tk.Button(right_frame, text="Close", command=self._on_close, bg="#C0C0C0", width=12, relief="raised", bd=2, font=self.ui_font).pack(pady=5)

    def refresh_listbox(self):
        self.zone_listbox.delete(0, "end")
        # Sort and list
        sorted_zones = sorted(self.safe_zones_list, key=lambda z: (z.get("y", 0), z.get("x", 0)))
        for z in sorted_zones:
            self.zone_listbox.insert("end", f"Chunk X: {z.get('x', 0)}, Y: {z.get('y', 0)} (Type: {z.get('type', 1)})")

    def apply(self):
        try:
            min_x = int(self.stat_vars["min_x"].get() or 0)
            min_y = int(self.stat_vars["min_y"].get() or 0)
            max_x = int(self.stat_vars["max_x"].get() or 0)
            max_y = int(self.stat_vars["max_y"].get() or 0)
            
            if min_x > max_x or min_y > max_y:
                messagebox.showerror("Error", "Min coordinates must be less than or equal to Max coordinates.")
                return

            added_count = 0
            # Add all safe chunks in the rectangle range
            for cy in range(min_y, max_y + 1):
                for cx in range(min_x, max_x + 1):
                    # Check if already safe
                    exists = any(z.get("x") == cx and z.get("y") == cy for z in self.safe_zones_list)
                    if not exists:
                        self.safe_zones_list.append({
                            "map": "WORLD",
                            "x": cx,
                            "y": cy,
                            "type": 1
                        })
                        added_count += 1
            
            if added_count > 0:
                self.save_safe_zones()
                self.refresh_listbox()
                messagebox.showinfo("Success", f"Added {added_count} safe zone chunks.")
            else:
                messagebox.showinfo("Info", "All selected chunks are already safe zones.")
        except Exception as e: 
            messagebox.showerror("Error", str(e))

    def delete_zone(self):
        sel = self.zone_listbox.curselection()
        if not sel:
            return
        
        # Parse selected line to find coordinates
        line = self.zone_listbox.get(sel[0])
        # Format: "Chunk X: 5, Y: 10 (Type: 1)"
        try:
            parts = line.split(",")
            cx = int(parts[0].split(":")[1].strip())
            cy = int(parts[1].split(":")[1].split("(")[0].strip())
            
            # Remove from list
            self.safe_zones_list = [z for z in self.safe_zones_list if not (z.get("x") == cx and z.get("y") == cy)]
            self.save_safe_zones()
            self.refresh_listbox()
        except Exception as e:
            messagebox.showerror("Error", f"Could not parse selected zone: {e}")

    def _on_close(self):
        if self.parent and self.parent.winfo_exists():
            self.parent.lift(); self.parent.focus_set()
        self.win.destroy()
