import tkinter as tk
from tkinter import messagebox, ttk
import os
import ScriptParser
import config
from EditorComponents import center_window

class MonsterTypeDataEditor:
    """
    Monster Type statistics and properties editor.
    """
    def __init__(self, parent, save_manager=None):
        self.parent = parent
        self.save_manager = save_manager
        
        # Mapping for Bidirectional Sync with .hry files
        self.MONSTER_MAP = {
            "hp_max": "LOCAL_HEALTH",
            "dam_min": "NPC_MIN_DMG",
            "dam_max": "NPC_MAX_DMG",
            "attack_speed": "NPC_ATK_SPEED",
            "moving_speed": "LOCAL_ATTACK_TICK",
            "level": "NPC_LEVEL",
            "tileset": "TILESET",
            "graphic_x": "GRAPHIC_X",
            "graphic_y": "GRAPHIC_Y",
            "rnd_walk_range": "RND_WALK_RANGE"
        }
        
        self.win = tk.Toplevel(parent)
        self.win.title("Monster Type Editor")
        
        center_window(self.win, parent, 550, 520)
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
        
        tk.Label(top_f, text="Monster Type:", bg="#dfdfdf", font=self.title_font).pack(side="left")
        self.type_select = ttk.Combobox(top_f, state="readonly", width=40)
        self.type_select.pack(side="left", padx=5)
        self.type_select.bind("<<ComboboxSelected>>", self._on_type_selected)

        mid_f = tk.Frame(self.win, bg="#dfdfdf", padx=10)
        mid_f.pack(fill="both", expand=True)

        left_col = tk.Frame(mid_f, bg="#dfdfdf")
        left_col.pack(side="left", fill="both", expand=True)

        self.stat_vars = {}
        fields = [
            ("hp_max", "Max Health:"),
            ("dam_min", "Min Damage:"),
            ("dam_max", "Max Damage:"),
            ("attack_speed", "Attack Speed:"),
            ("moving_speed", "Move Tick (ms):"),
            ("level", "Level:"),
            ("rnd_walk_range", "Walk Range:")
        ]
        for k, label in fields:
            lf = tk.Frame(left_col, bg="#dfdfdf")
            lf.pack(fill="x", pady=2)
            tk.Label(lf, text=label, bg="#dfdfdf", font=self.ui_font, width=18, anchor="w").pack(side="left")
            v = tk.StringVar(value="0")
            self.stat_vars[k] = v
            tk.Entry(lf, textvariable=v, width=10, relief="sunken", bd=2).pack(side="left", padx=5)

        right_col = tk.Frame(mid_f, bg="#dfdfdf")
        right_col.pack(side="right", fill="both", expand=True, padx=(10, 0))

        # Tileset & Graphic
        tf = tk.Frame(right_col, bg="#dfdfdf")
        tf.pack(fill="x", pady=2)
        tk.Label(tf, text="Tileset:", bg="#dfdfdf", font=self.ui_font, width=10, anchor="w").pack(side="left")
        self.tileset_var = tk.StringVar(value="AVATAR")
        self.tileset_select = ttk.Combobox(tf, values=["AVATAR", "ITEMS", "World", "OBJECTS"], textvariable=self.tileset_var, state="readonly", width=12)
        self.tileset_select.pack(side="left", padx=5)

        gf1 = tk.Frame(right_col, bg="#dfdfdf")
        gf1.pack(fill="x", pady=2)
        tk.Label(gf1, text="Graphic X:", bg="#dfdfdf", font=self.ui_font, width=10, anchor="w").pack(side="left")
        self.graphic_x_var = tk.StringVar(value="0")
        self.stat_vars["graphic_x"] = self.graphic_x_var
        tk.Entry(gf1, textvariable=self.graphic_x_var, width=8, relief="sunken", bd=2).pack(side="left", padx=5)

        gf2 = tk.Frame(right_col, bg="#dfdfdf")
        gf2.pack(fill="x", pady=2)
        tk.Label(gf2, text="Graphic Y:", bg="#dfdfdf", font=self.ui_font, width=10, anchor="w").pack(side="left")
        self.graphic_y_var = tk.StringVar(value="0")
        self.stat_vars["graphic_y"] = self.graphic_y_var
        tk.Entry(gf2, textvariable=self.graphic_y_var, width=8, relief="sunken", bd=2).pack(side="left", padx=5)

        # Flags LabelFrame
        flags_group = tk.LabelFrame(right_col, text="Flags", bg="#dfdfdf", font=self.ui_font, padx=10, pady=5)
        flags_group.pack(fill="x", pady=10)
        
        self.solid = tk.BooleanVar(value=True)
        self.ghost = tk.BooleanVar()
        self.fly = tk.BooleanVar()
        self.rnd_walk_off = tk.BooleanVar()

        tk.Checkbutton(flags_group, text="Solid", variable=self.solid, bg="#dfdfdf", font=self.ui_font).pack(anchor="w")
        tk.Checkbutton(flags_group, text="Ghost", variable=self.ghost, bg="#dfdfdf", font=self.ui_font).pack(anchor="w")
        tk.Checkbutton(flags_group, text="Fly", variable=self.fly, bg="#dfdfdf", font=self.ui_font).pack(anchor="w")
        tk.Checkbutton(flags_group, text="Rnd Walk Off", variable=self.rnd_walk_off, bg="#dfdfdf", font=self.ui_font).pack(anchor="w")

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
        items = sorted([f"{tid}: {v.get('name', 'Unnamed')}" for tid, v in self.types_data.items() if v.get("family") == "FAM_MONSTER"], key=lambda x: x.split(":")[1].lower())
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

        # Load values into text fields
        for k, var in self.stat_vars.items():
            if k == "graphic_x" or k == "graphic_y":
                # Handle GRAPHIC list format [x, y]
                g_str = hairy_data.get("GRAPHIC", "0,0").strip()
                if "," in g_str:
                    parts = g_str.split(",")
                else:
                    parts = g_str.split()
                if k == "graphic_x":
                    var.set(parts[0] if len(parts) > 0 else "0")
                else:
                    var.set(parts[1] if len(parts) > 1 else "0")
            else:
                var.set(hairy_data.get(self.MONSTER_MAP.get(k), "0"))
        
        self.tileset_var.set(hairy_data.get("TILESET", "AVATAR").strip('"'))
        self.solid.set(hairy_data.get("SOLID", "1") == "1")
        self.ghost.set(hairy_data.get("GHOST", "0") == "1")
        self.fly.set(hairy_data.get("FLY", "0") == "1")
        self.rnd_walk_off.set(hairy_data.get("RND_WALK_OFF", "0") == "1")
        
        self.win.title(f"Monster Type Editor - {data.get('name', 'Unnamed')}")

    def apply(self):
        if not self.active_type_id: return
        try:
            name = self.types_data[self.active_type_id].get("name", "")
            hairy_filename = ScriptParser._hairy_filename(name)
            hairy_path = os.path.join(self.save_manager.hairy_dir, hairy_filename)
            hairy_props = {}
            
            # Simple maps
            for k, v in self.stat_vars.items():
                if k not in ("graphic_x", "graphic_y"):
                    hairy_props[self.MONSTER_MAP[k]] = int(v.get() or 0)
            
            # Graphic array
            gx = int(self.graphic_x_var.get() or 0)
            gy = int(self.graphic_y_var.get() or 0)
            hairy_props["GRAPHIC"] = f"{gx},{gy}"
            
            hairy_props.update({
                "TILESET": f'"{self.tileset_var.get()}"',
                "SOLID": 1 if self.solid.get() else 0,
                "GHOST": 1 if self.ghost.get() else 0,
                "FLY": 1 if self.fly.get() else 0,
                "RND_WALK_OFF": 1 if self.rnd_walk_off.get() else 0,
                "FAM_MONSTER": 1
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
