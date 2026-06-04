import os
from PIL import Image
import json
import sqlite3
import threading
import asyncio
import struct
import re
import time
import sys
from typing import Dict, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    global main_loop
    main_loop = asyncio.get_running_loop()
    print("[SYSTEM] Event loop captured.")
    sys.stdout.flush()
    yield

app = FastAPI(lifespan=lifespan)

# --- Game Data Loading ----

class HryParser:
    @staticmethod
    def parse(file_path):
        if not os.path.exists(file_path):
            return {}
        
        data = {
            "defines": {},
            "objects": {}
        }
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            print(f"[ERROR] Failed to read {file_path}: {e}")
            return data
            
        # Parse #Define and DEFINE
        # Matches: #Define KEY VAL or DEFINE KEY VAL (handles comments)
        define_pattern = re.compile(r"(?:#Define|DEFINE)\s+([A-Za-z0-9_]+)(?:\s+([^\n/]+))?")
        for match in define_pattern.finditer(content):
            key = match.group(1)
            raw_val = match.group(2)
            val = raw_val.strip() if raw_val else 1 # Default to 1 if no value (like DEFINE FLAG)
            
            # Try to convert to int/bool if possible
            try:
                if val.lower() == "true":
                    val = 1
                elif val.lower() == "false":
                    val = 0
                else:
                    # Handle multiple values (comma or space separated)
                    if "," in val:
                        val = [int(v.strip()) for v in val.split(",")]
                    elif " " in val.strip():
                        parts = val.strip().split()
                        try:
                            val = [int(v.strip()) for v in parts]
                        except:
                            pass
                    else:
                        val = int(val)
            except ValueError:
                pass
            data["defines"][key] = val
            
        # Parse Object blocks
        object_pattern = re.compile(r"Object\s+\"([^\"]+)\"\s*\{([^\}]+)\}", re.DOTALL)
        for match in object_pattern.finditer(content):
            obj_name = match.group(1)
            obj_body = match.group(2)
            data["objects"][obj_name] = obj_body.strip()
            
        return data

