# server/item_database.py
import sqlite3
import os
from typing import List, Dict, Any, Optional
from core.items import ItemInstance

DB_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "items.db")

class ItemDatabaseManager:
    def __init__(self, db_path: str = None):
        self.db_path = db_path if db_path is not None else DB_FILE
        self.initialize_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def initialize_db(self):
        """Creates the items and item_logs tables if they don't already exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    used INTEGER DEFAULT 0,
                    know_id INTEGER DEFAULT 0,
                    item_id INTEGER DEFAULT 0,
                    item_type INTEGER DEFAULT 0,
                    family INTEGER DEFAULT 0,
                    durability INTEGER DEFAULT 0,
                    x INTEGER DEFAULT 0,
                    y INTEGER DEFAULT 0,
                    quantity INTEGER DEFAULT 1,
                    owner_id INTEGER DEFAULT 0,
                    container TEXT DEFAULT 'ground',
                    slot INTEGER DEFAULT 0
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS item_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    action TEXT,
                    character_id INTEGER,
                    character_name TEXT,
                    item_db_id INTEGER,
                    item_type INTEGER,
                    x INTEGER,
                    y INTEGER,
                    details TEXT
                )
            """)
            conn.commit()

    def log_item_transaction(self, action: str, char_id: int, char_name: str, item_db_id: int, item_type: int, x: int, y: int, details: str = ""):
        """Inserts an audit log entry for an item action."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO item_logs (action, character_id, character_name, item_db_id, item_type, x, y, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (action, char_id, char_name, item_db_id, item_type, x, y, details))
                conn.commit()
        except Exception as e:
            print(f"[DB ERROR] Failed to write item transaction log: {e}")

    def add_item(self, item: ItemInstance, owner_id: int, container: str, slot: int) -> int:
        """Inserts a new item into the database and returns its new ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO items (
                    used, know_id, item_id, item_type, family, durability, x, y, quantity, owner_id, container, slot
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                1 if item.used else 0,
                item.know_id,
                item.item_id,
                item.item_type,
                item.family,
                item.durability,
                item.x,
                item.y,
                item.quantity,
                owner_id,
                container,
                slot
            ))
            conn.commit()
            new_id = cursor.lastrowid
            
        self.log_item_transaction(
            action="create",
            char_id=owner_id,
            char_name=f"Owner {owner_id}" if owner_id else "System",
            item_db_id=new_id,
            item_type=item.item_type,
            x=item.x,
            y=item.y,
            details=f"Created in container '{container}' slot {slot}"
        )
        return new_id

    def update_item(self, db_id: int, item: ItemInstance, container: str, slot: int, owner_id: Optional[int] = None):
        """Updates an existing item's attributes in the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if owner_id is not None:
                cursor.execute("""
                    UPDATE items SET
                        used = ?, know_id = ?, item_id = ?, item_type = ?, family = ?, durability = ?,
                        x = ?, y = ?, quantity = ?, owner_id = ?, container = ?, slot = ?
                    WHERE id = ?
                """, (
                    1 if item.used else 0,
                    item.know_id,
                    item.item_id,
                    item.item_type,
                    item.family,
                    item.durability,
                    item.x,
                    item.y,
                    item.quantity,
                    owner_id,
                    container,
                    slot,
                    db_id
                ))
            else:
                cursor.execute("""
                    UPDATE items SET
                        used = ?, know_id = ?, item_id = ?, item_type = ?, family = ?, durability = ?,
                        x = ?, y = ?, quantity = ?, container = ?, slot = ?
                    WHERE id = ?
                """, (
                    1 if item.used else 0,
                    item.know_id,
                    item.item_id,
                    item.item_type,
                    item.family,
                    item.durability,
                    item.x,
                    item.y,
                    item.quantity,
                    container,
                    slot,
                    db_id
                ))
            conn.commit()

    def delete_item(self, db_id: int):
        """Deletes an item from the database."""
        item = self.get_item_by_id(db_id)
        if not item:
            return
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM items WHERE id = ?", (db_id,))
            conn.commit()

        self.log_item_transaction(
            action="delete",
            char_id=item.get("owner_id", 0),
            char_name=f"Owner {item.get('owner_id', 0)}" if item.get("owner_id") else "System",
            item_db_id=db_id,
            item_type=item.get("item_type", 0),
            x=item.get("x", 0),
            y=item.get("y", 0),
            details=f"Deleted from container '{item.get('container')}' slot {item.get('slot')}"
        )

    def get_items_for_owner(self, owner_id: int, container: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves items owned by a specific owner/character, optionally filtered by container type."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if container:
                cursor.execute("""
                    SELECT id, used, know_id, item_id, item_type, family, durability, x, y, quantity, owner_id, container, slot
                    FROM items
                    WHERE owner_id = ? AND container = ?
                """, (owner_id, container))
            else:
                cursor.execute("""
                    SELECT id, used, know_id, item_id, item_type, family, durability, x, y, quantity, owner_id, container, slot
                    FROM items
                    WHERE owner_id = ?
                """, (owner_id,))
            
            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get_ground_items(self) -> List[Dict[str, Any]]:
        """Retrieves all items currently lying on the ground (where container is 'ground')."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, used, know_id, item_id, item_type, family, durability, x, y, quantity, owner_id, container, slot
                FROM items
                WHERE container = 'ground'
            """)
            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]

    def move_item(self, db_id: int, new_container: str, new_slot: int, new_owner_id: Optional[int] = None, new_x: Optional[int] = None, new_y: Optional[int] = None):
        """Convenience method to move an item to a new container/slot/coordinates."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "UPDATE items SET container = ?, slot = ?"
            params = [new_container, new_slot]
            
            if new_owner_id is not None:
                query += ", owner_id = ?"
                params.append(new_owner_id)
            if new_x is not None:
                query += ", x = ?"
                params.append(new_x)
            if new_y is not None:
                query += ", y = ?"
                params.append(new_y)
                
            query += " WHERE id = ?"
            params.append(db_id)
            
            cursor.execute(query, tuple(params))
            conn.commit()

    def get_item_by_id(self, db_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a single item by its database ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, used, know_id, item_id, item_type, family, durability, x, y, quantity, owner_id, container, slot
                FROM items
                WHERE id = ?
            """, (db_id,))
            row = cursor.fetchone()
            return self._row_to_dict(row) if row else None

    def search_items(self, item_type: int = None, item_id: int = None) -> List[Dict[str, Any]]:
        """Search all items in the database by type and/or instance ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT id, used, know_id, item_id, item_type, family, durability, x, y, quantity, owner_id, container, slot FROM items WHERE 1=1"
            params = []
            if item_type is not None:
                query += " AND item_type = ?"
                params.append(item_type)
            if item_id is not None:
                query += " AND item_id = ?"
                params.append(item_id)
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]

    def _row_to_dict(self, row: tuple) -> Dict[str, Any]:
        return {
            "id": row[0],
            "used": bool(row[1]),
            "know_id": row[2],
            "item_id": row[3],
            "item_type": row[4],
            "family": row[5],
            "durability": row[6],
            "x": row[7],
            "y": row[8],
            "quantity": row[9],
            "owner_id": row[10],
            "container": row[11],
            "slot": row[12]
        }
