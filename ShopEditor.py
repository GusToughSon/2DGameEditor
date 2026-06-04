import tkinter as tk
from tkinter import ttk, messagebox
import os
import ScriptParser
from EditorComponents import center_window

class ShopEditor:
    """
    Classic Windows 95 Style Shop Editor.
    Manages Shops.hry for merchant databases.
    """
    def __init__(self, parent, save_manager, main_app=None):
        self.parent = parent
        self.save_manager = save_manager
        self.main_app = main_app
        self.project_path = save_manager.project_path
        
        # --- DATA ---
        self.shops_data = ScriptParser.parse_shops_hry(self.project_path)
        self.all_types = ScriptParser.parse_types_use_sync(os.path.join(self.project_path, "HAIRY", "Types.hry"))
        
        # UI State
        self.current_shop_name = tk.StringVar()
        self.filter_vars = {
            "Weapons": tk.BooleanVar(value=True),
            "Armour": tk.BooleanVar(value=True),
            "Useables": tk.BooleanVar(value=True)
        }
        self.on_buy_var = tk.StringVar()
        self.on_sell_var = tk.StringVar()
        
        # --- WINDOW SETUP ---
        self.win = tk.Toplevel(parent)
        self.win.title("Shop Editor")
        center_window(self.win, parent, 650, 500)
        self.win.configure(bg="#C0C0C0") # Win95 Gray
        self.ui_font = ("Tahoma", 8)
        self.title_font = ("Tahoma", 8, "bold")
        
        self.setup_layout()
        self.refresh_shop_list()
        
        if self.shops_data:
            first_shop = sorted(self.shops_data.keys())[0]
            self.shop_dropdown.set(first_shop)
            self._on_shop_select(first_shop)

    def setup_layout(self):
        # --- TOP GROUP (Shop:) ---
        top_f = tk.LabelFrame(self.win, text="Shop:", bg="#C0C0C0", font=self.title_font, padx=5, pady=5)
        top_f.pack(fill="x", padx=10, pady=5)
        
        self.shop_dropdown = ttk.Combobox(top_f, textvariable=self.current_shop_name, state="readonly")
        self.shop_dropdown.pack(side="left", fill="x", expand=True, padx=5)
        self.shop_dropdown.bind("<<ComboboxSelected>>", lambda e: self._on_shop_select(self.current_shop_name.get()))
        
        tk.Button(top_f, text="New", command=self._add_shop, bg="#C0C0C0", font=self.ui_font, width=8).pack(side="left", padx=2)
        tk.Button(top_f, text="Delete", command=self._delete_shop, bg="#C0C0C0", font=self.ui_font, width=8).pack(side="left", padx=2)
        
        # --- MIDDLE SECTION (Listboxes) ---
        mid_f = tk.Frame(self.win, bg="#C0C0C0")
        mid_f.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Left List: Item List
        left_f = tk.Frame(mid_f, bg="#C0C0C0")
        left_f.pack(side="left", fill="both", expand=True)
        tk.Label(left_f, text="Item List", bg="#C0C0C0", font=self.ui_font).pack(anchor="w")
        self.item_listbox = tk.Listbox(left_f, font=self.ui_font, selectmode="multiple")
        self.item_listbox.pack(fill="both", expand=True)
        
        # Middle Buttons
        btn_f = tk.Frame(mid_f, bg="#C0C0C0")
        btn_f.pack(side="left", padx=10)
        tk.Button(btn_f, text=">>", command=self._add_to_shop, bg="#C0C0C0", font=self.title_font, width=4).pack(pady=5)
        tk.Button(btn_f, text="<<", command=self._remove_from_shop, bg="#C0C0C0", font=self.title_font, width=4).pack(pady=5)
        
        # Right List: Items To Sell/Buy
        right_f = tk.Frame(mid_f, bg="#C0C0C0")
        right_f.pack(side="left", fill="both", expand=True)
        tk.Label(right_f, text="Item's To Sell/Buy", bg="#C0C0C0", font=self.ui_font).pack(anchor="w")
        self.shop_listbox = tk.Listbox(right_f, font=self.ui_font, selectmode="single")
        self.shop_listbox.pack(fill="both", expand=True)
        self.shop_listbox.bind("<Double-Button-1>", lambda e: self._edit_item_price())

        # --- BOTTOM SECTION ---
        bot_f = tk.Frame(self.win, bg="#C0C0C0")
        bot_f.pack(fill="x", padx=10, pady=5)
        
        # Bottom Left: Parameters
        param_f = tk.LabelFrame(bot_f, text="Object List Parameters", bg="#C0C0C0", font=self.title_font, padx=5, pady=5)
        param_f.pack(side="left", fill="y")
        for text, var in self.filter_vars.items():
            tk.Checkbutton(param_f, text=text, variable=var, bg="#C0C0C0", font=self.ui_font, command=self.refresh_item_list).pack(anchor="w")
            
        # Bottom Right: Callbacks
        call_f = tk.LabelFrame(bot_f, text="Usecase Callbacks", bg="#C0C0C0", font=self.title_font, padx=5, pady=5)
        call_f.pack(side="right", fill="both", expand=True, padx=(10, 0))
        
        tk.Label(call_f, text="OnBuy:", bg="#C0C0C0", font=self.ui_font).grid(row=0, column=0, sticky="w")
        tk.Entry(call_f, textvariable=self.on_buy_var, font=self.ui_font).grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        
        tk.Label(call_f, text="OnSell:", bg="#C0C0C0", font=self.ui_font).grid(row=1, column=0, sticky="w")
        tk.Entry(call_f, textvariable=self.on_sell_var, font=self.ui_font).grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        call_f.columnconfigure(1, weight=1)
        
        # --- FINAL BUTTONS ---
        btn_bar = tk.Frame(self.win, bg="#C0C0C0", padx=10, pady=10)
        btn_bar.pack(fill="x", side="bottom")
        tk.Button(btn_bar, text="OK", command=self._on_ok, width=10, bg="#C0C0C0").pack(side="left")
        tk.Button(btn_bar, text="Cancel", command=self.win.destroy, width=10, bg="#C0C0C0").pack(side="right")

        self.refresh_item_list()

    def refresh_shop_list(self):
        names = sorted(self.shops_data.keys())
        self.shop_dropdown['values'] = names

    def refresh_item_list(self):
        self.item_listbox.delete(0, tk.END)
        self.available_items = [] # Stores Type IDs
        
        # 1. Start with the Master Item Families from Defines.hry
        # This is now a project-wide global setting.
        allowed_fams = ScriptParser.get_shop_item_families(self.project_path)
        
        # 2. Apply UI Checkbox Filtering (Sub-set of the Master Families)
        # Note: If the user unchecks everything, we show nothing.
        ui_filter = []
        if self.filter_vars["Weapons"].get(): ui_filter.append("FAM_WEAPON")
        if self.filter_vars["Armour"].get():  ui_filter.append("FAM_ARMOR")
        if self.filter_vars["Useables"].get(): 
             ui_filter.extend(["FAM_CONSUMABLE", "FAM_OBJ"])
            
        for tid, data in sorted(self.all_types.items(), key=lambda x: x[1]['name']):
            fam = data.get("family")
            # Must be in the MASTER list AND pass the UI toggle
            if fam in allowed_fams and fam in ui_filter:
                name = data.get("name", "Unknown")
                self.item_listbox.insert(tk.END, name)
                self.available_items.append(tid)

    def _on_shop_select(self, name):
        self.shop_listbox.delete(0, tk.END)
        if name not in self.shops_data: return
        
        data = self.shops_data[name]
        self.on_buy_var.set(data.get("on_buy", ""))
        self.on_sell_var.set(data.get("on_sell", ""))
        
        for item in data.get("items", []):
            # Resolve name from type ID constant
            pretty_name = item["type"]
            self.shop_listbox.insert(tk.END, f"{pretty_name} (${item['price']}) [Stock: {item['stock']}]")

    def _add_shop(self):
        new_name = tk.simpledialog.askstring("New Shop", "Enter Shop Name:")
        if new_name:
            if new_name in self.shops_data:
                messagebox.showerror("Error", "Shop already exists.")
                return
            self.shops_data[new_name] = {"on_buy": "", "on_sell": "", "items": []}
            self.refresh_shop_list()
            self.shop_dropdown.set(new_name)
            self._on_shop_select(new_name)

    def _delete_shop(self):
        name = self.current_shop_name.get()
        if name and messagebox.askyesno("Delete", f"Delete shop '{name}'?"):
            del self.shops_data[name]
            self.refresh_shop_list()
            self.item_listbox.delete(0, tk.END)
            self.shop_listbox.delete(0, tk.END)
            self.current_shop_name.set("")

    def _add_to_shop(self):
        shop_name = self.current_shop_name.get()
        if not shop_name: return
        
        selected_indices = self.item_listbox.curselection()
        for idx in selected_indices:
            tid = self.available_items[idx]
            # Convert tid to TYPE_ constant name
            type_data = self.all_types.get(tid)
            if not type_data: continue
            
            # Simple sanitization to match constant generation
            safe_name = type_data['name'].replace(" ", "_").upper()
            const_name = f"TYPE_{type_data['family']}_{safe_name}"
            
            # Add with defaults
            self.shops_data[shop_name]["items"].append({
                "type": const_name,
                "price": 0,
                "stock": -1
            })
            
        self._on_shop_select(shop_name)

    def _remove_from_shop(self):
        shop_name = self.current_shop_name.get()
        idx = self.shop_listbox.curselection()
        if not shop_name or not idx: return
        
        del self.shops_data[shop_name]["items"][idx[0]]
        self._on_shop_select(shop_name)

    def _edit_item_price(self):
        shop_name = self.current_shop_name.get()
        indices = self.shop_listbox.curselection()
        if not shop_name or not indices: return
        
        idx = indices[0]
        item = self.shops_data[shop_name]["items"][idx]
        
        new_price = tk.simpledialog.askinteger("Edit Price", f"Enter price for {item['type']}:", initialvalue=item['price'])
        if new_price is not None:
            item['price'] = new_price
        
        new_stock = tk.simpledialog.askinteger("Edit Stock", "Enter stock (-1 for infinite):", initialvalue=item['stock'])
        if new_stock is not None:
            item['stock'] = new_stock
            
        self._on_shop_select(shop_name)

    def _on_ok(self):
        # Sync current shop callbacks before saving
        name = self.current_shop_name.get()
        if name in self.shops_data:
            self.shops_data[name]["on_buy"] = self.on_buy_var.get()
            self.shops_data[name]["on_sell"] = self.on_sell_var.get()
            
        if ScriptParser.save_shops_hry(self.project_path, self.shops_data):
            if self.main_app:
                self.main_app.save_project(prompt=False)
            self.win.destroy()
        else:
            messagebox.showerror("Error", "Failed to save Shops.hry")

