import tkinter as tk
from tkinter import messagebox, ttk
import os
import re
import config
from EditorComponents import center_window
import ScriptParser

class SkillEditor:
    """
    Skills Editor (Win95 Style).
    Directly manages Skills.hry and the project's EXP tables.
    """
    def __init__(self, parent, save_manager=None):
        self.parent = parent
        self.save_manager = save_manager
        
        self.win = tk.Toplevel(parent)
        self.win.title("Skills Editor")
        center_window(self.win, parent, 800, 550)
        self.win.configure(bg="#C0C0C0") # Win95 Gray
        
        if not self.save_manager or not self.save_manager.project_path:
             messagebox.showerror("Error", "No project active.")
             self.win.destroy()
             return

        self.skills_path = os.path.join(self.save_manager.project_path, "HAIRY", "Skills.hry")
        
        # --- NATIVE DATA ENGINE ---
        self.skills = []
        self.exp_tables = {}
        self.load_data()
        
        self.setup_ui()
        
        # --- DYNAMIC SYNC ---
        self.win.bind("<FocusIn>", lambda e: self.load_data(refresh_ui=True))

    def load_data(self, refresh_ui=False):
        """ Parses Skills.hry for EXP_TABLE and Skill blocks. """
        # --- OMNI-DIRECTIONAL HARVEST ---
        # We always check for new #Defines in the code to ensure the registry is complete
        self._harvest_legacy_skills()
        
        if not os.path.exists(self.skills_path) or os.path.getsize(self.skills_path) < 50:
            if refresh_ui: self.refresh_skill_list()
            return

        try:
            # Check for changes to avoid overwriting unsaved UI work unexpectedly
            # (Though FocusIn usually implies return from editor)
            with open(self.skills_path, "r") as f:
                content = f.read()

            temp_skills = []
            temp_tables = {}
            
            # --- PARSE EXP TABLES ---
            # Flexible match for EXP_TABLE "Name" { val1, ... } OR EXP_NAME { val1, ... }
            table_matches = re.finditer(r'(?i)(?:EXP_TABLE\s+"([^"]+)"|([a-zA-Z0-9_]+))\s*\{([^}]+)\}', content)
            for m in table_matches:
                name = m.group(1) or m.group(2)
                body = m.group(3)
                vals = [int(x.strip()) for x in body.split(",") if x.strip().isdigit()]
                temp_tables[name] = vals

            # --- PARSE SKILLS ---
            # Support both formats:
            # 1. Skill "Name" { ID x MaxLevel y Table "z" }
            # 2. Skill Name MaxLevel_100 Table ID
            
            # Format 1 (The Block Format)
            skill_matches_block = re.finditer(r'(?i)Skill\s+"([^"]+)"\s*\{([^}]+)\}', content)
            for m in skill_matches_block:
                name = m.group(1)
                body = m.group(2)
                skill_data = {"name": name}
                id_m = re.search(r'(?i)ID\s+(\d+)', body)
                ml_m = re.search(r'(?i)MaxLevel\s+(\d+)', body)
                tab_m = re.search(r'(?i)Table\s+"([^"]+)"', body)
                
                skill_data["id"] = int(id_m.group(1)) if id_m else 0
                skill_data["max_level"] = int(ml_m.group(1)) if ml_m else 100
                skill_data["table"] = tab_m.group(1) if tab_m else "EXP_0"
                temp_skills.append(skill_data)

            # Format 2 (The Flat Format: Skill Name MaxLevel_X TABLE ID)
            # We use a lazy match for Name until MaxLevel_
            flat_matches = re.finditer(r'(?i)Skill\s+(.*?)\s+MaxLevel_(\d+)\s+([a-zA-Z0-9_]+)\s+(\d+)', content)
            for m in flat_matches:
                name = m.group(1).strip().strip('"')
                ml = int(m.group(2))
                table_name = m.group(3)
                sid = int(m.group(4))
                
                # Check for duplicates if someone mixed formats
                if not any(s['name'] == name for s in temp_skills):
                    temp_skills.append({
                        "name": name,
                        "id": sid,
                        "max_level": ml,
                        "table": table_name
                    })

            if refresh_ui:
                # Only update if data actually changed to prevent cursor jumps
                if temp_skills != self.skills or temp_tables != self.exp_tables:
                    self.skills = temp_skills
                    self.exp_tables = temp_tables
                    self.refresh_skill_list()
            else:
                self.skills = temp_skills
                self.exp_tables = temp_tables
                
        except Exception as e:
            print(f"[ERROR] SkillEditor failed to parse Skills.hry: {e}")

    def _harvest_legacy_skills(self):
        """ Scans Defines.hry for existing #Define SKILL_ instances to bootstrap. """
        try:
            defines_path = os.path.join(self.save_manager.project_path, "HAIRY", "Defines.hry")
            if not os.path.exists(defines_path): return
            
            import ScriptParser
            legacy_defines = ScriptParser.get_hairy_defines(defines_path)
            
            found_any = False
            for key, val in legacy_defines.items():
                if key.startswith("SKILL_"):
                    # Clean the name (e.g. SKILL_LOOTING -> Looting)
                    pretty_name = key.replace("SKILL_", "").replace("_", " ").title()
                    try:
                        sid = int(val)
                        # Avoid duplicates
                        if not any(s['id'] == sid for s in self.skills):
                            self.skills.append({
                                "name": pretty_name,
                                "id": sid,
                                "max_level": 100,
                                "table": "Standard"
                            })
                            found_any = True
                    except: continue
            
            if found_any:
                print(f"[DEBUG] Skills Editor: Omni-Harvested {len(self.skills)} skills from code.")
                if "EXP_0" not in self.exp_tables:
                    # Initialize default tables if missing
                    self.exp_tables["EXP_0"] = [0, 10, 25, 50, 100, 200, 400, 800, 1600, 3200]
                
                # If we are in the middle of a load, UI will refresh later.
                # If this was a focused harvest, we might need a save trigger.
        except Exception as e:
            print(f"[ERROR] Legacy harvest failed: {e}")

    def save_data(self):
        """ Rebuilds Skills.hry from memory. """
        lines = ["// Skills.hry - AUTO-GENERATED BY SKILLS EDITOR\n\n"]
        
        # 1. EXP Tables
        for name, vals in self.exp_tables.items():
            val_str = ", ".join(map(str, vals))
            lines.append(f'{name}\n{{\n    {val_str}\n}}\n\n')
            
        # 2. Skills
        # Align headers for pretty vertical view
        lines.append("// " + "SKILL NAME".ljust(40) + "MAX_LVL".ljust(15) + "EXP_TABLE".ljust(20) + "ID\n")
        
        for s in self.skills:
            # Force quotes for safety and alignment
            clean_name = s["name"].strip('"')
            name_field = f'"{clean_name}"'.ljust(40)
            
            lines.append(f'Skill {name_field} MaxLevel_{s["max_level"]:<10} {s["table"]:<20} {s["id"]}\n')
            
        try:
            with open(self.skills_path, "w") as f:
                f.writelines(lines)
            
            # --- LOGIC SYNC ---
            ScriptParser.sync_skills_logic(self.save_manager.project_path)
            
            self.save_manager.mark_dirty()
            messagebox.showinfo("Success", "Skills.hry updated and SYNCED to Defines.hry.", parent=self.win)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save Skills.hry: {e}", parent=self.win)

    def setup_ui(self):
        # Master Paned Window
        paned = tk.PanedWindow(self.win, orient="horizontal", bg="#808080", sashwidth=4, sashrelief="raised")
        paned.pack(fill="both", expand=True, padx=5, pady=5)
        
        # --- LEFT: SKILL LIST ---
        left_f = tk.Frame(paned, bg="#C0C0C0", relief="sunken", bd=2)
        paned.add(left_f, width=250)
        
        tk.Label(left_f, text="Skills", bg="#000080", fg="white", font=("Arial", 9, "bold")).pack(fill="x")
        self.skill_lb = tk.Listbox(left_f, bg="white", font=("Arial", 9))
        self.skill_lb.pack(fill="both", expand=True, padx=2, pady=2)
        self.skill_lb.bind("<<ListboxSelect>>", self.on_skill_select)
        
        btn_f = tk.Frame(left_f, bg="#C0C0C0")
        btn_f.pack(fill="x", pady=5)
        tk.Button(btn_f, text="Add", width=8, command=self.add_skill).pack(side="left", padx=5)
        tk.Button(btn_f, text="Del", width=8, command=self.del_skill).pack(side="left")
        
        # --- RIGHT: EDITOR ---
        right_f = tk.Frame(paned, bg="#C0C0C0", relief="sunken", bd=2)
        paned.add(right_f)
        
        # Skill Details Group
        det_f = tk.LabelFrame(right_f, text="Skill Properties", bg="#C0C0C0", font=("Arial", 9, "bold"))
        det_f.pack(fill="x", padx=10, pady=10)
        
        tk.Label(det_f, text="Name:", bg="#C0C0C0").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.ent_name = tk.Entry(det_f, width=25)
        self.ent_name.grid(row=0, column=1, sticky="w")
        
        tk.Label(det_f, text="ID:", bg="#C0C0C0").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.ent_id = tk.Entry(det_f, width=10, state="disabled", disabledbackground="#E0E0E0", disabledforeground="black")
        self.ent_id.grid(row=1, column=1, sticky="w")
        
        tk.Label(det_f, text="Max Level:", bg="#C0C0C0").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.ent_max = tk.Entry(det_f, width=10)
        self.ent_max.grid(row=2, column=1, sticky="w")
        
        tk.Label(det_f, text="Exp Table:", bg="#C0C0C0").grid(row=3, column=0, sticky="e", padx=5, pady=5)
        self.cb_table = ttk.Combobox(det_f, values=["EXP_0"])
        self.cb_table.grid(row=3, column=1, sticky="w")
        self.cb_table.bind("<<ComboboxSelected>>", self.on_table_combo_change)
        
        tk.Button(det_f, text="Apply Logic Changes", command=self.apply_skill_changes, bg="#8080FF", fg="white").grid(row=4, column=1, pady=10)
        
        # EXP Table Editor Group (Rethought)
        exp_f = tk.LabelFrame(right_f, text="Experience Table Manager", bg="#C0C0C0", font=("Arial", 9, "bold"))
        exp_f.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Table Rename
        ren_f = tk.Frame(exp_f, bg="#C0C0C0")
        ren_f.pack(fill="x", padx=5, pady=5)
        tk.Label(ren_f, text="Rename Selected Table:", bg="#C0C0C0").pack(side="left")
        self.ent_table_name = tk.Entry(ren_f, width=20)
        self.ent_table_name.pack(side="left", padx=5)
        tk.Button(ren_f, text="Rename", command=self.rename_table).pack(side="left")

        # Layout: Left = Key Levels, Right = Slider
        split_f = tk.Frame(exp_f, bg="#C0C0C0")
        split_f.pack(fill="both", expand=True)

        # 1. KEY LEVELS (Vertical List)
        self.key_f = tk.LabelFrame(split_f, text="Key Milestones", bg="#C0C0C0")
        self.key_f.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        self.lvl_labels = {}
        for lvl in [10, 30, 50, 75, 100]:
            f = tk.Frame(self.key_f, bg="#C0C0C0")
            f.pack(fill="x", pady=2)
            tk.Label(f, text=f"Level {lvl}:", width=10, anchor="e", bg="#C0C0C0", font=("Arial", 9, "bold")).pack(side="left")
            var = tk.StringVar(value="0")
            lbl = tk.Label(f, textvariable=var, width=15, anchor="w", bg="white", relief="sunken")
            lbl.pack(side="left", padx=5)
            self.lvl_labels[lvl] = var

        # 2. THE SLIDER (Spring-Loaded 5% Scaling)
        adj_f = tk.LabelFrame(split_f, text="Power Scaler (±5% per step)", bg="#C0C0C0")
        adj_f.pack(side="right", fill="y", padx=5, pady=5)
        
        self.scale_var = tk.IntVar(value=0)
        self.scaler = tk.Scale(adj_f, from_=-5, to=5, orient="vertical", variable=self.scale_var, 
                              bg="#C0C0C0", length=150, sliderlength=30, showvalue=True,
                              command=self.on_scale_drag)
        self.scaler.pack(pady=10)
        self.scaler.bind("<ButtonRelease-1>", self.on_scale_release)
        
        tk.Label(adj_f, text="Drag to scale,\nrelease to apply", font=("Arial", 7, "italic"), bg="#C0C0C0").pack()
        
        # Bottom Actions
        foot = tk.Frame(self.win, bg="#C0C0C0", pady=10)
        foot.pack(side="bottom", fill="x")
        tk.Button(foot, text="💾 Save Skills.hry", bg="#008080", fg="white", width=20, command=self.save_data).pack(side="right", padx=10)
        tk.Button(foot, text="Cancel", width=12, command=self.win.destroy).pack(side="right")
        
        # Initial Refresh
        self.refresh_skill_list()

    def refresh_skill_list(self):
        self.skill_lb.delete(0, "end")
        for s in self.skills:
            self.skill_lb.insert("end", f"{s['id']}: {s['name']}")
            
        tables = list(self.exp_tables.keys())
        if not tables: tables = ["Standard"]
        self.cb_table.config(values=tables)

    def on_skill_select(self, e):
        sel = self.skill_lb.curselection()
        if not sel: return
        idx = sel[0]
        s = self.skills[idx]
        
        self.ent_name.delete(0, "end"); self.ent_name.insert(0, s['name'])
        
        self.ent_id.config(state="normal")
        self.ent_id.delete(0, "end"); self.ent_id.insert(0, str(s['id']))
        self.ent_id.config(state="disabled")
        
        self.ent_max.delete(0, "end"); self.ent_max.insert(0, str(s['max_level']))
        self.cb_table.set(s['table'])
        self.ent_table_name.delete(0, "end"); self.ent_table_name.insert(0, s['table'])
        
        self.refresh_key_levels()

    def on_table_combo_change(self, e):
        curr = self.cb_table.get()
        self.ent_table_name.delete(0, "end")
        self.ent_table_name.insert(0, curr)
        self.refresh_key_levels()

    def rename_table(self):
        old = self.cb_table.get()
        new = self.ent_table_name.get().strip()
        if not new or new == old: return
        
        if new in self.exp_tables:
            messagebox.showerror("Error", f"Table '{new}' already exists.")
            return

        # 1. Update dict
        self.exp_tables[new] = self.exp_tables.pop(old)
        
        # 2. Update all skills using this table
        for s in self.skills:
            if s['table'] == old:
                s['table'] = new
        
        self.refresh_skill_list()
        self.cb_table.set(new)
        messagebox.showinfo("Success", f"Table renamed to '{new}'")

    def refresh_key_levels(self):
        table_name = self.cb_table.get()
        vals = self.exp_tables.get(table_name, [0]*101)
        
        for lvl, var in self.lvl_labels.items():
            # Index lvl might be missing if table is short
            val = vals[lvl] if len(vals) > lvl else "???"
            var.set(f"{val:,}")

    def on_scale_drag(self, val):
        # Could show preview, but the user asked for release to apply
        pass

    def on_scale_release(self, e):
        steps = self.scale_var.get()
        if steps == 0: return

        table_name = self.cb_table.get()
        if table_name not in self.exp_tables: return

        # Multiply entire table by 1.05 ^ steps
        factor = 1.05 ** steps
        new_vals = []
        for v in self.exp_tables[table_name]:
            new_v = int(float(v) * factor)
            new_vals.append(new_v)
        
        self.exp_tables[table_name] = new_vals
        
        # Reset Scale and refresh
        self.scale_var.set(0)
        self.refresh_key_levels()
        messagebox.showinfo("Scaled", f"Adjusted '{table_name}' by {steps*5}%", parent=self.win)

    def apply_skill_changes(self):
        sel = self.skill_lb.curselection()
        if not sel: return
        idx = sel[0]
        
        # Update Skill
        self.skills[idx]['name'] = self.ent_name.get()
        self.skills[idx]['max_level'] = int(self.ent_max.get() or 100)
        self.skills[idx]['table'] = self.cb_table.get()
        
        self.refresh_skill_list()
        self.skill_lb.selection_set(idx)

    def add_skill(self):
        new_id = self.skills[-1]['id'] + 1 if self.skills else 1
        self.skills.append({"name": "New Skill", "id": new_id, "max_level": 100, "table": "Standard"})
        if "Standard" not in self.exp_tables: self.exp_tables["Standard"] = [0, 100, 250, 500, 1000]
        self.refresh_skill_list()
        self.skill_lb.selection_set("end")

    def del_skill(self):
        sel = self.skill_lb.curselection()
        if not sel: return
        self.skills.pop(sel[0])
        self.refresh_skill_list()
