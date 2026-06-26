# core/config.py — Game Configuration Parser for ThePlayerCity Python Port
# Ported from ThePlayerCityServer POC HryParser + hot-reload watcher
import os
import re
import threading
import time
from typing import Dict, Any, Optional, Callable


class HryParser:
    """Parser for .hry (HAIRY) game configuration files.
    
    Supports:
    - #Define KEY VALUE and DEFINE KEY VALUE directives
    - Object "name" { body } blocks
    - Shop "name" { body } blocks with ItemType, Price, Stock; entries
    - Single-line // comments
    - Multi-value defines (comma or space separated → list)
    - Boolean coercion (true/false → 1/0)
    """

    @staticmethod
    def parse(file_path: str) -> dict:
        if not os.path.exists(file_path):
            return {"defines": {}, "objects": {}, "shops": {}}

        data = {"defines": {}, "objects": {}, "shops": {}}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            print(f"[CONFIG ERROR] Failed to read {file_path}: {e}")
            return data

        # Remove single-line comments completely for easier regex matching on multiline blocks
        # but keep track of line endings
        clean_content = ""
        for line in content.splitlines():
            if "//" in line:
                line = line.split("//", 1)[0]
            clean_content += line + "\n"

        # Parse #Define and DEFINE directives
        define_pattern = re.compile(
            r"(?:#Define|DEFINE)[ \t]+([A-Za-z0-9_]+)(?:[ \t]+([^\n\r]+))?"
        )
        for match in define_pattern.finditer(clean_content):
            key = match.group(1)
            raw_val = match.group(2)
            val: Any = raw_val.strip() if raw_val else 1

            try:
                if isinstance(val, str):
                    low = val.lower()
                    if low == "true":
                        val = 1
                    elif low == "false":
                        val = 0
                    elif "," in val:
                        val = [int(v.strip()) for v in val.split(",")]
                    elif " " in val.strip():
                        parts = val.strip().split()
                        try:
                            val = [int(v.strip()) for v in parts]
                        except ValueError:
                            pass  # Keep as string
                    else:
                        val = int(val)
            except ValueError:
                pass  # Keep as string

            data["defines"][key] = val

        # Parse Object, Shop, and Race blocks using a brace-counting scanner to support nested braces
        idx = 0
        while idx < len(clean_content):
            # Find next block header
            match = re.search(r'\b(Object|Shop|Race)\s+((?:"[^"]+"\s*)+)\{', clean_content[idx:])
            if not match:
                break
            
            block_type = match.group(1)
            names_raw = match.group(2)
            names = re.findall(r'"([^"]+)"', names_raw)
            
            # Start of the block body (after the '{' we matched)
            start_pos = idx + match.end()
            
            # Find matching closing brace
            brace_count = 1
            current_pos = start_pos
            while current_pos < len(clean_content) and brace_count > 0:
                char = clean_content[current_pos]
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                current_pos += 1
            
            if brace_count == 0:
                body = clean_content[start_pos:current_pos-1].strip()
                if block_type in ('Object', 'Race'):
                    for obj_name in names:
                        data["objects"][obj_name] = body
                elif block_type == 'Shop':
                    items = []
                    for line in re.split(r'[;\n]', body):
                        line = line.strip()
                        if not line:
                            continue
                        parts = [p.strip() for p in line.split(',') if p.strip()]
                        if len(parts) >= 2:
                            item_type = parts[0]
                            try:
                                price = int(parts[1])
                            except ValueError:
                                price = parts[1]
                            stock = -1
                            if len(parts) >= 3:
                                try:
                                    stock = int(parts[2])
                                except ValueError:
                                    stock = parts[2]
                            items.append({
                                "item_type": item_type,
                                "price": price,
                                "stock": stock
                            })
                    for shop_name in names:
                        data["shops"][shop_name] = items
            
            # Advance past the matched block
            idx = start_pos + (current_pos - start_pos)

        return data

    @staticmethod
    def get_starting_items_from_body(body: str) -> list:
        """Extract starting item types from OnNew block inside an object's body."""
        items = []
        on_new_match = re.search(r'OnNew\s*\{([^}]+)\}', body, re.DOTALL)
        if on_new_match:
            on_new_body = on_new_match.group(1)
            matches = re.findall(r'Create\s+([A-Za-z0-9_]+)', on_new_body)
            for m in matches:
                items.append(m)
        return items



