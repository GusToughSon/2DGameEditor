import tkinter as tk
from tkinter import messagebox, ttk
import os
import json
import ScriptParser
from EditorComponents import center_window

class NPCSpawnEditor:
    """
    NPC Spawn Points Configuration Dialog.
    Reads and writes to Maps/NPCSpawns.json.
    """
    def __init__(self, parent, save_manager=None):
        self.parent = parent
        self.save_manager = save_manager
        
        self.win = tk.Toplevel(parent)
        self.win.title("NPC Spawn Configurator")
        
        center_window(self.win, parent, 600, 450)
        self.win.configure(bg="#dfdfdf")
        self.win.resizable(False, False)
        self.win.transient(parent)
        
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)
        self.ui_font = ("MS Sans Serif", 8)
        self.title_font = ("MS Sans Serif", 8, "bold")
        
        self.npc_spawns_list = []
        self.types_data = self._load_types_from_hry()
        self.load_npc_spawns()
        
        self.setup_ui()
        self.refresh_npc_dropdown()
        
    def _load_types_from_hry(self):
        if not self.save_manager or not self.save_manager.project_path: return {}
        path = os.path.join(self.save_manager.hairy_dir, "Types.hry")
        return ScriptParser.parse_types_use_sync(path)

    def load_npc_spawns(self):
        if not self.save_manager or not self.save_manager.project_path:
            return
        path = os.path.join(self.save_manager.project_path, "Maps", "NPCSpawns.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.npc_spawns_list = data.get("npc_spawns", [])
            except Exception as e:
                print(f"[ERROR] Failed to load NPCSpawns.json: {e}")

    def save_npc_spawns(self):
        if not self.save_manager or not self.save_manager.project_path:
            return
        os.makedirs(os.path.join(self.save_manager.project_path, "Maps"), exist_ok=True)
        path = os.path.join(self.save_manager.project_path, "Maps", "NPCSpawns.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"npc_spawns": self.npc_spawns_list}, f, indent=4)
            if self.save_manager:
                self.save_manager.mark_dirty()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save NPC spawns: {e}")

    def setup_ui(self):
        main_frame = tk.Frame(self.win, bg="#dfdfdf", padx=10, pady=10)
        main_frame.pack(fill="both", expand=True)

        # Left Column: Listbox
        left_frame = tk.Frame(main_frame, bg="#dfdfdf")
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        tk.Label(left_frame, text="Configured NPC Spawns:", bg="#dfdfdf", font=self.title_font).pack(anchor="w", pady=(0, 5))
        
        list_container = tk.Frame(left_frame)
        list_container.pack(fill="both", expand=True)

        self.spawn_listbox = tk.Listbox(list_container, font=self.ui_font, selectbackground="#0000A0")
        self.spawn_listbox.pack(side="left", fill="both", expand=True)
        
        sb = tk.Scrollbar(list_container, command=self.spawn_listbox.yview)
        sb.pack(side="right", fill="y")
        self.spawn_listbox.config(yscrollcommand=sb.set)

        self.refresh_listbox()

        btn_f_left = tk.Frame(left_frame, bg="#dfdfdf", pady=5)
        btn_f_left.pack(fill="x")
        tk.Button(btn_f_left, text="Delete Spawn", command=self.delete_spawn, bg="#C0C0C0", font=self.ui_font).pack(fill="x")

        # Right Column: Editor Details
        right_frame = tk.LabelFrame(main_frame, text="Add Spawn Point", bg="#dfdfdf", font=self.title_font, padx=10, pady=10)
        right_frame.pack(side="right", fill="both", padx=(10, 0))

        # Dropdown
        rf_type = tk.Frame(right_frame, bg="#dfdfdf")
        rf_type.pack(fill="x", pady=2)
        tk.Label(rf_type, text="NPC Type:", bg="#dfdfdf", font=self.ui_font).pack(side="left")
        self.npc_select = ttk.Combobox(rf_type, state="readonly", width=20)
        self.npc_select.pack(side="right", padx=5)

        self.stat_vars = {}
        fields = [
            ("x", "World X:"),
            ("y", "World Y:"),
            ("shop_id", "Shop ID:"),
            ("conv_id", "Conv ID:"),
            ("max_dist_x", "Max Dist X:"),
            ("max_dist_y", "Max Dist Y:")
        ]
        
        for k, label in fields:
            lf = tk.Frame(right_frame, bg="#dfdfdf")
            lf.pack(fill="x", pady=2)
            tk.Label(lf, text=label, bg="#dfdfdf", font=self.ui_font, width=12, anchor="w").pack(side="left")
            v = tk.StringVar(value="0")
            self.stat_vars[k] = v
            tk.Entry(lf, textvariable=v, width=8, relief="sunken", bd=2).pack(side="right", padx=5)

        tk.Button(right_frame, text="Add Spawn", command=self.apply, bg="#C0C0C0", width=12, relief="raised", bd=2, font=self.ui_font).pack(pady=15)
        tk.Button(right_frame, text="Close", command=self._on_close, bg="#C0C0C0", width=12, relief="raised", bd=2, font=self.ui_font).pack(pady=5)

    def refresh_npc_dropdown(self):
        self.types_data = self._load_types_from_hry()
        if not self.types_data: return
        items = sorted([f"{tid}: {v.get('name', 'Unnamed')}" for tid, v in self.types_data.items() if v.get("family") == "FAM_NPC"], key=lambda x: x.split(":")[1].lower())
        self.npc_select.config(values=items)

    def refresh_listbox(self):
        self.spawn_listbox.delete(0, "end")
        
        # Build ID to name cache
        npc_names = {int(tid): v.get("name", "Unknown") for tid, v in self.types_data.items()}
        
        for idx, s in enumerate(self.npc_spawns_list):
            npc_id = s.get("npc_type", 0)
            name = npc_names.get(npc_id, f"NPC {npc_id}")
            self.spawn_listbox.insert("end", f"#{idx}: {name} at ({s.get('x')}, {s.get('y')})")

    def apply(self):
        sel = self.npc_select.get()
        if not sel:
            messagebox.showerror("Error", "Please select an NPC Type.")
            return
            
        try:
            npc_type = int(sel.split(":")[0])
            x = int(self.stat_vars["x"].get() or 0)
            y = int(self.stat_vars["y"].get() or 0)
            shop_id = int(self.stat_vars["shop_id"].get() or 0)
            conv_id = int(self.stat_vars["conv_id"].get() or 0)
            max_dist_x = int(self.stat_vars["max_dist_x"].get() or 0)
            max_dist_y = int(self.stat_vars["max_dist_y"].get() or 0)
            
            self.npc_spawns_list.append({
                "npc_type": npc_type,
                "x": x,
                "y": y,
                "shop_id": shop_id,
                "conv_id": conv_id,
                "max_dist_x": max_dist_x,
                "max_dist_y": max_dist_y
            })
            
            self.save_npc_spawns()
            self.refresh_listbox()
            messagebox.showinfo("Success", "NPC spawn point added.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_spawn(self):
        sel = self.spawn_listbox.curselection()
        if not sel:
            return
        
        # Parse index from Listbox line e.g. "#3: Town Guard at (5, 10)"
        line = self.spawn_listbox.get(sel[0])
        try:
            idx = int(line.split(":")[0][1:])
            if 0 <= idx < len(self.npc_spawns_list):
                self.npc_spawns_list.pop(idx)
                self.save_npc_spawns()
                self.refresh_listbox()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete: {e}")

    def _on_close(self):
        if self.parent and self.parent.winfo_exists():
            self.parent.lift(); self.parent.focus_set()
        self.win.destroy()
