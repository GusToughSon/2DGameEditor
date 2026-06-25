# AdminToolEditor.py - GUI client for server administration and account/character editing
import tkinter as tk
from tkinter import messagebox, ttk
import socket
import json
import threading
import os
import sys
from EditorComponents import center_window

class AdminToolEditor:
    """
    Win95-Style Admin Tool Interface. Connects directly to the running game server
    to request, search, edit accounts/characters, and trigger global server actions.
    """
    def __init__(self, parent, save_manager, main_app=None):
        self.parent = parent
        self.save_manager = save_manager
        self.main_app = main_app
        
        # Connection state
        self.sock = None
        self.connected = False
        self.authed = False
        self.listen_thread = None
        
        # Data caches
        self.accounts = []
        self.characters = []
        self.selected_account_idx = None
        self.selected_character_idx = None
        
        # Request-Response callback registration
        self.pending_callbacks = {}
        
        # UI Font and Colors
        self.ui_font = ("Tahoma", 8)
        self.bg_color = "#C0C0C0"
        
        # --- WINDOW SETUP ---
        self.win = tk.Toplevel(parent)
        self.win.title("Administrator GM Control Console")
        center_window(self.win, parent, 850, 600)
        self.win.configure(bg=self.bg_color)
        self.win.transient(parent)
        
        self.setup_ui()
        
        # Automatically close socket when window is closed
        self.win.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_ui(self):
        # 1. Connection Header Frame
        conn_frame = tk.LabelFrame(self.win, text="Server Connection & Authentication", bg=self.bg_color, font=self.ui_font)
        conn_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(conn_frame, text="Host:", bg=self.bg_color, font=self.ui_font).grid(row=0, column=0, padx=5, pady=2, sticky="e")
        self.host_var = tk.StringVar(value="127.0.0.1")
        tk.Entry(conn_frame, textvariable=self.host_var, width=15, font=self.ui_font).grid(row=0, column=1, padx=5, pady=2, sticky="w")
        
        tk.Label(conn_frame, text="Port:", bg=self.bg_color, font=self.ui_font).grid(row=0, column=2, padx=5, pady=2, sticky="e")
        self.port_var = tk.StringVar(value="1338")
        tk.Entry(conn_frame, textvariable=self.port_var, width=6, font=self.ui_font).grid(row=0, column=3, padx=5, pady=2, sticky="w")
        
        tk.Label(conn_frame, text="Username:", bg=self.bg_color, font=self.ui_font).grid(row=0, column=4, padx=5, pady=2, sticky="e")
        self.user_var = tk.StringVar(value="admin")
        tk.Entry(conn_frame, textvariable=self.user_var, width=12, font=self.ui_font).grid(row=0, column=5, padx=5, pady=2, sticky="w")
        
        tk.Label(conn_frame, text="Password:", bg=self.bg_color, font=self.ui_font).grid(row=0, column=6, padx=5, pady=2, sticky="e")
        self.pass_var = tk.StringVar(value="admin")
        tk.Entry(conn_frame, textvariable=self.pass_var, show="*", width=12, font=self.ui_font).grid(row=0, column=7, padx=5, pady=2, sticky="w")
        
        self.btn_connect = tk.Button(conn_frame, text="Connect & Auth", font=self.ui_font, command=self.connect_and_auth, width=15)
        self.btn_connect.grid(row=0, column=8, padx=10, pady=2)
        
        self.lbl_status = tk.Label(conn_frame, text="Status: Disconnected", bg=self.bg_color, fg="red", font=("Tahoma", 8, "bold"))
        self.lbl_status.grid(row=0, column=9, padx=10, pady=2, sticky="w")

        # 2. Notebook / Tabs for Accounts, Characters, Item Search, Server Controls
        self.notebook = ttk.Notebook(self.win)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.tab_accounts = tk.Frame(self.notebook, bg=self.bg_color)
        self.tab_characters = tk.Frame(self.notebook, bg=self.bg_color)
        self.tab_search = tk.Frame(self.notebook, bg=self.bg_color)
        self.tab_server = tk.Frame(self.notebook, bg=self.bg_color)
        
        self.notebook.add(self.tab_accounts, text="Accounts Manager")
        self.notebook.add(self.tab_characters, text="Characters Manager")
        self.notebook.add(self.tab_search, text="Item Search Tool")
        self.notebook.add(self.tab_server, text="Server Controls")
        
        self.setup_accounts_tab()
        self.setup_characters_tab()
        self.setup_search_tab()
        self.setup_server_tab()
        
        # Disable tabs initially until authed
        self.set_tabs_state("disabled")

    def set_tabs_state(self, state):
        for idx in range(4):
            self.notebook.tab(idx, state=state)

    # -------------------------------------------------------------------------
    # ACCOUNTS TAB
    # -------------------------------------------------------------------------
    def setup_accounts_tab(self):
        # Left side list
        left_f = tk.Frame(self.tab_accounts, bg=self.bg_color)
        left_f.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        tk.Label(left_f, text="Account List:", bg=self.bg_color, font=self.ui_font).pack(anchor="w")
        
        list_f = tk.Frame(left_f)
        list_f.pack(fill="both", expand=True)
        
        self.acc_tree = ttk.Treeview(list_f, columns=("id", "name", "banned", "premium", "golden"), show="headings", selectmode="browse")
        self.acc_tree.heading("id", text="ID")
        self.acc_tree.heading("name", text="Account Name")
        self.acc_tree.heading("banned", text="Banned")
        self.acc_tree.heading("premium", text="Premium")
        self.acc_tree.heading("golden", text="Golden")
        
        self.acc_tree.column("id", width=40, anchor="center")
        self.acc_tree.column("name", width=120, anchor="w")
        self.acc_tree.column("banned", width=60, anchor="center")
        self.acc_tree.column("premium", width=60, anchor="center")
        self.acc_tree.column("golden", width=60, anchor="center")
        self.acc_tree.pack(side="left", fill="both", expand=True)
        
        sb = tk.Scrollbar(list_f, command=self.acc_tree.yview)
        sb.pack(side="right", fill="y")
        self.acc_tree.config(yscrollcommand=sb.set)
        
        self.acc_tree.bind("<<TreeviewSelect>>", self.on_account_select)
        
        btn_f = tk.Frame(left_f, bg=self.bg_color)
        btn_f.pack(fill="x", pady=5)
        tk.Button(btn_f, text="Refresh Account List", font=self.ui_font, command=self.refresh_accounts).pack(side="left")
        
        # Right side properties
        right_f = tk.LabelFrame(self.tab_accounts, text="Account Properties", bg=self.bg_color, font=self.ui_font)
        right_f.pack(side="right", fill="y", padx=5, pady=5)
        
        tk.Label(right_f, text="Edit Account Fields:", bg=self.bg_color, font=("Tahoma", 8, "bold")).pack(anchor="w", padx=10, pady=5)
        
        # Fields
        self.acc_banned_var = tk.BooleanVar()
        tk.Checkbutton(right_f, text="Is Banned (is_banned)", variable=self.acc_banned_var, bg=self.bg_color, font=self.ui_font).pack(anchor="w", padx=20, pady=5)
        
        self.acc_premium_var = tk.BooleanVar()
        tk.Checkbutton(right_f, text="Is Premium (is_premium)", variable=self.acc_premium_var, bg=self.bg_color, font=self.ui_font).pack(anchor="w", padx=20, pady=5)
        
        self.acc_golden_var = tk.BooleanVar()
        tk.Checkbutton(right_f, text="Is Golden (is_golden)", variable=self.acc_golden_var, bg=self.bg_color, font=self.ui_font).pack(anchor="w", padx=20, pady=5)
        
        self.btn_save_account = tk.Button(right_f, text="Save Account Properties", font=self.ui_font, command=self.save_account_changes, state="disabled", width=22)
        self.btn_save_account.pack(padx=20, pady=20)

    # -------------------------------------------------------------------------
    # CHARACTERS TAB
    # -------------------------------------------------------------------------
    def setup_characters_tab(self):
        # Left side list
        left_f = tk.Frame(self.tab_characters, bg=self.bg_color)
        left_f.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        tk.Label(left_f, text="Character List:", bg=self.bg_color, font=self.ui_font).pack(anchor="w")
        
        list_f = tk.Frame(left_f)
        list_f.pack(fill="both", expand=True)
        
        self.char_tree = ttk.Treeview(list_f, columns=("id", "name", "level", "pos", "dev_mode", "online"), show="headings", selectmode="browse")
        self.char_tree.heading("id", text="ID")
        self.char_tree.heading("name", text="Name")
        self.char_tree.heading("level", text="Level")
        self.char_tree.heading("pos", text="Coords")
        self.char_tree.heading("dev_mode", text="GM Level")
        self.char_tree.heading("online", text="Online")
        
        self.char_tree.column("id", width=40, anchor="center")
        self.char_tree.column("name", width=120, anchor="w")
        self.char_tree.column("level", width=50, anchor="center")
        self.char_tree.column("pos", width=80, anchor="center")
        self.char_tree.column("dev_mode", width=60, anchor="center")
        self.char_tree.column("online", width=60, anchor="center")
        self.char_tree.pack(side="left", fill="both", expand=True)
        
        sb = tk.Scrollbar(list_f, command=self.char_tree.yview)
        sb.pack(side="right", fill="y")
        self.char_tree.config(yscrollcommand=sb.set)
        
        self.char_tree.bind("<<TreeviewSelect>>", self.on_character_select)
        
        btn_f = tk.Frame(left_f, bg=self.bg_color)
        btn_f.pack(fill="x", pady=5)
        tk.Button(btn_f, text="Refresh Character List", font=self.ui_font, command=self.refresh_characters).pack(side="left")
        
        # Right side properties
        right_f = tk.LabelFrame(self.tab_characters, text="Character Attributes", bg=self.bg_color, font=self.ui_font)
        right_f.pack(side="right", fill="y", padx=5, pady=5)
        
        # Form grid
        form_frame = tk.Frame(right_f, bg=self.bg_color, padx=10, pady=10)
        form_frame.pack(fill="both", expand=True)
        
        fields = [
            ("level", "Level:"),
            ("x", "Coords X:"),
            ("y", "Coords Y:"),
            ("dev_mode", "GM Mode Level:"),
            ("avatar", "Avatar ID:"),
            ("hp_left", "HP Left:"),
            ("hp_max", "HP Max:"),
            ("mana_left", "Mana Left:")
        ]
        
        self.char_entries = {}
        for idx, (field_name, label_text) in enumerate(fields):
            tk.Label(form_frame, text=label_text, bg=self.bg_color, font=self.ui_font).grid(row=idx, column=0, sticky="e", pady=3)
            var = tk.StringVar()
            entry = tk.Entry(form_frame, textvariable=var, width=12, font=self.ui_font)
            entry.grid(row=idx, column=1, sticky="w", padx=5, pady=3)
            self.char_entries[field_name] = var
            
        self.btn_save_character = tk.Button(right_f, text="Save Character Attributes", font=self.ui_font, command=self.save_character_changes, state="disabled", width=22)
        self.btn_save_character.pack(padx=20, pady=20)

    # -------------------------------------------------------------------------
    # ITEM SEARCH TAB
    # -------------------------------------------------------------------------
    def setup_search_tab(self):
        # Header controls
        top_f = tk.Frame(self.tab_search, bg=self.bg_color, pady=5)
        top_f.pack(fill="x", padx=10)
        
        tk.Label(top_f, text="Item Type ID:", bg=self.bg_color, font=self.ui_font).pack(side="left", padx=5)
        self.search_type_var = tk.StringVar()
        tk.Entry(top_f, textvariable=self.search_type_var, width=10, font=self.ui_font).pack(side="left", padx=5)
        
        tk.Label(top_f, text="OR Item Instance ID:", bg=self.bg_color, font=self.ui_font).pack(side="left", padx=5)
        self.search_id_var = tk.StringVar()
        tk.Entry(top_f, textvariable=self.search_id_var, width=10, font=self.ui_font).pack(side="left", padx=5)
        
        tk.Button(top_f, text="Search Database", font=self.ui_font, command=self.perform_item_search).pack(side="left", padx=15)
        
        # Results grid
        list_f = tk.Frame(self.tab_search)
        list_f.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.search_tree = ttk.Treeview(list_f, columns=("id", "type", "qty", "owner", "container", "slot", "coords"), show="headings")
        self.search_tree.heading("id", text="Item ID")
        self.search_tree.heading("type", text="Type")
        self.search_tree.heading("qty", text="Qty")
        self.search_tree.heading("owner", text="Owner Name")
        self.search_tree.heading("container", text="Container")
        self.search_tree.heading("slot", text="Slot")
        self.search_tree.heading("coords", text="Coords (X, Y)")
        
        self.search_tree.column("id", width=60, anchor="center")
        self.search_tree.column("type", width=60, anchor="center")
        self.search_tree.column("qty", width=55, anchor="center")
        self.search_tree.column("owner", width=120, anchor="w")
        self.search_tree.column("container", width=80, anchor="center")
        self.search_tree.column("slot", width=50, anchor="center")
        self.search_tree.column("coords", width=90, anchor="center")
        self.search_tree.pack(side="left", fill="both", expand=True)
        
        sb = tk.Scrollbar(list_f, command=self.search_tree.yview)
        sb.pack(side="right", fill="y")
        self.search_tree.config(yscrollcommand=sb.set)

    # -------------------------------------------------------------------------
    # SERVER CONTROLS TAB
    # -------------------------------------------------------------------------
    def setup_server_tab(self):
        # Broadcast section
        msg_frame = tk.LabelFrame(self.tab_server, text="Global Server Message Broadcast", bg=self.bg_color, font=self.ui_font, padx=10, pady=10)
        msg_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(msg_frame, text="Announcement Message Text:", bg=self.bg_color, font=self.ui_font).pack(anchor="w")
        self.broadcast_msg_var = tk.StringVar()
        tk.Entry(msg_frame, textvariable=self.broadcast_msg_var, width=80, font=self.ui_font).pack(fill="x", pady=5)
        
        tk.Button(msg_frame, text="Broadcast Announcement to All Players", font=self.ui_font, command=self.send_broadcast).pack(anchor="e", pady=5)
        
        # Save section
        save_frame = tk.LabelFrame(self.tab_server, text="Forced Database Serialization", bg=self.bg_color, font=self.ui_font, padx=10, pady=10)
        save_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(save_frame, text="Command the server to write all in-memory accounts and parameters to SQLite:", bg=self.bg_color, font=self.ui_font).pack(anchor="w")
        tk.Button(save_frame, text="Force Server Save", font=self.ui_font, command=self.force_server_save, width=20).pack(anchor="w", pady=10)

    # -------------------------------------------------------------------------
    # NETWORK LOGIC & THREADING
    # -------------------------------------------------------------------------
    def connect_and_auth(self):
        if self.connected:
            self.disconnect()
            return
            
        host = self.host_var.get().strip()
        try:
            port = int(self.port_var.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Invalid port number.")
            return
            
        username = self.user_var.get().strip()
        password = self.pass_var.get().strip()
        
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, port))
            
            # Send init
            init_req = {"type": "admin_init"}
            self.sock.sendall(self.pack_json(init_req))
            
            # Synchronous read of first packet
            res = self.read_packet_sync(self.sock)
            if res and res.get("type") == "admin_init_response" and res.get("success"):
                self.connected = True
                
                # Start listener thread
                self.listen_thread = threading.Thread(target=self.listen_responses_loop, daemon=True)
                self.listen_thread.start()
                
                # Send Auth
                self.lbl_status.config(text="Status: Authenticating...", fg="orange")
                self.send_with_callback({
                    "type": "admin_auth",
                    "username": username,
                    "password": password
                }, "admin_auth_response", self.handle_auth_response)
            else:
                self.lbl_status.config(text="Status: Rejected Init", fg="red")
                self.sock.close()
        except Exception as e:
            self.lbl_status.config(text="Status: Connection Failed", fg="red")
            messagebox.showerror("Connection Error", f"Could not connect to {host}:{port}\n{e}")

    def disconnect(self):
        self.connected = False
        self.authed = False
        if self.sock:
            try:
                self.sock.close()
            except: pass
            self.sock = None
            
        self.lbl_status.config(text="Status: Disconnected", fg="red")
        self.btn_connect.config(text="Connect & Auth")
        self.set_tabs_state("disabled")
        
        # Clear lists
        self.acc_tree.delete(*self.acc_tree.get_children())
        self.char_tree.delete(*self.char_tree.get_children())
        self.search_tree.delete(*self.search_tree.get_children())

    def listen_responses_loop(self):
        try:
            while self.connected:
                packet = self.read_packet_sync(self.sock)
                if not packet:
                    break
                p_type = packet.get("type")
                if p_type == "admin_error":
                    err_msg = packet.get("error", "Unknown server error.")
                    self.win.after(0, lambda e=err_msg: messagebox.showerror("Server Error", e))
                elif p_type in self.pending_callbacks:
                    callback = self.pending_callbacks.pop(p_type)
                    self.win.after(0, callback, packet)
        except Exception as e:
            print(f"Connection ended in listener thread: {e}")
        finally:
            self.win.after(0, self.disconnect)

    def send_with_callback(self, req_packet: dict, resp_type: str, callback):
        self.pending_callbacks[resp_type] = callback
        try:
            self.sock.sendall(self.pack_json(req_packet))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send request: {e}")
            self.disconnect()

    def pack_json(self, data: dict) -> bytes:
        from core.crypto import xor_cipher
        # Check constants for decryption salt
        constants_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ThePlayerCity", "server", "constants.md")
        key = 212
        if os.path.exists(constants_path):
            try:
                with open(constants_path, 'r') as f:
                    for line in f:
                        if "TCPKEY:" in line:
                            key = int(line.split("TCPKEY:")[1].strip())
                            break
            except: pass
            
        raw_json = json.dumps(data)
        encrypted = xor_cipher(raw_json.encode('utf-8'), key)
        length = len(encrypted)
        return struct.pack(f"<I{length}s", length, encrypted)

    def read_packet_sync(self, sock) -> dict:
        try:
            header = sock.recv(4)
            if not header or len(header) < 4:
                return {}
            length = struct.unpack("<I", header)[0]
            data = sock.recv(length)
            while len(data) < length:
                chunk = sock.recv(length - len(data))
                if not chunk:
                    break
                data += chunk
            from core.crypto import xor_cipher
            constants_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ThePlayerCity", "server", "constants.md")
            key = 212
            if os.path.exists(constants_path):
                try:
                    with open(constants_path, 'r') as f:
                        for line in f:
                            if "TCPKEY:" in line:
                                key = int(line.split("TCPKEY:")[1].strip())
                                break
                except: pass
            decrypted = xor_cipher(data, key).decode('utf-8')
            return json.loads(decrypted)
        except:
            return {}

    # -------------------------------------------------------------------------
    # CALLBACK HANDLERS
    # -------------------------------------------------------------------------
    def handle_auth_response(self, packet: dict):
        if packet.get("success"):
            self.authed = True
            self.lbl_status.config(text="Status: Authenticated", fg="green")
            self.btn_connect.config(text="Disconnect")
            self.set_tabs_state("normal")
            
            # Fetch lists initially
            self.refresh_accounts()
            self.refresh_characters()
        else:
            self.lbl_status.config(text="Status: Auth Failed", fg="red")
            messagebox.showerror("Authentication Failed", packet.get("error", "Unknown error."))
            self.disconnect()

    def refresh_accounts(self):
        if not self.authed: return
        self.send_with_callback({"type": "admin_request_accounts"}, "admin_accounts_list", self.handle_accounts_list)

    def handle_accounts_list(self, packet: dict):
        self.accounts = packet.get("accounts", [])
        self.acc_tree.delete(*self.acc_tree.get_children())
        for idx, a in enumerate(self.accounts):
            self.acc_tree.insert("", "end", iid=str(idx), values=(
                a["id"], a["acc_name"], a["is_banned"], a["is_premium"], a["is_golden"]
            ))
        self.btn_save_account.config(state="disabled")

    def on_account_select(self, event):
        selected = self.acc_tree.selection()
        if not selected:
            self.btn_save_account.config(state="disabled")
            return
        idx = int(selected[0])
        self.selected_account_idx = idx
        a = self.accounts[idx]
        
        self.acc_banned_var.set(a["is_banned"])
        self.acc_premium_var.set(a["is_premium"])
        self.acc_golden_var.set(a["is_golden"])
        self.btn_save_account.config(state="normal")

    def save_account_changes(self):
        if self.selected_account_idx is None: return
        acc = self.accounts[self.selected_account_idx]
        
        fields = [
            ("is_banned", 1 if self.acc_banned_var.get() else 0),
            ("is_premium", 1 if self.acc_premium_var.get() else 0),
            ("is_golden", 1 if self.acc_golden_var.get() else 0)
        ]
        
        def send_edit_field(f_idx):
            if f_idx >= len(fields):
                messagebox.showinfo("Success", "Account saved successfully.")
                self.refresh_accounts()
                return
                
            field, val = fields[f_idx]
            self.send_with_callback({
                "type": "admin_edit_account",
                "account_id": acc["id"],
                "field": field,
                "value": val
            }, "admin_edit_account_response", lambda p, idx=f_idx: send_edit_field(idx + 1))
            
        send_edit_field(0)

    def refresh_characters(self):
        if not self.authed: return
        self.send_with_callback({"type": "admin_request_characters"}, "admin_characters_list", self.handle_characters_list)

    def handle_characters_list(self, packet: dict):
        self.characters = packet.get("characters", [])
        self.char_tree.delete(*self.char_tree.get_children())
        for idx, c in enumerate(self.characters):
            self.char_tree.insert("", "end", iid=str(idx), values=(
                c["id"], c["name"], c["level"], f"({c['x']}, {c['y']})", c["dev_mode"], "Yes" if c["is_online"] else "No"
            ))
        self.btn_save_character.config(state="disabled")

    def on_character_select(self, event):
        selected = self.char_tree.selection()
        if not selected:
            self.btn_save_character.config(state="disabled")
            return
        idx = int(selected[0])
        self.selected_character_idx = idx
        c = self.characters[idx]
        
        self.char_entries["level"].set(str(c["level"]))
        self.char_entries["x"].set(str(c["x"]))
        self.char_entries["y"].set(str(c["y"]))
        self.char_entries["dev_mode"].set(str(c["dev_mode"]))
        self.char_entries["avatar"].set(str(c["avatar"]))
        self.char_entries["hp_left"].set("10")
        self.char_entries["hp_max"].set("10")
        self.char_entries["mana_left"].set("5")
        
        self.btn_save_character.config(state="normal")

    def save_character_changes(self):
        if self.selected_character_idx is None: return
        char = self.characters[self.selected_character_idx]
        
        edits = []
        for field, var in self.char_entries.items():
            val = var.get().strip()
            if val:
                edits.append((field, val))
                
        def send_edit_field(f_idx):
            if f_idx >= len(edits):
                messagebox.showinfo("Success", "Character attributes saved successfully.")
                self.refresh_characters()
                return
                
            field, val = edits[f_idx]
            self.send_with_callback({
                "type": "admin_edit_character",
                "character_id": char["id"],
                "field": field,
                "value": val
            }, "admin_edit_character_response", lambda p, idx=f_idx: send_edit_field(idx + 1))
            
        send_edit_field(0)

    # -------------------------------------------------------------------------
    # SEARCH HANDLERS
    # -------------------------------------------------------------------------
    def perform_item_search(self):
        if not self.authed: return
        
        type_str = self.search_type_var.get().strip()
        id_str = self.search_id_var.get().strip()
        
        item_type = int(type_str) if type_str else None
        item_id = int(id_str) if id_str else None
        
        self.send_with_callback({
            "type": "admin_search_item",
            "item_type": item_type,
            "item_id": item_id
        }, "admin_search_item_response", self.handle_search_response)

    def handle_search_response(self, packet: dict):
        results = packet.get("results", [])
        self.search_tree.delete(*self.search_tree.get_children())
        for r in results:
            coord_str = f"({r['x']}, {r['y']})" if r["x"] is not None else "-"
            self.search_tree.insert("", "end", values=(
                r["id"], r["item_type"], r["quantity"], r["owner_name"], r["container"], r["slot"], coord_str
            ))
        if not results:
            messagebox.showinfo("Search Results", "No items matched the search query.")

    # -------------------------------------------------------------------------
    # GLOBAL SERVER ACTIONS
    # -------------------------------------------------------------------------
    def send_broadcast(self):
        if not self.authed: return
        msg = self.broadcast_msg_var.get().strip()
        if not msg: return
        
        try:
            self.sock.sendall(self.pack_json({
                "type": "admin_server_message",
                "message": msg
            }))
            messagebox.showinfo("Broadcast Sent", f"System message broadcasted successfully:\n'{msg}'")
            self.broadcast_msg_var.set("")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send broadcast: {e}")

    def force_server_save(self):
        if not self.authed: return
        self.send_with_callback({"type": "admin_forced_save"}, "admin_forced_save_response", self.handle_forced_save_response)

    def handle_forced_save_response(self, packet: dict):
        if packet.get("success"):
            messagebox.showinfo("Save Complete", "Server database serialized to SQLite successfully.")
        else:
            messagebox.showerror("Save Failed", "Server reported a serialization error.")

    def on_close(self):
        self.disconnect()
        if self.main_app and hasattr(self.main_app, 'current_admin_tool_editor'):
            self.main_app.current_admin_tool_editor = None
        self.win.destroy()
