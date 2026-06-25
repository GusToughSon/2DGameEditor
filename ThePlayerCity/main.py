# main.py
import threading
import asyncio
import sys
import os
from server.database import DatabaseManager
from server.network import GameServer
from server.gui import ServerGUI
import tkinter as tk

def start_network_thread(db_manager):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    server = GameServer(db_manager)
    loop.run_until_complete(server.start())

def main():
    # Initialize DB Manager
    db = DatabaseManager()
    db.load_accounts()
    
    # Start TCP network server in a background thread
    net_thread = threading.Thread(target=start_network_thread, args=(db,), daemon=True)
    net_thread.start()
    
    # Run the Tkinter GUI Dashboard in the main thread
    root = tk.Tk()
    app = ServerGUI(root)
    
    # Connect the database manager reference so GUI operations sync
    app.db = db
    app.refresh_tree()
    
    root.mainloop()

if __name__ == "__main__":
    main()
