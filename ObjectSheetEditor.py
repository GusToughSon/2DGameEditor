import tkinter as tk
from tkinter import messagebox, ttk
import os
import json
from EditorComponents import center_window

class ObjectSheetEditor:
    """
    Object Types Configuration Editor (Win95 Style).
    Handles object type definitions (chests, doors, signs) saved in Maps/ObjectTypes.json.
    """
    def __init__(self, parent, save_manager=None):
        self.parent = parent
        self.save_manager = save_manager
        
        self.win = tk.Toplevel(parent)
        self.win.title("Object Type Definition Editor")
        
        center_window(self.win, parent, 600, 450)
        self.win.configure(bg="#dfdfdf")
        self.win.resizable(False, False)
        
        self.win.transient(parent)
        self.win.grab_set()
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)
        
        self.ui_font = ("MS Sans Serif", 8)
        self.title_font = ("MS Sans Serif", 8, "bold")
        
        self.object_types = {}
        self.load_object_types()
        
        self.setup_ui()
        
    def load_object_types(self):
        if not self.save_manager or not self.save_manager.project_path:
            return
        path = os.path.join(self.save_manager.project_path, "Maps", "ObjectTypes.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Convert keys to integers
                    self.object_types = {int(k): v for k, v in data.items()}
            except Exception as e:
                print(f"[ERROR] Failed to load ObjectTypes.json: {e}")
        else:
            # Populate defaults if file doesn't exist
            self.object_types = {
                1858: {"name": "Wooden Door", "openable": True, "block": True, "vis_block": True, "use_type": 0, "animated": False},
                640: {"name": "Wooden Sign", "openable": False, "block": True, "vis_block": False, "use_type": 0, "animated": False}
            }

    def save_object_types(self):
        if not self.save_manager or not self.save_manager.project_path:
            return
        os.makedirs(os.path.join(self.save_manager.project_path, "Maps"), exist_ok=True)
        path = os.path.join(self.save_manager.project_path, "Maps", "ObjectTypes.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.object_types, f, indent=4)
            if self.save_manager:
                self.save_manager.mark_dirty()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save object types: {e}")

    def setup_ui(self):
        main_frame = tk.Frame(self.win, bg="#dfdfdf", padx=10, pady=10)
        main_frame.pack(fill="both", expand=True)

        # Left Column: Listbox
        left_frame = tk.Frame(main_frame, bg="#dfdfdf")
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        tk.Label(left_frame, text="Configured Object Types:", bg="#dfdfdf", font=self.title_font).pack(anchor="w", pady=(0, 5))
        
        list_container = tk.Frame(left_frame)
        list_container.pack(fill="both", expand=True)

        self.listbox = tk.Listbox(list_container, font=self.ui_font, selectbackground="#0000A0")
        self.listbox.pack(side="left", fill="both", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)
        
        sb = tk.Scrollbar(list_container, command=self.listbox.yview)
        sb.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=sb.set)

        self.refresh_listbox()

        btn_f_left = tk.Frame(left_frame, bg="#dfdfdf", pady=5)
        btn_f_left.pack(fill="x")
        tk.Button(btn_f_left, text="Delete Selected", command=self.delete_type, bg="#C0C0C0", font=self.ui_font).pack(fill="x")

        # Right Column: Editor Details
        right_frame = tk.LabelFrame(main_frame, text="Object Details", bg="#dfdfdf", font=self.title_font, padx=10, pady=10)
        right_frame.pack(side="right", fill="both", padx=(10, 0))

        # Inputs
        self.id_var = tk.StringVar(value="0")
        lf_id = tk.Frame(right_frame, bg="#dfdfdf")
        lf_id.pack(fill="x", pady=2)
        tk.Label(lf_id, text="Type ID:", bg="#dfdfdf", font=self.ui_font).pack(side="left")
        self.id_entry = tk.Entry(lf_id, textvariable=self.id_var, width=10, relief="sunken", bd=2)
        self.id_entry.pack(side="right", padx=5)

        self.name_var = tk.StringVar(value="")
        lf_name = tk.Frame(right_frame, bg="#dfdfdf")
        lf_name.pack(fill="x", pady=2)
        tk.Label(lf_name, text="Name:", bg="#dfdfdf", font=self.ui_font).pack(side="left")
        tk.Entry(lf_name, textvariable=self.name_var, width=18, relief="sunken", bd=2).pack(side="right", padx=5)

        # Dropdown
        lf_ut = tk.Frame(right_frame, bg="#dfdfdf")
        lf_ut.pack(fill="x", pady=2)
        tk.Label(lf_ut, text="Use Type:", bg="#dfdfdf", font=self.ui_font).pack(side="left")
        self.use_type_var = tk.StringVar(value="NONE")
        use_types = ["NONE", "MINE", "SMELT", "FORGE", "BOOST", "REPAIR", "TELEPORT", "TELEP_AND_SPAWN", "SPAWN_GATE"]
        self.use_type_select = ttk.Combobox(lf_ut, values=use_types, textvariable=self.use_type_var, state="readonly", width=15)
        self.use_type_select.pack(side="right", padx=5)

        # Checks
        flags_group = tk.LabelFrame(right_frame, text="Properties", bg="#dfdfdf", font=self.ui_font, padx=10, pady=5)
        flags_group.pack(fill="x", pady=10)

        self.openable = tk.BooleanVar()
        self.block = tk.BooleanVar(value=True)
        self.vis_block = tk.BooleanVar()
        self.animated = tk.BooleanVar()

        tk.Checkbutton(flags_group, text="Openable", variable=self.openable, bg="#dfdfdf", font=self.ui_font).pack(anchor="w")
        tk.Checkbutton(flags_group, text="Block Movement", variable=self.block, bg="#dfdfdf", font=self.ui_font).pack(anchor="w")
        tk.Checkbutton(flags_group, text="Block Visibility", variable=self.vis_block, bg="#dfdfdf", font=self.ui_font).pack(anchor="w")
        tk.Checkbutton(flags_group, text="Animated", variable=self.animated, bg="#dfdfdf", font=self.ui_font).pack(anchor="w")

        tk.Button(right_frame, text="Add/Update Type", command=self.apply, bg="#C0C0C0", width=15, relief="raised", bd=2, font=self.ui_font).pack(pady=10)
        tk.Button(right_frame, text="Close", command=self._on_close, bg="#C0C0C0", width=15, relief="raised", bd=2, font=self.ui_font).pack(pady=5)

    def refresh_listbox(self):
        self.listbox.delete(0, "end")
        for tid in sorted(self.object_types.keys()):
            o = self.object_types[tid]
            self.listbox.insert("end", f"{tid}: {o.get('name', 'Object')}")

    def _on_select(self, event):
        sel = self.listbox.curselection()
        if not sel: return
        line = self.listbox.get(sel[0])
        try:
            tid = int(line.split(":")[0])
            o = self.object_types[tid]
            self.id_var.set(str(tid))
            self.name_var.set(o.get("name", ""))
            self.openable.set(o.get("openable", False))
            self.block.set(o.get("block", False))
            self.vis_block.set(o.get("vis_block", False))
            self.animated.set(o.get("animated", False))
            
            # Use type
            ut_idx = o.get("use_type", 0)
            ut_list = ["NONE", "MINE", "SMELT", "FORGE", "BOOST", "REPAIR", "TELEPORT", "TELEP_AND_SPAWN", "SPAWN_GATE"]
            self.use_type_var.set(ut_list[ut_idx] if 0 <= ut_idx < len(ut_list) else "NONE")
            
            # Disable ID entry when modifying
            self.id_entry.config(state="disabled")
        except Exception as e:
            print(f"Error selecting: {e}")

    def apply(self):
        try:
            # Enable ID entry temporarily to read it
            self.id_entry.config(state="normal")
            tid = int(self.id_var.get() or 0)
            name = self.name_var.get().strip()
            
            if tid <= 0 or not name:
                messagebox.showerror("Error", "Please provide a valid Type ID and Name.")
                return
                
            ut_list = ["NONE", "MINE", "SMELT", "FORGE", "BOOST", "REPAIR", "TELEPORT", "TELEP_AND_SPAWN", "SPAWN_GATE"]
            use_type_val = ut_list.index(self.use_type_var.get()) if self.use_type_var.get() in ut_list else 0

            self.object_types[tid] = {
                "name": name,
                "openable": self.openable.get(),
                "block": self.block.get(),
                "vis_block": self.vis_block.get(),
                "use_type": use_type_val,
                "animated": self.animated.get()
            }
            
            self.save_object_types()
            self.refresh_listbox()
            
            # Reset inputs
            self.id_var.set("0")
            self.name_var.set("")
            self.openable.set(False)
            self.block.set(True)
            self.vis_block.set(False)
            self.animated.set(False)
            self.use_type_var.set("NONE")
            self.id_entry.config(state="normal")
            
            messagebox.showinfo("Success", "Object Type registered successfully.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_type(self):
        sel = self.listbox.curselection()
        if not sel: return
        line = self.listbox.get(sel[0])
        try:
            tid = int(line.split(":")[0])
            if tid in self.object_types:
                del self.object_types[tid]
                self.save_object_types()
                self.refresh_listbox()
                
                # Reset inputs
                self.id_var.set("0")
                self.name_var.set("")
                self.openable.set(False)
                self.block.set(True)
                self.vis_block.set(False)
                self.animated.set(False)
                self.use_type_var.set("NONE")
                self.id_entry.config(state="normal")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete: {e}")

    def _on_close(self):
        if self.parent and self.parent.winfo_exists():
            self.parent.lift(); self.parent.focus_set()
        self.win.destroy()
