# gui.py
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import sys
import queue
import time
from server.database import DatabaseManager

class LogCapture:
    def __init__(self, text_widget, log_queue):
        self.text_widget = text_widget
        self.log_queue = log_queue

    def write(self, string):
        self.log_queue.put(string)

    def flush(self):
        pass

class ServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ThePlayerCity - Server Dashboard")
        self.root.geometry("900x600")
        
        # Configure Premium Dark Mode Style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('.', background='#1e1e2e', foreground='#cdd6f4', fieldbackground='#313244')
        self.style.configure('TFrame', background='#1e1e2e')
        self.style.configure('TLabel', background='#1e1e2e', foreground='#cdd6f4', font=('Segoe UI', 10))
        self.style.configure('TButton', background='#45475a', foreground='#cdd6f4', borderwidth=0, font=('Segoe UI', 10, 'bold'))
        self.style.map('TButton', background=[('active', '#585b70')])
        
        # Database Manager
        self.db = DatabaseManager()
        self.db.load_accounts()
        
        self.log_queue = queue.Queue()
        self.setup_ui()
        
        # Redirect stdout to GUI console
        sys.stdout = LogCapture(self.console_text, self.log_queue)
        
        # Start queue processing
        self.root.after(100, self.process_logs)
        self.root.after(1000, self.auto_refresh_accounts)
        
        print("== ThePlayerCity Server GUI Initialized ==")
        print(f"Loaded {len(self.db.accounts)} accounts from database.")

    def setup_ui(self):
        # Left Panel (Stats & Controls)
        left_panel = ttk.Frame(self.root, width=250, padding=10)
        left_panel.pack(side=tk.LEFT, fill=tk.Y)
        
        ttk.Label(left_panel, text="ThePlayerCity Admin", font=('Segoe UI', 14, 'bold')).pack(pady=10)
        
        # Stats Frame
        stats_frame = ttk.LabelFrame(left_panel, text=" Server Status ", padding=10)
        stats_frame.pack(fill=tk.X, pady=10)
        
        self.status_label = ttk.Label(stats_frame, text="Status: Running", foreground="#a6e3a1")
        self.status_label.pack(anchor=tk.W, pady=2)
        
        self.players_label = ttk.Label(stats_frame, text="Players Online: 0")
        self.players_label.pack(anchor=tk.W, pady=2)
        
        self.accs_label = ttk.Label(stats_frame, text=f"Total Accounts: {len(self.db.accounts)}")
        self.accs_label.pack(anchor=tk.W, pady=2)
        
        # Actions Frame
        actions_frame = ttk.LabelFrame(left_panel, text=" Database Actions ", padding=10)
        actions_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(actions_frame, text="Reload Database", command=self.reload_db).pack(fill=tk.X, pady=5)
        ttk.Button(actions_frame, text="Save Database", command=self.save_db).pack(fill=tk.X, pady=5)
        ttk.Button(actions_frame, text="Create Account", command=self.create_account_dialog).pack(fill=tk.X, pady=5)
        
        # Right Panel (Tabs for Console / Account View)
        right_panel = ttk.Frame(self.root, padding=10)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        notebook = ttk.Notebook(right_panel)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Live Logs Console
        console_tab = ttk.Frame(notebook)
        notebook.add(console_tab, text=" Live Console Logs ")
        
        self.console_text = tk.Text(console_tab, wrap=tk.WORD, bg='#11111b', fg='#cdd6f4', insertbackground='#cdd6f4', font=('Consolas', 10))
        self.console_text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        scrollbar = ttk.Scrollbar(console_tab, command=self.console_text.yview)
        scrollbar.pack(fill=tk.Y, side=tk.RIGHT)
        self.console_text.config(yscrollcommand=scrollbar.set)
        
        # Tab 2: Accounts Viewer
        db_tab = ttk.Frame(notebook)
        notebook.add(db_tab, text=" Accounts Database ")
        
        columns = ("id", "name", "password", "banned")
        self.tree = ttk.Treeview(db_tab, columns=columns, show="headings")
        self.tree.heading("id", text="Account ID")
        self.tree.heading("name", text="Username")
        self.tree.heading("password", text="Password")
        self.tree.heading("banned", text="Banned")
        
        self.tree.column("id", width=80, anchor=tk.CENTER)
        self.tree.column("name", width=200)
        self.tree.column("password", width=200)
        self.tree.column("banned", width=80, anchor=tk.CENTER)
        
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.refresh_tree()

    def process_logs(self):
        while not self.log_queue.empty():
            msg = self.log_queue.get()
            self.console_text.insert(tk.END, msg)
            self.console_text.see(tk.END)
        self.root.after(100, self.process_logs)

    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        for acc in self.db.accounts:
            self.tree.insert("", tk.END, values=(acc.data.id, acc.data.acc_name, acc.data.acc_pass, acc.data.is_banned))
        self.accs_label.config(text=f"Total Accounts: {len(self.db.accounts)}")

    def reload_db(self):
        self.db.accounts.clear()
        if self.db.load_accounts():
            print("Database reloaded successfully.")
        else:
            print("Failed to reload database (or file missing).")
        self.refresh_tree()

    def save_db(self):
        if self.db.save_accounts():
            print("Database saved successfully to accounts.json.")
            messagebox.showinfo("Saved", "Database saved successfully!")
        else:
            messagebox.showerror("Error", "Failed to save database.")

    def create_account_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Create Account")
        dialog.geometry("300x200")
        dialog.configure(bg='#1e1e2e')
        
        ttk.Label(dialog, text="Username:").pack(pady=5)
        entry_user = ttk.Entry(dialog)
        entry_user.pack(fill=tk.X, padx=20)
        
        ttk.Label(dialog, text="Password:").pack(pady=5)
        entry_pass = ttk.Entry(dialog, show="*")
        entry_pass.pack(fill=tk.X, padx=20)
        
        def save():
            name = entry_user.get().strip()
            password = entry_pass.get().strip()
            if not name or not password:
                messagebox.showerror("Error", "Fields cannot be blank")
                return
            
            # Check duplicate
            if any(acc.data.acc_name.lower() == name.lower() for acc in self.db.accounts):
                messagebox.showerror("Error", "Username already exists")
                return
            
            # Append new account
            from core.models import Account
            new_acc = Account()
            new_acc.data.id = self.db.last_used_id + 1
            self.db.last_used_id += 1
            new_acc.data.acc_name = name
            new_acc.data.acc_pass = password
            self.db.accounts.append(new_acc)
            self.db.save_accounts()  # Auto-save changes to file
            self.refresh_tree()
            print(f"Created account: {name}")
            dialog.destroy()
            
        ttk.Button(dialog, text="Create", command=save).pack(pady=15)

    def auto_refresh_accounts(self):
        # Auto-refresh account database display if the database count changes
        try:
            current_tree_count = len(self.tree.get_children())
            current_db_count = len(self.db.accounts)
            if current_tree_count != current_db_count:
                self.refresh_tree()
        except Exception:
            pass # Avoid crash if GUI window is closed
        self.root.after(1000, self.auto_refresh_accounts)

def run_gui():
    root = tk.Tk()
    gui = ServerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    run_gui()
