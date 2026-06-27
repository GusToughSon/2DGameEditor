# main.py
import threading
import asyncio
import sys
import os
from server.database import DatabaseManager
from server.network import GameServer
from server.gui import ServerGUI
import tkinter as tk
import http.server
import socketserver

def start_http_server():
    editor_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    web_dir = os.path.join(editor_dir, "WebClient", "dist")
    if os.path.exists(web_dir):
        os.chdir(web_dir)
        # Suppress logging to keep console clean
        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, format, *args):
                pass
            def do_GET(self):
                # Check if it's a tileset request
                if self.path.endswith("_TILESET.png"):
                    # Serve from the Saves directory
                    tileset_dir = os.path.join(editor_dir, "Saves", "ThePlayerCity", "TILESET")
                    filename = os.path.basename(self.path)
                    file_path = os.path.join(tileset_dir, filename)
                    if os.path.exists(file_path):
                        with open(file_path, 'rb') as f:
                            self.send_response(200)
                            self.send_header("Content-type", "image/png")
                            self.send_header("Access-Control-Allow-Origin", "*")
                            self.end_headers()
                            self.wfile.write(f.read())
                        return
                super().do_GET()
        with socketserver.TCPServer(("", 8080), QuietHandler) as httpd:
            print("WebClient HTTP Server listening on http://localhost:8080")
            httpd.serve_forever()
    else:
        print("WebClient dist folder not found. Run 'npm run build' in WebClient to enable browser play.")

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
    
    # Start WebClient HTTP server in a background thread
    http_thread = threading.Thread(target=start_http_server, daemon=True)
    http_thread.start()
    
    # Run the Tkinter GUI Dashboard in the main thread
    root = tk.Tk()
    app = ServerGUI(root)
    
    # Connect the database manager reference so GUI operations sync
    app.db = db
    app.refresh_tree()
    
    root.mainloop()

if __name__ == "__main__":
    main()
