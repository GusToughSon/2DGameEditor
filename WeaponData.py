import tkinter as tk
from tkinter import messagebox, ttk
import os
import ScriptParser
import config
from EditorComponents import center_window

class WeaponDataEditor:
    """
    Weapon Statistics Editor.
    """
    def __init__(self, parent, save_manager=None):
        self.parent = parent
        self.save_manager = save_manager
        
        # Mapping for Bidirectional Sync with .hry files
        self.WEAPON_MAP = {
            "to_hit": "WEAPON_TO_HIT",
            "min_dmg": "WEAPON_MIN_DMG",
            "max_dmg": "WEAPON_MAX_DMG",
            "speed": "WEAPON_SPEED",
            "min_hp": "WEAPON_MIN_HP",
            "max_hp": "WEAPON_MAX_HP",
            "w_class": "WEAPON_CLASS",
            "alignment": "WEAPON_ALIGNMENT",
            "req_lvl": "WEAPON_REQ_LEVEL",
            "req_str": "WEAPON_REQ_STR",
            "req_int": "WEAPON_REQ_INT",
            "req_dex": "WEAPON_REQ_DEX",
            "req_con": "WEAPON_REQ_CON",
            "can_repair": "WEAPON_REPAIRABLE",
            "is_ranged": "WEAPON_RANGED",
            "is_magic": "WEAPON_MAGIC"
        }
        
        self.win = tk.Toplevel(parent)
        self.win.title("Weapon Data")
        
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
        
        tk.Label(top_f, text=str("Weapon Type:"), bg="#dfdfdf", font=self.title_font).pack(side="left")
        self.type_select = ttk.Combobox(top_f, state="readonly", width=40)
        self.type_select.pack(side="left", padx=5)
        self.type_select.bind("<<ComboboxSelected>>", self._on_type_selected)

        mid_f = tk.Frame(self.win, bg="#dfdfdf", padx=10)
        mid_f.pack(fill="both", expand=True)

        left_col = tk.Frame(mid_f, bg="#dfdfdf")
        left_col.pack(side="left", fill="both", expand=True)

        self.stat_vars = {}
        fields = [("to_hit", "To Hit Mod:"), ("min_dmg", "Min Damage:"), ("max_dmg", "Max Damage:"), ("speed", "Speed:"), ("min_hp", "Min Health:"), ("max_hp", "Max Health:")]
        for k, label in fields:
            lf = tk.Frame(left_col, bg="#dfdfdf")
            lf.pack(fill="x", pady=2)
            tk.Label(lf, text=label, bg="#dfdfdf", font=self.ui_font, width=15, anchor="w").pack(side="left")
            v = tk.StringVar(value="0")
            self.stat_vars[k] = v
            tk.Entry(lf, textvariable=v, width=10, relief="sunken", bd=2).pack(side="left", padx=5)

        right_col = tk.Frame(mid_f, bg="#dfdfdf")
        right_col.pack(side="right", fill="both", expand=True, padx=(10, 0))

        cf = tk.Frame(right_col, bg="#dfdfdf")
        cf.pack(fill="x", pady=2)
        tk.Label(cf, text="Class:", bg="#dfdfdf", font=self.ui_font).pack(side="left")
        self.class_var = tk.StringVar(value="Dagger")
        classes = ["Dagger", "Sword", "Axe", "Mace", "Spear", "Bow", "Crossbow", "Staff", "Polearm"]
        self.class_select = ttk.Combobox(cf, values=classes, textvariable=self.class_var, state="readonly", width=12)
        self.class_select.pack(side="right", padx=5)

        af = tk.Frame(right_col, bg="#dfdfdf")
        af.pack(fill="x", pady=2)
        tk.Label(af, text="Alignment:", bg="#dfdfdf", font=self.ui_font).pack(side="left")
        self.align_var = tk.StringVar(value="ANY")
        self.align_select = ttk.Combobox(af, values=["ANY", "GOOD", "NEUTRAL", "EVIL"], textvariable=self.align_var, state="readonly", width=12)
        self.align_select.pack(side="right", padx=5)

        req_group = tk.LabelFrame(right_col, text="Requirements", bg="#dfdfdf", font=self.ui_font, padx=10, pady=5)
        req_group.pack(fill="x", pady=10)
        req_f = [("req_lvl", "Min Lvl:"), ("req_str", "Min Str:"), ("req_int", "Min Int:"), ("req_dex", "Min Dex:"), ("req_con", "Min Con:")]
        for k, label in req_f:
            rf = tk.Frame(req_group, bg="#dfdfdf")
            rf.pack(fill="x", pady=1)
            tk.Label(rf, text=label, bg="#dfdfdf", font=self.ui_font, width=10, anchor="w").pack(side="left")
            v = tk.StringVar(value="0")
            self.stat_vars[k] = v
            tk.Entry(rf, textvariable=v, width=8, relief="sunken", bd=2).pack(side="right", padx=2)

        bottom_f = tk.Frame(self.win, bg="#dfdfdf", padx=10, pady=10)
        bottom_f.pack(fill="x", side="bottom")
        
        flags_group = tk.LabelFrame(bottom_f, text="Flags", bg="#dfdfdf", font=self.ui_font, padx=5, pady=5)
        flags_group.pack(side="left", fill="y", padx=5)
        self.can_repair = tk.BooleanVar(); self.is_ranged = tk.BooleanVar(); self.is_magic = tk.BooleanVar()
        tk.Checkbutton(flags_group, text="Can repair", variable=self.can_repair, bg="#dfdfdf", font=self.ui_font).pack(anchor="w")
        tk.Checkbutton(flags_group, text="Ranged", variable=self.is_ranged, bg="#dfdfdf", font=self.ui_font).pack(anchor="w")
        tk.Checkbutton(flags_group, text="Magic", variable=self.is_magic, bg="#dfdfdf", font=self.ui_font).pack(anchor="w")

        act_f = tk.Frame(bottom_f, bg="#dfdfdf")
        act_f.pack(side="right", fill="y", padx=5)
        tk.Button(act_f, text="OK", command=self.apply, bg="#C0C0C0", width=12, relief="raised", bd=2, font=self.ui_font).pack(side="left", padx=5)
        tk.Button(act_f, text="Cancel", command=self._on_close, bg="#C0C0C0", width=12, relief="raised", bd=2, font=self.ui_font).pack(side="left", padx=5)

    def _load_types_from_hry(self):
        if not self.save_manager or not self.save_manager.project_path: return {}
        path = os.path.join(self.save_manager.project_path, "HAIRY", "Types.hry")
        return ScriptParser.parse_types_use_sync(path)

    def refresh_type_dropdown(self):
        self.types_data = self._load_types_from_hry()
        if not self.types_data: return
        items = sorted([f"{tid}: {v.get('name', 'Unnamed')}" for tid, v in self.types_data.items()], key=lambda x: x.split(":")[1].lower())
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
        hairy_path = os.path.join(self.save_manager.project_path, "HAIRY", hairy_filename)
        hairy_data = ScriptParser.get_hairy_defines(hairy_path) if os.path.exists(hairy_path) else {}

        for k, var in self.stat_vars.items():
            var.set(hairy_data.get(self.WEAPON_MAP.get(k), "0"))
        self.align_var.set({0: "GOOD", 13750: "NEUTRAL", 27500: "EVIL"}.get(int(hairy_data.get("WEAPON_ALIGNMENT", "0")), "ANY"))
        self.class_var.set(hairy_data.get("WEAPON_CLASS", "Sword"))
        self.can_repair.set(hairy_data.get("WEAPON_REPAIRABLE") == "1")
        self.is_ranged.set(hairy_data.get("WEAPON_RANGED") == "1")
        self.is_magic.set(hairy_data.get("WEAPON_MAGIC") == "1")
        self.win.title(f"Weapon Data - {data.get('name', 'Unnamed')}")

    def apply(self):
        if not self.active_type_id: return
        try:
            name = self.types_data[self.active_type_id].get("name", "")
            hairy_filename = ScriptParser._hairy_filename(name)
            hairy_path = os.path.join(self.save_manager.project_path, "HAIRY", hairy_filename)
            hairy_props = {self.WEAPON_MAP[k]: int(v.get() or 0) for k, v in self.stat_vars.items() if k in self.WEAPON_MAP}
            hairy_props.update({
                "WEAPON_CLASS": self.class_var.get(),
                "WEAPON_ALIGNMENT": {"ANY": 0, "GOOD": 0, "NEUTRAL": 13750, "EVIL": 27500}.get(self.align_var.get(), 0),
                "WEAPON_REPAIRABLE": 1 if self.can_repair.get() else 0,
                "WEAPON_RANGED": 1 if self.is_ranged.get() else 0,
                "WEAPON_MAGIC": 1 if self.is_magic.get() else 0
            })
            if os.path.exists(hairy_path):
                ScriptParser.update_hairy_defines(hairy_path, hairy_props)
            if self.save_manager: self.save_manager.mark_dirty()
            self._on_close()
        except Exception as e: messagebox.showerror("Error", str(e))

    def _on_close(self):
        if self.parent and self.parent.winfo_exists():
            self.parent.lift(); self.parent.focus_set()
        self.win.destroy()