class GameData:
    def __init__(self, root_dir, on_config_change=None):
        print(f"[DEBUG] Initializing game data from: {root_dir}")
        self.root_dir = root_dir
        self.on_config_change = on_config_change
        self.load_folder = os.path.join(root_dir, "LoadFolder")
        self.active_save = self.find_active_save()
        
        self.hry_data = {}
        self.hry_last_modified = {}
        
        if self.active_save:
            self.save_path = os.path.join(self.load_folder, self.active_save)
            print(f"[DEBUG] Active save folder: {self.active_save}")
            self.tile_properties = self.load_json(os.path.join(self.save_path, "WorldProperties.json")).get("World", {})
            self.tile_types = self.load_json(os.path.join(self.save_path, "Types.json"))
            self.map_data = self.load_world_map()
            self.load_all_hry()
            # Cache chunks to a static JSON file to avoid memory issues and slow serialization
            self.chunks = self.load_chunks()
            self.chunks_cache_file = os.path.join(self.save_path, "Maps", "Chunks_Cache.json")
            print(f"[DEBUG] Caching {len(self.chunks)} chunks to {self.chunks_cache_file}...")
            with open(self.chunks_cache_file, "w") as f:
                json.dump(self.chunks, f)
            # We KEEP self.chunks for server-side validation
        else:
            print("[WARNING] No save folder found in LoadFolder!")
            self.tile_properties = {}
            self.tile_types = {}
            self.map_data = []
            self.chunks = {}

        # Stride detection
        self.config = self.get_config()
        self.tile_size = self.config.get("TILE_SIZE", 16)
        self.tiles_per_row = 14
        if self.active_save:
            ts_path = os.path.join(self.save_path, "TILESET", "World_TILESET.png")
            if os.path.exists(ts_path):
                try:
                    with Image.open(ts_path) as img:
                        self.tiles_per_row = img.width // self.tile_size
                        print(f"[DEBUG] Detected Tileset Stride: {self.tiles_per_row}")
                except Exception as e:
                    print(f"[ERROR] Stride probe failed: {e}")

        # Start Watcher
        self.stop_watcher = False
        self.watcher_thread = threading.Thread(target=self._hry_watcher_loop, daemon=True)
        self.watcher_thread.start()
        
        print("[DEBUG] Game data initialization complete.")

    def find_active_save(self):
        if not os.path.exists(self.load_folder):
            os.makedirs(self.load_folder, exist_ok=True)
            return None
        
        # Treat the first directory as the active save for now
        for entry in os.listdir(self.load_folder):
            if os.path.isdir(os.path.join(self.load_folder, entry)):
                return entry
        return None

    def load_json(self, path):
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
        return {}

    def normalize_cid(self, cid):
        """ Returns the numeric part of a CID (strips C_). """
        if isinstance(cid, str) and cid.startswith("C_"):
            return cid[2:]
        return str(cid)

    def load_world_map(self):
        db_path = os.path.join(self.save_path, "Maps", "World.db")
        if not os.path.exists(db_path):
            # Fallback to World.json
            world_json_path = os.path.join(self.save_path, "Maps", "World.json")
            if os.path.exists(world_json_path):
                data = self.load_json(world_json_path)
                return data.get("grid", [])
            return [["0" for _ in range(32)] for _ in range(32)]

        # --- SMART DRIVER: Detect Format ---
        with open(db_path, "rb") as f:
            magic = f.read(4)
        
        grid = []
        if magic == b"WBF!":
            # Binary Driver Format (from BinaryDriver.py logic)
            print(f"[DEBUG] Loading Binary World Map (WBF!): {db_path}")
            with open(db_path, "rb") as f:
                header = f.read(16)
                _, version, tile_map_id, width, height = struct.unpack("<IIHHH", header)
                raw = f.read(width * height * 4)
                for y in range(height):
                    row = []
                    for x in range(width):
                        idx = (y * width + x) * 4
                        chunk_id, world_data = struct.unpack("<hh", raw[idx:idx+4])
                        # Keep C_ prefix for client consistency
                        row.append(f"C_{chunk_id}")
                    grid.append(row)
        else:
            # SQLite Format
            print(f"[DEBUG] Loading SQLite World Map: {db_path}")
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT x, y, chunk_id FROM world_grid")
                rows = cursor.fetchall()
                conn.close()
                
                if not rows: return [["0" * 32] for _ in range(32)]
                
                max_x = max(r[0] for r in rows)
                max_y = max(r[1] for r in rows)
                grid = [["0"] * (max_x + 1) for _ in range(max_y + 1)]
                
                for x, y, cid in rows:
                    # Force C_ prefix if not present to match memory state
                    cid_str = str(cid)
                    if not cid_str.startswith("C_"):
                        cid_str = f"C_{cid_str}"
                    grid[y][x] = cid_str
            except Exception as e:
                print(f"[ERROR] SQL World Load failed: {e}")
                return [["0" for _ in range(32)] for _ in range(32)]
        
        return grid

    def load_chunks(self):
        db_path = os.path.join(self.save_path, "Maps", "Chunks.db")
        if os.path.exists(db_path):
            print(f"[DEBUG] Loading chunks from: {db_path}")
            try:
                import sqlite3
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT id, data FROM chunks")
                chunks = {str(row[0]): json.loads(row[1]) for row in cursor.fetchall()}
                conn.close()
                return chunks
            except Exception as e:
                print(f"[ERROR] Failed to load Chunks.db: {e}")
        
        # Fallback to Chunks.json
        chunks_json_path = os.path.join(self.save_path, "Maps", "Chunks.json")
        return self.load_json(chunks_json_path)

    def load_all_hry(self):
        hry_dir = os.path.join(self.save_path, "HAIRY")
        if not os.path.exists(hry_dir):
            return
            
        for file in os.listdir(hry_dir):
            if file.endswith(".hry"):
                path = os.path.join(hry_dir, file)
                self.hry_data[file] = HryParser.parse(path)
                self.hry_last_modified[path] = os.path.getmtime(path)

    def _hry_watcher_loop(self):
        hry_dir = os.path.join(self.save_path, "HAIRY")
        while not self.stop_watcher:
            if os.path.exists(hry_dir):
                for file in os.listdir(hry_dir):
                    if file.endswith(".hry"):
                        path = os.path.join(hry_dir, file)
                        try:
                            mtime = os.path.getmtime(path)
                            if path not in self.hry_last_modified or mtime > self.hry_last_modified[path]:
                                print(f"[DEBUG] Hry file updated: {file}")
                                sys.stdout.flush()
                                self.hry_data[file] = HryParser.parse(path)
                                self.hry_last_modified[path] = mtime
                                # Update config if it was Defines.hry or Player.hry
                                if file == "Defines.hry" or file == "Player.hry":
                                    self.config = self.get_config()
                                    self.tile_size = self.config.get("TILE_SIZE", self.tile_size)
                                    if self.on_config_change:
                                        self.on_config_change(self.config)
                        except Exception as e:
                            print(f"[ERROR] Watcher error: {e}")
                            sys.stdout.flush()
            time.sleep(1)

    def get_config(self):
        # Merge defines from Defines.hry and Player.hry
        config = {}
        if "Defines.hry" in self.hry_data:
            config.update(self.hry_data["Defines.hry"]["defines"])
        if "Player.hry" in self.hry_data:
            config.update(self.hry_data["Player.hry"]["defines"])
        return config

    def get_tile_at(self, wx, wy, layer=0):
        CHUNK_SIZE = 16
        rows = len(self.map_data)
        cols = len(self.map_data[0]) if rows > 0 else 0
        
        if wx < 0 or wy < 0 or wx >= cols * CHUNK_SIZE or wy >= rows * CHUNK_SIZE:
            return 0
            
        cx, cy = wx // CHUNK_SIZE, wy // CHUNK_SIZE
        tx, ty = wx % CHUNK_SIZE, wy % CHUNK_SIZE
        
        chunk_id = self.map_data[cy][cx]
        # Normalize mapping: World says C_1598, look for 1598 or C_1598 in chunks
        raw_id = self.normalize_cid(chunk_id)
            
        # We need to load chunks if they aren't in memory
        # In our current server, we cache them to a file, so we should check game_data.chunks or re-read
        # For validation, we'll use the chunks loaded during init
        chunk = None
        if hasattr(self, 'chunks'):
             # Try numeric first, then prefixed
             chunk = self.chunks.get(raw_id) or self.chunks.get(f"C_{raw_id}")
        
        if chunk and "data" in chunk:
            layer_key = "ground" if layer == 0 else "objects"
            if layer_key in chunk["data"]:
                data_grid = chunk["data"][layer_key]
                if ty < len(data_grid) and tx < len(data_grid[ty]):
                    return data_grid[ty][tx]
        return 0

    def is_passable(self, wx, wy):
        for layer in range(2):
            t_id = self.get_tile_at(wx, wy, layer)
            if t_id == 0:
                if layer == 0: return False # Empty ground is blocked
                continue
            
            # Check Types.json
            str_id = str(t_id)
            if str_id in self.tile_types:
                if self.tile_types[str_id].get("properties", {}).get("block_move"):
                    return False
                    
            # Check WorldProperties.json (1-indexed tileset coords)
            pr = self.tiles_per_row
            tileset_idx = t_id # Removed -1 offset
            ty = (tileset_idx // pr) + 1
            tx = (tileset_idx % pr) + 1
            prop_key = f"{ty},{tx}"
            if prop_key in self.tile_properties:
                if self.tile_properties[prop_key].get("block_move"):
                    return False
                
        return True

# Initialize Game Data
base_dir = os.path.dirname(os.path.abspath(__file__))
# We'll set the loop later during startup
main_loop = None

def broadcast_config_update(cfg):
    if main_loop:
        asyncio.run_coroutine_threadsafe(manager.broadcast({"type": "config_update", "config": cfg}), main_loop)

game_data = GameData(base_dir, on_config_change=broadcast_config_update)

# --- Server Logic ---

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.players: Dict[str, dict] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        # Load player basis from Player.hry
        player_config = game_data.hry_data.get("Player.hry", {}).get("defines", {})
        
        # Spawn Logic
        spawn_pos = player_config.get("PLAYERSTART", [300, 300])
        px = spawn_pos[0] if isinstance(spawn_pos, list) else 300
        py = spawn_pos[1] if isinstance(spawn_pos, list) and len(spawn_pos) > 1 else 300

        self.players[client_id] = {
            "id": client_id,
            "x": px, "y": py,
            "hp": player_config.get("LOCAL_HEALTH", 100),
            "max_hp": player_config.get("LOCAL_HEALTH", 100),
            "strength": player_config.get("LOCAL_STRENGTH", 10),
            "name": client_id,
            "category": "NPCs",
            "type": "player"
        }
        print(f"[DEBUG] Client {client_id} connected. Current players: {len(self.players)}")
        sys.stdout.flush()
        # Send initial world state - only objects near the player
        px, py = self.players[client_id]["x"], self.players[client_id]["y"]
        # In the new system, spawns might be handled differently, 
        # but for now we'll use an empty list if not defined in the old way
        nearby_spawns = []
        
        await self.send_personal_message({
            "type": "init", 
            "player": self.players[client_id],
            "players": self.players,
            "spawns": nearby_spawns
        }, websocket)
        await self.broadcast({"type": "player_joined", "player": self.players[client_id]})

    async def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.players:
            del self.players[client_id]
        print(f"[DEBUG] Client {client_id} disconnected. Current players: {len(self.players)}")
        sys.stdout.flush()
        await self.broadcast({"type": "player_left", "player_id": client_id})

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: dict):
        for client_id, connection in list(self.active_connections.items()):
            try:
                await connection.send_json(message)
            except:
                # If connection is dead, remove it silently
                pass

