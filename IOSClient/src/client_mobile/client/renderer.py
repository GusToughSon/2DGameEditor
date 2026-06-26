# client/renderer.py - Game Client Renderer for ThePlayerCity
# Reads tilesets from 2DGameEditor and renders the world using the SQLite map data.
import pygame
import sys
import os
from pathlib import Path
from core.maps import MapDatabase, CHUNK_SIZE
from client.network import GameClientNetwork

# ─── Display constants ───────────────────────────────────────────────────
SCREEN_WIDTH  = 800
SCREEN_HEIGHT = 600
TILE_SIZE     = 16     # Source tile size in the tileset images (16x16px)
SCALE         = 2      # Draw scale factor
DRAW_SIZE     = TILE_SIZE * SCALE  # 32 px per rendered tile

# How many tiles fit in the play viewport (left side of screen)?
SIDEBAR_WIDTH = 180                              # Right-side HUD width
VIEWPORT_W    = (SCREEN_WIDTH - SIDEBAR_WIDTH)   # 620 px available
VIEWPORT_H    = SCREEN_HEIGHT                    # 600 px
TILES_ACROSS  = VIEWPORT_W // DRAW_SIZE          # 620//32 = 19 tiles
TILES_DOWN    = VIEWPORT_H // DRAW_SIZE          # 600//32 = 18 tiles

# The viewport is anchored at the top-left of the screen (play area on LEFT).
VIEWPORT_X    = 0
VIEWPORT_Y    = 0

# The player is drawn at the centre of the viewport.
PLAYER_TILE_X = TILES_ACROSS // 2   # 9
PLAYER_TILE_Y = TILES_DOWN   // 2   # 9

# ─── Tileset ID mapping (matches 2DGameEditor conventions) ────────────
TILESET_FILES = {
0: "World_TILESET.png",
1: "ITEMS_TILESET.png",
2: "OBJECTS_TILESET.png",
3: "AVATARS_TILESET.png",
}

TILESET_DIR = Path(__file__).resolve().parents[2] / "Saves" / "ThePlayerCity" / "TILESET"


