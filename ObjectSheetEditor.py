import tkinter as tk
from tkinter import messagebox
import os
import config
from EditorComponents import center_window

class ObjectSheetEditor:
    """
    ObjectSheet Editor (Win95 Style).
    Handles bulk object metadata and spreadsheet-style editing.
    """
    def __init__(self, parent, save_manager=None):
        self.parent = parent
        self.save_manager = save_manager
        
        self.win = tk.Toplevel(parent)
        self.win.title("ObjectSheet Editor")
        
        # Standardized Centering
        center_window(self.win, parent, 800, 500)
        
        self.win.configure(bg=config.COLOR_BG)
        self.win.resizable(False, False)
        
        # Focus management
        self.win.transient(parent)
        self.win.grab_set()
        
        self.setup_ui()

    def setup_ui(self):
        # Header
        header = tk.Frame(self.win, bg=config.COLOR_TITLE_BAR, padx=10, pady=5)
        header.pack(fill="x")
        tk.Label(header, text="Global Object Metadata Sheet", fg=config.COLOR_TITLE_TEXT, 
                 bg=config.COLOR_TITLE_BAR, font=config.FONT_TITLE).pack(side="left")

        # Placeholder Content
        content = tk.Frame(self.win, bg=config.COLOR_BG, padx=20, pady=20)
        content.pack(fill="both", expand=True)

        tk.Label(content, text="[Spreadsheet Object Interface - Coming Soon]", 
                 bg=config.COLOR_BG, font=config.FONT_UI).pack(pady=50)

        # Action Bar
        btn_f = tk.Frame(self.win, bg=config.COLOR_BG, pady=10)
        btn_f.pack(fill="x", side="bottom")
        
        tk.Button(btn_f, text="Save", width=12, bg=config.COLOR_BG, relief="raised", bd=2,
                  command=self.win.destroy).pack(side="right", padx=10)
        tk.Button(btn_f, text="Cancel", width=12, bg=config.COLOR_BG, relief="raised", bd=2,
                  command=self.win.destroy).pack(side="right")