manager = ConnectionManager()

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_json()
            if data["type"] == "move":
                player = manager.players[client_id]
                new_x, new_y = data["x"], data["y"]
                
                # Server-Side Validation
                # 1. Distance check (only 1 tile allowed per move)
                dx = abs(new_x - player["x"])
                dy = abs(new_y - player["y"])
                
                is_valid = True
                if dx > 1 or dy > 1:
                    print(f"[SECURITY] Client {client_id} tried to teleport from ({player['x']},{player['y']}) to ({new_x},{new_y})")
                    is_valid = False
                
                # 2. Passability check
                if is_valid and not game_data.is_passable(new_x, new_y):
                    print(f"[SECURITY] Client {client_id} tried to move into blocked tile at ({new_x},{new_y})")
                    is_valid = False
                
                if is_valid:
                    player["x"], player["y"] = new_x, new_y
                
                # Broadcast the position (even if invalid, to snap the client back)
                await manager.broadcast({
                    "type": "update",
                    "player_id": client_id,
                    "x": player["x"],
                    "y": player["y"]
                })
            elif data["type"] == "chat":
                await manager.broadcast({
                    "type": "chat",
                    "player_id": client_id,
                    "text": data["text"]
                })
    except WebSocketDisconnect:
        await manager.disconnect(client_id)

