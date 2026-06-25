import config
import os
import json
import shutil
import zipfile
import ctypes
import threading
import struct
from PIL import Image, ImageDraw
from DebugUtils import DebugUtils
from DatabaseManager import DatabaseManager
from WorldDatabaseManager import WorldDatabaseManager

class SaveLogic:
    """
    Handles all project persistence, including ZIP archival and temporary Editing Pools.
    Class name matches the module name for clean 'from SaveLogic import SaveLogic' imports.
    """
    def __init__(self):
        self.project_path = None
        self.project_name = "MyNewProject"
        self.project_data = {}
        self.types_data = {}
        self.is_dirty = False
        self.io_lock = threading.Lock() # Global lock for file operations
        
        # Ensure temporary pool exists — anchored to script directory, not CWD
        import sys
        if getattr(sys, 'frozen', False):
            self._script_dir = os.path.dirname(sys.executable)
        else:
            self._script_dir = os.path.dirname(os.path.abspath(__file__))
        self.pool_root = os.path.join(self._script_dir, "EditingPool")
        os.makedirs(self.pool_root, exist_ok=True)
        self._hide_folder(self.pool_root)


    def _hide_folder(self, path):
        """ Hardened Security: Sets the 'Hidden' attribute on Windows systems. """
        if os.name == 'nt':
            try:
                # 2 = FILE_ATTRIBUTE_HIDDEN
                ctypes.windll.kernel32.SetFileAttributesW(path, 2)
            except: pass

    @property
    def hairy_dir(self):
        hdir = os.path.join(self._script_dir, "HAIRY")
        os.makedirs(hdir, exist_ok=True)
        return hdir

    def seed_defines(self):
        """ The master project configuration. Explains and defines Global Scopes. """
        path = os.path.join(self.hairy_dir, "Defines.hry")
        content = """// ==============================================================================
// DEFINES.HRY - MASTER PROJECT CONFIGURATION & GLOBAL STATE
// ==============================================================================
// This file is the "Brain" of your world. It stores constants that are shared
// across EVERY script in your project.
//
// SYNTAX: DEFINE [TYPE] [NAME] [VALUE]
// ==============================================================================

// --- 0. TILESET ASSIGNMENT RULES ---
// These rules are followed by the engine when generating new scripts:
//   FAM_OBJ                ->  DEFINE TILESET OBJECT
//   FAM_NPC / FAM_MONSTER  ->  DEFINE TILESET AVATAR
//   FAM_WEAPON / FAM_ARMOR ->  DEFINE TILESET ITEMS

// --- 1. CONFIGURATION ---
DEFINE SHOP_ITEM_FAMILIES        FAM_WEAPON, FAM_ARMOR, FAM_CONSUMABLE, FAM_OBJ

// --- 2. OBJECT FAMILIES ---
// All object-types must belong to exactly one Family.
DEFINE FAM_NPC                 0
DEFINE FAM_WEAPON              1
DEFINE FAM_ARMOR               2
DEFINE FAM_OBJ                 3
DEFINE FAM_CONSUMABLE          4
DEFINE FAM_TILE                5

// --- 2. GLOBAL VARIABLES ---
// These exist once for the entire world. Use them for quest-stages, weather, 
// or economy. Any script can read or modify these.
// Use 'GLOBAL_' prefix as a best-practice for clarity.
DEFINE GLOBAL GLOBAL_QUEST_STAGE     0
DEFINE GLOBAL GLOBAL_KILLS_TOTAL     0
DEFINE GLOBAL GLOBAL_WEATHER_STATE   1

// --- 3. GLOBAL TIMERS ---
// These fire at a set interval (in milliseconds) for ALL objects listening.
// Perfect for synchronized events like Day/Night cycles or server hearts.
DEFINE GLOBAL_TIMER GLOBAL_WORLD_TICK 5000
DEFINE GLOBAL_TIMER GLOBAL_DAY_CYCLE  60000

// --- 4. MAPS ---
DEFINE GLOBAL MAP_WORLD               0
DEFINE GLOBAL MAP_CAVE                1

// --- 5. TILESETS ---
DEFINE GLOBAL TILESET_WORLD           1
DEFINE GLOBAL TILESET_ITEMS           2
DEFINE GLOBAL TILESET_OBJECTS         3
DEFINE GLOBAL TILESET_AVATARS         4

// --- 6. LOGIC CONSTANTS ---
DEFINE GLOBAL TRUE                    1
DEFINE GLOBAL FALSE                   0
"""
        with open(path, 'w') as f: f.write(content)

    # MASTER ENGINE ROADMAP - Shared across all script generation
    MASTER_API_ROADMAP = ""

    def seed_player(self):
        """ Default Player.hry file with Full API Roadmap and Generic Player logic """
        path = os.path.join(self.hairy_dir, "Player.hry")
        content = f"""{self.MASTER_API_ROADMAP}
Object "Plr_Male_Warrior" "Plr_Mage" "Plr_Rogue" 
{{
    OnOpenInventory
    {{
        // Open the default player container
        OpenContainer object
    }}

    OnNew
    {{
        // Spawn basic starting kit
        Object dagger = Create TYPE_DAGGER
        Object gold   = Create TYPE_GOLD
    }}
}}
"""
        with open(path, 'w') as f: f.write(content)
        self.mark_dirty()

    def seed_skills(self):
        """ Seeds the massive hierarchical Skills.hry structure using modern DEFINE syntax """
        path = os.path.join(self.hairy_dir, "Skills.hry")
        content = """// SKILLS.HRY - HIERARCHICAL SKILL TREE & PROGRESSION
// Syntax: <Skill Name> [Table #]

Agriculture
{
    Foraging       [Table 1]
    Harvesting     [Table 0]
}

Combat
{
    Archery
    {
        Crossbows        [Table 0]
        Short_Bows       [Table 1]
        Long_Bows        [Table 3]
        Heavy_Crossbows  [Table 3]
    }
    Axes                 [Table 3]
    Blunt_Weapons        [Table 3]
    Defending            [Table 3]
    Small_Blades         [Table 3]
}

Magery
{
    Mage_Weapons     [Table 0]
    Chaos
    {
        Curses       [Table 0]
        Summon       [Table 0]
    }
}
"""
        with open(path, 'w') as f: f.write(content)

    def seed_tables(self):
        """ Seeds the EXP progression tables into Tables.hry """
        path = os.path.join(self.hairy_dir, "Tables.hry")
        content = """// TABLES.HRY - EXPERIENCE PROGRESSION DATA
// Syntax: Table <Index> { LVL0_EXP, LVL1_EXP, LVL2_EXP, ... }

Table 0
{
    0, 10, 25, 50, 100, 250, 500, 1000
}

Table 1
{
    0, 12, 31, 65, 130, 300, 700, 1500
}

Table 2
{
    0, 16, 41, 90, 200, 450, 1000, 2500
}

Table 3
{
    0, 25, 62, 150, 350, 800, 2000, 5000
}

Table 4
{
    0, 50, 125, 300, 750, 2000, 5000, 12000
}

Table 5
{
    0, 100, 250, 600, 1500, 4000, 10000, 25000
}
"""
        with open(path, 'w') as f: f.write(content)

    def seed_shops(self):
        """ The global Merchant Registry. Defines inventories and prices. """
        path = os.path.join(self.hairy_dir, "Shops.hry")
        # Self-Heal Guard
        if os.path.exists(path): return
        
        content = """// ==============================================================================
// SHOPS.HRY - GLOBAL MERCHANT REGISTRY
// ==============================================================================
// This file defines the inventories and prices for all shops in the world.
// Syntax: Shop "Name" { ItemType, Price, Stock; ... }
// ==============================================================================

Shop "Blacksmith"
{
    // Inventory format: Type, Price, Stock (-1 for infinite)
    TYPE_WEAPON_LONG_SWORD, 150, -1;
    TYPE_ARMOR_IRON_PLATE, 500, 2;
    TYPE_GOLD, 1, -1; // Buyback scrap
}

Shop "General Store"
{
    TYPE_CONSUMABLE_BREAD, 5, 20;
    TYPE_ITEM_TORCH, 10, -1;
}
"""
        with open(path, 'w', encoding='utf-8') as f: f.write(content)

    def new_project(self, name="MyNewProject", tile_size=16):
        """ Creates a fresh Native Workspace directly in the Saves folder. """
        self.project_name = name
        saves_dir = os.path.join(self._script_dir, config.SAVES_DIR)
        os.makedirs(saves_dir, exist_ok=True)
        
        self.project_path = os.path.join(saves_dir, name)
        
        # If it exists, we clear it for a TRULY fresh start (be careful!)
        if os.path.exists(self.project_path):
            try: shutil.rmtree(self.project_path)
            except: pass 
        
        os.makedirs(self.project_path, exist_ok=True)
        
        folders = ["TILESET", "Animations", "Maps", "Types", "IMPORT"]
        for f in folders:
            os.makedirs(os.path.join(self.project_path, f), exist_ok=True)
            
        # 2. Seed Hairy files
        self.seed_defines()
        self.seed_player()
        self.seed_skills()
        self.seed_tables()
        self.seed_shops()

        # 3. Seed Example Scripts (Existing API Template)
        hairy_dir = self.hairy_dir
        self._seed_template(hairy_dir)
        self._seed_beginner_example(hairy_dir)

        # 4. Seed Starter Tileset PNGs (minimum 1 tile each)
        self._seed_tilesets(tile_size)

        # 5. Seed empty Types.json
        types_path = os.path.join(self.project_path, "Types.json")
        if not os.path.exists(types_path):
            with open(types_path, 'w') as f:
                json.dump({}, f)

        # 6. Self-heal Chunks and World data
        self._ensure_map_structures()

        # 7. Create binary databases
        DatabaseManager(self.project_path)
        WorldDatabaseManager(self.project_path)

        # 8. Create project metadata
        self.project_data = {
            "name": name,
            "tile_size": tile_size,
            "version": "1.0.0",
            "last_saved": "Never"
        }
        self.is_dirty = False
        return self.project_path

    def _ensure_map_structures(self):
        """ Internal: Ensures Maps/Chunks.json and Maps/World.json exist. """
        map_dir = os.path.join(self.project_path, "Maps")
        os.makedirs(map_dir, exist_ok=True)
        
        chunks_path = os.path.join(map_dir, "Chunks.json")
        if not os.path.exists(chunks_path):
            # Create a default chunk (empty)
            default_chunk = {
                "0": {
                    "name": "0",
                    "data": {
                        "ground": [[0 for _ in range(config.CHUNK_SIZE)] for _ in range(config.CHUNK_SIZE)],
                        "objects": [[0 for _ in range(config.CHUNK_SIZE)] for _ in range(config.CHUNK_SIZE)]
                    },
                    "locked": False
                }
            }
            with open(chunks_path, 'w') as f:
                json.dump(default_chunk, f, indent=4)

        world_path = os.path.join(map_dir, "World.json")
        if not os.path.exists(world_path):
            # Create a 32x32 world grid of chunk 0
            default_world = {
                "grid": [["0" for _ in range(32)] for _ in range(32)],
                "points": []
            }
            with open(world_path, 'w') as f:
                json.dump(default_world, f, indent=4)

    def load_chunks(self, progress_callback=None, deep_load=True):
        """ 
        Unified Registry: Loads everything from the Binary spatial database. 
        Legacy JSON files and individual .chunk files are retired.
        """
        if not self.project_path:
            DebugUtils.log("Load_chunks failed: project_path is None", level="ERROR")
            return {}

        import_dir = os.path.join(self.project_path, "IMPORT")
        
        # --- 1. DELEGATE TO DATABASE MANAGER ---
        db_mgr = DatabaseManager(self.project_path)
        all_chunks = db_mgr.load_all_chunks()
        
        if not all_chunks:
            DebugUtils.log("DB Load empty - New project or corrupted database.", level="WARNING")

        # Ensure IMPORT exists
        os.makedirs(import_dir, exist_ok=True)
        modified = False


        # --- 2. THE CSV FORGE (IMPORT) ---
        try:
            import csv
            files_to_forge = [f for f in os.listdir(import_dir) if f.lower().endswith(".csv")]
            if files_to_forge:
                modified = True
                for f in files_to_forge:
                    path = os.path.join(import_dir, f)
                    original_name = os.path.splitext(f)[0]
                    chunk_name = original_name
                    
                    if progress_callback: progress_callback(f"Forging CSV: {f}...")

                    # Avoid collisions
                    scid = f"C_{chunk_name}"
                    counter = 1
                    while scid in all_chunks:
                        chunk_name = f"{original_name}_{counter}"
                        scid = f"C_{chunk_name}"
                        counter += 1
                    
                    with open(path, "r", encoding="utf-8-sig") as csv_f:
                        reader = csv.reader(csv_f)
                        csv_data = []
                        for row in reader:
                            csv_data.append([int(val.strip()) if val.strip().isdigit() else 0 for val in row])
                    
                    sz = config.CHUNK_SIZE
                    final_data = [[0 for _ in range(sz)] for _ in range(sz)]
                    for r in range(min(len(csv_data), sz)):
                        for c in range(min(len(csv_data[r]), sz)):
                            final_data[r][c] = csv_data[r][c]
                    
                    chunk_struct = {
                        "name": chunk_name,
                        "data": {"ground": final_data, "objects": [[0 for _ in range(sz)] for _ in range(sz)]},
                        "locked": False
                    }
                    all_chunks[scid] = chunk_struct
                    os.remove(path)
        except Exception as e:
            DebugUtils.log(f"CSV Forge stage failed: {e}", level="ERROR")

        # --- 3. THE SCRIPT FORGE ---
        try:
            scripts_to_import = [f for f in os.listdir(import_dir) if f.lower().endswith(".hry")]
            for f in scripts_to_import:
                src = os.path.join(import_dir, f)
                name = os.path.splitext(f)[0]
                dest = os.path.join(self.hairy_dir, f)
                self._process_script_import(src, dest, name)
                self._manifest_ghost_type(name)
                if os.path.exists(dest): os.remove(src)
        except Exception as e:
            DebugUtils.log(f"Script Forge failed: {e}", level="ERROR")

        if modified:
            self.save_chunks(all_chunks)
            
        DebugUtils.log(f"Successfully loaded {len(all_chunks)} chunks.")
        return all_chunks

    def _process_script_import(self, src_path, dest_path, name):
        """ Copies a script to the repository. """
        import shutil
        shutil.copy2(src_path, dest_path)

    def _manifest_ghost_type(self, name):
        """ Creates a placeholder type in Types.json so scripts are immediately placeable. """
        types_path = os.path.join(self.project_path, "Types.json")
        try:
            if not os.path.exists(types_path):
                with open(types_path, "w") as f: json.dump({}, f)
                
            with open(types_path, "r") as f:
                data = json.load(f)
            
            if name not in data:
                data[name] = {
                    "name": name,
                    "hairy": name,
                    "tile_id": -1, 
                    "is_solid": True,
                    "family": "FAM_OBJECT"
                }
                with open(types_path, "w") as f:
                    json.dump(data, f, indent=4)
                DebugUtils.log(f"Manifested Ghost Type: {name}", level="FORGE")
        except Exception as e:
            DebugUtils.log(f"Manifest failed for {name}: {e}", level="ERROR")

    def save_chunks(self, chunks, chunk_ids_to_save=None):
        """ 
        Saves chunks to the High-Speed Binary Dat system.
        """
        db_mgr = DatabaseManager(self.project_path)
        if chunk_ids_to_save:
            # Optimize: Only save the specified chunks to database
            for scid in chunk_ids_to_save:
                chunk_data = chunks.get(scid)
                if chunk_data:
                    cid = scid[2:] if scid.startswith("C_") else scid
                    db_mgr.save_chunk(cid, chunk_data)
        else:
            # Prepare for storage (strip C_ prefixes)
            to_save = {}
            for scid, info in chunks.items():
                cid = scid[2:] if scid.startswith("C_") else scid
                to_save[cid] = info
            db_mgr.save_all_chunks(to_save)
        self.mark_dirty()

    def delete_chunk(self, chunk_id):
        """ 
        Retired: Chunks are now deleted from the in-memory dictionary and 
        written back to the registry via save_chunks.
        """
        pass

    def load_world(self, map_name="WORLD"):
        """ Loads a specific map grid using the Spatial Engine. Scenario C Aware. """
        if not self.project_path: return {"grid": [["0" for _ in range(32)] for _ in range(32)], "points": []}
        
        # --- 1. DELEGATE TO SPATIAL MANAGER ---
        spatial_mgr = WorldDatabaseManager(self.project_path)
        world_data = spatial_mgr.load_world_state(map_name)
        
        if not world_data.get("grid"):
            DebugUtils.log("Spatial Load empty, fallback triggered...", level="WARNING")

        return world_data

    def save_world(self, world_data, map_name="WORLD"):
        """ Saves the providing world grid to the Spatial Database. """
        if not self.project_path: return
        
        spatial_mgr = WorldDatabaseManager(self.project_path)
        spatial_mgr.save_world_state(world_data, map_name)
        self.mark_dirty()

    def _seed_tilesets(self, tile_size):
        """
        Creates starter tileset PNG files so the editor has something to display.
        """
        tileset_dir = os.path.join(self.project_path, "TILESET")
        os.makedirs(tileset_dir, exist_ok=True)
        
        # 4 standard tilesets with distinct starter colors
        tilesets = {
            "World_TILESET.png":   (34, 139, 34, 255),    # Forest Green (grass)
            "ITEMS_TILESET.png":   (139, 119, 101, 255),   # Tan/Brown (items)
            "OBJECTS_TILESET.png": (105, 105, 105, 255),   # Gray (objects)
            "AVATARS_TILESET.png": (70, 130, 180, 255),    # Steel Blue (avatars)
        }
        
        for filename, color in tilesets.items():
            path = os.path.join(tileset_dir, filename)
            if not os.path.exists(path):
                # Create a single-tile image
                img = Image.new("RGBA", (tile_size, tile_size), color)
                # Draw a subtle grid marker in the corner so it's not a flat square
                draw = ImageDraw.Draw(img)
                draw.rectangle([0, 0, tile_size - 1, tile_size - 1], outline=(255, 255, 255, 80))
                img.save(path, "PNG")
                DebugUtils.log(f"Created starter tileset: {filename} ({tile_size}x{tile_size})", level="SEED")

    def _seed_template(self, hairy_dir):
        """ Creates the 'Master API Bible' Template.hry with full descriptions and strict rules. """
        path = os.path.join(hairy_dir, "Template.hry")
        with open(path, "w") as f:
            f.write("//====================================================================\n")
            f.write("//\n")
            f.write("// Template.hry - MASTER DEVELOPMENT SKELETON\n")
            f.write("//\n")
            f.write("//====================================================================\n\n")

            f.write("DEFINE FAM_OBJ                    // The logic family (determines folder and editor behavior)\n")
            f.write("DEFINE LOCAL_HEALTH          100  // Initial Health Points for this instance\n")
            f.write("DEFINE LOCAL_STRENGTH        10   // Physical power / Carry capacity\n")
            f.write("DEFINE LOCAL_IS_USEABLE      1    // Interaction toggle (0 = static, 1 = interactive)\n")
            f.write("DEFINE LOCAL_ATTACK_TICK     0    // Attack speed (0 = null/none, >0 = ms between hits)\n")
            f.write("// DEFINE LOCAL_REGEN_INTERVAL 5000 // (Optional) Recovery speed in ms. Enable to trigger regen loops.\n\n")

            f.write("DEFINE HasClicked            0    // Tracks how many times a player interacts with this\n")
            f.write("DEFINE IsActivated           0    // Logical toggle (e.g. 0=Closed, 1=Open)\n\n")

            f.write("DEFINE TILESET OBJECT            // Visual Asset Source (FAM_OBJ requires OBJECT tileset)\n")
            f.write("DEFINE GRAPHIC 0, 0              // X, Y coordinate of the tile in the tileset\n")
            f.write("DEFINE SOLID TRUE                // Physical state (TRUE = impassable, FALSE = walkthrough)\n\n")

            f.write("// --- Syntax QuickRef ---\n")
            f.write("// Math: Health += 10 | Health Plus 10\n")
            f.write("// Choices: DEFINE IsActivated 0 | DEFINE HasClicked 0\n\n")

            f.write("Object \"My_Template_Object\"\n{\n")
            f.write("    OnUse\n    {\n")
            f.write("        // Triggered when a player Double-Clicks this object.\n")
            f.write("        Print \"You triggered the Interaction Hook!\\n\"\n")
            f.write("        HasClicked += 1\n")
            f.write("    }\n\n")

            f.write("    OnLook\n    {\n")
            f.write("        // Triggered when a player Right-Clicks / Examines this object.\n")
            f.write("        Print \"It is a perfectly formed Template Object.\\n\"\n")
            f.write("    }\n\n")

            f.write("    OnNew\n    {\n")
            f.write("        // Fires ONCE when this object is first created in the world.\n")
            f.write("    }\n\n")

            f.write("    OnSpawn\n    {\n")
            f.write("        // Fires every time this object enters the world (map load/spawn).\n")
            f.write("    }\n\n")

            f.write("    OnDeath\n    {\n")
            f.write("        // Fires when Health reaches 0. Ideal for drops or removal.\n")
            f.write("        Print \"The object has been destroyed!\\n\"\n")
            f.write("    }\n\n")

            f.write("    OnTalk\n    {\n")
            f.write("        // Fires when a player initiates dialogue with this entity.\n")
            f.write("    }\n\n")

            f.write("    OnTouch\n    {\n")
            f.write("        // Fires when a player or entity steps onto this object's tile.\n")
            f.write("    }\n\n")

            f.write("    OnEnterContainer\n    {\n")
            f.write("        // Fires when this object is picked up / put into a bag.\n")
            f.write("    }\n\n")

            f.write("    OnRemoveFromContainer\n    {\n")
            f.write("        // Fires when this object is taken out of a bag/container.\n")
            f.write("    }\n\n")

            f.write("    OnEquip\n    {\n")
            f.write("        // Fires when this item is worn or held in an equipment slot.\n")
            f.write("    }\n\n")

            f.write("    OnUnEquip\n    {\n")
            f.write("        // Fires when this item is removed from an equipment slot.\n")
            f.write("    }\n\n")

            f.write("    OnDrop\n    {\n")
            f.write("        // Fires when this object is dropped onto the ground.\n")
            f.write("    }\n\n")

            f.write("    OnDrag\n    {\n")
            f.write("        // Fires when a player clicks and drags this object UI.\n")
            f.write("    }\n\n")

            f.write("    OnMove\n    {\n")
            f.write("        // Fires every time this object changes position in the world.\n")
            f.write("    }\n\n")

            f.write("    OnCollide\n    {\n")
            f.write("        // Fires when a movement action results in a collision.\n")
            f.write("    }\n\n")

            f.write("    OnHit\n    {\n")
            f.write("        // Fires when this object takes damage from an external source.\n")
            f.write("    }\n\n")

            f.write("    OnCombat\n    {\n")
            f.write("        // Fires when this object enters the combat state.\n")
            f.write("    }\n\n")

            f.write("    OnAnimate\n    {\n")
            f.write("        // Custom driver for sprite animations.\n")
            f.write("    }\n\n")

            f.write("    OnTimer LOCAL_ATTACK_TICK\n    {\n")
            f.write("        // Periodic logic driven by LOCAL_ATTACK_TICK (0 = disabled).\n")
            f.write("    }\n\n")

            f.write("    OnTimer GLOBAL_WORLD_TICK\n    {\n")
            f.write("        // Server-wide heartbeat pulse (Synchronized across all objects).\n")
            f.write("    }\n")
            f.write("}\n\n")

            f.write("// *****************************************************************\n")
            f.write("//   ENGINE COMMAND REFERENCE\n")
            f.write("// *****************************************************************\n")
            f.write("//\n")
            f.write("// --- Object Lifecycle ---\n")
            f.write("//   Create <type>              Create a new object in the world\n")
            f.write("//   Destroy <object>            Remove object from world permanently\n")
            f.write("//   Respawn <object>            Bring a dead creature back to life\n")
            f.write("//   Kill <object>               Instantly kill a creature\n")
            f.write("//   Resurrect <object>          Revive a dead player\n")
            f.write("//\n")
            f.write("// --- Health & Status ---\n")
            f.write("//   Heal <target> <amount>      Restore health points\n")
            f.write("//   GiveHealth <target> <amt>   Same as Heal\n")
            f.write("//   GiveMana <target> <amount>  Restore mana points\n")
            f.write("//   Poison <target> <level>     Apply poison effect\n")
            f.write("//   Cure <target>               Remove poison\n")
            f.write("//   Stasis <object> TRUE/FALSE  Freeze/unfreeze (cannot move)\n")
            f.write("//\n")
            f.write("// --- Movement & World ---\n")
            f.write("//   Teleport <who> <map> <x> <y>   Move to coordinates\n")
            f.write("//   Walk <object> <direction>       Force walk a direction\n")
            f.write("//   Follow <object> <target>        Follow another object\n")
            f.write("//   Flee <object>                   Run away from combat\n")
            f.write("//   Sleep <ticks>                   Pause script execution\n")
            f.write("//   GetDistance <a> <b>              Returns distance between\n")
            f.write("//   CheckLineOfSight <a> <b>        Can A see B?\n")
            f.write("//\n")
            f.write("// --- Communication ---\n")
            f.write("//   Print \"text\\n\"              Display text to player\n")
            f.write("//   Say 'text'                  Speak above head (visible)\n")
            f.write("//   Whisper <target> 'text'     Private message\n")
            f.write("//   Broadcast 'text'            Send to all players\n")
            f.write("//   GetName <object>            Returns the object's name\n")
            f.write("//\n")

    def _seed_beginner_example(self, hairy_dir):
        """ Seeds Example_Beginner.hry to show a starting user how things work. """
        path = os.path.join(hairy_dir, "Example_Beginner.hry")
        with open(path, "w") as f:
            f.write("//==============================================================================\n")
            f.write("//   EXAMPLE_BEGINNER.HRY - YOUR FIRST SCRIPT\n")
            f.write("//==============================================================================\n")
            f.write("// This script shows you how to use the DEFINEs from Defines.hry\n")
            f.write("// and basic logic functions like If, Else, and Print.\n")
            f.write("//==============================================================================\n\n")
            
            f.write("// --- 1. LOCAL DATA ---\n")
            f.write("// These variables belong ONLY to this specific object.\n")
            f.write("DEFINE UseCount      0\n\n")

            f.write("// (Example script - add logic below)\n")
            f.write("Object \"Beginner_Item\"\n")
            f.write("{\n")
            f.write("    OnUse\n")
            f.write("    {\n")
            f.write("        UseCount += 1\n")
            f.write("        Print \"You have used this object \"\n")
            f.write("        Print UseCount\n")
            f.write("        Print \" times.\\n\"\n\n")

            f.write("        // Example using Logic Constants from Defines.hry\n")
            f.write("        If (G_TALKED_TO_KING == TRUE)\n")
            f.write("        {\n")
            f.write("            Print \"The King said you were coming! Welcome traveler.\\n\"\n")
            f.write("        }\n")
            f.write("        Else\n")
            f.write("        {\n")
            f.write("            Print \"Go find the King first!\\n\"\n")
            f.write("        }\n")
            f.write("    }\n")
            f.write("}\n")

    def save_project(self):
        """ Finalizes the workspace state. Returns (success, error_msg). """
        if not self.project_path:
            return (False, "No project loaded.")
        
        with self.io_lock:
            try:
                # 1. Update master metadata
                meta_path = os.path.join(self.project_path, "project.json")
                with open(meta_path, 'w') as f:
                    json.dump(self.project_data, f, indent=4)
                            
                print(f"[DEBUG] Project '{self.project_name}' Saved Locally: {self.project_path}")
                self.is_dirty = False
                return (True, None)
            except Exception as e:
                print(f"[ERROR] Save failed: {e}")
                return (False, str(e))

    def load_project(self, project_dir, progress_callback=None):
        """ Points the engine to a Workspace Folder. Returns (project_data, error_msg). """
        try:
            if progress_callback: progress_callback("Mapping Project Workspace...")
            print(f"[DEBUG] Mapping Project: {project_dir}")
            
            if not os.path.isdir(project_dir):
                return (None, f"Not a valid directory: {project_dir}")
            
            name = os.path.basename(project_dir)
            self.project_name = name
            self.project_path = project_dir
            
            # Load metadata
            meta_path = os.path.join(self.project_path, "project.json")
            if os.path.exists(meta_path):
                with open(meta_path, 'r') as f:
                    self.project_data = json.load(f)
            else:
                self.project_data = {"name": name, "version": "1.0.0"}
            
            # Self-Healing: Seed necessary infrastructure directly in the workspace
            tile_size = self.project_data.get("tile_size", 16)
            self._seed_tilesets(tile_size)
            
            types_path = os.path.join(self.project_path, "Types.json")
            if not os.path.exists(types_path):
                with open(types_path, 'w') as f: json.dump({}, f)
            
            self._ensure_map_structures()

            # --- 1. SPATIAL & ASSET DATABASE HANDSHAKE ---
            # Instantiate managers once to trigger Scenario A/B/C checks immediately
            if progress_callback: progress_callback("Engaging Binary Data Handshake...")
            try:
                DatabaseManager(self.project_path)
                WorldDatabaseManager(self.project_path)
                DebugUtils.log("Binary Synchronization Layer: Active & Healthy.")
            except Exception as e:
                DebugUtils.log(f"Database Handshake Failure: {e}", level="ERROR")

            hairy_dir = self.hairy_dir
            
            # --- SELF HEAL: Shops.hry ---
            self.seed_shops()
            defines_path = os.path.join(hairy_dir, "Defines.hry")
            if os.path.exists(defines_path):
                try:
                    with open(defines_path, 'r', encoding='utf-8') as f:
                        d_content = f.read()
                    if '#include "Shops.hry"' not in d_content:
                        with open(defines_path, 'w', encoding='utf-8') as f:
                            f.write('#include "Shops.hry"\n' + d_content)
                except: pass
            
            # --- MANDATORY ASYNC-READY TRANSMUTATION ---
            os.makedirs(os.path.join(self.project_path, "IMPORT"), exist_ok=True)
            os.makedirs(os.path.join(self.project_path, "Maps"), exist_ok=True)
            
            # Forge chunks directly in the workspace (Shallow Mapping)
            # This is nearly instant compared to the 21s deep-parse.
            self.load_chunks(progress_callback=progress_callback, deep_load=False)
            
            # --- ASSET SYNC ---
            # Automatically heal Defines.hry if new files were added manually
            self.sync_asset_definitions()
            
            # --- ASYNC TYPES LOAD ---
            def async_load_types():
                try:
                    import ScriptParser
                    self.types_data = ScriptParser.load_all_types_with_metadata(self.project_path)
                    DebugUtils.log(f"Asynchronously loaded {len(self.types_data)} Hairy types into cache.")
                except Exception as ex:
                    print(f"[ERROR] Async type loading failed: {ex}")
            threading.Thread(target=async_load_types, daemon=True).start()
            
            self.is_dirty = False
            return (self.project_data, None)
        except Exception as e:
            print(f"[ERROR] Load failed: {e}")
            return (None, str(e))

    def sync_asset_definitions(self):
        """ Audits physical assets vs script defines and 'heals' if missing. """
        if not self.project_path: return
        
        tileset_dir = os.path.join(self.project_path, "TILESET")
        hairy_dir = self.hairy_dir
        defines_path = os.path.join(hairy_dir, "Defines.hry")
        
        if not os.path.exists(tileset_dir) or not os.path.exists(defines_path): return
        
        try:
            # 1. Read existing defines
            import ScriptParser
            defined_tilesets = ScriptParser.get_all_tilesets(self.project_path)
            
            # 2. Check disk for orphans
            needs_append = []
            for f in os.listdir(tileset_dir):
                if f.lower().endswith(".png"):
                    core = f.replace("_TILESET.png", "").replace(".png", "").upper()
                    if core not in defined_tilesets:
                        needs_append.append(core)
            
            # 3. Heal the script
            if needs_append:
                DebugUtils.log(f"Auto-Registering {len(needs_append)} orphaned tilesets in Defines.hry")
                with open(defines_path, "a", encoding="utf-8") as f:
                    f.write("\n// --- AUTO-REGISTERED ASSETS ---\n")
                    for name in needs_append:
                        f.write(f"DEFINE GLOBAL TILESET_{name} 0\n")
        except Exception as e:
            DebugUtils.log(f"Asset sync failed: {e}", level="ERROR")

    def rename_project(self, new_name):
        """ Renames the current project folder and updates metadata. Returns (success, error_msg). """
        if not self.project_path:
            return (False, "No project loaded.")
        
        try:
            old_path = self.project_path
            new_path = os.path.join(self.pool_root, new_name)
            
            if os.path.exists(new_path) and new_path != old_path:
                shutil.rmtree(new_path)
                
            os.rename(old_path, new_path)
            self.project_path = new_path
            self.project_name = new_name
            self.project_data["name"] = new_name
            
            return (True, None)
        except Exception as e:
            return (False, str(e))

    def cleanup_pool(self):
        """ Deletes all temporary editing folders. """
        if os.path.exists(self.pool_root):
            try:
                shutil.rmtree(self.pool_root)
                print("[DEBUG] Editing Pool cleaned.")
            except Exception as e:
                print(f"[DEBUG] Warning: Pool cleanup partial (locked files): {e}")

    def mark_dirty(self):
        self.is_dirty = True
