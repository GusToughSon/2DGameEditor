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
        
        self.setup_ui()
        
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
        
        # Populate Default list and select it
        self.table_list.insert(tk.END, "Default")
        self.table_list.selection_set(0)
        
        btn_frame_left = tk.Frame(left_frame, bg=self.bg_color)
        btn_frame_left.pack(fill="x", pady=(5, 0))
        
        tk.Button(btn_frame_left, text="Add Spawn", font=self.ui_font, width=12).pack(side="left", padx=(0, 2))
        tk.Button(btn_frame_left, text="Del Spawn", font=self.ui_font, width=12).pack(side="right", padx=(2, 0))
        
        # -------------------------------------------------------------
        # RIGHT PANEL
        # -------------------------------------------------------------
        right_frame = tk.LabelFrame(main_frame, text="Loot Table Properties", bg=self.bg_color, font=self.ui_font)
        right_frame.pack(side="left", fill="both", expand=True)
        
        # Inner splits for the right frame: left side is list+buttons, right is props
        inner_left = tk.Frame(right_frame, bg=self.bg_color)
        inner_left.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        # Large blank white area (could be a Listbox)
        self.item_list = tk.Listbox(inner_left, font=self.ui_font, bg="white")
        self.item_list.pack(fill="both", expand=True)
        
        # Item action buttons vertically aligned
        btn_frame_inner = tk.Frame(inner_left, bg=self.bg_color)
        btn_frame_inner.pack(fill="x", pady=(5, 0))
        tk.Button(btn_frame_inner, text="Add Item", font=self.ui_font, width=10).pack(pady=2)
        tk.Button(btn_frame_inner, text="Del Item", font=self.ui_font, width=10).pack(pady=2)
        
        # Right side properties
        inner_right = tk.Frame(right_frame, bg=self.bg_color)
        inner_right.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)
        
        # Name Entry
        self.name_var = tk.StringVar(value="Default")
        tk.Entry(inner_right, textvariable=self.name_var, font=self.ui_font, width=20).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        
        # "There is a" [0] "% chance that"
        tk.Label(inner_right, text="There is a", bg=self.bg_color, font=self.ui_font).grid(row=1, column=0, sticky="w")
        self.chance_var = tk.StringVar(value="0")
        tk.Entry(inner_right, textvariable=self.chance_var, font=self.ui_font, width=5).grid(row=1, column=1, sticky="w")
        
        tk.Label(inner_right, text="% chance that", bg=self.bg_color, font=self.ui_font).grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 10))
        
        # [0] "to" [0]
        self.min_var = tk.StringVar(value="0")
        tk.Entry(inner_right, textvariable=self.min_var, font=self.ui_font, width=5).grid(row=3, column=0, sticky="w")
        
        tk.Label(inner_right, text="to", bg=self.bg_color, font=self.ui_font).grid(row=3, column=1, sticky="w")
        
        self.max_var = tk.StringVar(value="0")
        tk.Entry(inner_right, textvariable=self.max_var, font=self.ui_font, width=5).grid(row=3, column=2, sticky="w", padx=(0, 5))
        
        # Larger Empty Entry
        self.item_type_var = tk.StringVar()
        tk.Entry(inner_right, textvariable=self.item_type_var, font=self.ui_font, width=25).grid(row=4, column=0, columnspan=3, sticky="w", pady=(10, 0))
        
        # -------------------------------------------------------------
        # BOTTOM BUTTONS
        # -------------------------------------------------------------
        bottom_frame = tk.Frame(self.win, bg=self.bg_color)
        bottom_frame.pack(fill="x", side="bottom", padx=10, pady=10)
        
        tk.Button(bottom_frame, text="OK", width=12, font=self.ui_font, command=self._on_ok).pack(side="left")
        tk.Button(bottom_frame, text="Cancel", width=12, font=self.ui_font, command=self.win.destroy).pack(side="right")
        
    def _on_ok(self):
        """ Closes visually, ready for saving mechanics later. """
        self.win.destroy()
