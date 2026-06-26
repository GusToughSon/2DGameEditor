# ==============================================================================
# DATABASEMANAGER.PY - SENIOR DATA ENGINEER EDITION
# ==============================================================================
import sqlite3
import json
import os
import time
from datetime import datetime

# Color Constants for "Noisy" Debugging
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

class DatabaseManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, project_path):
        if hasattr(self, '_initialized'): return
        self.project_path = project_path
        self.json_path = os.path.join(project_path, "Maps", "Chunks.json")
        self.db_path = os.path.join(project_path, "Maps", "Chunks.db")
        self.conn = None
        self._initialized = True
        self._noisy_log(Colors.HEADER, "DATABASE MANAGER ENGINE INITIALIZED")
        self._bootstrap()

    def _noisy_log(self, color, message):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"{color}[{timestamp}] [DB_MANAGER] {message}{Colors.ENDC}")

    def _bootstrap(self):
        """ The Safe-Switch Data Handler Implementation """
        json_exists = os.path.exists(self.json_path)
        db_exists = os.path.exists(self.db_path)

        # Scenario A: JSON Only - (SUNSETTED: Migration logic deactivated)
        # if json_exists and not db_exists:
        #     self._noisy_log(Colors.WARNING, "Scenario A: Legacy JSON detected. Initializing Migration...")
        #     self._init_db()
        #     self._migrate_json_to_db()

        # Scenario B/C: Production Mode
        if db_exists:
            self._noisy_log(Colors.OKGREEN, "Native Binary Mode: Accessing production database.")
            self._init_db()
        else:
            self._noisy_log(Colors.FAIL, "CRITICAL: Database missing and Migration Sunsetted.")
            self._init_db() # Create empty DB structure at least

    def _init_db(self):
        try:
            self._noisy_log(Colors.OKBLUE, f"Opening connection to binary database: {self.db_path}")
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = self.conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    data TEXT,
                    last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            self.conn.commit()
            self._noisy_log(Colors.OKGREEN, "Database schema verified and committed.")
        except Exception as e:
            self._noisy_log(Colors.FAIL, f"CRITICAL: Schema initialization failed: {e}")

    def _migrate_json_to_db(self):
        start_time = time.time()
        self._noisy_log(Colors.WARNING, "MIGRATION START: parsing legacy JSON source...")
        try:
            with open(self.json_path, 'r') as f:
                legacy_data = json.load(f)
            
            self._noisy_log(Colors.OKBLUE, f"Source parsed: {len(legacy_data)} records found. Initializing Batch Transaction...")
            
            cursor = self.conn.cursor()
            count = 0
            for cid, cdata in legacy_data.items():
                cursor.execute("INSERT OR REPLACE INTO chunks (id, data) VALUES (?, ?)", 
                               (str(cid), json.dumps(cdata)))
                count += 1
                if count % 500 == 0:
                    self._noisy_log(Colors.OKBLUE, f"Transaction Progress: {count} records committed...")

            self.conn.commit()
            duration = time.time() - start_time
            self._noisy_log(Colors.OKGREEN, f"MIGRATION COMPLETE: {count} records synced in {duration:.2f}s.")
            
        except Exception as e:
            self._noisy_log(Colors.FAIL, f"MIGRATION INTERRUPTED: {e}")
            if self.conn: self.conn.rollback()

    def load_all_chunks(self):
        """ Attempt Primary Read with Fallback Redundancy """
        chunks = {}
        try:
            self._noisy_log(Colors.OKBLUE, "FETCH: Querying production database...")
            cursor = self.conn.cursor()
            cursor.execute("SELECT id, data FROM chunks")
            rows = cursor.fetchall()
            for row in rows:
                cid = row[0]
                # Standardize to "C_#" for system compatibility
                scid = f"C_{cid}" if cid.isdigit() else cid
                chunks[scid] = json.loads(row[1])
            self._noisy_log(Colors.OKGREEN, f"FETCH SUCCESS: {len(chunks)} records pulled from binary store.")
            return chunks
        except Exception as e:
            self._noisy_log(Colors.FAIL, f"FETCH FAILED: {e}. (SUNSETTED: JSON Fallback deactivated)")
            return {}

    def _fallback_json_load(self):
        """ DEACTIVATED: JSON Fallback Sunsetted """
        return {}

    def save_chunk(self, cid, data):
        """ Atomic save to Database only (Scenario C requirement) """
        try:
            cursor = self.conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO chunks (id, data, last_modified) VALUES (?, ?, CURRENT_TIMESTAMP)", 
                           (str(cid), json.dumps(data)))
            self.conn.commit()
            self._noisy_log(Colors.OKGREEN, f"COMMIT SUCCESS: Chunk {cid} persisted to binary store.")
        except Exception as e:
            self._noisy_log(Colors.FAIL, f"COMMIT FAILED: {e}")

    def save_all_chunks(self, chunks):
        """ Bulk Persistence Layer """
        self._noisy_log(Colors.WARNING, f"BULK SAVE: Preparing sync for {len(chunks)} master records...")
        try:
            cursor = self.conn.cursor()
            for cid, cdata in chunks.items():
                cursor.execute("INSERT OR REPLACE INTO chunks (id, data, last_modified) VALUES (?, ?, CURRENT_TIMESTAMP)", 
                               (str(cid), json.dumps(cdata)))
            self.conn.commit()
            self._noisy_log(Colors.OKGREEN, f"BULK SAVED: {len(chunks)} records synced to binary database.")
        except Exception as e:
            self._noisy_log(Colors.FAIL, f"BULK SAVE FAILED: {e}")
            if self.conn: self.conn.rollback()

    def close(self):
        if self.conn:
            self.conn.close()
            self._noisy_log(Colors.HEADER, "DATABASE CONNECTION TERMINATED CLEANLY.")
