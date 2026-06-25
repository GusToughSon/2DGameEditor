import tkinter as tk
from tkinter import ttk, messagebox
import os
from EditorComponents import center_window

class MonsterSpawnEditor:
    """
    Classic 'Treasure Type Dialog' for modifying Monster Loot Tables.
    """
    def __init__(self, parent, save_manager, main_app=None):
        self.parent = parent
        self.save_manager = save_manager
        self.main_app = main_app
        
        # --- WINDOW SETUP ---
        self.win = tk.Toplevel(parent)
        self.win.title("Treasure Type Dialog")
        center_window(self.win, parent, 600, 400)
        self.win.configure(bg="#C0C0C0") # Classic light grey
        self.win.transient(parent)
        self.win.grab_set() # Modal
        
        self.ui_font = ("Tahoma", 8)
        self.bg_color = "#C0C0C0"
        
        self.loot_tables = {}
        self.active_table = "Default"
        self.active_item_idx = None
        
        self.setup_ui()
        self.load_loot_tables()
        
    def setup_ui(self):
        # Master container for left and right panels
        main_frame = tk.Frame(self.win, bg=self.bg_color)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # -------------------------------------------------------------
        # LEFT PANEL
        # -------------------------------------------------------------
        left_frame = tk.Frame(main_frame, bg=self.bg_color)
        left_frame.pack(side="left", fill="y", padx=(0, 10))
        
        tk.Label(left_frame, text="Loot Table :", bg=self.bg_color, font=self.ui_font).pack(anchor="w")
        
        list_frame = tk.Frame(left_frame)
        list_frame.pack(fill="y", expand=True)
        
        self.table_list = tk.Listbox(list_frame, font=self.ui_font, selectbackground="#0000A0", selectforeground="white", width=25)
        self.table_list.pack(side="left", fill="y", expand=True)
        
        scrollbar = tk.Scrollbar(list_frame, command=self.table_list.yview)
        scrollbar.pack(side="right", fill="y")
        self.table_list.config(yscrollcommand=scrollbar.set)
        
        self.table_list.bind("<<ListboxSelect>>", self._on_table_select)
        
        btn_frame_left = tk.Frame(left_frame, bg=self.bg_color)
        btn_frame_left.pack(fill="x", pady=(5, 0))
        
        tk.Button(btn_frame_left, text="Add Table", font=self.ui_font, width=11, command=self._add_table).pack(side="left", padx=(0, 2))
        tk.Button(btn_frame_left, text="Del Table", font=self.ui_font, width=11, command=self._del_table).pack(side="right", padx=(2, 0))
        
        # -------------------------------------------------------------
        # RIGHT PANEL
        # -------------------------------------------------------------
        right_frame = tk.LabelFrame(main_frame, text="Loot Table Properties", bg=self.bg_color, font=self.ui_font)
        right_frame.pack(side="left", fill="both", expand=True)
        
        # Inner splits for the right frame: left side is list+buttons, right is props
        inner_left = tk.Frame(right_frame, bg=self.bg_color)
        inner_left.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        self.item_list = tk.Listbox(inner_left, font=self.ui_font, bg="white")
        self.item_list.pack(fill="both", expand=True)
        self.item_list.bind("<<ListboxSelect>>", self._on_item_select)
        
        # Item action buttons vertically aligned
        btn_frame_inner = tk.Frame(inner_left, bg=self.bg_color)
        btn_frame_inner.pack(fill="x", pady=(5, 0))
        tk.Button(btn_frame_inner, text="Add Item", font=self.ui_font, width=10, command=self._add_item).pack(side="left", padx=2)
        tk.Button(btn_frame_inner, text="Del Item", font=self.ui_font, width=10, command=self._del_item).pack(side="left", padx=2)
        
        # Right side properties
        inner_right = tk.Frame(right_frame, bg=self.bg_color)
        inner_right.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)
        
        # Name Entry
        self.name_var = tk.StringVar(value="Default")
        tk.Entry(inner_right, textvariable=self.name_var, font=self.ui_font, width=20, state="readonly").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        
        # "There is a" [0] "% chance that"
        tk.Label(inner_right, text="There is a", bg=self.bg_color, font=self.ui_font).grid(row=1, column=0, sticky="w")
        self.chance_var = tk.StringVar(value="50")
        tk.Entry(inner_right, textvariable=self.chance_var, font=self.ui_font, width=5).grid(row=1, column=1, sticky="w")
        
        tk.Label(inner_right, text="% chance that", bg=self.bg_color, font=self.ui_font).grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 10))
        
        # [0] "to" [0]
        self.min_var = tk.StringVar(value="1")
        tk.Entry(inner_right, textvariable=self.min_var, font=self.ui_font, width=5).grid(row=3, column=0, sticky="w")
        
        tk.Label(inner_right, text="to", bg=self.bg_color, font=self.ui_font).grid(row=3, column=1, sticky="w")
        
        self.max_var = tk.StringVar(value="1")
        tk.Entry(inner_right, textvariable=self.max_var, font=self.ui_font, width=5).grid(row=3, column=2, sticky="w", padx=(0, 5))
        
        # Larger Empty Entry
        tk.Label(inner_right, text="Spec (Family,Type,SubID):", bg=self.bg_color, font=self.ui_font).grid(row=4, column=0, columnspan=3, sticky="w", pady=(10, 0))
        self.item_type_var = tk.StringVar(value="1,1,1")
        tk.Entry(inner_right, textvariable=self.item_type_var, font=self.ui_font, width=25).grid(row=5, column=0, columnspan=3, sticky="w", pady=(2, 10))
        
        # Update Item button
        tk.Button(inner_right, text="Apply Changes", font=self.ui_font, command=self._update_item_properties).grid(row=6, column=0, columnspan=3, sticky="ew")
        
        # -------------------------------------------------------------
        # BOTTOM BUTTONS
        # -------------------------------------------------------------
        bottom_frame = tk.Frame(self.win, bg=self.bg_color)
        bottom_frame.pack(fill="x", side="bottom", padx=10, pady=10)
        
        tk.Button(bottom_frame, text="OK", width=12, font=self.ui_font, command=self._on_ok).pack(side="left")
        tk.Button(bottom_frame, text="Cancel", width=12, font=self.ui_font, command=self.win.destroy).pack(side="right")
        
    def load_loot_tables(self):
        self.loot_tables = {}
        path = os.path.join(self.save_manager.project_path, "Maps", "LootTables.json")
        if os.path.exists(path):
            try:
                import json
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.loot_tables = data.get("loot_tables", {})
            except Exception as e:
                print(f"Error loading loot tables: {e}")
        if not self.loot_tables:
            self.loot_tables = {
                "Default": [
                    {"chance": 50, "min_qty": 1, "max_qty": 1, "family": 1, "item_type": 1, "item_id": 1}
                ]
            }
        self._refresh_tables_list()
        
    def _refresh_tables_list(self):
        self.table_list.delete(0, tk.END)
        for name in sorted(self.loot_tables.keys()):
            self.table_list.insert(tk.END, name)
            
        # Select active table
        if self.active_table in self.loot_tables:
            idx = sorted(self.loot_tables.keys()).index(self.active_table)
            self.table_list.selection_set(idx)
            self._load_active_table_items()
            
    def _load_active_table_items(self):
        self.item_list.delete(0, tk.END)
        items = self.loot_tables.get(self.active_table, [])
        for idx, item in enumerate(items):
            spec = f"{item.get('family', 1)},{item.get('item_type', 1)},{item.get('item_id', 1)}"
            self.item_list.insert(tk.END, f"[{idx}] Chance: {item.get('chance', 50)}% ({spec})")
            
        self.name_var.set(self.active_table)
        self._clear_item_properties_ui()
        
    def _on_table_select(self, event=None):
        sel = self.table_list.curselection()
        if not sel: return
        self.active_table = self.table_list.get(sel[0])
        self.active_item_idx = None
        self._load_active_table_items()
        
    def _on_item_select(self, event=None):
        sel = self.item_list.curselection()
        if not sel: return
        self.active_item_idx = sel[0]
        item = self.loot_tables[self.active_table][self.active_item_idx]
        
        self.chance_var.set(str(item.get("chance", 50)))
        self.min_var.set(str(item.get("min_qty", 1)))
        self.max_var.set(str(item.get("max_qty", 1)))
        spec = f"{item.get('family', 1)},{item.get('item_type', 1)},{item.get('item_id', 1)}"
        self.item_type_var.set(spec)
        
    def _clear_item_properties_ui(self):
        self.chance_var.set("50")
        self.min_var.set("1")
        self.max_var.set("1")
        self.item_type_var.set("1,1,1")
        self.active_item_idx = None
        
    def _add_table(self):
        name = tk.simpledialog.askstring("New Table", "Enter Loot Table Name:")
        if name:
            clean_name = name.strip()
            if clean_name in self.loot_tables:
                messagebox.showwarning("Warning", "Table already exists!")
                return
            self.loot_tables[clean_name] = []
            self.active_table = clean_name
            self.active_item_idx = None
            self._refresh_tables_list()
            
    def _del_table(self):
        if self.active_table == "Default":
            messagebox.showwarning("Warning", "Cannot delete the Default table!")
            return
        if messagebox.askyesno("Confirm Delete", f"Delete table {self.active_table}?"):
            self.loot_tables.pop(self.active_table, None)
            self.active_table = "Default"
            self.active_item_idx = None
            self._refresh_tables_list()
            
    def _add_item(self):
        if self.active_table not in self.loot_tables: return
        new_item = {"chance": 50, "min_qty": 1, "max_qty": 1, "family": 1, "item_type": 1, "item_id": 1}
        self.loot_tables[self.active_table].append(new_item)
        self._load_active_table_items()
        
    def _del_item(self):
        if self.active_item_idx is None: return
        del self.loot_tables[self.active_table][self.active_item_idx]
        self._load_active_table_items()
        
    def _update_item_properties(self):
        if self.active_item_idx is None: return
        try:
            chance = int(self.chance_var.get())
            min_q = int(self.min_var.get())
            max_q = int(self.max_var.get())
            parts = [int(x.strip()) for x in self.item_type_var.get().split(",")]
            if len(parts) < 3:
                raise ValueError("Specification must be 3 numbers (Family,Type,SubID)")
                
            self.loot_tables[self.active_table][self.active_item_idx] = {
                "chance": chance,
                "min_qty": min_q,
                "max_qty": max_q,
                "family": parts[0],
                "item_type": parts[1],
                "item_id": parts[2]
            }
            self._load_active_table_items()
            messagebox.showinfo("Success", "Loot item properties updated.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply: {e}")
            
    def _on_ok(self):
        self.save_loot_tables()
        self.save_manager.mark_dirty()
        self.win.destroy()
        
    def save_loot_tables(self):
        path = os.path.join(self.save_manager.project_path, "Maps", "LootTables.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            import json
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"loot_tables": self.loot_tables}, f, indent=4)
            print(f"[DEBUG] Saved loot tables to {path}")
        except Exception as e:
            print(f"[ERROR] Failed to save loot tables: {e}")
