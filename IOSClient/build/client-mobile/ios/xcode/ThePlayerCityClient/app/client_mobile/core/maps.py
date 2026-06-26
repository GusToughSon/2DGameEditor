# core/maps.py - Map Database Manager for ThePlayerCity Python Port
# Reads World.db (chunk grid) and Chunks.db (chunk tile data) from the 2DGameEditor save.
import os
import sqlite3
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

DEFAULT_PROJECT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "Saves",
    "ThePlayerCity"
)
CHUNK_SIZE = 16  # 16x16 tiles per chunk


def normalize_chunk_id(raw_id):
    """Normalize a chunk ID to the 'C_#' format used as dict keys."""
    s = str(raw_id).strip()
    if s.startswith("C_"):
        return s
    return f"C_{s}"


@dataclass
class TileInfo:
    """Represents property info for a tile type.
    Mirrors C++ TileClass."""
    block: int = 0
    visibility: int = 0
    name: str = ""
    r: int = 255
    g: int = 255
    b: int = 255
    animated: int = 0
    usetype: int = 0


@dataclass
class ObjectType:
    """Represents a type definition for an interactive world object.
    Mirrors C++ ObjectsStruct."""
    name: str = ""
    openable: bool = False
    block: bool = False
    vis_block: bool = False
    use_type: int = 0
    animated: bool = False


@dataclass
class MapObject:
    """Represents an interactive object instance placed in the world.
    Mirrors C++ MapObjects."""
    x: int = 0
    y: int = 0
    type_id: int = 0
    on: bool = True
    container: List[int] = field(default_factory=lambda: [0] * 8)
    text: str = ""


@dataclass
class CrimSpawn:
    """Represents a criminal spawn point coordinate.
    Mirrors C++ CrimSpawnList."""
    x: int = 0
    y: int = 0


