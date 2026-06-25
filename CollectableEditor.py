import tkinter as tk
from tkinter import messagebox, ttk
import os
import ScriptParser
import config
from EditorComponents import center_window

class CollectableItemDataEditor:
    """
    Collectable/Misc Item Statistics Editor.
    """
    def __init__(self, parent, save_manager=None):
        self.parent = parent
        self.save_manager = save_manager
        
        # Mapping for Bidirectional Sync with .hry files
        self.COLLECTABLE_MAP = {
            "value": "COLLECTABLE_VALUE",
            "weight": "COLLECTABLE_WEIGHT",
            "dam_min": "COLLECTABLE_MIN_DMG",
            "dam_max": "COLLECTABLE_MAX_DMG",
            "cure_type": "COLLECTABLE_CURE_TYPE",
            "max_durability": "COLLECTABLE_MAX_DURABILITY",
            "use_type": "COLLECTABLE_USE_TYPE",
            "req_lvl": "COLLECTABLE_REQ_LEVEL",
            "req_str": "COLLECTABLE_REQ_STR",
            "req_int": "COLLECTABLE_REQ_INT",
            "req_dex": "COLLECTABLE_REQ_DEX",
            "req_con": "COLLECTABLE_REQ_CON"
        }
        
        self.win = tk.Toplevel(parent)
        self.win.title("Collectable Item Data")
        
        center_window(self.win, parent, 500, 500)
        self.win.configure(bg="#dfdfdf")
        self.win.resizable(False, False)
        self.win.transient(parent)
        
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)
        
        self.ui_font = ("MS Sans Serif", 8)
        self.title_font = ("MS Sans Serif", 8, "bold")
        
        self.active_type_id = None
        self.types_data = self._load_types_from_hry()
        
        self.setup_ui()
        self.refresh_type_dropdown()
        
    def setup_ui(self):
        top_f = tk.Frame(self.win, bg="#dfdfdf", pady=10, padx=10)
        top_f.pack(fill="x")
        
        tk.Label(top_f, text="Collectable Type:", bg="#dfdfdf", font=self.title_font).pack(side="left")
        self.type_select = ttk.Combobox(top_f, state="readonly", width=40)
        self.type_select.pack(side="left", padx=5)
        self.type_select.bind("<<ComboboxSelected>>", self._on_type_selected)

        mid_f = tk.Frame(self.win, bg="#dfdfdf", padx=10)
        mid_f.pack(fill="both", expand=True)

        left_col = tk.Frame(mid_f, bg="#dfdfdf")
        left_col.pack(side="left", fill="both", expand=True)

        self.stat_vars = {}
        fields = [
            ("value", "Gold Value:"),
            ("weight", "Weight:"),
            ("dam_min", "Min Damage:"),
            ("dam_max", "Max Damage:"),
            ("cure_type", "Cure Type:"),
            ("max_durability", "Max Durability:")
        ]
        for k, label in fields:
            lf = tk.Frame(left_col, bg="#dfdfdf")
            lf.pack(fill="x", pady=2)
            tk.Label(lf, text=label, bg="#dfdfdf", font=self.ui_font, width=15, anchor="w").pack(side="left")
            v = tk.StringVar(value="0")
            self.stat_vars[k] = v
            tk.Entry(lf, textvariable=v, width=10, relief="sunken", bd=2).pack(side="left", padx=5)

        right_col = tk.Frame(mid_f, bg="#dfdfdf")
        right_col.pack(side="right", fill="both", expand=True, padx=(10, 0))

        uf = tk.Frame(right_col, bg="#dfdfdf")
        uf.pack(fill="x", pady=2)
        tk.Label(uf, text="Use Type:", bg="#dfdfdf", font=self.ui_font).pack(side="left")
        self.use_type_var = tk.StringVar(value="NONE")
        use_types = ["NONE", "MINE", "SMELT", "FORGE", "BOOST", "REPAIR", "TELEPORT", "TELEP_AND_SPAWN", "SPAWN_GATE"]
        self.use_type_select = ttk.Combobox(uf, values=use_types, textvariable=self.use_type_var, state="readonly", width=15)
        self.use_type_select.pack(side="right", padx=5)

        req_group = tk.LabelFrame(right_col, text="Requirements", bg="#dfdfdf", font=self.ui_font, padx=10, pady=5)
        req_group.pack(fill="x", pady=10)
        req_f = [
            ("req_lvl", "Min Lvl:"),
            ("req_str", "Min Str:"),
            ("req_int", "Min Int:"),
            ("req_dex", "Min Dex:"),
            ("req_con", "Min Con:")
        ]
        for k, label in req_f:
            rf = tk.Frame(req_group, bg="#dfdfdf")
            rf.pack(fill="x", pady=1)
            tk.Label(rf, text=label, bg="#dfdfdf", font=self.ui_font, width=10, anchor="w").pack(side="left")
            v = tk.StringVar(value="0")
            self.stat_vars[k] = v
            tk.Entry(rf, textvariable=v, width=8, relief="sunken", bd=2).pack(side="right", padx=2)

        bottom_f = tk.Frame(self.win, bg="#dfdfdf", padx=10, pady=10)
        bottom_f.pack(fill="x", side="bottom")

        act_f = tk.Frame(bottom_f, bg="#dfdfdf")
        act_f.pack(side="right", fill="y", padx=5)
        tk.Button(act_f, text="OK", command=self.apply, bg="#C0C0C0", width=12, relief="raised", bd=2, font=self.ui_font).pack(side="left", padx=5)
        tk.Button(act_f, text="Cancel", command=self._on_close, bg="#C0C0C0", width=12, relief="raised", bd=2, font=self.ui_font).pack(side="left", padx=5)

    def _load_types_from_hry(self):
        if not self.save_manager or not self.save_manager.project_path: return {}
        path = os.path.join(self.save_manager.hairy_dir, "Types.hry")
        return ScriptParser.parse_types_use_sync(path)

    def refresh_type_dropdown(self):
        self.types_data = self._load_types_from_hry()
        if not self.types_data: return
        items = sorted([f"{tid}: {v.get('name', 'Unnamed')}" for tid, v in self.types_data.items() if v.get("family") == "FAM_COLLECTABLE"], key=lambda x: x.split(":")[1].lower())
        self.type_select.config(values=items)

    def _on_type_selected(self, event):
        sel = self.type_select.get()
        if sel:
            self.active_type_id = sel.split(":")[0]
            self.load_type_data()

    def load_type_data(self):
        if not self.active_type_id or self.active_type_id not in self.types_data: return
        data = self.types_data[self.active_type_id]
        hairy_filename = ScriptParser._hairy_filename(data.get("name", ""))
        hairy_path = os.path.join(self.save_manager.hairy_dir, hairy_filename)
        hairy_data = ScriptParser.get_hairy_defines(hairy_path) if os.path.exists(hairy_path) else {}

        for k, var in self.stat_vars.items():
            var.set(hairy_data.get(self.COLLECTABLE_MAP.get(k), "0"))
        
        # Load use type
        ut_idx = int(hairy_data.get("COLLECTABLE_USE_TYPE", "0"))
        ut_list = ["NONE", "MINE", "SMELT", "FORGE", "BOOST", "REPAIR", "TELEPORT", "TELEP_AND_SPAWN", "SPAWN_GATE"]
        ut_name = ut_list[ut_idx] if 0 <= ut_idx < len(ut_list) else "NONE"
        self.use_type_var.set(ut_name)
        
        self.win.title(f"Collectable Data - {data.get('name', 'Unnamed')}")

    def apply(self):
        if not self.active_type_id: return
        try:
            name = self.types_data[self.active_type_id].get("name", "")
            hairy_filename = ScriptParser._hairy_filename(name)
            hairy_path = os.path.join(self.save_manager.hairy_dir, hairy_filename)
            hairy_props = {self.COLLECTABLE_MAP[k]: int(v.get() or 0) for k, v in self.stat_vars.items() if k in self.COLLECTABLE_MAP}
            
            ut_list = ["NONE", "MINE", "SMELT", "FORGE", "BOOST", "REPAIR", "TELEPORT", "TELEP_AND_SPAWN", "SPAWN_GATE"]
            use_type_val = ut_list.index(self.use_type_var.get()) if self.use_type_var.get() in ut_list else 0
            hairy_props["COLLECTABLE_USE_TYPE"] = use_type_val
            hairy_props["FAM_COLLECTABLE"] = 1

            if os.path.exists(hairy_path):
                ScriptParser.update_hairy_defines(hairy_path, hairy_props)
            if self.save_manager: self.save_manager.mark_dirty()
            self._on_close()
        except Exception as e: messagebox.showerror("Error", str(e))

    def _on_close(self):
        if self.parent and self.parent.winfo_exists():
            self.parent.lift(); self.parent.focus_set()
        self.win.destroy()