class GameConfig:
    """Manages game configuration from HAIRY/*.hry files.
    
    Provides:
    - Initial loading of all .hry files in a directory
    - Merged config dict from Defines.hry + Player.hry
    - File watcher thread for hot-reload on changes
    - Callback notification when config changes
    """

    def __init__(self, hairy_dir: str = "", on_change: Optional[Callable] = None):
        self.hairy_dir = hairy_dir
        self.on_change = on_change
        self.hry_data: Dict[str, dict] = {}
        self.hry_last_modified: Dict[str, float] = {}
        self._stop_watcher = False
        self._watcher_thread: Optional[threading.Thread] = None

    def load_all(self):
        """Load all .hry files from the HAIRY directory."""
        if not self.hairy_dir or not os.path.exists(self.hairy_dir):
            print(f"[CONFIG] HAIRY directory not found: {self.hairy_dir}")
            return

        for filename in os.listdir(self.hairy_dir):
            if filename.endswith(".hry"):
                path = os.path.join(self.hairy_dir, filename)
                self.hry_data[filename] = HryParser.parse(path)
                self.hry_last_modified[path] = os.path.getmtime(path)
                print(f"[CONFIG] Loaded {filename}: "
                      f"{len(self.hry_data[filename].get('defines', {}))} defines, "
                      f"{len(self.hry_data[filename].get('objects', {}))} objects, "
                      f"{len(self.hry_data[filename].get('shops', {}))} shops")

    def get_merged_config(self) -> Dict[str, Any]:
        """Return a merged dict of all defines from Defines.hry and Player.hry."""
        config: Dict[str, Any] = {}
        if "Defines.hry" in self.hry_data:
            config.update(self.hry_data["Defines.hry"].get("defines", {}))
        if "Player.hry" in self.hry_data:
            config.update(self.hry_data["Player.hry"].get("defines", {}))
        return config

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value by key from the merged config."""
        return self.get_merged_config().get(key, default)

    def get_monster_types(self) -> Dict[str, dict]:
        """Returns a dict of all monster type definitions parsed from HRY files."""
        monsters = {}
        for filename, data in self.hry_data.items():
            defines = data.get("defines", {})
            if "FAM_MONSTER" in defines:
                name = list(data.get("objects", {}).keys())[0] if data.get("objects") else os.path.splitext(filename)[0]
                monsters[name] = {
                    "name": name,
                    "hp_max": defines.get("LOCAL_HEALTH", 0),
                    "dam_min": defines.get("NPC_MIN_DMG", 0),
                    "dam_max": defines.get("NPC_MAX_DMG", 0),
                    "attack_speed": defines.get("NPC_ATK_SPEED", 0),
                    "moving_speed": defines.get("LOCAL_ATTACK_TICK", 0),
                    "level": defines.get("NPC_LEVEL", 0),
                    "graphic": defines.get("GRAPHIC", [0, 0]),
                    "tileset": defines.get("TILESET", "AVATAR"),
                    "solid": defines.get("SOLID", 1)
                }
        return monsters

    def get_npc_types(self) -> Dict[str, dict]:
        """Returns a dict of all NPC type definitions parsed from HRY files."""
        npcs = {}
        for filename, data in self.hry_data.items():
            defines = data.get("defines", {})
            if "FAM_NPC" in defines:
                name = list(data.get("objects", {}).keys())[0] if data.get("objects") else os.path.splitext(filename)[0]
                npcs[name] = {
                    "name": name,
                    "hp_max": defines.get("LOCAL_HEALTH", 0),
                    "dam_min": defines.get("NPC_MIN_DMG", 0),
                    "dam_max": defines.get("NPC_MAX_DMG", 0),
                    "speed": defines.get("NPC_ATK_SPEED", 0),
                    "level": defines.get("NPC_LEVEL", 0),
                    "graphic": defines.get("GRAPHIC", [0, 0]),
                    "tileset": defines.get("TILESET", "AVATAR"),
                    "solid": defines.get("SOLID", 1)
                }
        return npcs

    def get_weapon_types(self) -> Dict[str, dict]:
        """Returns a dict of all weapon type definitions parsed from HRY files."""
        weapons = {}
        for filename, data in self.hry_data.items():
            defines = data.get("defines", {})
            if "FAM_WEAPON" in defines:
                name = list(data.get("objects", {}).keys())[0] if data.get("objects") else os.path.splitext(filename)[0]
                weapons[name] = {
                    "name": name,
                    "hp_max": defines.get("LOCAL_HEALTH", 0),
                    "dam_min": defines.get("WEAPON_MIN_DMG", 0),
                    "dam_max": defines.get("WEAPON_MAX_DMG", 0),
                    "speed": defines.get("WEAPON_SPEED", 0),
                    "class": defines.get("WEAPON_CLASS", ""),
                    "req_level": defines.get("WEAPON_REQ_LEVEL", 0),
                    "req_str": defines.get("WEAPON_REQ_STR", 0),
                    "graphic": defines.get("GRAPHIC", [0, 0]),
                    "tileset": defines.get("TILESET", "ITEMS"),
                    "solid": defines.get("SOLID", 1)
                }
        return weapons

    def get_object_types(self) -> Dict[str, dict]:
        """Returns a dict of all object type definitions parsed from HRY files, including animation properties."""
        objects = {}
        for filename, data in self.hry_data.items():
            defines = data.get("defines", {})
            if "FAM_OBJ" in defines:
                name = list(data.get("objects", {}).keys())[0] if data.get("objects") else os.path.splitext(filename)[0]
                
                # Retrieve animation sequence
                anim_seq = []
                seq_str = defines.get("ANIM_SEQUENCE", "")
                if isinstance(seq_str, str):
                    seq_str = seq_str.strip('"').strip("'")
                    if seq_str:
                        # "0,0,World;1,0,World;2,0,World"
                        for part in seq_str.split(";"):
                            if part.strip():
                                coords = part.strip().split(",")
                                if len(coords) >= 3:
                                    try:
                                        anim_seq.append([int(coords[0]), int(coords[1]), coords[2].strip()])
                                    except ValueError:
                                        pass
                
                objects[name] = {
                    "name": name,
                    "hp_max": defines.get("LOCAL_HEALTH", 0),
                    "graphic": defines.get("GRAPHIC", [0, 0]),
                    "tileset": defines.get("TILESET", "OBJECT"),
                    "solid": defines.get("SOLID", 1),
                    "animated": 1 if defines.get("ANIM_FRAMES", 1) > 1 or defines.get("ANIM_MODE") else 0,
                    "anim_mode": str(defines.get("ANIM_MODE", "Cycle")).strip('"').strip("'"),
                    "anim_speed": defines.get("ANIM_SPEED", 100),
                    "anim_frames": defines.get("ANIM_FRAMES", 1),
                    "anim_rand_speed": defines.get("ANIM_RAND_SPEED", 0),
                    "anim_sequence": anim_seq
                }
        return objects

    def get_shops(self) -> Dict[str, list]:
        """Returns all parsed shops merged across all loaded HRY files."""
        shops = {}
        for filename, data in self.hry_data.items():
            shops.update(data.get("shops", {}))
        return shops

    def start_watcher(self):
        """Start a background thread to watch for .hry file changes."""
        if self._watcher_thread and self._watcher_thread.is_alive():
            return
        self._stop_watcher = False
        self._watcher_thread = threading.Thread(
            target=self._watcher_loop, daemon=True
        )
        self._watcher_thread.start()
        print("[CONFIG] File watcher started.")

    def stop_watcher(self):
        """Stop the background watcher thread."""
        self._stop_watcher = True
        if self._watcher_thread:
            self._watcher_thread.join(timeout=3)
            self._watcher_thread = None
        print("[CONFIG] File watcher stopped.")

    def _watcher_loop(self):
        """Poll .hry files for modifications and reload on change."""
        while not self._stop_watcher:
            if self.hairy_dir and os.path.exists(self.hairy_dir):
                for filename in os.listdir(self.hairy_dir):
                    if not filename.endswith(".hry"):
                        continue
                    path = os.path.join(self.hairy_dir, filename)
                    try:
                        mtime = os.path.getmtime(path)
                        if (path not in self.hry_last_modified or
                                mtime > self.hry_last_modified[path]):
                            print(f"[CONFIG] Reloading changed file: {filename}")
                            self.hry_data[filename] = HryParser.parse(path)
                            self.hry_last_modified[path] = mtime
                            if self.on_change:
                                self.on_change(self.get_merged_config())
                    except Exception as e:
                        print(f"[CONFIG ERROR] Watcher error on {filename}: {e}")
            time.sleep(1)
