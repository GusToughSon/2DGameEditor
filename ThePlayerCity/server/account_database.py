# server/account_database.py
import sqlite3
import os
import json
from typing import List, Dict, Any, Optional
from core.models import Account, AccountData, CharacterData, SkillData

DB_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "accounts.db")

class AccountDatabaseManager:
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self.initialize_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def initialize_db(self):
        """Creates the accounts and characters tables if they don't already exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Accounts Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    acc_name TEXT UNIQUE NOT NULL,
                    acc_pass TEXT NOT NULL,
                    is_banned INTEGER DEFAULT 0,
                    is_premium INTEGER DEFAULT 0,
                    is_golden INTEGER DEFAULT 0,
                    c_minute INTEGER DEFAULT 0,
                    c_hour INTEGER DEFAULT 0,
                    c_day INTEGER DEFAULT 0,
                    c_month INTEGER DEFAULT 0,
                    c_year INTEGER DEFAULT 0
                )
            """)
            # Characters Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS characters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL,
                    slot INTEGER NOT NULL,
                    used INTEGER DEFAULT 0,
                    name TEXT UNIQUE,
                    wanted INTEGER DEFAULT 0,
                    marked INTEGER DEFAULT 0,
                    x INTEGER DEFAULT 0,
                    y INTEGER DEFAULT 0,
                    map_level INTEGER DEFAULT 0,
                    hp_left INTEGER DEFAULT 10,
                    hp_max INTEGER DEFAULT 10,
                    mana_left INTEGER DEFAULT 5,
                    char_update INTEGER DEFAULT 0,
                    shrine_x INTEGER DEFAULT 0,
                    shrine_y INTEGER DEFAULT 0,
                    status TEXT DEFAULT '[]',
                    status_mode TEXT DEFAULT '[]',
                    tag TEXT DEFAULT '',
                    dev_mode INTEGER DEFAULT 0,
                    avatar INTEGER DEFAULT 0,
                    reputation INTEGER DEFAULT 0,
                    race INTEGER DEFAULT 0,
                    guild INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    str INTEGER DEFAULT 5,
                    con INTEGER DEFAULT 5,
                    dex INTEGER DEFAULT 5,
                    int INTEGER DEFAULT 5,
                    cha INTEGER DEFAULT 5,
                    lck INTEGER DEFAULT 5,
                    stat_points INTEGER DEFAULT 15,
                    killed_monsters INTEGER DEFAULT 0,
                    crim_count INTEGER DEFAULT 0,
                    overall_mon_count INTEGER DEFAULT 0,
                    overall_crim_count INTEGER DEFAULT 0,
                    overall_player_kills INTEGER DEFAULT 0,
                    overall_deaths_monster INTEGER DEFAULT 0,
                    overall_deaths_player INTEGER DEFAULT 0,
                    mon_count_since_death INTEGER DEFAULT 0,
                    exp_count_since_death INTEGER DEFAULT 0,
                    pk_since_death INTEGER DEFAULT 0,
                    exp INTEGER DEFAULT 0,
                    exp_pool INTEGER DEFAULT 0,
                    skills TEXT DEFAULT '[]',
                    class_template TEXT DEFAULT '',
                    c_minute INTEGER DEFAULT 0,
                    c_hour INTEGER DEFAULT 0,
                    c_day INTEGER DEFAULT 0,
                    c_month INTEGER DEFAULT 0,
                    c_year INTEGER DEFAULT 0,
                    FOREIGN KEY(account_id) REFERENCES accounts(id)
                )
            """)
            # Check if hry_script column exists, if not, add it
            cursor.execute("PRAGMA table_info(characters)")
            columns = [col[1] for col in cursor.fetchall()]
            if "hry_script" not in columns:
                cursor.execute("ALTER TABLE characters ADD COLUMN hry_script TEXT DEFAULT ''")

            # Kill logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS kill_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    killer_id INTEGER,
                    killer_name TEXT,
                    killer_type TEXT,
                    victim_id INTEGER,
                    victim_name TEXT,
                    victim_type TEXT,
                    x INTEGER,
                    y INTEGER,
                    map_level INTEGER
                )
            """)

            # Spawn logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS spawn_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    entity_type TEXT,
                    entity_id INTEGER,
                    entity_name TEXT,
                    x INTEGER,
                    y INTEGER,
                    map_level INTEGER,
                    details TEXT
                )
            """)

            # Action/System logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS action_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    char_id INTEGER,
                    char_name TEXT,
                    action_type TEXT,
                    details TEXT
                )
            """)
            conn.commit()

    def get_account_by_name(self, acc_name: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM accounts WHERE acc_name = ?", (acc_name,))
            row = cursor.fetchone()
            if row:
                return self._row_to_account_dict(row)
            return None

    def get_character_by_name(self, char_name: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM characters WHERE name = ?", (char_name,))
            row = cursor.fetchone()
            if row:
                return self._row_to_character_dict(row)
            return None

    def get_account_by_id(self, acc_id: int) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM accounts WHERE id = ?", (acc_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_account_dict(row)
            return None

    def create_account(self, acc_name: str, acc_pass: str) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO accounts (acc_name, acc_pass) VALUES (?, ?)
            """, (acc_name, acc_pass))
            conn.commit()
            return cursor.lastrowid

    def update_account(self, acc_id: int, banned: bool, premium: bool, golden: bool):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE accounts SET is_banned = ?, is_premium = ?, is_golden = ? WHERE id = ?
            """, (1 if banned else 0, 1 if premium else 0, 1 if golden else 0, acc_id))
            conn.commit()

    def get_characters_by_account(self, account_id: int) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM characters WHERE account_id = ? ORDER BY slot ASC", (account_id,))
            rows = cursor.fetchall()
            return [self._row_to_character_dict(row) for row in rows]

    def create_character(self, account_id: int, slot: int, name: str, class_template: str, avatar: int, race: int, hry_script: str = "") -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Default empty skills list
            empty_skills = json.dumps([{"exp": 0, "level": 1, "bonus": 0} for _ in range(30)])
            cursor.execute("""
                INSERT INTO characters (
                    account_id, slot, used, name, class_template, avatar, race, hp_left, hp_max, skills, hry_script
                ) VALUES (?, ?, 1, ?, ?, ?, ?, 10, 10, ?, ?)
            """, (account_id, slot, name, class_template, avatar, race, empty_skills, hry_script))
            conn.commit()
            return cursor.lastrowid

    def update_character(self, char_id: int, c: CharacterData):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            skills_data = [{"exp": sk.exp, "level": sk.level, "bonus": sk.bonus} for sk in c.skills]
            cursor.execute("""
                UPDATE characters SET
                    used = ?, wanted = ?, marked = ?, name = ?, x = ?, y = ?, map_level = ?,
                    hp_left = ?, hp_max = ?, mana_left = ?, char_update = ?, shrine_x = ?, shrine_y = ?,
                    status = ?, status_mode = ?, tag = ?, dev_mode = ?, avatar = ?, reputation = ?,
                    race = ?, guild = ?, level = ?, str = ?, con = ?, dex = ?, int = ?, cha = ?, lck = ?,
                    stat_points = ?, killed_monsters = ?, crim_count = ?, overall_mon_count = ?,
                    overall_crim_count = ?, overall_player_kills = ?, overall_deaths_monster = ?,
                    overall_deaths_player = ?, mon_count_since_death = ?, exp_count_since_death = ?,
                    pk_since_death = ?, exp = ?, exp_pool = ?, skills = ?, class_template = ?,
                    c_minute = ?, c_hour = ?, c_day = ?, c_month = ?, c_year = ?, hry_script = ?
                WHERE id = ?
            """, (
                1 if c.used else 0, 1 if c.wanted else 0, 1 if c.marked else 0, c.name, c.x, c.y, c.map_level,
                c.hp_left, c.hp_max, c.mana_left, c.char_update, c.shrine_x, c.shrine_y,
                json.dumps(c.status), json.dumps(c.status_mode), c.tag, c.dev_mode, c.avatar, c.reputation,
                c.race, c.guild, c.level, c.str, c.con, c.dex, c.int, c.cha, c.lck,
                c.stat_points, c.killed_monsters, c.crim_count, c.overall_mon_count,
                c.overall_crim_count, c.overall_player_kills, c.overall_deaths_monster,
                c.overall_deaths_player, c.mon_count_since_death, c.exp_count_since_death,
                c.pk_since_death, c.exp, c.exp_pool, json.dumps(skills_data), c.class_template,
                c.c_minute, c.c_hour, c.c_day, c.c_month, c.c_year, c.hry_script,
                char_id
            ))
            conn.commit()

    def get_all_accounts(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM accounts")
            rows = cursor.fetchall()
            return [self._row_to_account_dict(row) for row in rows]

    def _row_to_account_dict(self, row: tuple) -> Dict[str, Any]:
        return {
            "id": row[0],
            "acc_name": row[1],
            "acc_pass": row[2],
            "is_banned": bool(row[3]),
            "is_premium": bool(row[4]),
            "is_golden": bool(row[5]),
            "c_minute": row[6],
            "c_hour": row[7],
            "c_day": row[8],
            "c_month": row[9],
            "c_year": row[10]
        }

    def _row_to_character_dict(self, row: tuple) -> Dict[str, Any]:
        return {
            "id": row[0],
            "account_id": row[1],
            "slot": row[2],
            "used": bool(row[3]),
            "name": row[4],
            "wanted": bool(row[5]),
            "marked": bool(row[6]),
            "x": row[7],
            "y": row[8],
            "map_level": row[9],
            "hp_left": row[10],
            "hp_max": row[11],
            "mana_left": row[12],
            "char_update": row[13],
            "shrine_x": row[14],
            "shrine_y": row[15],
            "status": json.loads(row[16] or "[]"),
            "status_mode": json.loads(row[17] or "[]"),
            "tag": row[18],
            "dev_mode": row[19],
            "avatar": row[20],
            "reputation": row[21],
            "race": row[22],
            "guild": row[23],
            "level": row[24],
            "str": row[25],
            "con": row[26],
            "dex": row[27],
            "int": row[28],
            "cha": row[29],
            "lck": row[30],
            "stat_points": row[31],
            "killed_monsters": row[32],
            "crim_count": row[33],
            "overall_mon_count": row[34],
            "overall_crim_count": row[35],
            "overall_player_kills": row[36],
            "overall_deaths_monster": row[37],
            "overall_deaths_player": row[38],
            "mon_count_since_death": row[39],
            "exp_count_since_death": row[40],
            "pk_since_death": row[41],
            "exp": row[42],
            "exp_pool": row[43],
            "skills": json.loads(row[44] or "[]"),
            "class_template": row[45],
            "c_minute": row[46],
            "c_hour": row[47],
            "c_day": row[48],
            "c_month": row[49],
            "c_year": row[50],
            "hry_script": row[51] if len(row) > 51 else ""
        }

    def log_kill(self, killer_id: int, killer_name: str, killer_type: str, victim_id: int, victim_name: str, victim_type: str, x: int, y: int, map_level: int = 0):
        """Inserts an entry into the kill logs table."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO kill_logs (killer_id, killer_name, killer_type, victim_id, victim_name, victim_type, x, y, map_level)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (killer_id, killer_name, killer_type, victim_id, victim_name, victim_type, x, y, map_level))
                conn.commit()
        except Exception as e:
            print(f"[DB ERROR] Failed to write kill log: {e}")

    def log_spawn(self, entity_type: str, entity_id: int, entity_name: str, x: int, y: int, map_level: int = 0, details: str = ""):
        """Inserts an entry into the spawn logs table."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO spawn_logs (entity_type, entity_id, entity_name, x, y, map_level, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (entity_type, entity_id, entity_name, x, y, map_level, details))
                conn.commit()
        except Exception as e:
            print(f"[DB ERROR] Failed to write spawn log: {e}")

    def log_action(self, char_id: int, char_name: str, action_type: str, details: str = ""):
        """Inserts an entry into the action logs table."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO action_logs (char_id, char_name, action_type, details)
                    VALUES (?, ?, ?, ?)
                """, (char_id, char_name, action_type, details))
                conn.commit()
        except Exception as e:
            print(f"[DB ERROR] Failed to write action log: {e}")