class GameClientEngine:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("ThePlayerCity - World View")
        self.clock = pygame.time.Clock()

        # Auth parameters passed from launcher
        self.username = "test"
        self.password = "test"
        self.char_slot = 0
        if len(sys.argv) >= 3:
            self.username = sys.argv[1]
            self.password = sys.argv[2]
            if len(sys.argv) >= 4:
                try:
                    self.char_slot = int(sys.argv[3])
                except ValueError:
                    pass

        # Resources
        self.tilesets = {}   # ts_id → (Surface, stride)
        self.map_db = MapDatabase()
        self._load_tilesets()
        self.map_db.load()

        # Connect to Server
        self.net = GameClientNetwork()
        print(f"[ENGINE] Connecting to server as {self.username}...")
        resp = self.net.connect_and_enter(self.username, self.password, self.char_slot)
        if not resp.get("success"):
            print(f"[ENGINE ERROR] Failed to join game: {resp.get('error')}")
            pygame.quit()
            sys.exit(1)

        self.player_x = resp.get("x", 10)
        self.player_y = resp.get("y", 10)
        self.player_avatar = resp.get("avatar", 0)
        self.player_hp = resp.get("hp", 10)
        self.player_hp_max = resp.get("hp_max", 10)
        self.player_mana = resp.get("mana", 5)
        self.player_level = resp.get("level", 1)
        self.player_name = resp.get("name", "Unknown")

        # Surrounding Entity Registries
        self.other_players = {}  # name -> {x, y, avatar}
        self.monsters = {}       # know_id -> {name, x, y, hp, hp_max, graphic}
        self.npcs = {}           # npc_id -> {name, x, y, avatar, npc_type}
        self.ground_items = {}   # item_id -> {item_type, x, y}
        self.bodies = {}         # body_id -> {name, x, y}
        self.target_monster_id = None
        
        # Local inventory storage (slot index mappings)
        self.backpack = [None] * 24
        self.bank = [None] * 50
        self.worn = [None] * 10
        self.bank_active = False

        # Drag and drop state
        self.is_dragging = False
        self.dragged_item = None
        self.drag_source = None
        self.dragged_slot = None

        # Chat details
        self.chat_log = []
        self.chat_input = ""
        self.chat_active = False
        
        # GM overlay and Tooltips / Minimap state
        self.gm_active = False
        self.item_types = {}
        types_path = Path(__file__).resolve().parents[2] / "Saves" / "ThePlayerCity" / "Types.json"
        if types_path.exists():
            try:
                import json
                with open(types_path, 'r', encoding='utf-8') as f:
                    self.item_types = json.load(f)
            except Exception as e:
                print(f"Error loading Types.json: {e}")

        # Load HAIRY config for object details/animations
        from core.config import GameConfig
        self.cfg = GameConfig(str(Path(__file__).resolve().parents[2] / "HAIRY"))
        self.cfg.load_all()
        self.object_types_cfg = self.cfg.get_object_types()

        # HUD font
        self.font = pygame.font.SysFont("Segoe UI", 12)
        self.font_large = pygame.font.SysFont("Segoe UI", 14, bold=True)

    def get_avatar_tile_id(self, graphic) -> int:
        """Translates pixel graphic coordinates [gx, gy] from HAIRY files to a tile ID in the AVATARS tileset."""
        if not isinstance(graphic, list) or len(graphic) < 2:
            return 0
        gx, gy = graphic[0], graphic[1]
        col = gx // 16
        row = gy // 16
        return row * 50 + col

    def _load_tilesets(self):
        ts_dir = TILESET_DIR if TILESET_DIR.exists() else Path("TILESET")
        for ts_id, filename in TILESET_FILES.items():
            path = ts_dir / filename
            if path.exists():
                try:
                    surf = pygame.image.load(str(path)).convert_alpha()
                    surf.set_colorkey((255, 0, 255))
                    stride = surf.get_width() // TILE_SIZE
                    self.tilesets[ts_id] = (surf, stride)
                    print(f"[ENGINE] Loaded {filename}: {surf.get_width()}x{surf.get_height()} (stride={stride})")
                except Exception as e:
                    print(f"[ENGINE ERROR] {filename}: {e}")
            else:
                print(f"[ENGINE WARNING] {filename} not found at {path}")

        if 0 in self.tilesets:
            self.map_db.tiles_per_row = self.tilesets[0][1]

    def _blit_tile(self, ts_id: int, tile_id: int, screen_x: int, screen_y: int):
        if tile_id <= 0 or ts_id not in self.tilesets:
            return
        sheet, stride = self.tilesets[ts_id]
        src_col = tile_id % stride
        src_row = tile_id // stride
        src_x = src_col * TILE_SIZE
        src_y = src_row * TILE_SIZE

        if src_x + TILE_SIZE > sheet.get_width() or src_y + TILE_SIZE > sheet.get_height():
            return
        src_rect = pygame.Rect(src_x, src_y, TILE_SIZE, TILE_SIZE)
        sub = sheet.subsurface(src_rect)
        if sub.get_size() != (DRAW_SIZE, DRAW_SIZE):
            sub = pygame.transform.scale(sub, (DRAW_SIZE, DRAW_SIZE))
        self.screen.blit(sub, (screen_x, screen_y))

    def process_incoming_packets(self):
        """Drain the network client queue and update active states."""
        while not self.net.incoming_queue.empty():
            packet = self.net.incoming_queue.get()
            ptype = packet.get("type")
            
            if ptype == "move_response":
                if packet.get("success"):
                    self.player_x = packet.get("x", self.player_x)
                    self.player_y = packet.get("y", self.player_y)
                    if self.bank_active:
                        if abs(self.player_x - 12) > 1 or abs(self.player_y - 12) > 1:
                            self.bank_active = False
                    
            elif ptype == "coordinates":
                name = packet.get("name")
                if name:
                    self.other_players[name] = {
                        "x": packet.get("x", 10),
                        "y": packet.get("y", 10),
                        "avatar": packet.get("avatar", 0)
                    }
                    
            elif ptype == "player_left":
                name = packet.get("name")
                if name in self.other_players:
                    del self.other_players[name]

            elif ptype == "stats_update":
                self.player_hp = packet.get("hp", self.player_hp)
                self.player_hp_max = packet.get("hp_max", self.player_hp_max)
                self.player_mana = packet.get("mana", self.player_mana)
                
            elif ptype == "inventory_update":
                self.backpack = [None] * 24
                self.bank = [None] * 50
                self.worn = [None] * 10
                for item in packet.get("items", []):
                    container = item.get("container")
                    slot = item.get("slot", 0)
                    if container == "backpack" and 0 <= slot < len(self.backpack):
                        self.backpack[slot] = item
                    elif container == "bank" and 0 <= slot < len(self.bank):
                        self.bank[slot] = item
                    elif container == "worn" and 0 <= slot < len(self.worn):
                        self.worn[slot] = item
                
            elif ptype == "chat_broadcast":
                sender = packet.get("sender", "Server")
                msg = packet.get("message", "")
                self.chat_log.append(f"{sender}: {msg}")
                if len(self.chat_log) > 8:
                    self.chat_log.pop(0)
                    
            elif ptype == "object_state":
                ox = packet.get("x")
                oy = packet.get("y")
                on = packet.get("on")
                for obj in self.map_db.map_objects:
                    if obj.x == ox and obj.y == oy:
                        obj.on = on
                        break
                        
            elif ptype == "monster_spawn":
                m_id = packet.get("know_id")
                self.monsters[m_id] = {
                    "name": packet.get("name"),
                    "x": packet.get("x"),
                    "y": packet.get("y"),
                    "hp": packet.get("hp"),
                    "hp_max": packet.get("hp_max"),
                    "graphic": packet.get("graphic")
                }
                
            elif ptype == "monster_move":
                m_id = packet.get("know_id")
                if m_id in self.monsters:
                    self.monsters[m_id]["x"] = packet.get("x")
                    self.monsters[m_id]["y"] = packet.get("y")
                    
            elif ptype == "monster_left":
                m_id = packet.get("know_id")
                if m_id in self.monsters:
                    del self.monsters[m_id]
                if self.target_monster_id == m_id:
                    self.target_monster_id = None
                    
            elif ptype == "monster_hp":
                m_id = packet.get("know_id")
                if m_id in self.monsters:
                    self.monsters[m_id]["hp"] = packet.get("hp")
                    
            elif ptype == "monster_death":
                m_id = packet.get("know_id")
                if m_id in self.monsters:
                    del self.monsters[m_id]
                if self.target_monster_id == m_id:
                    self.target_monster_id = None

            elif ptype == "combat_result":
                attacker = packet.get("attacker", "Someone")
                target = packet.get("target", "someone")
                hit = packet.get("hit", False)
                damage = packet.get("damage", 0)
                if hit:
                    msg = f"{attacker} hit {target} for {damage} damage!"
                else:
                    msg = f"{attacker} missed {target}."
                self.chat_log.append(msg)
                if len(self.chat_log) > 8:
                    self.chat_log.pop(0)
            
            elif ptype == "npc_spawn":
                n_id = packet.get("npc_id")
                self.npcs[n_id] = {
                    "name": packet.get("name"),
                    "x": packet.get("x"),
                    "y": packet.get("y"),
                    "avatar": packet.get("avatar", 0),
                    "npc_type": packet.get("npc_type")
                }
                
            elif ptype == "npc_left":
                n_id = packet.get("npc_id")
                if n_id in self.npcs:
                    del self.npcs[n_id]
                    
            elif ptype == "ground_item_spawn":
                it_id = packet.get("item_id")
                self.ground_items[it_id] = {
                    "item_type": packet.get("item_type"),
                    "x": packet.get("x"),
                    "y": packet.get("y")
                }
                
            elif ptype == "ground_item_despawn":
                it_id = packet.get("item_id")
                if it_id in self.ground_items:
                    del self.ground_items[it_id]
                    
            elif ptype == "body_spawn":
                b_id = packet.get("body_id")
                self.bodies[b_id] = {
                    "name": packet.get("name"),
                    "x": packet.get("x"),
                    "y": packet.get("y")
                }
                
            elif ptype == "body_left":
                b_id = packet.get("body_id")
                if b_id in self.bodies:
                    del self.bodies[b_id]

    def render(self):
        self.screen.fill((0, 0, 0))

        # ── Map viewport (play area on LEFT) ─────────────────────────────
        for vy in range(TILES_DOWN):
            for vx in range(TILES_ACROSS):
                wx = self.player_x - PLAYER_TILE_X + vx
                wy = self.player_y - PLAYER_TILE_Y + vy
                px = VIEWPORT_X + vx * DRAW_SIZE
                py = VIEWPORT_Y + vy * DRAW_SIZE

                # Layer 0: Ground (World_TILESET)
                ground_tid = self.map_db.get_tile_at(wx, wy, 0)
                if ground_tid > 0:
                    self._blit_tile(0, ground_tid, px, py)

                # Layer 1: Objects (OBJECTS_TILESET)
                obj_tid = self.map_db.get_tile_at(wx, wy, 1)
                if obj_tid > 0:
                    is_open_door = False
                    o_type = None
                    for obj in self.map_db.map_objects:
                        if obj.x == wx and obj.y == wy:
                            o_type = self.map_db.object_types.get(obj.type_id)
                            if o_type and o_type.openable and not obj.on:
                                is_open_door = True
                                break
                    if not is_open_door:
                        ts_id = 2  # Default OBJECTS_TILESET
                        if o_type and o_type.name in self.object_types_cfg:
                            cfg_obj = self.object_types_cfg[o_type.name]
                            if cfg_obj.get("animated") and cfg_obj.get("anim_sequence"):
                                now_ms = pygame.time.get_ticks()
                                speed = cfg_obj.get("anim_speed", 200)
                                frames = cfg_obj.get("anim_frames", 1)
                                frame_idx = (now_ms // speed) % frames
                                seq = cfg_obj["anim_sequence"]
                                if frame_idx < len(seq):
                                    ts_map = {"World": 0, "ITEMS": 1, "OBJECT": 2, "AVATAR": 3, "AVATARS": 3}
                                    ts_name = seq[frame_idx][2]
                                    ts_id = ts_map.get(ts_name, 2)
                                    if ts_id in self.tilesets:
                                        stride = self.tilesets[ts_id][1]
                                        obj_tid = seq[frame_idx][1] * stride + seq[frame_idx][0]
                        self._blit_tile(ts_id, obj_tid, px, py)

        # ── Render other players ──────────────────────────────────────────
        for name, p in self.other_players.items():
            vx = p["x"] - self.player_x + PLAYER_TILE_X
            vy = p["y"] - self.player_y + PLAYER_TILE_Y
            if 0 <= vx < TILES_ACROSS and 0 <= vy < TILES_DOWN:
                other_px = VIEWPORT_X + vx * DRAW_SIZE
                other_py = VIEWPORT_Y + vy * DRAW_SIZE
                if 3 in self.tilesets:
                    self._blit_tile(3, p["avatar"], other_px, other_py)
                else:
                    pygame.draw.rect(self.screen, (0, 0, 255), (other_px, other_py, DRAW_SIZE, DRAW_SIZE))

        # ── Render monsters ──────────────────────────────────────────────
        for m_id, m in self.monsters.items():
            vx = m["x"] - self.player_x + PLAYER_TILE_X
            vy = m["y"] - self.player_y + PLAYER_TILE_Y
            if 0 <= vx < TILES_ACROSS and 0 <= vy < TILES_DOWN:
                mon_px = VIEWPORT_X + vx * DRAW_SIZE
                mon_py = VIEWPORT_Y + vy * DRAW_SIZE
                
                # Convert graphic [gx, gy] to tile ID on avatars tileset (ID 3)
                tile_id = self.get_avatar_tile_id(m.get("graphic"))
                if 3 in self.tilesets and tile_id > 0:
                    self._blit_tile(3, tile_id, mon_px, mon_py)
                else:
                    pygame.draw.rect(self.screen, (0, 255, 0), (mon_px, mon_py, DRAW_SIZE, DRAW_SIZE))
                
                # Draw HP bar above monster
                hp = m.get("hp", 10)
                hp_max = m.get("hp_max", 10)
                if hp_max > 0:
                    hp_pct = max(0.0, min(1.0, hp / hp_max))
                    bar_w = int(DRAW_SIZE * hp_pct)
                    pygame.draw.rect(self.screen, (100, 100, 100), (mon_px, mon_py - 6, DRAW_SIZE, 3))
                    pygame.draw.rect(self.screen, (255, 0, 0), (mon_px, mon_py - 6, bar_w, 3))
                
                # Draw red selection ring around targeted monster
                if self.target_monster_id == m_id:
                    pygame.draw.rect(self.screen, (255, 0, 0), (mon_px - 2, mon_py - 2, DRAW_SIZE + 4, DRAW_SIZE + 4), 1)

        # ── Render ground items ──────────────────────────────────────────
        for it_id, item in self.ground_items.items():
            vx = item["x"] - self.player_x + PLAYER_TILE_X
            vy = item["y"] - self.player_y + PLAYER_TILE_Y
            if 0 <= vx < TILES_ACROSS and 0 <= vy < TILES_DOWN:
                item_px = VIEWPORT_X + vx * DRAW_SIZE
                item_py = VIEWPORT_Y + vy * DRAW_SIZE
                self._blit_tile(1, item["item_type"], item_px, item_py)

        # ── Render corpses/bodies ────────────────────────────────────────
        for b_id, body in self.bodies.items():
            vx = body["x"] - self.player_x + PLAYER_TILE_X
            vy = body["y"] - self.player_y + PLAYER_TILE_Y
            if 0 <= vx < TILES_ACROSS and 0 <= vy < TILES_DOWN:
                body_px = VIEWPORT_X + vx * DRAW_SIZE
                body_py = VIEWPORT_Y + vy * DRAW_SIZE
                # Draw a gray tombstone
                pygame.draw.rect(self.screen, (108, 112, 134), (body_px + 8, body_py + 4, 16, 24))
                pygame.draw.line(self.screen, (205, 214, 244), (body_px + 16, body_py + 8), (body_px + 16, body_py + 22), 2)
                pygame.draw.line(self.screen, (205, 214, 244), (body_px + 12, body_py + 12), (body_px + 20, body_py + 12), 2)

        # ── Render NPCs ──────────────────────────────────────────────────
        for npc_id, npc in self.npcs.items():
            vx = npc["x"] - self.player_x + PLAYER_TILE_X
            vy = npc["y"] - self.player_y + PLAYER_TILE_Y
            if 0 <= vx < TILES_ACROSS and 0 <= vy < TILES_DOWN:
                npc_px = VIEWPORT_X + vx * DRAW_SIZE
                npc_py = VIEWPORT_Y + vy * DRAW_SIZE
                if 3 in self.tilesets:
                    self._blit_tile(3, npc["avatar"], npc_px, npc_py)
                else:
                    pygame.draw.rect(self.screen, (166, 227, 161), (npc_px, npc_py, DRAW_SIZE, DRAW_SIZE))
                lbl = self.font.render(npc["name"], True, (166, 227, 161))
                self.screen.blit(lbl, (npc_px + DRAW_SIZE // 2 - lbl.get_width() // 2, npc_py - 12))

        # ── Player character ─────────────────────────────────────────────
        player_px = VIEWPORT_X + PLAYER_TILE_X * DRAW_SIZE
        player_py = VIEWPORT_Y + PLAYER_TILE_Y * DRAW_SIZE
        if 3 in self.tilesets:
            self._blit_tile(3, self.player_avatar, player_px, player_py)
        else:
            pygame.draw.rect(self.screen, (255, 0, 0), (player_px, player_py, DRAW_SIZE, DRAW_SIZE))

        # ── Render chat overlay ──────────────────────────────────────────
        chat_y = VIEWPORT_H - 120
        for log in self.chat_log:
            lbl = self.font.render(log, True, (245, 194, 231))
            self.screen.blit(lbl, (15, chat_y))
            chat_y += 14

        # Active chat input indicator
        if self.chat_active:
            lbl = self.font.render(f"Say: {self.chat_input}_", True, (166, 227, 161))
            self.screen.blit(lbl, (15, VIEWPORT_H - 24))

        # ── Right Sidebar HUD ────────────────────────────────────────────
        sidebar_x = SCREEN_WIDTH - SIDEBAR_WIDTH
        pygame.draw.rect(self.screen, (24, 24, 37), (sidebar_x, 0, SIDEBAR_WIDTH, SCREEN_HEIGHT))
        pygame.draw.rect(self.screen, (69, 71, 90), (sidebar_x, 0, SIDEBAR_WIDTH, SCREEN_HEIGHT), 2)

        # Title
        self.screen.blit(self.font_large.render(self.player_name, True, (205, 214, 244)), (sidebar_x + 12, 14))
        pygame.draw.line(self.screen, (69, 71, 90), (sidebar_x + 10, 38), (sidebar_x + SIDEBAR_WIDTH - 10, 38))

        # Stats
        self.screen.blit(self.font.render(f"HP: {self.player_hp} / {self.player_hp_max}", True, (243, 139, 168)), (sidebar_x + 12, 48))
        self.screen.blit(self.font.render(f"Mana: {self.player_mana}", True, (137, 180, 250)), (sidebar_x + 12, 66))
        self.screen.blit(self.font.render(f"Level: {self.player_level}", True, (249, 226, 175)), (sidebar_x + 12, 84))
        self.screen.blit(self.font.render(f"X: {self.player_x}  Y: {self.player_y}", True, (166, 227, 161)), (sidebar_x + 12, 102))

        # ── Equipped Items (Worn Slots) ──────────────────────────────────
        self.screen.blit(self.font_large.render("Equipment", True, (205, 214, 244)), (sidebar_x + 12, 120))
        worn_labels = ["Wep", "Arm", "Helm", "Shld"]
        for slot_idx in range(4):
            slot_x = sidebar_x + 15 + slot_idx * 38
            slot_y = 140
            pygame.draw.rect(self.screen, (49, 50, 68), (slot_x, slot_y, 32, 32))
            pygame.draw.rect(self.screen, (137, 180, 250), (slot_x, slot_y, 32, 32), 1)
            
            # Label placeholder when empty
            if slot_idx < len(self.worn) and self.worn[slot_idx] is not None:
                item = self.worn[slot_idx]
                self._blit_tile(1, item.get("item_type", 0), slot_x, slot_y)
            else:
                lbl = self.font.render(worn_labels[slot_idx], True, (108, 112, 134))
                self.screen.blit(lbl, (slot_x + 16 - lbl.get_width() // 2, slot_y + 16 - lbl.get_height() // 2))

        # ── Backpack Inventory Grid ──────────────────────────────────────
        self.screen.blit(self.font_large.render("Backpack", True, (205, 214, 244)), (sidebar_x + 12, 185))
        
        slot_size = 32
        spacing = 6
        grid_x_start = sidebar_x + 15
        grid_y_start = 205
        
        for row in range(6):
            for col in range(4):
                slot_idx = row * 4 + col
                slot_x = grid_x_start + col * (slot_size + spacing)
                slot_y = grid_y_start + row * (slot_size + spacing)
                
                # Draw slot background
                pygame.draw.rect(self.screen, (49, 50, 68), (slot_x, slot_y, slot_size, slot_size))
                pygame.draw.rect(self.screen, (108, 112, 134), (slot_x, slot_y, slot_size, slot_size), 1)
                
                # Draw item if exists
                if slot_idx < len(self.backpack) and self.backpack[slot_idx] is not None:
                    item = self.backpack[slot_idx]
                    item_type = item.get("item_type", 0)
                    self._blit_tile(1, item_type, slot_x, slot_y)
                    
                    # Draw quantity
                    qty = item.get("quantity", 1)
                    if qty > 1:
                        qty_lbl = self.font.render(str(qty), True, (255, 255, 255))
                        self.screen.blit(qty_lbl, (slot_x + slot_size - qty_lbl.get_width() - 2, slot_y + slot_size - qty_lbl.get_height() - 2))

        # ── Controls Help (Bottom of Sidebar) ───────────────────────────
        controls_y = SCREEN_HEIGHT - 70
        pygame.draw.line(self.screen, (69, 71, 90), (sidebar_x + 10, controls_y - 8), (sidebar_x + SIDEBAR_WIDTH - 10, controls_y - 8))
        self.screen.blit(self.font.render("Arrow Keys: Move", True, (147, 153, 178)), (sidebar_x + 12, controls_y))
        self.screen.blit(self.font.render("Enter: Type Chat", True, (147, 153, 178)), (sidebar_x + 12, controls_y + 16))
        self.screen.blit(self.font.render("G / F10: GM Tool", True, (147, 153, 178)), (sidebar_x + 12, controls_y + 32))
        
        # ── Minimap HUD ────────────────────────────────────────────────
        minimap_w = 90
        minimap_h = 90
        minimap_x = VIEWPORT_W - minimap_w - 10
        minimap_y = 10
        pygame.draw.rect(self.screen, (17, 17, 27), (minimap_x, minimap_y, minimap_w, minimap_h))
        pygame.draw.rect(self.screen, (137, 180, 250), (minimap_x, minimap_y, minimap_w, minimap_h), 1)
        
        # Render 15x15 tiles onto the minimap
        for dy in range(-7, 8):
            for dx in range(-7, 8):
                wx = self.player_x + dx
                wy = self.player_y + dy
                
                # Default terrain color
                color = (34, 139, 34)  # green
                
                g_id = self.map_db.get_tile_at(wx, wy, 0)
                o_id = self.map_db.get_tile_at(wx, wy, 1)
                
                if dx == 0 and dy == 0:
                    color = (255, 255, 0)  # Player (yellow)
                elif any(p["x"] == wx and p["y"] == wy for p in self.other_players.values()):
                    color = (137, 180, 250)  # Other Player (blue)
                elif any(m["x"] == wx and m["y"] == wy for m in self.monsters.values()):
                    color = (243, 139, 168)  # Monster (red)
                elif g_id == 0:
                    color = (30, 30, 46)  # Dark void
                elif o_id > 0:
                    color = (147, 153, 178)  # Structure / wall (gray)
                    
                px = minimap_x + (dx + 7) * 6
                py = minimap_y + (dy + 7) * 6
                pygame.draw.rect(self.screen, color, (px, py, 5, 5))

        # ── GM Overlay ──────────────────────────────────────────────────
        if self.gm_active:
            gm_w, gm_h = 320, 240
            gm_x = (VIEWPORT_W - gm_w) // 2
            gm_y = (VIEWPORT_H - gm_h) // 2
            
            # Draw GM Window
            pygame.draw.rect(self.screen, (30, 30, 46), (gm_x, gm_y, gm_w, gm_h))
            pygame.draw.rect(self.screen, (137, 180, 250), (gm_x, gm_y, gm_w, gm_h), 2)
            
            # Title
            pygame.draw.rect(self.screen, (137, 180, 250), (gm_x, gm_y, gm_w, 24))
            self.screen.blit(self.font_large.render("GM Control Panel (G/F10 to Close)", True, (17, 17, 27)), (gm_x + 10, gm_y + 3))
            
            # Options list
            options = [
                "[1] Teleport to Home (15, 15)",
                "[2] GM Full Heal",
                "[3] Announce Server Maintenance",
                "[4] Spawn Goblin",
                "[5] Spawn Skeleton",
                "[6] Give Gold"
            ]
            for idx, opt in enumerate(options):
                self.screen.blit(self.font.render(opt, True, (205, 214, 244)), (gm_x + 20, gm_y + 40 + idx * 24))

        # ── Bank Window Overlay ──────────────────────────────────────────
        bank_w, bank_h = 390, 245
        bank_x = (VIEWPORT_W - bank_w) // 2
        bank_y = (VIEWPORT_H - bank_h) // 2
        if self.bank_active:
            # Draw window background
            pygame.draw.rect(self.screen, (30, 30, 46), (bank_x, bank_y, bank_w, bank_h))
            pygame.draw.rect(self.screen, (137, 180, 250), (bank_x, bank_y, bank_w, bank_h), 2)
            
            # Header
            pygame.draw.rect(self.screen, (137, 180, 250), (bank_x, bank_y, bank_w, 24))
            self.screen.blit(self.font_large.render("Bank Vault", True, (17, 17, 27)), (bank_x + 10, bank_y + 3))
            
            # Close button [X]
            close_btn_x = bank_x + bank_w - 24
            close_btn_y = bank_y + 4
            pygame.draw.rect(self.screen, (243, 139, 168), (close_btn_x, close_btn_y, 16, 16))
            close_lbl = self.font.render("X", True, (17, 17, 27))
            self.screen.blit(close_lbl, (close_btn_x + 8 - close_lbl.get_width() // 2, close_btn_y + 8 - close_lbl.get_height() // 2))

            # Slots grid (10 columns, 5 rows)
            slot_size = 32
            spacing = 4
            grid_x_start = bank_x + 15
            grid_y_start = bank_y + 40
            
            for row in range(5):
                for col in range(10):
                    slot_idx = row * 10 + col
                    slot_x = grid_x_start + col * (slot_size + spacing)
                    slot_y = grid_y_start + row * (slot_size + spacing)
                    
                    pygame.draw.rect(self.screen, (49, 50, 68), (slot_x, slot_y, slot_size, slot_size))
                    pygame.draw.rect(self.screen, (137, 180, 250), (slot_x, slot_y, slot_size, slot_size), 1)
                    
                    # Draw item if exists
                    if slot_idx < len(self.bank) and self.bank[slot_idx] is not None:
                        item = self.bank[slot_idx]
                        item_type = item.get("item_type", 0)
                        self._blit_tile(1, item_type, slot_x, slot_y)
                        
                        qty = item.get("quantity", 1)
                        if qty > 1:
                            qty_lbl = self.font.render(str(qty), True, (255, 255, 255))
                            self.screen.blit(qty_lbl, (slot_x + slot_size - qty_lbl.get_width() - 2, slot_y + slot_size - qty_lbl.get_height() - 2))

        # ── Tooltips / Identify ──────────────────────────────────────────
        hovered_item = None
        mx, my = pygame.mouse.get_pos()
        
        # 1. Check Worn Slots
        for slot_idx in range(4):
            slot_x = sidebar_x + 15 + slot_idx * 38
            slot_y = 140
            if slot_x <= mx <= slot_x + 32 and slot_y <= my <= slot_y + 32:
                if slot_idx < len(self.worn) and self.worn[slot_idx] is not None:
                    hovered_item = self.worn[slot_idx]
                    break
        
        # 2. Check Backpack Slots
        if not hovered_item:
            slot_size = 32
            spacing = 6
            grid_x_start = sidebar_x + 15
            grid_y_start = 205
            for row in range(6):
                for col in range(4):
                    slot_idx = row * 4 + col
                    slot_x = grid_x_start + col * (slot_size + spacing)
                    slot_y = grid_y_start + row * (slot_size + spacing)
                    if slot_x <= mx <= slot_x + slot_size and slot_y <= my <= slot_y + slot_size:
                        if slot_idx < len(self.backpack) and self.backpack[slot_idx] is not None:
                            hovered_item = self.backpack[slot_idx]
                            break

        # 3. Check Bank Slots
        if not hovered_item and self.bank_active:
            slot_size = 32
            spacing = 4
            grid_x_start = bank_x + 15
            grid_y_start = bank_y + 40
            for row in range(5):
                for col in range(10):
                    slot_idx = row * 10 + col
                    slot_x = grid_x_start + col * (slot_size + spacing)
                    slot_y = grid_y_start + row * (slot_size + spacing)
                    if slot_x <= mx <= slot_x + slot_size and slot_y <= my <= slot_y + slot_size:
                        if slot_idx < len(self.bank) and self.bank[slot_idx] is not None:
                            hovered_item = self.bank[slot_idx]
                            break
                            
        # Render tooltip box
        if hovered_item:
            item_type = hovered_item.get("item_type", 0)
            family = hovered_item.get("family", 0)
            qty = hovered_item.get("quantity", 1)
            dur = hovered_item.get("durability", 100)
            
            # Name Lookup
            item_name = self.item_types.get(str(item_type), {}).get("name", f"Item #{item_type}")
            fam_names = {0: "None", 1: "Weapon", 2: "Armor", 3: "Collectable", 4: "Useable"}
            fam_str = fam_names.get(family, "Item")
            
            tooltip_lines = [
                item_name,
                f"Type: {fam_str}",
                f"Durability: {dur}/100"
            ]
            if qty > 1:
                tooltip_lines.append(f"Qty: {qty}")
                
            # Draw box
            t_w = 140
            t_h = len(tooltip_lines) * 16 + 10
            t_x = mx + 15
            t_y = my + 15
            # Keep on screen
            if t_x + t_w > SCREEN_WIDTH:
                t_x = mx - t_w - 5
            if t_y + t_h > SCREEN_HEIGHT:
                t_y = my - t_h - 5
                
            pygame.draw.rect(self.screen, (30, 30, 46), (t_x, t_y, t_w, t_h))
            pygame.draw.rect(self.screen, (137, 180, 250), (t_x, t_y, t_w, t_h), 1)
            
            for idx, line in enumerate(tooltip_lines):
                color = (137, 180, 250) if idx == 0 else (205, 214, 244)
                self.screen.blit(self.font.render(line, True, color), (t_x + 8, t_y + 5 + idx * 16))

        # Draw dragged item floating under mouse cursor
        if self.is_dragging and self.dragged_item:
            mx, my = pygame.mouse.get_pos()
            item_type = self.dragged_item.get("item_type", 0)
            self._blit_tile(1, item_type, mx - 16, my - 16)

        pygame.display.flip()

    def run(self):
        running = True
        while running:
            self.clock.tick(60)
            self.process_incoming_packets()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        mx, my = event.pos
                        sidebar_x = SCREEN_WIDTH - SIDEBAR_WIDTH
                        
                        # Check Bank UI close button or slot selection
                        bank_w, bank_h = 390, 245
                        bank_x = (VIEWPORT_W - bank_w) // 2
                        bank_y = (VIEWPORT_H - bank_h) // 2
                        
                        if self.bank_active:
                            close_btn_x = bank_x + bank_w - 24
                            close_btn_y = bank_y + 4
                            if close_btn_x <= mx <= close_btn_x + 16 and close_btn_y <= my <= close_btn_y + 16:
                                self.bank_active = False
                                continue
                                
                            # Check Bank Slots selection
                            slot_size = 32
                            spacing = 4
                            grid_x_start = bank_x + 15
                            grid_y_start = bank_y + 40
                            slot_clicked = False
                            for row in range(5):
                                for col in range(10):
                                    slot_idx = row * 10 + col
                                    slot_x = grid_x_start + col * (slot_size + spacing)
                                    slot_y = grid_y_start + row * (slot_size + spacing)
                                    if slot_x <= mx <= slot_x + slot_size and slot_y <= my <= slot_y + slot_size:
                                        if slot_idx < len(self.bank) and self.bank[slot_idx] is not None:
                                            self.is_dragging = True
                                            self.dragged_item = self.bank[slot_idx]
                                            self.drag_source = "bank"
                                            self.dragged_slot = slot_idx
                                            slot_clicked = True
                                            break
                                if slot_clicked:
                                    break
                            if slot_clicked:
                                continue

                        if mx < sidebar_x:
                            # Clicked in the world viewport. Let's see if we clicked a monster, NPC, or ground item!
                            vx = mx // DRAW_SIZE
                            vy = my // DRAW_SIZE
                            wx = self.player_x - PLAYER_TILE_X + vx
                            wy = self.player_y - PLAYER_TILE_Y + vy
                            
                            # Check Monster Click
                            clicked_monster_id = None
                            for m_id, m in self.monsters.items():
                                if m["x"] == wx and m["y"] == wy:
                                    clicked_monster_id = m_id
                                    break
                            self.target_monster_id = clicked_monster_id
                            
                            # Check NPC Click (Banker NPC toggles Bank UI)
                            clicked_npc = None
                            for npc in self.npcs.values():
                                if npc["x"] == wx and npc["y"] == wy:
                                    clicked_npc = npc
                                    break
                            if clicked_npc and clicked_npc.get("npc_type") == "banker":
                                if abs(self.player_x - clicked_npc["x"]) <= 1 and abs(self.player_y - clicked_npc["y"]) <= 1:
                                    self.bank_active = not self.bank_active
                                    
                            # Check Ground Item Click
                            clicked_item = None
                            for it_id, item in self.ground_items.items():
                                if item["x"] == wx and item["y"] == wy:
                                    clicked_item = item
                                    clicked_item["id"] = it_id
                                    break
                            if clicked_item:
                                if abs(self.player_x - clicked_item["x"]) <= 1 and abs(self.player_y - clicked_item["y"]) <= 1:
                                    self.net.send_action({
                                        "type": "pickup_item",
                                        "item_id": clicked_item["id"]
                                    })
                        else:
                            # 1. Check Worn Slots
                            for slot_idx in range(4):
                                slot_x = sidebar_x + 15 + slot_idx * 38
                                slot_y = 140
                                if slot_x <= mx <= slot_x + 32 and slot_y <= my <= slot_y + 32:
                                    if slot_idx < len(self.worn) and self.worn[slot_idx] is not None:
                                        self.is_dragging = True
                                        self.dragged_item = self.worn[slot_idx]
                                        self.drag_source = "worn"
                                        self.dragged_slot = slot_idx
                                        break
                            # 2. Check Backpack Slots
                            if not self.is_dragging:
                                slot_size = 32
                                spacing = 6
                                grid_x_start = sidebar_x + 15
                                grid_y_start = 205
                                for row in range(6):
                                    for col in range(4):
                                        slot_idx = row * 4 + col
                                        slot_x = grid_x_start + col * (slot_size + spacing)
                                        slot_y = grid_y_start + row * (slot_size + spacing)
                                        if slot_x <= mx <= slot_x + slot_size and slot_y <= my <= slot_y + slot_size:
                                            if slot_idx < len(self.backpack) and self.backpack[slot_idx] is not None:
                                                self.is_dragging = True
                                                self.dragged_item = self.backpack[slot_idx]
                                                self.drag_source = "backpack"
                                                self.dragged_slot = slot_idx
                                                break

                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1 and self.is_dragging:
                        mx, my = event.pos
                        sidebar_x = SCREEN_WIDTH - SIDEBAR_WIDTH
                        self.is_dragging = False
                        dragged = self.dragged_item
                        
                        if self.drag_source == "backpack":
                            src_list = 1
                        elif self.drag_source == "bank":
                            src_list = 2
                        else:
                            src_list = 3
                            
                        src_slot = self.dragged_slot
                        
                        if mx < sidebar_x:
                            # Check if dropped inside the Bank UI popup window
                            bank_w, bank_h = 390, 245
                            bank_x = (VIEWPORT_W - bank_w) // 2
                            bank_y = (VIEWPORT_H - bank_h) // 2
                            if self.bank_active and bank_x <= mx <= bank_x + bank_w and bank_y <= my <= bank_y + bank_h:
                                dropped = False
                                slot_size = 32
                                spacing = 4
                                grid_x_start = bank_x + 15
                                grid_y_start = bank_y + 40
                                for row in range(5):
                                    for col in range(10):
                                        slot_idx = row * 10 + col
                                        slot_x = grid_x_start + col * (slot_size + spacing)
                                        slot_y = grid_y_start + row * (slot_size + spacing)
                                        if slot_x <= mx <= slot_x + slot_size and slot_y <= my <= slot_y + slot_size:
                                            self.net.send_action({
                                                "type": "item_move",
                                                "from_list": src_list,
                                                "to_list": 2,
                                                "from_slot": src_slot,
                                                "to_slot": slot_idx,
                                                "amount": 1
                                            })
                                            dropped = True
                                            break
                            else:
                                # Dropped in the world -> Drop item on ground!
                                self.net.send_action({
                                    "type": "drop_item",
                                    "item_id": dragged["id"]
                                })
                        else:
                            # Dropped in the sidebar -> Check target slot
                            dropped = False
                            # 1. Check Worn Slots
                            for slot_idx in range(4):
                                slot_x = sidebar_x + 15 + slot_idx * 38
                                slot_y = 140
                                if slot_x <= mx <= slot_x + 32 and slot_y <= my <= slot_y + 32:
                                    self.net.send_action({
                                        "type": "item_move",
                                        "from_list": src_list,
                                        "to_list": 3,
                                        "from_slot": src_slot,
                                        "to_slot": slot_idx,
                                        "amount": 1
                                    })
                                    dropped = True
                                    break
                            
                            # 2. Check Backpack Slots
                            if not dropped:
                                slot_size = 32
                                spacing = 6
                                grid_x_start = sidebar_x + 15
                                grid_y_start = 205
                                for row in range(6):
                                    for col in range(4):
                                        slot_idx = row * 4 + col
                                        slot_x = grid_x_start + col * (slot_size + spacing)
                                        slot_y = grid_y_start + row * (slot_size + spacing)
                                        if slot_x <= mx <= slot_x + slot_size and slot_y <= my <= slot_y + slot_size:
                                            self.net.send_action({
                                                "type": "item_move",
                                                "from_list": src_list,
                                                "to_list": 1,
                                                "from_slot": src_slot,
                                                "to_slot": slot_idx,
                                                "amount": 1
                                            })
                                            dropped = True
                                            break
                        
                        self.dragged_item = None
                        self.drag_source = None
                        self.dragged_slot = None

                elif event.type == pygame.KEYDOWN:
                    if self.chat_active:
                        if event.key == pygame.K_RETURN:
                            if self.chat_input.strip():
                                self.net.send_action({"type": "say", "message": self.chat_input.strip()})
                            self.chat_input = ""
                            self.chat_active = False
                        elif event.key == pygame.K_BACKSPACE:
                            self.chat_input = self.chat_input[:-1]
                        elif event.key == pygame.K_ESCAPE:
                            self.chat_active = False
                        else:
                            # Append character if visible
                            if event.unicode.isprintable():
                                self.chat_input += event.unicode
                    else:
                        if event.key in (pygame.K_g, pygame.K_F10):
                            self.gm_active = not self.gm_active
                        elif self.gm_active and event.key == pygame.K_1:
                            self.net.send_action({"type": "say", "message": "/teleport 15 15"})
                        elif self.gm_active and event.key == pygame.K_2:
                            self.net.send_action({"type": "say", "message": "/heal"})
                        elif self.gm_active and event.key == pygame.K_3:
                            self.net.send_action({"type": "say", "message": "/announce Server is running smoothly."})
                        elif self.gm_active and event.key == pygame.K_4:
                            self.net.send_action({"type": "say", "message": "/spawn Goblin"})
                        elif self.gm_active and event.key == pygame.K_5:
                            self.net.send_action({"type": "say", "message": "/spawn Skeleton"})
                        elif self.gm_active and event.key == pygame.K_6:
                            self.net.send_action({"type": "say", "message": "/give 3 9412 1"})
                        elif event.key == pygame.K_ESCAPE:
                            running = False
                        elif event.key == pygame.K_RETURN:
                            self.chat_active = True
                        elif event.key == pygame.K_a:
                            if self.target_monster_id is not None:
                                self.net.send_action({
                                    "type": "attack",
                                    "target_id": self.target_monster_id
                                })
                        elif event.key == pygame.K_SPACE:
                            # 1. First check for adjacent Banker NPC
                            found_banker = None
                            for dy in [-1, 0, 1]:
                                for dx in [-1, 0, 1]:
                                    if dx == 0 and dy == 0:
                                        continue
                                    tx = self.player_x + dx
                                    ty = self.player_y + dy
                                    for npc in self.npcs.values():
                                        if npc["x"] == tx and npc["y"] == ty and npc.get("npc_type") == "banker":
                                            found_banker = npc
                                            break
                                    if found_banker:
                                        break
                                if found_banker:
                                    break
                            
                            if found_banker:
                                self.bank_active = not self.bank_active
                            else:
                                # 2. Fall back to adjacent object interaction
                                found_obj = None
                                for dy in [-1, 0, 1]:
                                    for dx in [-1, 0, 1]:
                                        if dx == 0 and dy == 0:
                                            continue
                                        tx = self.player_x + dx
                                        ty = self.player_y + dy
                                        for obj in self.map_db.map_objects:
                                            if obj.x == tx and obj.y == ty:
                                                found_obj = obj
                                                break
                                        if found_obj:
                                            break
                                    if found_obj:
                                        break
                                
                                if found_obj:
                                    self.net.send_action({
                                        "type": "interact_object",
                                        "x": found_obj.x,
                                        "y": found_obj.y
                                    })
                        else:
                            dx, dy = 0, 0
                            if event.key == pygame.K_LEFT:
                                dx = -1
                            elif event.key == pygame.K_RIGHT:
                                dx = 1
                            elif event.key == pygame.K_UP:
                                dy = -1
                            elif event.key == pygame.K_DOWN:
                                dy = 1
                            if dx or dy:
                                self.net.send_action({"type": "move", "dx": dx, "dy": dy})

            self.render()
        
        self.net.disconnect()
        pygame.quit()


if __name__ == "__main__":
    engine = GameClientEngine()
    engine.run()