class MapDatabase:
    def __init__(self, project_path: str = DEFAULT_PROJECT_PATH):
        self.project_path = project_path
        self.world_db_path = os.path.join(project_path, "Maps", "World.db")
        self.chunks_db_path = os.path.join(project_path, "Maps", "Chunks.db")
        self.properties_path = os.path.join(project_path, "WorldProperties.json")
        self.types_path = os.path.join(project_path, "Types.json")

        self.grid = []           # 2D list[row][col] of normalised chunk IDs ("C_#")
        self.chunks = {}         # dict  { "C_#": { "name":..., "data": {"ground":[[]], "objects":[[]]} } }
        self.properties = {}     # WorldProperties.json -> World section
        self.types = {}          # Types.json full dict
        self.tiles_per_row = 17  # World_TILESET stride (280px / 16px)

        # New port additions
        self.tile_info_cache: Dict[int, TileInfo] = {}
        self.object_types: Dict[int, ObjectType] = {}
        self.map_objects: List[MapObject] = []
        self.crim_spawns: List[CrimSpawn] = []
        self.safe_zones: List[List[int]] = [] # 2D array matching chunk grid size (e.g. 32x32)
        self.encounters: Dict[int, dict] = {} # encounter_id -> encounter dict
        self.chunk_encounters: List[List[Optional[int]]] = [] # 2D array mapping (cy, cx) to encounter_id

    def load(self, map_name="WORLD"):
        print(f"[MAPS] Loading map data from project: {self.project_path}")
        self.load_world_grid(map_name)
        self.load_chunks()
        self.load_properties()
        self.load_types()
        self.init_safe_zones(map_name)
        self.init_encounters(map_name)
        self.load_crim_spawns()
        self.load_map_objects()
        print(f"[MAPS] Map data loaded. Grid: {len(self.grid)}x{len(self.grid[0]) if self.grid else 0}, "
              f"Chunks: {len(self.chunks)}, Safe Zones: {len(self.safe_zones)}x{len(self.safe_zones[0]) if self.safe_zones else 0}")

    def init_encounters(self, map_name="WORLD"):
        """Initializes the spawn encounters chunk-level grid and definitions."""
        map_name = map_name.upper()
        rows = len(self.grid)
        cols = len(self.grid[0]) if rows > 0 else 0
        self.chunk_encounters = [[None] * cols for _ in range(rows)]
        self.encounters = {}

        # 1. Load Encounter definitions
        enc_path = os.path.join(self.project_path, "Maps", "Encounters.json")
        if os.path.exists(enc_path):
            try:
                with open(enc_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for enc in data.get("encounters", []):
                        eid = enc.get("id")
                        if eid is not None:
                            self.encounters[int(eid)] = enc
                print(f"[MAPS] Loaded {len(self.encounters)} spawn encounter definitions.")
            except Exception as e:
                print(f"[MAPS WARNING] Failed to load Encounters.json: {e}")

        # 2. Load Chunk assignments
        chunk_enc_path = os.path.join(self.project_path, "Maps", "ChunkEncounters.json")
        if os.path.exists(chunk_enc_path):
            try:
                with open(chunk_enc_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for ce in data.get("chunk_encounters", []):
                        if ce.get("map", "WORLD").upper() == map_name:
                            cx = ce.get("x", 0)
                            cy = ce.get("y", 0)
                            eid = ce.get("encounter_id")
                            if 0 <= cy < rows and 0 <= cx < cols and eid is not None:
                                self.chunk_encounters[cy][cx] = int(eid)
                print(f"[MAPS] Loaded chunk-to-encounter assignments.")
            except Exception as e:
                print(f"[MAPS WARNING] Failed to load ChunkEncounters.json: {e}")

    def init_safe_zones(self, map_name="WORLD"):
        """Initializes the SafeZones chunk-level grid (matching chunk grid dimensions)."""
        map_name = map_name.upper()
        rows = len(self.grid)
        cols = len(self.grid[0]) if rows > 0 else 0
        # Initialize safe zone value to 0 (none) for all chunks.
        # Can be loaded from config/JSON if needed.
        self.safe_zones = [[0] * cols for _ in range(rows)]

        # Try to load SafeZones config if it exists
        safezones_path = os.path.join(self.project_path, "Maps", "SafeZones.json")
        if os.path.exists(safezones_path):
            try:
                with open(safezones_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for sz in data.get("safe_zones", []):
                        if sz.get("map", "WORLD").upper() == map_name:
                            cx, cy, sz_type = sz.get("x", 0), sz.get("y", 0), sz.get("type", 0)
                            if 0 <= cy < rows and 0 <= cx < cols:
                                self.safe_zones[cy][cx] = sz_type
                print(f"[MAPS] Loaded safe zone configurations.")
            except Exception as e:
                print(f"[MAPS WARNING] Failed to load SafeZones.json: {e}")

    def load_crim_spawns(self):
        """Load criminal spawn points from the map database/JSON."""
        self.crim_spawns = []
        crim_path = os.path.join(self.project_path, "Maps", "CrimSpawns.json")
        if os.path.exists(crim_path):
            try:
                with open(crim_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for pt in data.get("spawns", []):
                        self.crim_spawns.append(CrimSpawn(x=pt.get("x", 0), y=pt.get("y", 0)))
                print(f"[MAPS] Loaded {len(self.crim_spawns)} criminal spawn points.")
            except Exception as e:
                print(f"[MAPS WARNING] Failed to load CrimSpawns.json: {e}")

    def load_map_objects(self):
        """Loads interactive map objects (chests, doors, tables, etc.)."""
        self.map_objects = []
        
        # Populate default registered ObjectTypes
        # Treat 1858 as Wooden Door (openable, blocks move/vis)
        self.object_types[1858] = ObjectType(name="Wooden Door", openable=True, block=True, vis_block=True)
        # Treat 640 as Wooden Sign (blocks move, has text)
        self.object_types[640] = ObjectType(name="Wooden Sign", openable=False, block=True, vis_block=False)

        # Load custom ObjectTypes from JSON
        obj_types_path = os.path.join(self.project_path, "Maps", "ObjectTypes.json")
        if os.path.exists(obj_types_path):
            try:
                with open(obj_types_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        self.object_types[int(k)] = ObjectType(
                            name=v.get("name", "Object"),
                            openable=v.get("openable", False),
                            block=v.get("block", False),
                            vis_block=v.get("vis_block", False),
                            use_type=v.get("use_type", 0),
                            animated=v.get("animated", False)
                        )
                print(f"[MAPS] Loaded custom ObjectTypes from JSON.")
            except Exception as e:
                print(f"[MAPS WARNING] Failed to load ObjectTypes.json: {e}")

        objects_path = os.path.join(self.project_path, "Maps", "MapObjects.json")
        loaded_from_json = False
        if os.path.exists(objects_path):
            try:
                with open(objects_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for obj in data.get("objects", []):
                        self.map_objects.append(MapObject(
                            x=obj.get("x", 0),
                            y=obj.get("y", 0),
                            type_id=obj.get("type_id", 0),
                            on=obj.get("on", True),
                            container=obj.get("container", [0] * 8),
                            text=obj.get("text", "")
                        ))
                print(f"[MAPS] Loaded {len(self.map_objects)} map objects from JSON.")
                loaded_from_json = True
            except Exception as e:
                print(f"[MAPS WARNING] Failed to load MapObjects.json: {e}")

        # Auto-scan map chunks to register map objects dynamically
        scanned_count = 0
        for chunk_id, chunk in self.chunks.items():
            data = chunk.get("data", {})
            objects_layer = data.get("objects", [])
            for r_idx, row in enumerate(objects_layer):
                for c_idx, val in enumerate(row):
                    if val in [1858, 640]:
                        # Translate local chunk coordinate to world coordinate
                        # Find where this chunk is in the grid
                        for cy, grid_row in enumerate(self.grid):
                            if chunk_id in grid_row:
                                cx = grid_row.index(chunk_id)
                                wx = cx * CHUNK_SIZE + c_idx
                                wy = cy * CHUNK_SIZE + r_idx
                                
                                # Check if already exists
                                exists = any(o.x == wx and o.y == wy for o in self.map_objects)
                                if not exists:
                                    text = f"Welcome to tile ({wx}, {wy})!" if val == 640 else ""
                                    self.map_objects.append(MapObject(
                                        x=wx,
                                        y=wy,
                                        type_id=val,
                                        on=True,
                                        text=text
                                    ))
                                    scanned_count += 1
                                break
        if scanned_count > 0:
            print(f"[MAPS] Dynamically registered {scanned_count} map objects (doors/signs) from chunks.")

    # ------------------------------------------------------------------
    # World Grid  (World.db → world_grid table)
    # ------------------------------------------------------------------
    def load_world_grid(self, map_name="WORLD"):
        map_name = map_name.upper()
        if not os.path.exists(self.world_db_path):
            print(f"[MAPS WARNING] {self.world_db_path} not found. Using empty 32x32 grid.")
            self.grid = [["C_0"] * 32 for _ in range(32)]
            return

        try:
            conn = sqlite3.connect(self.world_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT x, y, chunk_id FROM world_grid WHERE map_name = ?", (map_name,))
            rows = cursor.fetchall()
            conn.close()

            if not rows:
                self.grid = [["C_0"] * 32 for _ in range(32)]
                return

            max_x = max(r[0] for r in rows)
            max_y = max(r[1] for r in rows)
            self.grid = [["C_0"] * (max_x + 1) for _ in range(max_y + 1)]

            for x, y, cid in rows:
                self.grid[y][x] = normalize_chunk_id(cid)

            print(f"[MAPS] World grid loaded: {len(self.grid)} rows x {len(self.grid[0])} cols")
        except Exception as e:
            print(f"[MAPS ERROR] Failed to load world grid: {e}")
            self.grid = [["C_0"] * 32 for _ in range(32)]

    # ------------------------------------------------------------------
    # Chunks  (Chunks.db → chunks table)
    # ------------------------------------------------------------------
    def load_chunks(self):
        if not os.path.exists(self.chunks_db_path):
            print(f"[MAPS WARNING] {self.chunks_db_path} not found.")
            return

        try:
            conn = sqlite3.connect(self.chunks_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id, data FROM chunks")
            self.chunks = {}
            for row in cursor.fetchall():
                key = normalize_chunk_id(row[0])
                self.chunks[key] = json.loads(row[1])
            conn.close()
            print(f"[MAPS] Loaded {len(self.chunks)} chunks from Chunks.db")
        except Exception as e:
            print(f"[MAPS ERROR] Failed to load Chunks.db: {e}")

    # ------------------------------------------------------------------
    # Properties & Types
    # ------------------------------------------------------------------
    def load_properties(self):
        if os.path.exists(self.properties_path):
            try:
                with open(self.properties_path, "r", encoding="utf-8") as f:
                    self.properties = json.load(f).get("World", {})
                print(f"[MAPS] Loaded {len(self.properties)} tile properties.")
            except Exception as e:
                print(f"[MAPS ERROR] WorldProperties.json: {e}")
        else:
            print("[MAPS WARNING] WorldProperties.json not found.")

    def load_types(self):
        if os.path.exists(self.types_path):
            try:
                with open(self.types_path, "r", encoding="utf-8") as f:
                    self.types = json.load(f)
                print(f"[MAPS] Loaded {len(self.types)} type definitions.")
            except Exception as e:
                print(f"[MAPS ERROR] Types.json: {e}")
        else:
            print("[MAPS WARNING] Types.json not found.")

    # ------------------------------------------------------------------
    # Tile access  (world tile coordinates → tile ID)
    # ------------------------------------------------------------------
    def get_tile_at(self, wx: int, wy: int, layer: int = 0) -> int:
        """Return the tile ID at world-tile coordinates (wx, wy)."""
        grid_rows = len(self.grid)
        grid_cols = len(self.grid[0]) if grid_rows > 0 else 0

        # Bounds check in tile space
        if wx < 0 or wy < 0:
            return 0
        if wx >= grid_cols * CHUNK_SIZE or wy >= grid_rows * CHUNK_SIZE:
            return 0

        cx = wx // CHUNK_SIZE
        cy = wy // CHUNK_SIZE
        tx = wx % CHUNK_SIZE
        ty = wy % CHUNK_SIZE

        chunk_id = self.grid[cy][cx]
        chunk = self.chunks.get(chunk_id)
        if not chunk:
            return 0

        data = chunk.get("data")
        if not data:
            return 0

        layer_key = "ground" if layer == 0 else "objects"

        # Handle both dict and list data layouts
        if isinstance(data, dict):
            layer_data = data.get(layer_key)
        elif isinstance(data, list) and layer_key == "ground":
            layer_data = data
        else:
            return 0

        if layer_data is None:
            return 0

        # Access the tile value
        if isinstance(layer_data, list):
            if ty < len(layer_data):
                row = layer_data[ty]
                if isinstance(row, list) and tx < len(row):
                    return row[tx] or 0
        elif isinstance(layer_data, dict):
            row = layer_data.get(str(ty), layer_data.get(ty))
            if row is not None:
                if isinstance(row, dict):
                    return row.get(str(tx), row.get(tx, 0)) or 0
                elif isinstance(row, list) and tx < len(row):
                    return row[tx] or 0
        return 0

    # ------------------------------------------------------------------
    # Passability & Visibility Properties
    # ------------------------------------------------------------------
    def get_tile_properties(self, tile_id: int) -> Dict[str, Any]:
        """Fetch properties for a specific tile ID."""
        # Check Types.json first
        str_id = str(tile_id)
        if str_id in self.types:
            return self.types[str_id].get("properties", {})

        # Check WorldProperties.json (key format: "Y,X" 1-indexed)
        y_coord = (tile_id // self.tiles_per_row) + 1
        x_coord = (tile_id % self.tiles_per_row) + 1
        prop_key = f"{y_coord},{x_coord}"
        if prop_key in self.properties:
            return self.properties[prop_key]

        return {}

    def is_passable(self, wx: int, wy: int) -> bool:
        """Check if the player can walk on tile (wx, wy)."""
        has_open_door = False
        for obj in self.map_objects:
            if obj.x == wx and obj.y == wy:
                o_type = self.object_types.get(obj.type_id)
                if o_type:
                    if o_type.openable:
                        if obj.on:  # closed
                            return False
                        else:  # open
                            has_open_door = True
                    elif o_type.block:
                        return False

        for layer in range(2):
            if layer == 1 and has_open_door:
                continue
            t_id = self.get_tile_at(wx, wy, layer)
            if t_id == 0:
                if layer == 0:
                    return False  # No ground tile = blocked
                continue

            props = self.get_tile_properties(t_id)
            if props.get("block_move"):
                return False
        return True

    def is_visibility_blocking(self, wx: int, wy: int) -> bool:
        """Check if tile (wx, wy) blocks line of sight."""
        has_open_door = False
        for obj in self.map_objects:
            if obj.x == wx and obj.y == wy:
                o_type = self.object_types.get(obj.type_id)
                if o_type:
                    if o_type.openable:
                        if obj.on:  # closed
                            return True
                        else:  # open
                            has_open_door = True
                    elif o_type.vis_block:
                        return True

        for layer in range(2):
            if layer == 1 and has_open_door:
                continue
            t_id = self.get_tile_at(wx, wy, layer)
            if t_id == 0:
                continue
            props = self.get_tile_properties(t_id)
            if props.get("block_light") or props.get("visibility") == 1:
                return True
        return False

    def is_safe_zone(self, wx: int, wy: int) -> int:
        """Returns the SafeZone type index at tile coordinates (wx, wy)."""
        cx = wx // CHUNK_SIZE
        cy = wy // CHUNK_SIZE
        if 0 <= cy < len(self.safe_zones) and 0 <= cx < len(self.safe_zones[0]):
            return self.safe_zones[cy][cx]
        return 0

    # ------------------------------------------------------------------
    # Line of Sight (LOS) calculation
    # Ported from legacy algorithms.cpp visibility flood-fill
    # ------------------------------------------------------------------
    def calculate_local_los(self, px: int, py: int) -> List[List[int]]:
        """Calculate local visibility around coordinates (px, py) on a 21x21 viewport.
        
        Returns:
            A 21x21 grid representing local tile visibility.
            Values matching legacy specifications:
              0 = Unseen / Hidden
              2 = Visibility blocked (e.g. wall/obstacle itself is visible but blocks view behind it)
              4 = Fully visible (walkable/clear view)
              5 = Fully visible border or adjacent override
        """
        # 1. Initialize vis_block table (21x21) representing whether local grid tiles block light
        vis_block = [[0] * 21 for _ in range(21)]
        for y in range(21):
            for x in range(21):
                wx = px - 10 + x
                wy = py - 10 + y
                # Is it blocked?
                if self.is_visibility_blocking(wx, wy):
                    vis_block[y][x] = 1

        # Also block via any MapObject with vis_block configuration
        for obj in self.map_objects:
            if abs(px - obj.x) <= 10 and abs(py - obj.y) <= 10:
                local_x = obj.x - px + 10
                local_y = obj.y - py + 10
                if 0 <= local_x < 21 and 0 <= local_y < 21:
                    # If object has visibility blocking enabled
                    if obj.on:
                        # Fetch type if registered
                        o_type = self.object_types.get(obj.type_id)
                        if o_type and o_type.vis_block:
                            vis_block[local_y][local_x] = 1

        # 2. calclos(0) - Initialize Visible matrix
        visible_matrix = [[0] * 21 for _ in range(21)]
        for y in range(21):
            for x in range(21):
                if vis_block[y][x] > 0:
                    visible_matrix[y][x] = 2

        # 3. Player tile is set to 0 for flood-fill start
        visible_matrix[10][10] = 0

        # 4. recurfill(10, 10) - flood fill visibility
        def recurfill(x: int, y: int):
            visible_matrix[y][x] = 4
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, 1), (1, -1), (1, 1), (-1, -1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < 21 and 0 <= ny < 21:
                    if visible_matrix[ny][nx] != 4 and visible_matrix[ny][nx] != 1 and visible_matrix[ny][nx] != 2:
                        recurfill(nx, ny)

        recurfill(10, 10)

        # 5. calclos(1) - Finalize boundaries and visibility override (adjacent tiles)
        for y in range(21):
            for x in range(21):
                # propagate to blocks
                if visible_matrix[y][x] == 2:
                    # check if next to a clear tile
                    adjacent_clear = False
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, 1), (1, -1), (1, 1), (-1, -1)]:
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < 21 and 0 <= ny < 21:
                            if visible_matrix[ny][nx] == 4:
                                adjacent_clear = True
                                break
                    if adjacent_clear:
                        visible_matrix[y][x] = 5

        # Override adjacent tiles around player to be fully visible
        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                nx, ny = 10 + dx, 10 + dy
                if 0 <= nx < 21 and 0 <= ny < 21:
                    visible_matrix[ny][nx] = 5

        return visible_matrix
