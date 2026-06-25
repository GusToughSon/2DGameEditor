# client/network.py
import socket
import threading
import queue
from core.packets import VERSION, pack_json, read_packet_sync

class GameClientNetwork:
    """Manages the TCP socket connection to the server for the live gameplay renderer.
    Runs a background thread to receive and decrypt incoming server packets.
    """
    def __init__(self, host="127.0.0.1", port=1338):
        self.host = host
        self.port = port
        self.sock = None
        self.running = False
        self.incoming_queue = queue.Queue()
        self.thread = None

    def connect_and_enter(self, username, password, char_slot=0) -> dict:
        """Connects to the server, signs in, enters the game world, and starts the receive thread.
        Returns the initial world state or error details.
        """
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            
            # Send enter_game request
            req = {
                "type": "enter_game",
                "username": username,
                "password": password,
                "char_slot": char_slot
            }
            self.sock.sendall(pack_json(req))
            
            resp = read_packet_sync(self.sock)
            if resp and resp.get("type") == "enter_game_response" and resp.get("success"):
                self.running = True
                self.thread = threading.Thread(target=self._recv_loop, daemon=True)
                self.thread.start()
                return resp
            else:
                self.sock.close()
                return {"success": False, "error": resp.get("error") if resp else "No response"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def send_action(self, packet: dict):
        """Send a gameplay action packet to the server."""
        if not self.running or not self.sock:
            return
        try:
            self.sock.sendall(pack_json(packet))
        except Exception as e:
            print(f"[NET ERROR] Failed to send packet: {e}")
            self.running = False

    def _recv_loop(self):
        """Continuously polls incoming server packets and queue them."""
        while self.running:
            try:
                packet = read_packet_sync(self.sock)
                if packet is None:
                    print("[NET] Connection closed by server.")
                    self.running = False
                    break
                self.incoming_queue.put(packet)
            except Exception as e:
                print(f"[NET ERROR] Connection exception: {e}")
                self.running = False
                break
        if self.sock:
            self.sock.close()

    def disconnect(self):
        self.running = False
        if self.sock:
            self.sock.close()
