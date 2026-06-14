# ==============================================================================
# WORLDDATABASEMANAGER.PY - GLOBAL SPATIAL ENGINE
# ==============================================================================
import sqlite3
import json
import os
import time
from datetime import datetime

# Shared Senior Engineer Color Palette
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

class WorldDatabaseManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(WorldDatabaseManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, project_path):
        if hasattr(self, '_initialized'):
            if self.project_path == project_path:
                return
            if self.conn:
                try:
                    self.conn.close()
                except: pass
                self.conn = None
        self.project_path = project_path
        self.json_path = os.path.join(project_path, "Maps", "World.json")
        self.db_path = os.path.join(project_path, "Maps", "World.db")
        self.conn = None
        self._initialized = True
        self._noisy_log(Colors.HEADER, "WORLD SPATIAL ENGINE INITIALIZED")
        self._bootstrap()

    def _noisy_log(self, color, message):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"{color}[{timestamp}] [WORLD_DB] {message}{Colors.ENDC}")

    def _bootstrap(self):
        """ Safe-Switch Implementation for Global Map """
        json_exists = os.path.exists(self.json_path)
        db_exists = os.path.exists(self.db_path)

        # Sceneario A: JSON Only - (SUNSETTED: Migration logic deactivated)
        # if json_exists and not db_exists:
        #     self._noisy_log(Colors.WARNING, "Scenario A: Legacy World JSON detected. Initializing Bulk Migration...")
        #     self._init_db()
        #     self._migrate_json_to_db()

        # Scenario B/C: Global Binary Mode
        if db_exists:
            self._noisy_log(Colors.OKGREEN, "Native Global Mode: Primary Spatial Database detected.")
            self._init_db()
        else:
            self._noisy_log(Colors.FAIL, "CRITICAL: Global Database missing and Migration Sunsetted.")
            self._init_db() 

    def _init_db(self):
        try:
            self._noisy_log(Colors.OKCYAN, f"Establishing spatial connection: {self.db_path}")
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = self.conn.cursor()
            
            # Check if map_name column exists in world_grid to trigger auto-upgrade
            cursor.execute("PRAGMA table_info(world_grid)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if columns and "map_name" not in columns:
                self._noisy_log(Colors.WARNING, "Upgrading world_grid table to support multiple maps...")
                cursor.execute("ALTER TABLE world_grid RENAME TO old_world_grid")
                cursor.execute('''
                    CREATE TABLE world_grid (
                        map_name TEXT,
                        x INTEGER,
                        y INTEGER,
                        chunk_id TEXT,
                        PRIMARY KEY (map_name, x, y)
                    )
                ''')
                cursor.execute("INSERT INTO world_grid (map_name, x, y, chunk_id) SELECT 'WORLD', x, y, chunk_id FROM old_world_grid")
                cursor.execute("DROP TABLE old_world_grid")
                
            # Same upgrade check for world_points
            cursor.execute("PRAGMA table_info(world_points)")
            columns_pts = [col[1] for col in cursor.fetchall()]
            if columns_pts and "map_name" not in columns_pts:
                self._noisy_log(Colors.WARNING, "Upgrading world_points table to support multiple maps...")
                cursor.execute("ALTER TABLE world_points RENAME TO old_world_points")
                cursor.execute('''
                    CREATE TABLE world_points (
                        map_name TEXT,
                        id TEXT,
                        x INTEGER,
                        y INTEGER,
                        data TEXT,
                        PRIMARY KEY (map_name, id)
                    )
                ''')
                cursor.execute("INSERT INTO world_points (map_name, id, x, y, data) SELECT 'WORLD', id, x, y, data FROM old_world_points")
                cursor.execute("DROP TABLE old_world_points")

            # Final check to ensure tables exist with the map_name architecture
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS world_grid (
                    map_name TEXT,
                    x INTEGER,
                    y INTEGER,
                    chunk_id TEXT,
                    PRIMARY KEY (map_name, x, y)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS world_points (
                    map_name TEXT,
                    id TEXT,
                    x INTEGER,
                    y INTEGER,
                    data TEXT,
                    PRIMARY KEY (map_name, id)
                )
            ''')
            
            self.conn.commit()
            self._noisy_log(Colors.OKGREEN, "World Spatial Schema verified.")
        except Exception as e:
            self._noisy_log(Colors.FAIL, f"CRITICAL: Spatial DB initialization failed: {e}")

    def _migrate_json_to_db(self):
        start_time = time.time()
        self._noisy_log(Colors.WARNING, "SPATIAL MIGRATION START: parsing master world grid...")
        try:
            with open(self.json_path, 'r') as f:
                legacy_world = json.load(f)
            
            grid = legacy_world.get("grid", [])
            points = legacy_world.get("points", [])
            
            self._noisy_log(Colors.OKBLUE, f"Source parsed: {len(grid)} rows found. Indexing coordinates...")
            
            cursor = self.conn.cursor()
            count = 0
            # Perform atomic migration to default map name 'WORLD'
            for r_idx, row in enumerate(grid):
                for c_idx, cid in enumerate(row):
                    cursor.execute("INSERT OR REPLACE INTO world_grid (map_name, x, y, chunk_id) VALUES (?, ?, ?, ?)", 
                                   ('WORLD', c_idx, r_idx, str(cid)))
                    count += 1
                if r_idx % 20 == 0:
                    self._noisy_log(Colors.OKCYAN, f"Spatial Indexing Progress: Row {r_idx} committed...")

            for p in points:
                cursor.execute("INSERT OR REPLACE INTO world_points (map_name, id, x, y, data) VALUES (?, ?, ?, ?, ?)", 
                               ('WORLD', p.get("name", "POI"), p.get("x", 0), p.get("y", 0), json.dumps(p)))

            self.conn.commit()
            duration = time.time() - start_time
            self._noisy_log(Colors.OKGREEN, f"SPATIAL MIGRATION COMPLETE: {count} coordinates indexed in {duration:.2f}s.")
            
        except Exception as e:
            self._noisy_log(Colors.FAIL, f"SPATIAL MIGRATION FAILED: {e}")
            if self.conn: self.conn.rollback()

    def load_world_state(self, map_name="WORLD"):
        """ Fetch Global Grid and Points for a specific map """
        map_name = str(map_name).upper()
        world_data = {"grid": [], "points": []}
        try:
            self._noisy_log(Colors.OKCYAN, f"QUERY: Reconstructing global world grid for map {map_name}...")
            cursor = self.conn.cursor()
            
            # Fetch grid size
            cursor.execute("SELECT MAX(x), MAX(y) FROM world_grid WHERE map_name = ?", (map_name,))
            res = cursor.fetchone()
            max_x, max_y = (res[0], res[1]) if res else (None, None)
            if max_x is None:
                # Map doesn't exist yet, return a clean default 32x32 grid
                grid = [["0" for _ in range(32)] for _ in range(32)]
                return {"grid": grid, "points": []}
            
            # Pre-allocate grid for performance
            grid = [["0" for _ in range(max_x + 1)] for _ in range(max_y + 1)]
            cursor.execute("SELECT x, y, chunk_id FROM world_grid WHERE map_name = ?", (map_name,))
            for x, y, cid in cursor.fetchall():
                grid[y][x] = cid
            
            # Fetch points
            points = []
            cursor.execute("SELECT data FROM world_points WHERE map_name = ?", (map_name,))
            for (p_json,) in cursor.fetchall():
                points.append(json.loads(p_json))
                
            world_data["grid"] = grid
            world_data["points"] = points
            self._noisy_log(Colors.OKGREEN, f"SPATIAL SYNC SUCCESS: {len(grid)}x{len(grid[0])} grid restored for map {map_name}.")
            return world_data
        except Exception as e:
            self._noisy_log(Colors.FAIL, f"SPATIAL SYNC FAILED for map {map_name}: {e}.")
            return {"grid": [["0" for _ in range(32)] for _ in range(32)], "points": []}

    def _fallback_json_load(self):
        """ DEACTIVATED: World Fallback Sunsetted """
        return {"grid": [["0" for _ in range(32)] for _ in range(32)], "points": []}

    def save_world_state(self, world_data, map_name="WORLD"):
        """ Atomic Spatial Commit for a specific map """
        map_name = str(map_name).upper()
        try:
            self._noisy_log(Colors.WARNING, f"TRANSACTION: Committing global map updates for map {map_name}...")
            cursor = self.conn.cursor()
            
            # Save Grid
            grid = world_data.get("grid", [])
            for r_idx, row in enumerate(grid):
                for c_idx, cid in enumerate(row):
                    cursor.execute("INSERT OR REPLACE INTO world_grid (map_name, x, y, chunk_id) VALUES (?, ?, ?, ?)", 
                                   (map_name, c_idx, r_idx, str(cid)))
            
            # Save Points
            cursor.execute("DELETE FROM world_points WHERE map_name = ?", (map_name,)) # Refresh POIs
            for p in world_data.get("points", []):
                cursor.execute("INSERT OR REPLACE INTO world_points (map_name, id, x, y, data) VALUES (?, ?, ?, ?, ?)", 
                               (map_name, p.get("name", "POI"), p.get("x", 0), p.get("y", 0), json.dumps(p)))
                
            self.conn.commit()
            self._noisy_log(Colors.OKGREEN, f"SPATIAL TRANSACTION COMMITTED for map {map_name}.")
        except Exception as e:
            self._noisy_log(Colors.FAIL, f"SPATIAL TRANSACTION FAILED for map {map_name}: {e}")
            if self.conn: self.conn.rollback()


    def close(self):
        if self.conn:
            try:
                self.conn.close()
            except: pass
            self.conn = None
            self._noisy_log(Colors.HEADER, "SPATIAL DB CLOSED.")
        
        # Reset singleton state
        WorldDatabaseManager._instance = None
        if hasattr(self, '_initialized'):
            del self._initialized
