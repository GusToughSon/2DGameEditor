import tkinter as tk
from tkinter import messagebox, ttk
import os
import ScriptParser
import config
from EditorComponents import center_window

class NPCDataEditor:
    """
    A professional-grade Creature Statistics Editor.
    Fully script-driven via Types.hry and .hry headers.
    """
    def __init__(self, parent, save_manager=None):
        self.parent = parent
        self.save_manager = save_manager
        
        # Mapping for Bidirectional Sync with .hry files
        self.NPC_MAP = {
            "min_hits": "NPC_MIN_HITS", "max_hits": "NPC_MAX_HITS",
            "to_hit": "NPC_TO_HIT", "min_dmg": "NPC_MIN_DMG", "max_dmg": "NPC_MAX_DMG",
            "ac": "NPC_AC", "level": "NPC_LEVEL", "atk_spd": "NPC_ATK_SPEED", "mov_spd": "NPC_MOV_SPEED",
            "strength": "NPC_STR", "intelligence": "NPC_INT", "dexterity": "NPC_DEX", "constitution": "NPC_CON",
            "cast_chance": "NPC_CAST_CHANCE", "spell_chance": "NPC_SPELL_CHANCE",
            "walk_type": "NPC_WALK_TYPE", "activity": "NPC_ACTIVITY", "alignment": "NPC_ALIGNMENT"
        }
        
        self.win = tk.Toplevel(parent)
        self.win.title("NPC Data")
        
        center_window(self.win, parent, 850, 700)
        self.win.configure(bg="#dfdfdf")
        self.win.resizable(False, False)
        self.win.transient(parent)
        
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)
        
        self.ui_font = ("Tahoma", 8)
        self.title_font = ("Tahoma", 8, "bold")
        
        self.active_type_id = None
        self.types_data = self._load_types_from_hry()
        
        self.setup_ui()
        self.refresh_type_dropdown()
        
    def setup_ui(self):
        # Header: Type Selection
        header = tk.Frame(self.win, bg="#dfdfdf", pady=10)
        header.pack(fill="x")
        tk.Label(header, text="Select NPC Type:", bg="#dfdfdf", font=self.title_font).pack(side="left", padx=10)
        self.type_select = ttk.Combobox(header, state="readonly", width=50)
        self.type_select.pack(side="left", padx=5)
        self.type_select.bind("<<ComboboxSelected>>", self._on_type_selected)

        # Main Body: Area-based layout
        body = tk.Frame(self.win, bg="#dfdfdf", padx=10, pady=10)
        body.pack(fill="both", expand=True)

        # --- Combat & Vitality ---
        combat_f = tk.LabelFrame(body, text="Combat & Vitality", bg="#dfdfdf", font=self.title_font, padx=10, pady=10)
        combat_f.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.combat_vars = {}
        c_fields = [("min_hits", "Min Hits:"), ("max_hits", "Max Hits:"), ("to_hit", "To Hit:"), ("min_dmg", "Min Dmg:"), ("max_dmg", "Max Dmg:"), ("ac", "Armor Class:")]
        for i, (k, l) in enumerate(c_fields):
            tk.Label(combat_f, text=l, bg="#dfdfdf", font=self.ui_font).grid(row=i, column=0, sticky="w", pady=2)
            v = tk.StringVar(value="0"); self.combat_vars[k] = v
            tk.Entry(combat_f, textvariable=v, width=10, relief="sunken", bd=2).grid(row=i, column=1, padx=5)

        # --- Attributes & Levels ---
        attr_f = tk.LabelFrame(body, text="Attributes & Levels", bg="#dfdfdf", font=self.title_font, padx=10, pady=10)
        attr_f.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.attr_vars = {}
        a_fields = [("level", "Level:"), ("strength", "Str:"), ("intelligence", "Int:"), ("dexterity", "Dex:"), ("constitution", "Con:")]
        for i, (k, l) in enumerate(a_fields):
            tk.Label(attr_f, text=l, bg="#dfdfdf", font=self.ui_font).grid(row=i, column=0, sticky="w", pady=2)
            v = tk.StringVar(value="0"); self.attr_vars[k] = v
            tk.Entry(attr_f, textvariable=v, width=10, relief="sunken", bd=2).grid(row=i, column=1, padx=5)

        # --- Movement & Behavior ---
        behave_f = tk.LabelFrame(body, text="Behavior", bg="#dfdfdf", font=self.title_font, padx=10, pady=10)
        behave_f.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        tk.Label(behave_f, text="Activity:", bg="#dfdfdf").grid(row=0, column=0, sticky="w")
        self.activity_var = tk.StringVar()
        self.activity_cb = ttk.Combobox(behave_f, values=["Stand", "Wander", "Hostile", "Guard", "Shop"], textvariable=self.activity_var, state="readonly", width=12)
        self.activity_cb.grid(row=0, column=1, pady=5)

        tk.Label(behave_f, text="Alignment:", bg="#dfdfdf").grid(row=1, column=0, sticky="w")
        self.align_val = tk.StringVar(value="0")
        tk.Entry(behave_f, textvariable=self.align_val, width=12, relief="sunken", bd=2).grid(row=1, column=1, pady=5)

        # --- Magical Capabilities ---
        magic_f = tk.LabelFrame(body, text="Magic", bg="#dfdfdf", font=self.title_font, padx=10, pady=10)
        magic_f.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        self.magic_vars = {}
        m_fields = [("cast_chance", "Cast %:"), ("spell_chance", "Spell %:")]
        for i, (k, l) in enumerate(m_fields):
            tk.Label(magic_f, text=l, bg="#dfdfdf", font=self.ui_font).grid(row=i, column=0, sticky="w", pady=2)
            v = tk.StringVar(value="0"); self.magic_vars[k] = v
            tk.Entry(magic_f, textvariable=v, width=10, relief="sunken", bd=2).grid(row=i, column=1, padx=5)

        # Footer Buttons
        footer = tk.Frame(self.win, bg="#dfdfdf", pady=15)
        footer.pack(fill="x", side="bottom")
        tk.Button(footer, text="Save Changes", command=self.apply, width=20, bg="#C0C0C0", relief="raised", bd=2).pack(side="left", padx=20)
        tk.Button(footer, text="Cancel", command=self.win.destroy, width=20, bg="#C0C0C0", relief="raised", bd=2).pack(side="right", padx=20)

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
            self.load_data()

    def load_data(self):
        if not self.active_type_id or self.active_type_id not in self.types_data: return
        name = self.types_data[self.active_type_id].get("name", "")
        hairy_filename = ScriptParser._hairy_filename(name)
        hairy_path = os.path.join(self.save_manager.project_path, "HAIRY", hairy_filename)
        hairy_data = ScriptParser.get_hairy_defines(hairy_path) if os.path.exists(hairy_path) else {}

        for k, var in {**self.combat_vars, **self.attr_vars, **self.magic_vars}.items():
            var.set(hairy_data.get(self.NPC_MAP.get(k), "0"))
        self.align_val.set(hairy_data.get("NPC_ALIGNMENT", "0"))
        self.activity_var.set(hairy_data.get("NPC_ACTIVITY", "Stand"))
        self.win.title(f"NPC Data - {name}")

    def apply(self):
        if not self.active_type_id: return
        try:
            name = self.types_data[self.active_type_id].get("name", "")
            hairy_filename = ScriptParser._hairy_filename(name)
            hairy_path = os.path.join(self.save_manager.project_path, "HAIRY", hairy_filename)
            
            data = {**self.combat_vars, **self.attr_vars, **self.magic_vars}
            hairy_props = {self.NPC_MAP[k]: int(v.get() or 0) for k, v in data.items()}
            hairy_props["NPC_ALIGNMENT"] = int(self.align_val.get() or 0)
            hairy_props["NPC_ACTIVITY"] = self.activity_var.get()

            if os.path.exists(hairy_path):
                ScriptParser.update_hairy_defines(hairy_path, hairy_props)
            if self.save_manager: self.save_manager.mark_dirty()
            messagebox.showinfo("Success", f"NPC statistics for {name} updated in script.")
            self.win.destroy()
        except Exception as e: messagebox.showerror("Error", str(e))

    def _on_close(self):
        if self.parent and self.parent.winfo_exists():
            self.parent.lift(); self.parent.focus_set()
        self.win.destroy()
