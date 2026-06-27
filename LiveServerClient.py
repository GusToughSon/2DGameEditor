import socket
import json
import threading
import queue

_instance = None

class LiveServerClientImpl:
    def __init__(self, host, port, auth):
        self.host = host
        self.port = int(port)
        self.auth = auth
        self.active = True
        self.sock = None
        self.send_queue = queue.Queue()
        
        self.live_entities = {} # map_name -> {entity_id -> data}
        self.entities_lock = threading.Lock()
        
        # Start background worker to process sending queue without blocking the UI
        self.worker_thread = threading.Thread(target=self._network_worker, daemon=True)
        self.worker_thread.start()
        
        # Start background receiver thread for bi-directional live sync
        self.recv_thread = threading.Thread(target=self._network_recv_worker, daemon=True)
        self.recv_thread.start()
        
    def _network_recv_worker(self):
        buffer = ""
        while self.active:
            if not self.sock:
                import time
                time.sleep(1)
                continue
            try:
                # Use a short timeout for the recv block so it can check self.active
                self.sock.settimeout(1.0)
                data = self.sock.recv(4096)
                if not data:
                    # Connection closed by server
                    self.sock.close()
                    self.sock = None
                    continue
                buffer += data.decode('utf-8')
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        self._handle_server_message(line)
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[LiveServerClient] Recv error: {e}")
                if self.sock:
                    self.sock.close()
                    self.sock = None
                    
    def _handle_server_message(self, line):
        try:
            payload = json.loads(line)
            action = payload.get("action")
            if action == "ENTITY_UPDATE":
                map_name = payload.get("map", "WORLD")
                entity_id = payload.get("id")
                if entity_id:
                    with self.entities_lock:
                        if map_name not in self.live_entities:
                            self.live_entities[map_name] = {}
                        self.live_entities[map_name][entity_id] = payload
            elif action == "ENTITY_REMOVE":
                map_name = payload.get("map", "WORLD")
                entity_id = payload.get("id")
                with self.entities_lock:
                    if map_name in self.live_entities and entity_id in self.live_entities[map_name]:
                        del self.live_entities[map_name][entity_id]
        except Exception as e:
            print(f"[LiveServerClient] Failed to parse message: {e}")

    def _network_worker(self):
        # Initial connection
        self._connect()
        while self.active:
            try:
                payload = self.send_queue.get(timeout=1.0)
                if not self.sock:
                    self._connect()
                
                if self.sock:
                    # Append auth token to payload
                    payload["auth_token"] = self.auth
                    msg = json.dumps(payload) + "\n"
                    self.sock.sendall(msg.encode('utf-8'))
            except queue.Empty:
                pass
            except Exception as e:
                print(f"[LiveServerClient] Network error: {e}")
                if self.sock:
                    self.sock.close()
                    self.sock = None
                    
    def _connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            # Restore short timeout for recv worker looping
            self.sock.settimeout(1.0)
            print(f"[LiveServerClient] Connected to {self.host}:{self.port}")
        except Exception as e:
            print(f"[LiveServerClient] Failed to connect: {e}")
            self.sock = None
            
    def send(self, action, data=None):
        payload = {"action": action}
        if data:
            payload.update(data)
        self.send_queue.put(payload)

def initialize(host, port, auth):
    global _instance
    if not _instance:
        _instance = LiveServerClientImpl(host, port, auth)

def is_active():
    global _instance
    return _instance is not None

def send(action, data=None):
    global _instance
    if _instance:
        _instance.send(action, data)

def get_entities(map_name):
    global _instance
    if not _instance:
        return {}
    with _instance.entities_lock:
        return _instance.live_entities.get(map_name, {}).copy()

