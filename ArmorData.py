import tkinter as tk
from tkinter import messagebox, ttk
import os
import ScriptParser
import config
from EditorComponents import center_window

class ArmorDataEditor:
    """
    Armor Statistics Editor.
    """
    def __init__(self, parent, save_manager=None):
        self.parent = parent
        self.save_manager = save_manager
        
        # Mapping for Bidirectional Sync with .hry files
        self.ARMOR_MAP = {
            "ac": "ARMOR_AC",
            "can_repair": "ARMOR_REPAIRABLE",
            "is_magic": "ARMOR_MAGIC",
            "min_hp": "ARMOR_MIN_HP",
            "max_hp": "ARMOR_MAX_HP",
            "req_lvl": "ARMOR_REQ_LEVEL",
            "req_str": "ARMOR_REQ_STR",
            "req_int": "ARMOR_REQ_INT",
            "req_dex": "ARMOR_REQ_DEX",
            "req_con": "ARMOR_REQ_CON",
            "alignment": "ARMOR_ALIGNMENT"
        }
        
        self.win = tk.Toplevel(parent)
        self.win.title("Armor Data")
        
        center_window(self.win, parent, 450, 400)
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

        # Row 1: Type & Alignment
        r1 = tk.Frame(top_f, bg="#dfdfdf")
        r1.pack(fill="x", pady=2)
        
        tk.Label(r1, text="Type:", bg="#dfdfdf", font=self.ui_font).pack(side="left")
        self.type_select = ttk.Combobox(r1, state="readonly", width=25)
        self.type_select.pack(side="left", padx=5)
        self.type_select.bind("<<ComboboxSelected>>", self._on_type_selected)
        
        tk.Label(r1, text="Alignment:", bg="#dfdfdf", font=self.ui_font).pack(side="left", padx=(10, 0))
        self.align_var = tk.StringVar(value="ANY")
        self.align_select = ttk.Combobox(r1, values=["ANY", "GOOD", "NEUTRAL", "EVIL"], textvariable=self.align_var, state="readonly", width=10)
        self.align_select.pack(side="left", padx=5)

        # Row 2: Protection Value
        r2 = tk.Frame(top_f, bg="#dfdfdf")
        r2.pack(fill="x", pady=2)
        tk.Label(r2, text="Protection Value:", bg="#dfdfdf", font=self.ui_font).pack(side="left")
        self.ac_val = tk.StringVar(value="0")
        tk.Entry(r2, textvariable=self.ac_val, width=10, relief="sunken", bd=2).pack(side="left", padx=5)

        mid_f = tk.Frame(self.win, bg="#dfdfdf", padx=10)
        mid_f.pack(fill="both", expand=True)

        left_col = tk.Frame(mid_f, bg="#dfdfdf")
        left_col.pack(side="left", fill="both", expand=True)

        flags_group = tk.LabelFrame(left_col, text="Flags", bg="#dfdfdf", font=self.ui_font, padx=5, pady=5)
        flags_group.pack(fill="x", pady=5)
        
        self.can_repair = tk.BooleanVar()
        self.is_magic = tk.BooleanVar()
        tk.Checkbutton(flags_group, text="Can be repaired", variable=self.can_repair, bg="#dfdfdf", font=self.ui_font).pack(anchor="w")
        tk.Checkbutton(flags_group, text="Magic", variable=self.is_magic, bg="#dfdfdf", font=self.ui_font).pack(anchor="w")

        tk.Label(left_col, text="Min Health:", bg="#dfdfdf", font=self.ui_font).pack(anchor="w", pady=(5,0))
        self.min_hp = tk.StringVar(value="0")
        tk.Entry(left_col, textvariable=self.min_hp, width=15, relief="sunken", bd=2).pack(anchor="w", pady=2)
        
        tk.Label(left_col, text="Max Health:", bg="#dfdfdf", font=self.ui_font).pack(anchor="w", pady=(5,0))
        self.max_hp = tk.StringVar(value="0")
        tk.Entry(left_col, textvariable=self.max_hp, width=15, relief="sunken", bd=2).pack(anchor="w", pady=2)

        right_col = tk.Frame(mid_f, bg="#dfdfdf")
        right_col.pack(side="right", fill="both", expand=True, padx=(10, 0))

        req_group = tk.LabelFrame(right_col, text="Attribute Requirements", bg="#dfdfdf", font=self.ui_font, padx=10, pady=5)
        req_group.pack(fill="both", expand=True, pady=5)

        self.req_vars = {}
        req_fields = [("req_lvl", "Min Level:"), ("req_str", "Min Str:"), ("req_int", "Min Int:"), ("req_dex", "Min Dex:"), ("req_con", "Min Con:")]
        for k, label in req_fields:
            f = tk.Frame(req_group, bg="#dfdfdf")
            f.pack(fill="x", pady=1)
            tk.Label(f, text=label, bg="#dfdfdf", font=self.ui_font, width=10, anchor="w").pack(side="left")
            v = tk.StringVar(value="0")
            self.req_vars[k] = v
            tk.Entry(f, textvariable=v, width=8, relief="sunken", bd=2).pack(side="right", padx=2)

        btn_f = tk.Frame(self.win, bg="#dfdfdf", pady=15, padx=10)
        btn_f.pack(fill="x", side="bottom")
        tk.Button(btn_f, text="OK", command=self.apply, bg="#C0C0C0", width=12, relief="raised", bd=2, font=self.ui_font).pack(side="left")
        tk.Button(btn_f, text="Cancel", command=self.win.destroy, bg="#C0C0C0", width=12, relief="raised", bd=2, font=self.ui_font).pack(side="right")

    def _load_types_from_hry(self):
        if not self.save_manager or not self.save_manager.project_path: return {}
        path = os.path.join(self.save_manager.project_path, "HAIRY", "Types.hry")
        return ScriptParser.parse_types_use_sync(path)

    def refresh_type_dropdown(self):
        self.types_data = self._load_types_from_hry()
        if not self.types_data: return
        items = sorted([(v.get('name', 'Unnamed'), tid) for tid, v in self.types_data.items()], key=lambda x: x[0].lower())
        self.type_select.config(values=[f"{tid}: {name}" for name, tid in items])

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

        self.ac_val.set(hairy_data.get("ARMOR_AC", "0"))
        self.min_hp.set(hairy_data.get("ARMOR_MIN_HP", "0"))
        self.max_hp.set(hairy_data.get("ARMOR_MAX_HP", "0"))
        align_code = int(hairy_data.get("ARMOR_ALIGNMENT", "0"))
        self.align_var.set({0: "GOOD", 13750: "NEUTRAL", 27500: "EVIL"}.get(align_code, "ANY"))
        self.can_repair.set(hairy_data.get("ARMOR_REPAIRABLE") == "1")
        self.is_magic.set(hairy_data.get("ARMOR_MAGIC") == "1")
        for k, var in self.req_vars.items():
            var.set(hairy_data.get(self.ARMOR_MAP.get(k), "0"))
        self.win.title(f"Armor Data - {data.get('name', 'Unnamed')}")

    def apply(self):
        if not self.active_type_id: return
        try:
            name = self.types_data[self.active_type_id].get("name", "")
            hairy_filename = ScriptParser._hairy_filename(name)
            hairy_path = os.path.join(self.save_manager.project_path, "HAIRY", hairy_filename)
            hairy_props = {
                "ARMOR_AC": int(self.ac_val.get() or 0),
                "ARMOR_MIN_HP": int(self.min_hp.get() or 0),
                "ARMOR_MAX_HP": int(self.max_hp.get() or 0),
                "ARMOR_REPAIRABLE": 1 if self.can_repair.get() else 0,
                "ARMOR_MAGIC": 1 if self.is_magic.get() else 0
            }
            align_map = {"ANY": 0, "GOOD": 0, "NEUTRAL": 13750, "EVIL": 27500}
            hairy_props["ARMOR_ALIGNMENT"] = align_map.get(self.align_var.get(), 0)
            for k, var in self.req_vars.items():
                hairy_props[self.ARMOR_MAP.get(k)] = int(var.get() or 0)

            if os.path.exists(hairy_path):
                ScriptParser.update_hairy_defines(hairy_path, hairy_props)
            if self.save_manager: self.save_manager.mark_dirty()
            self._on_close()
        except Exception as e: messagebox.showerror("Error", str(e))

    def _on_close(self):
        if self.parent and self.parent.winfo_exists():
            self.parent.lift(); self.parent.focus_set()
        self.win.destroy()
