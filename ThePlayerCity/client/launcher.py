# launcher.py
# Cloned client launcher for ThePlayerCity
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from tkinter import ttk, messagebox
import socket
import struct
from core.packets import VERSION, pack_json, read_packet_sync

class ClientLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("ThePlayerCity - Launcher")
        self.root.geometry("400x300")
        self.root.configure(bg='#1e1e2e')
        
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('.', background='#1e1e2e', foreground='#cdd6f4', fieldbackground='#313244')
        self.style.configure('TLabel', background='#1e1e2e', foreground='#cdd6f4', font=('Segoe UI', 10))
        self.style.configure('TButton', background='#89b4fa', foreground='#11111b', font=('Segoe UI', 10, 'bold'), borderwidth=0)
        self.style.map('TButton', background=[('active', '#b4befe')])
        
        self.setup_ui()

    def setup_ui(self):
        ttk.Label(self.root, text="ThePlayerCity Launcher", font=('Segoe UI', 16, 'bold')).pack(pady=20)
        
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Username:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.entry_user = ttk.Entry(frame)
        self.entry_user.grid(row=0, column=1, sticky='ew', pady=5)
        
        ttk.Label(frame, text="Password:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.entry_pass = ttk.Entry(frame, show="*")
        self.entry_pass.grid(row=1, column=1, sticky='ew', pady=5)
        
        btn_frame = ttk.Frame(frame, padding=10)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=15)
        
        ttk.Button(btn_frame, text=" Login ", command=self.attempt_login).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text=" Register ", command=self.attempt_register).pack(side=tk.LEFT, padx=10)

    def attempt_login(self):
        username = self.entry_user.get().strip()
        password = self.entry_pass.get().strip()
        
        if not username or not password:
            messagebox.showerror("Error", "Fields cannot be empty")
            return
            
        try:
            print(f"[CLIENT] Attempting connection to 127.0.0.1:1338...")
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(('127.0.0.1', 1338))
            print(f"[CLIENT] Socket successfully connected.")
            
            # Create login request JSON
            login_req = {
                "type": "login",
                "username": username,
                "password": password,
                "version": VERSION
            }
            packet = pack_json(login_req)
            print(f"[CLIENT] Sending Login Request: {login_req}")
            
            s.sendall(packet)
            print(f"[CLIENT] Packet sent successfully. Waiting for authentication response...")
            
            # Read JSON response
            resp = read_packet_sync(s)
            if resp and resp.get("type") == "login_response":
                success = resp.get("success", False)
                print(f"[CLIENT] Received Auth Response success: {success}")
                if success:
                    print("[CLIENT] Authentication successful! Loading slot configuration...")
                    slots = resp.get("slots", {})
                    print(f"[CLIENT] Slots: {slots}")
                    
                    s.close()
                    classes = resp.get("classes", ["Plr_Male_Warrior", "Plr_Mage", "Plr_Rogue"])
                    
                    has_chars = any(slots.get("used", []))
                    if not has_chars:
                        self.show_char_creation(username, classes, slot=0, password=password)
                    else:
                        self.show_char_select(username, password, slots, classes)
                    return
                else:
                    err_code = resp.get("error_code")
                    print(f"[CLIENT] Authentication failed. Error code: {err_code}")
                    messagebox.showerror("Error", "Invalid username or password.")
            else:
                print("[CLIENT] Connection closed unexpectedly by host.")
            s.close()
            print("[CLIENT] Connection socket closed cleanly.")
        except Exception as e:
            print(f"[CLIENT ERROR] Connection or payload exception: {e}")
            messagebox.showerror("Error", f"Failed to connect to server: {e}")

    def attempt_register(self):
        username = self.entry_user.get().strip()
        password = self.entry_pass.get().strip()
        
        if not username or not password:
            messagebox.showerror("Error", "Fields cannot be empty")
            return
            
        try:
            print(f"[CLIENT] Attempting connection to 127.0.0.1:1338 for registration...")
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(('127.0.0.1', 1338))
            
            # Create register request JSON
            register_req = {
                "type": "register",
                "username": username,
                "password": password
            }
            packet = pack_json(register_req)
            s.sendall(packet)
            
            # Read JSON response
            resp = read_packet_sync(s)
            if resp and resp.get("type") == "register_response":
                success = resp.get("success", False)
                if success:
                    messagebox.showinfo("Success", f"Account '{username}' successfully registered! You can now log in.")
                else:
                    error_msg = resp.get("error", "Registration failed.")
                    messagebox.showerror("Error", error_msg)
            else:
                messagebox.showerror("Error", "Connection closed unexpectedly by host.")
            s.close()
        except Exception as e:
            print(f"[CLIENT ERROR] Registration connection or payload exception: {e}")
            messagebox.showerror("Error", f"Failed to connect to server: {e}")

    def show_char_creation(self, username, classes, slot=0, password=None):
        # Create a new top-level window or frame to poll user for character creation
        create_win = tk.Toplevel(self.root)
        create_win.title("Create Character")
        create_win.geometry("400x300")
        create_win.configure(bg='#1e1e2e')
        create_win.grab_set()  # Make it modal
        
        # Center the window relative to self.root
        create_win.transient(self.root)
        
        ttk.Label(create_win, text=f"Create Character in Slot {slot + 1}", font=('Segoe UI', 14, 'bold')).pack(pady=15)
        
        frame = ttk.Frame(create_win, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Character Name:").grid(row=0, column=0, sticky=tk.W, pady=5)
        entry_name = ttk.Entry(frame)
        entry_name.grid(row=0, column=1, sticky='ew', pady=5)
        
        ttk.Label(frame, text="Choose Class:").grid(row=1, column=0, sticky=tk.W, pady=5)
        class_var = tk.StringVar()
        class_combo = ttk.Combobox(frame, textvariable=class_var, values=classes, state="readonly")
        if classes:
            class_combo.set(classes[0])
        class_combo.grid(row=1, column=1, sticky='ew', pady=5)
        
        def attempt_create():
            char_name = entry_name.get().strip()
            selected_class = class_var.get()
            if not char_name:
                messagebox.showerror("Error", "Character name cannot be empty.")
                return
            
            try:
                print(f"[CLIENT] Connecting to server to create character in slot {slot}...")
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect(('127.0.0.1', 1338))
                
                req = {
                    "type": "create_character",
                    "username": username,
                    "char_name": char_name,
                    "class_template": selected_class,
                    "slot": slot
                }
                s.sendall(pack_json(req))
                
                resp = read_packet_sync(s)
                s.close()
                
                if resp and resp.get("type") == "create_character_response" and resp.get("success"):
                    messagebox.showinfo("Success", f"Character '{char_name}' created successfully!")
                    create_win.destroy()
                    
                    # Launch client renderer with updated character slot coordinates
                    import subprocess
                    import sys
                    subprocess.Popen([sys.executable, "-m", "client.renderer", username, password or "", str(slot)])
                    self.root.destroy()
                else:
                    err = resp.get("error", "Failed to create character.") if resp else "Server disconnected."
                    messagebox.showerror("Error", err)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to connect to server: {e}")
                
        btn_frame = ttk.Frame(frame, padding=10)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=15)
        ttk.Button(btn_frame, text=" Create Character ", command=attempt_create).pack()

    def show_char_select(self, username, password, slots, classes):
        # Clear existing widgets from launcher window
        for widget in self.root.winfo_children():
            widget.destroy()
            
        self.root.geometry("500x350")
        
        ttk.Label(self.root, text="Select Your Character", font=('Segoe UI', 16, 'bold')).pack(pady=20)
        
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # We display character slots (up to 2 slots)
        for i in range(2):
            slot_frame = ttk.LabelFrame(main_frame, text=f" Character Slot {i + 1} ", padding=10)
            slot_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            is_used = False
            if slots.get("used") and i < len(slots["used"]):
                is_used = slots["used"][i]
                
            if is_used:
                name = slots["names"][i]
                level = slots["levels"][i]
                hp = slots["hps"][i]
                hp_max = slots["hpmaxs"][i]
                
                ttk.Label(slot_frame, text=name, font=('Segoe UI', 12, 'bold')).pack(anchor=tk.W, pady=2)
                ttk.Label(slot_frame, text=f"Level: {level}").pack(anchor=tk.W, pady=2)
                ttk.Label(slot_frame, text=f"HP: {hp}/{hp_max}").pack(anchor=tk.W, pady=2)
                
                # We need a closure to capture the correct slot index i
                def make_play_callback(slot_idx):
                    return lambda: self.launch_game(username, password, slot_idx)
                
                ttk.Button(slot_frame, text=" Play ", command=make_play_callback(i)).pack(fill=tk.X, pady=10)
            else:
                ttk.Label(slot_frame, text="Empty Slot", font=('Segoe UI', 10, 'italic')).pack(anchor=tk.CENTER, pady=15)
                
                def make_create_callback(slot_idx):
                    return lambda: self.show_char_creation(username, classes, slot=slot_idx, password=password)
                
                ttk.Button(slot_frame, text=" Create ", command=make_create_callback(i)).pack(fill=tk.X, pady=10)

        # Back to Login Button
        def back_to_login():
            for widget in self.root.winfo_children():
                widget.destroy()
            self.root.geometry("400x300")
            self.setup_ui()
            
        ttk.Button(self.root, text=" Back to Login ", command=back_to_login).pack(pady=10)

    def launch_game(self, username, password, slot_idx):
        import subprocess
        import sys
        print(f"[LAUNCHER] Launching client.renderer for {username} in slot {slot_idx}...")
        subprocess.Popen([sys.executable, "-m", "client.renderer", username, password, str(slot_idx)])
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ClientLauncher(root)
    root.mainloop()
