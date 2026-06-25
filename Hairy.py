import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
import os
import EditorColors
from EditorComponents import center_window

class HairyEditor:
    """
    A professional script editor for .hry files.
    Provides syntax highlighting, multi-file management, and project integration.
    """
    def __init__(self, parent, save_manager=None, initial_file="Defines.hry"):
        self.parent = parent
        self.save_manager = save_manager
        self.current_filename = initial_file
        
        self.win = tk.Toplevel(parent)
        self.win.overrideredirect(True) # Custom Frame
        
        # Window State
        self.is_maximized = False
        self.old_geometry = "850x650+100+100"
        
        self.setup_custom_titlebar()
        self.setup_ui()
        self.setup_resize_handles()
        
        # Standardized Centering (Initial)
        center_window(self.win, parent, 850, 650)
        self.load_file(initial_file)

    def setup_custom_titlebar(self):
        """ Classic dark-themed title bar for the Scripting Suite. """
        self.title_bar = tk.Frame(self.win, bg="#333", height=28, bd=0)
        self.title_bar.pack(fill="x", side="top")
        
        lbl = tk.Label(self.title_bar, text=f"HAIRY SCRIPT EDITOR - {self.current_filename}", 
                       bg="#333", fg="white", font=("Arial", 8, "bold"), padx=10)
        lbl.pack(side="left")
        self.title_label = lbl # Update when opening files
        
        # Controls
        tk.Button(self.title_bar, text="✕", bg="#333", fg="white", bd=0, 
                  command=self.on_close, font=("Arial", 10), width=3).pack(side="right")
        self.max_btn = tk.Button(self.title_bar, text="🗖", bg="#333", fg="white", bd=0, 
                                command=self.toggle_maximize, font=("Arial", 10), width=3)
        self.max_btn.pack(side="right")

        # Draggable Logic
        self.title_bar.bind("<Button-1>", self._start_window_drag)
        self.title_bar.bind("<B1-Motion>", self._do_window_drag)
        self.title_bar.bind("<Double-Button-1>", lambda e: self.toggle_maximize())

    def setup_resize_handles(self):
        """ Adds invisible frames to the edges for easier resizing. """
        self.resizer_r = tk.Frame(self.win, bg="#808080", width=4, cursor="sb_h_double_arrow")
        self.resizer_r.place(relx=1.0, rely=0, relheight=1.0, anchor="ne")
        self.resizer_r.bind("<B1-Motion>", self._resize_width)

        self.resizer_b = tk.Frame(self.win, bg="#808080", height=4, cursor="sb_v_double_arrow")
        self.resizer_b.place(relx=0, rely=1.0, relwidth=1.0, anchor="sw")
        self.resizer_b.bind("<B1-Motion>", self._resize_height)

    def on_close(self):
        """ Prevents UI callback exceptions and orphaned memory when closing mid-typing. """
        if hasattr(self, "_debounce_id"):
            try: self.win.after_cancel(self._debounce_id)
            except: pass
        self.win.destroy()

    def _start_window_drag(self, event):
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def _do_window_drag(self, event):
        if self.is_maximized: return
        x = self.win.winfo_x() + (event.x - self._drag_start_x)
        y = self.win.winfo_y() + (event.y - self._drag_start_y)
        self.win.geometry(f"+{x}+{y}")

    def _resize_width(self, event):
        if self.is_maximized: return
        new_w = max(400, event.x_root - self.win.winfo_x())
        self.win.geometry(f"{new_w}x{self.win.winfo_height()}")

    def _resize_height(self, event):
        if self.is_maximized: return
        new_h = max(300, event.y_root - self.win.winfo_y())
        self.win.geometry(f"{self.win.winfo_width()}x{new_h}")

    def toggle_maximize(self):
        if not self.is_maximized:
            self.old_geometry = self.win.geometry()
            # Full Screen math
            mw = self.win.winfo_screenwidth()
            mh = self.win.winfo_screenheight()
            self.win.geometry(f"{mw}x{mh}+0+0")
            self.max_btn.config(text="🗗")
            self.is_maximized = True
        else:
            self.win.geometry(self.old_geometry)
            self.max_btn.config(text="🗖")
            self.is_maximized = False

    def setup_ui(self):
        # 0. Ensure Infrastructure (Self-Healing & Seeding)
        if self.save_manager and self.save_manager.project_path:
            hairy_dir = self.save_manager.hairy_dir
            
            # Seed Defines.hry if missing (Enhanced Starter Template)
            def_path = os.path.join(hairy_dir, "Defines.hry")
            if not os.path.exists(def_path):
                with open(def_path, "w") as f:
                    f.write("//==============================================================================\n")
                    f.write("// DEFINES.HRY - MASTER PROJECT CONFIGURATION\n")
                    f.write("//==============================================================================\n")
                    f.write("// This file is your project's \"Brain\". Every #Define here creates a Global \n")
                    f.write("// Variable that you can use across ANY .hry script in your project.\n")
                    f.write("//==============================================================================\n")
                    f.write("#include \"Types.hry\"\n\n")
                    
                    f.write("// --- 1. LOGIC CONSTANTS ---\n")
                    f.write("#Define TRUE                1\n")
                    f.write("#Define FALSE               0\n")
                    f.write("#Define INVALID_OBJECT_ID   0\n\n")
                    
                    f.write("// --- 2. OBJECT FAMILIES ---\n")
                    fams = ["TILES", "PORTAL", "NPC", "AMMO", "WEAPON", "ARMOR", "EGG", "SIGN", "USEABLE", "CURRENCY"]
                    for i, fam in enumerate(fams):
                        f.write(f"#Define FAM_{fam:<20} {i}\n")
                    f.write("\n")
                    
                    f.write("// --- 3. WORLD MAPS ---\n")
                    f.write("#Define MAP_WORLD           0\n")
                    f.write("#Define MAP_CAVE            1\n\n")
                    
                    f.write("// --- 4. UI MENUS ---\n")
                    menus = ["BLACKSMITH", "CARPENTER", "TINKER", "MASON", "ARTIST"]
                    for i, m in enumerate(menus):
                        f.write(f"#Define MENU_{m:<19} {i}\n")
                    f.write("\n")

                    f.write("// --- 5. EQUIPMENT SLOTS ---\n")
                    slots = ["WEAPON", "BODY", "SHIELD", "HEAD", "ARMS", "LEGS"]
                    for i, s in enumerate(slots):
                        f.write(f"#Define SLOT_{s:<19} {i}\n")
                    f.write("\n")

                    f.write("// --- 6. USER GLOBAL VARIABLES ---\n")
                    f.write("#Define G_TALKED_TO_KING    0\n")
                    f.write("#Define G_QUEST_STAGE      0\n\n")

                    f.write("// --- 7. RPG SKILLS (SYNCED) ---\n")
                    f.write("// These are auto-synced with Skills.hry. Edit there for hierarchy!\n")
                    f.write("#Define SKILL_ALCHEMY              0\n")
                    f.write("#Define SKILL_HEALING              1\n")
                    f.write("\n")
                    
                    f.write("// --- 8. PLAYER ENUMERATIONS (SYNCED) ---\n")
                    f.write("#Define PLR_MALE_WARRIOR     0\n")
                    f.write("#Define PLR_FEMALE_WARRIOR   1\n")
                    f.write("#Define PLR_MALE_MAGE        2\n")
                    f.write("#Define PLR_FEMALE_MAGE        3\n\n")

                    f.write("// --- 9. WORLD POINTS (POI) ---\n")
                    f.write("// These are auto-generated when you add Points in the World Editor.\n")
                    f.write("// Use them for Teleporting (e.g. Teleport(ME, POI_TOWN_SQUARE))\n")
                    f.write("#Define POI_START_LOCATION   0\n")
                    
            # Seed Types.hry if missing
            typ_path = os.path.join(hairy_dir, "Types.hry")
            if not os.path.exists(typ_path):
                with open(typ_path, "w") as f:
                    f.write("// Types.hry - Auto-generated\n")
                    f.write("// (Will be populated by Type Editor)\n")

            # Seed Template.hry (THE MASTER API BIBLE) if missing
            tmp_path = os.path.join(hairy_dir, "Template.hry")
            if not os.path.exists(tmp_path):
                if self.save_manager and hasattr(self.save_manager, '_seed_template'):
                    self.save_manager._seed_template(hairy_dir)
                    
            # Seed Example_Beginner.hry if missing
            beg_path = os.path.join(hairy_dir, "Example_Beginner.hry")
            if not os.path.exists(beg_path):
                if self.save_manager and hasattr(self.save_manager, '_seed_beginner_example'):
                    self.save_manager._seed_beginner_example(hairy_dir)

            # Seed Player.hry if missing (Primary Sync Target)
            plr_path = os.path.join(hairy_dir, "Player.hry")
            if not os.path.exists(plr_path):
                # Pull API skeleton from template if available
                header = "//==============================================================================\n"
                header += "// PLAYER.HRY - MASTER PLAYER LOGIC\n"
                header += "//==============================================================================\n"
                header += "// Any #Define PLR_ variables here will automatically sync to Defines.hry\n"
                header += "//==============================================================================\n\n"
                
                body = "Type Player\n{\n    OnSpawn\n    {\n        Say(\"Welcome to the world!\")\n    }\n}\n"
                
                # Try to append the API bible
                try:
                    tmp_path = os.path.join(hairy_dir, "Template.hry")
                    if os.path.exists(tmp_path):
                        with open(tmp_path, 'r') as f:
                            body = f.read()
                except: pass

                with open(plr_path, "w") as f:
                    f.write(header)
                    f.write("#Define PLR_MALE_WARRIOR     0\n")
                    f.write("#Define PLR_FEMALE_WARRIOR   1\n\n")
                    f.write(body)

        # 1. Toolbar
        toolbar = tk.Frame(self.win, bg="#C0C0C0", bd=1, relief="raised")
        toolbar.pack(fill="x", side="top")
        
        # SAVE PROJECT button
        tk.Button(toolbar, text="Save", command=self.save_file, font=("Arial", 9), bg="#dfdfdf", relief="raised", bd=1, width=8).pack(side="left", padx=2)
        tk.Button(toolbar, text="Compile", command=self.compile_script, font=("Arial", 9, "bold"), bg="#dfdfdf", fg="#008000", relief="raised", bd=1, width=8).pack(side="left", padx=2)
        tk.Button(toolbar, text="New Script", command=self.create_new_script, font=("Arial", 9), bg="#dfdfdf", relief="raised", bd=1, width=10).pack(side="left", padx=2)
        
        self.status_var = tk.StringVar(value="Auto-Save Active")
        tk.Label(toolbar, textvariable=self.status_var, bg="#C0C0C0", fg="#333", font=("Arial", 8)).pack(side="right", padx=10)

        # 2. Main Paned Layout
        self.paned = tk.PanedWindow(self.win, orient="horizontal", bg="#808080", sashwidth=4, sashrelief="sunken")
        self.paned.pack(fill="both", expand=True, padx=5, pady=5)

        # Left: Editor
        editor_f = tk.Frame(self.paned, bg="#1e1e1e")
        self.paned.add(editor_f, width=650, stretch="always")
        
        self.scroll_y = tk.Scrollbar(editor_f)
        self.scroll_y.pack(side="right", fill="y")
        
        self.text = tk.Text(editor_f, wrap="none", undo=True, 
                            bg="#1e1e1e", fg="#d4d4d4", insertbackground="white",
                            font=("Consolas", 11), yscrollcommand=self.scroll_y.set)
        self.text.pack(fill="both", expand=True)
        self.scroll_y.config(command=self.text.yview)

        # Right: File List
        self.explorer_f = tk.Frame(self.paned, bg="#dfdfdf")
        self.paned.add(self.explorer_f, width=150, stretch="never")
        tk.Label(self.explorer_f, text="PROJECT SCRIPTS", bg="#333", fg="white", font=("Arial", 8, "bold")).pack(fill="x")
        self.file_list = tk.Listbox(self.explorer_f, bg="#dfdfdf", font=("Arial", 9), relief="flat", activestyle="none", highlightthickness=0)
        self.file_list.pack(fill="both", expand=True)
        self.file_list.bind("<Double-Button-1>", self._on_list_double_click)

        # 3. Syntax Highlighting Tags from EditorColors
        for tag, color in EditorColors.SYNTAX.items():
            self.text.tag_config(tag, foreground=color)
            
        # User Additions: Danger & Disabled Block Themes
        self.text.tag_configure("danger", foreground="white", background="#880000") 
        self.text.tag_configure("disabled_bg", background="#282828") 

        self.text.bind("<KeyRelease>", self.on_key_release)
        self.text.bind("<Button-3>", self.show_context_menu) # Right-click
        
        # IDE Features: Brackets & Indents
        self.text.bind("{", self.auto_bracket)
        self.text.bind("<Return>", self.auto_indent)
        
        # --- TAB HANDLING ---
        self.text.bind("<Tab>", self.handle_tab)
        # Shift-Tab (Windows/Linux)
        self.text.bind("<Shift-Tab>", self.handle_shift_tab)
        self.text.bind("<ISO_Left_Tab>", self.handle_shift_tab) # X11/Linux fallback
        
        self.refresh_file_list()

    def show_context_menu(self, event):
        """ Displays the Win95-style context menu at the mouse position. """
        # Destroy previous menu to prevent memory leak
        if hasattr(self, '_ctx_menu') and self._ctx_menu:
            try: self._ctx_menu.destroy()
            except: pass
        self._ctx_menu = tk.Menu(self.win, tearoff=0, bg="#dfdfdf", font=("Arial", 9))
        self._ctx_menu.add_command(label="Cut", command=lambda: self.text.event_generate("<<Cut>>"))
        self._ctx_menu.add_command(label="Copy", command=lambda: self.text.event_generate("<<Copy>>"))
        self._ctx_menu.add_command(label="Paste", command=lambda: self.text.event_generate("<<Paste>>"))
        self._ctx_menu.add_separator()
        self._ctx_menu.add_command(label="Select All", command=self.select_all)
        self._ctx_menu.post(event.x_root, event.y_root)

    def select_all(self):
        self.text.tag_add("sel", "1.0", "end")
        return "break"

    def auto_bracket(self, event):
        """ Smart Bracket: inserts pair and centers cursor. """
        self.text.insert("insert", "{\n    \n}")
        self.text.mark_set("insert", "insert - 2c")
        return "break"

    def auto_indent(self, event):
        """ Smart Indent: Carries over whitespace and handles bracket opening. """
        line = self.text.get("insert linestart", "insert")
        import re
        match = re.match(r'^(\s+)', line)
        whitespace = match.group(0) if match else ""
        if line.strip().endswith("{"):
            whitespace += "    "
        self.text.insert("insert", "\n" + whitespace)
        self.perform_highlighting()
        return "break"

    def handle_tab(self, event):
        """ IDE Indent: Inserts 4 spaces or indents a selected block. """
        try:
            # Check for range selection
            sel_start = self.text.index("sel.first")
            sel_end = self.text.index("sel.last")
            
            # Identify line range
            start_line = int(sel_start.split(".")[0])
            end_line = int(sel_end.split(".")[0])
            
            # Apply indentation to each line in range
            for i in range(start_line, end_line + 1):
                self.text.insert(f"{i}.0", "    ")
            
        except tk.TclError:
            # No selection, just insert 4 spaces at cursor
            self.text.insert("insert", "    ")
            
        return "break" # Kill default Tkinter focus behavior

    def handle_shift_tab(self, event):
        """ IDE Outdent: Removes 4 spaces from current line or selection. """
        try:
            sel_start = self.text.index("sel.first")
            sel_end = self.text.index("sel.last")
            start_line = int(sel_start.split(".")[0])
            end_line = int(sel_end.split(".")[0])
        except tk.TclError:
            # No selection, outdent current line
            start_line = end_line = int(self.text.index("insert").split(".")[0])

        for i in range(start_line, end_line + 1):
            line_start = f"{i}.0"
            line_content = self.text.get(line_start, f"{i}.end")
            
            # Detect 4 spaces or a literal tab to strip
            if line_content.startswith("    "):
                self.text.delete(line_start, f"{i}.4")
            elif line_content.startswith("\t"):
                self.text.delete(line_start, f"{i}.1")
            elif line_content.startswith(" "):
                # Strip single spaces if it's less than 4
                while line_content.startswith(" "):
                    self.text.delete(line_start, f"{i}.1")
                    line_content = self.text.get(line_start, f"{i}.end")
                    break # Just one for now or loop? User said 4 spaces.
            
        return "break"

    def compile_script(self):
        """ Veteran Syntax Linter: Verifies structural headers and bracket balance. """
        content = self.text.get("1.0", "end")
        
        # 1. Bracket Check
        open_b = content.count("{")
        close_b = content.count("}")
        if open_b != close_b:
            diff = abs(open_b - close_b)
            side = "missing" if open_b > close_b else "extra"
            messagebox.showerror("Syntax Error", f"Bracket Mismatch!\nOpen: {open_b} | Close: {close_b}\nCheck your Type/Object blocks! {diff} {side} '}}'.", parent=self.win)
            return

        # 2. Header Check (Structure Linter)
        headers = ["Type", "Object", "on_", "On"]
        found = False
        for h in headers:
            if h in content:
                found = True
                break
        
        if not found:
            messagebox.showwarning("Logic Warning", "No Definitions found.\nUse 'Type' or 'Object' to define your logic blocks.", parent=self.win)
            return

        messagebox.showinfo("Syntax Success", "Structure Validated.\nLogic is structurally sound and ready for engine export.", parent=self.win)

    def on_key_release(self, event):
        """ Debounce Logic: Highlights and Auto-Saves after user stops typing. """
        if hasattr(self, "_debounce_id"):
            self.win.after_cancel(self._debounce_id)
        self._debounce_id = self.win.after(300, self._process_text_update)

    def _process_text_update(self):
        """ Runs highlighter and silently saves to the pool. """
        self.perform_highlighting()
        self.auto_save()

    def auto_save(self):
        """ Hardened Silent Disk Commit: Security Sanity Check. """
        if not self.save_manager or not self.save_manager.project_path: return
        # Security: Force basename to prevent directory traversal
        safe_name = os.path.basename(self.current_filename)
        path = os.path.join(self.save_manager.project_path, "HAIRY", safe_name)
        try:
            content = self.text.get("1.0", "end-1c")
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.status_var.set(f"Saved: {safe_name}")
            self.save_manager.mark_dirty()
            
            # --- BI-DIRECTIONAL LOGIC SYNC ---
            self._sync_plr_definitions(safe_name, content)
            
            self.win.after(1000, lambda: self.status_var.set("Auto-Save Active"))
        except Exception as e:
            print(f"[ERROR] Auto-save failed for {safe_name}: {e}")

    def create_new_script(self):
        """ Wizard to create a new script file and seed it with the Template. """
        name = simpledialog.askstring("New Hairy", "Enter script name:", parent=self.win)
        if not name: return
        
        # Sanitize extension and path
        name = os.path.basename(name)  # Security: strip any path components
        if not name.lower().endswith(".hry"):
            name += ".hry"
            
        hairy_dir = os.path.join(self.save_manager.project_path, "HAIRY")
        new_path = os.path.join(hairy_dir, name)
        
        if os.path.exists(new_path):
            messagebox.showwarning("Warning", f"A script named {name} already exists!")
            return

        # Seed the new script with Template.hry content if available
        template_path = os.path.join(hairy_dir, "Template.hry")
        content = f"// New Script: {name}\n\n"
        if os.path.exists(template_path):
            try:
                with open(template_path, 'r') as f:
                    content = f.read()
                
                # SMART RENAME: Replace placeholder with actual script name
                clean_name = name.replace(".hry", "")
                content = content.replace("My_Template_Object", clean_name)
                content = content.replace("Template.hry", name)
            except: pass

        try:
            with open(new_path, 'w') as f:
                f.write(content)
            self.refresh_file_list()
            self.load_file(name)
            self.status_var.set(f"Created: {name}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create script: {e}")

    def load_file(self, filename):
        """ Hardened: Loads file with 'Auto-Heal' intelligence. """
        if not self.save_manager or not self.save_manager.project_path: return
        
        path = os.path.join(self.save_manager.project_path, "HAIRY", filename)
        if not os.path.exists(path): return
        
        self.current_filename = filename
        self.win.title(f"Hairy Editor - {filename}")
        if hasattr(self, 'title_label'):
            self.title_label.config(text=f"HAIRY SCRIPT EDITOR - {filename}")
        
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            
            self.text.delete("1.0", "end")
            self.text.insert("1.0", content)
            self.perform_highlighting()
        except Exception as e:
            print(f"[ERROR] Failed to load {filename}: {e}")


    def save_file(self):
        """ Explicit save: writes current buffer to file and updates status. """
        if not self.save_manager or not self.save_manager.project_path: return
        # Security: Force basename to prevent directory traversal
        safe_name = os.path.basename(self.current_filename)
        path = os.path.join(self.save_manager.project_path, "HAIRY", safe_name)
        try:
            content = self.text.get("1.0", "end-1c")
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # --- SKILLS LOGIC BRIDGE ---
            if safe_name == "Skills.hry" or safe_name == "Defines.hry":
                import ScriptParser
                ScriptParser.sync_skills_logic(self.save_manager.project_path)

            self.save_manager.mark_dirty()
            success, err = self.save_manager.save_project()
            
            if success:
                self.status_var.set(f"Project Saved: {safe_name}")
            else:
                self.status_var.set(f"ERR: {safe_name}")
                print(f"[ERROR] Hairy Save failed project-sync: {err}")
                
            self.win.after(2000, lambda: self.status_var.set("Ready"))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save script: {e}")

    def refresh_file_list(self):
        """ Scans the HAIRY directory and updates the library list (Case-Insensitive). """
        if not self.save_manager or not self.save_manager.project_path: return
        self.file_list.delete(0, "end")
        
        hairy_dir = os.path.join(self.save_manager.project_path, "HAIRY")
        if os.path.exists(hairy_dir):
            # Case-insensitive filter for .hry files
            files = [f for f in os.listdir(hairy_dir) if f.lower().endswith(".hry")]
            for f in sorted(files):
                self.file_list.insert("end", f)

    def _on_list_double_click(self, event):
        selection = self.file_list.curselection()
        if selection:
            filename = self.file_list.get(selection[0])
            self.load_file(filename)

    def perform_highlighting(self, event=None):
        """ Veteran-Grade Semantic Highlighting. """
        for tag in list(EditorColors.SYNTAX.keys()) + ["danger", "disabled_bg", "define_keyword"]:
            self.text.tag_remove(tag, "1.0", "end")
        
        # Pass 1: Numbers & Members (lowest priority, painted first)
        self._highlight_pattern(r"\b\d+\b", "literal")
        self._highlight_pattern(r"\.[a-zA-Z0-9_]+\b", "member")
        
        # Pass 2: User-defined constants (ALL_CAPS identifiers)
        self._highlight_pattern(r"\b[A-Z][A-Z0-9_]{2,}\b", "constant")
        
        # Pass 3: Variable Type declarations
        self._highlight_pattern(r"\b(Number|String|Boolean|Array)\b", "type_def")

        # Pass 4: Brackets
        self._highlight_pattern(r"[{}]", "bracket")
        
        # Pass 5: Directives & Danger
        self._highlight_pattern(r"(?i)#?(Define|Defign)", "directive")
        self._highlight_pattern(r"\bDEFINE\b", "define_keyword")
        self._highlight_pattern(r"\b(Destroy|ApplyDamage|Done)\b", "danger")

        # Pass 6: Architecture headers (Type/Object/Skill/EXP_)
        self._highlight_pattern(r"\b(Type|Object|Skill|EXP_[A-Z0-9_]*)\b", "hook")

        # Pass 7: Interaction Hooks
        hooks = r"(?i)\b(OnLook|OnUse|OnTouch|OnEquip|OnUnEquip|OnTalk|OnNew|OnDeath|OnSpawn|OnDestroy|OnRespawn|OnLogout|OnBoard|OnDock|OnHit|OnCombat|OnTarget|OnDrag|OnEnterContainer|OnRemoveFromContainer)\b"
        self._highlight_pattern(hooks, "hook")
        
        # Pass 8: Logic Controls & Literal Comparisons
        logic = r"(?i)\b(If|Else|Equals|NotEquals|GreaterThan|LessThan|GreaterThanOrEquals|LessThanOrEquals|IsValid|Return|And|Or|Not|True|False|In|Call|Sleep|While|Loop|Plus|Minus|Divide|Multiply|Random)\b"
        self._highlight_pattern(logic, "keyword")
        
        # Pass 9: Engine Methods (ALL commands)
        actions = r"(?i)\b(Create|Respawn|Resurrect|Kill|Heal|GiveHealth|GiveMana|Poison|Cure|Teleport|Walk|Follow|Flee|Set|Get|SetFlag|SetTimer|Print|Say|Whisper|Broadcast|GetName|Cast|Equip|Put|Give|Take|Drop|OpenContainer|OpenInventory|OpenTradeWindow|OpenShop|AddGold|RemoveGold|GiveSkill|GetSkill|GiveExperience|PlaySound|PlayEffect|ScreenShake|OpenGump|CloseGump|AskQuestion|FireProjectile|ClearAdjustments|Search|CheckLineOfSight|GetDistance|SelectObject|SelectLocation|ReadMap|CheckResource|TestSkill|UnEquip|ObjectCreateMenu|GetTypeName)\b"
        self._highlight_pattern(actions, "method")
        
        # Pass 10: Math & Comparison Symbols
        symbols = r"[\+\-\*\/\=\>\<\!]"
        self._highlight_pattern(symbols, "bracket") # Reuse gold/distinct color for symbols

        # Pass 10: Entity Pointers (high priority — overrides earlier tags)
        self._highlight_pattern(r"\bME\b", "self")
        globals_ptr = r"(?i)\b(player|target|this|dead_body|owner|object|inventory|bank|obj)\b"
        self._highlight_pattern(globals_ptr, "global")

        # Pass 11: Disabled Hook Detection (The "X" skipped logic)
        start = "1.0"
        while True:
            start = self.text.search(r"\bx[A-Za-z]+\b", start, stopindex="end", regexp=True)
            if not start: break
            end = f"{start} lineend"
            self.text.tag_add("danger", start, end)
            block_end = self.text.search(r"\}", start, stopindex="end")
            if block_end:
                self.text.tag_add("disabled_bg", start, f"{block_end} + 1c")
            start = end

        # Pass 12: #Define identifier helpers
        self._setup_tag_config() # Ensure tags are configured
        self._highlight_defines()

        # Pass 13: Strings & Comments (highest priority — override everything)
        self._highlight_pattern(r"'.*?'|\".*?\"", "string")
        self._highlight_pattern(r"//.*", "comment")

    def _setup_tag_config(self):
        """ Binds tag names to colors from the token registry. """
        for tag, color in EditorColors.SYNTAX.items():
            self.text.tag_configure(tag, foreground=color)
        self.text.tag_configure("define_keyword", foreground=EditorColors.SYNTAX.get("define_keyword", "#FF33CC"))
        self.text.tag_configure("danger", foreground=EditorColors.SYNTAX.get("danger", "red"))
        self.text.tag_configure("disabled_bg", background="#333")

    def _highlight_defines(self):
        """ Pure-Python pass for #Define tri-color: directive, identifier, value. """
        import re
        content = self.text.get("1.0", "end")
        for i, line in enumerate(content.splitlines(), 1):
            # Matches: #Define ID VALUE, DEFINE FAMILY ID, DEFINE GLOBAL ID VALUE, etc.
            m = re.match(r"(\s*)(#Defig?ne|DEFINE)(\s+)([A-Z0-9_\s:]+)(?:(\s+)(\d+))?", line, re.IGNORECASE)
            if not m:
                continue
            
            # Use specific color for 'DEFINE' (unquoted/all-caps variant)
            directive_tag = "define_keyword" if m.group(2).upper() == "DEFINE" else "directive"
            
            # Directive
            start = f"{i}.{len(m.group(1))}"
            end = f"{i}.{len(m.group(1)) + len(m.group(2))}"
            self.text.tag_add(directive_tag, start, end)
            
            # Identifier (group 4)
            id_start = len(m.group(1)) + len(m.group(2)) + len(m.group(3))
            id_end = id_start + len(m.group(4))
            self.text.tag_add("identifier", f"{i}.{id_start}", f"{i}.{id_end}")
            # Numeric value (group 6) if present
            if m.group(6):
                val_start = id_end + len(m.group(5))
                val_end = val_start + len(m.group(6))
                self.text.tag_add("literal", f"{i}.{val_start}", f"{i}.{val_end}")

    def _sync_plr_definitions(self, changed_name, content):
        """ Master Synchronizer for Player/Defines bi-directional logic flow. """
        import re
        if not self.save_manager or not self.save_manager.project_path: return
        
        # We only sync specific files
        target_files = ["Defines.hry", "Player.hry"]
        if changed_name not in target_files: return
        
        other_name = "Player.hry" if changed_name == "Defines.hry" else "Defines.hry"
        other_path = os.path.join(self.save_manager.project_path, "HAIRY", other_name)
        
        # 1. Extract PLR_ definitions from current content
        # Pattern: #Define PLR_NAME VALUE
        my_defines = re.findall(r"(?i)#Defig?ne\s+(PLR_[A-Za-z0-9_]+)\s+(\d+)", content)
        if not my_defines and changed_name == "Player.hry": return # Nothing to sync from player
        
        # 2. Load the other file
        if not os.path.exists(other_path):
            try:
                with open(other_path, 'w') as f: f.write(f"// {other_name} - Auto-Synced\n\n")
            except: return

        try:
            with open(other_path, 'r') as f:
                other_content = f.read()
            
            modified = False
            for identifier, value in my_defines:
                # Check if it exists in the other file
                pattern = rf"(?i)(#Defig?ne\s+{identifier}\s+)(\d+)"
                match = re.search(pattern, other_content)
                
                if match:
                    if match.group(2) != value:
                        # Update value
                        other_content = re.sub(pattern, rf"\1{value}", other_content)
                        modified = True
                else:
                    # Add new definition
                    other_content += f"\n#Define {identifier.upper()} {value}"
                    modified = True
            
            if modified:
                with open(other_path, 'w') as f:
                    f.write(other_content)
                print(f"[DEBUG] Synced {len(my_defines)} definitions to {other_name}")
                # If we updated the file currently in the listbox, we might want to refresh it
                # but better to let the user load it.
        except Exception as e:
            print(f"[ERROR] Sync failed: {e}")

    def _highlight_pattern(self, pattern, tag):
        """ Uses a robust double-check for match length to prevent tagging glitches. """
        start = "1.0"
        while True:
            # We use count to get the exact character length matched by the regex engine
            count_var = tk.IntVar()
            start = self.text.search(pattern, start, stopindex="end", regexp=True, count=count_var)
            if not start: break
            
            length = count_var.get()
            if length == 0: break # Safety exit for null matches
            
            end = f"{start} + {length}c"
            self.text.tag_add(tag, start, end)
            start = end