@app.get("/favicon.ico")
async def favicon():
    return FileResponse(os.path.join(base_dir, "favicon.ico")) if os.path.exists(os.path.join(base_dir, "favicon.ico")) else None

# Ensure directories exist for mounting
for d in ["gfx", "AnimImages"]:
    path = os.path.join(base_dir, d)
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)

app.mount("/gfx", StaticFiles(directory=os.path.join(base_dir, "gfx")), name="gfx")
if game_data.active_save:
    save_path = os.path.join(game_data.load_folder, game_data.active_save)
    if os.path.exists(save_path):
        app.mount("/save", StaticFiles(directory=save_path), name="save")
app.mount("/AnimImages", StaticFiles(directory=os.path.join(base_dir, "AnimImages")), name="AnimImages")

@app.get("/debug_tile")
async def debug_tile(x: int, y: int):
    return {
        "x": x, "y": y,
        "ground": game_data.get_tile_at(x, y, 0),
        "objects": game_data.get_tile_at(x, y, 1)
    }

@app.get("/map_data")
async def get_map_data():
    return {
        "grid": game_data.map_data, 
        "tile_size": game_data.tile_size,
        "tiles_per_row": game_data.tiles_per_row
    }

@app.get("/chunks")
async def get_chunks():
    # Redirect to the static cache file for better performance
    return FileResponse(game_data.chunks_cache_file)

@app.get("/tile_types")
async def get_tile_types():
    return game_data.tile_types

@app.get("/world_properties")
async def get_world_properties():
    return game_data.tile_properties

@app.get("/map")
async def get_map():
    if game_data.active_save:
        map_path = os.path.join(game_data.save_path, "Maps", "World.json")
        if os.path.exists(map_path):
            return FileResponse(map_path)
    return {"error": "Map not found"}

@app.get("/style.css")
async def get_css():
    return FileResponse(os.path.join(base_dir, "style.css"))

@app.get("/game.js")
async def get_js():
    return FileResponse(os.path.join(base_dir, "game.js"))

@app.get("/")
async def get():
    return FileResponse(os.path.join(base_dir, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
