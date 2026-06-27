# server/network.py
import asyncio
import os
import websockets
from core.packets import read_packet_async, pack_json
from server.client_state import ClientState
from server.game_loop import GameLoop
from core.maps import MapDatabase

class WsStreamReader:
    def __init__(self, ws):
        self.ws = ws
        self.buffer = b""
        
    async def readexactly(self, n):
        while len(self.buffer) < n:
            try:
                msg = await self.ws.recv()
                self.buffer += msg
            except Exception:
                raise ConnectionResetError()
        data = self.buffer[:n]
        self.buffer = self.buffer[n:]
        return data

class WsStreamWriter:
    def __init__(self, ws):
        self.ws = ws
        self.loop = asyncio.get_running_loop()
        self.queue = asyncio.Queue()
        self.worker = self.loop.create_task(self._send_worker())
        
    async def _send_worker(self):
        try:
            while True:
                data = await self.queue.get()
                if data is None:
                    break
                await self.ws.send(data)
        except Exception:
            pass
            
    def write(self, data):
        self.queue.put_nowait(data)
        
    async def drain(self):
        pass
        
    def close(self):
        # Gracefully stop the send worker
        self.queue.put_nowait(None)
        
    async def wait_closed(self):
        # Wait for worker to finish
        try:
            await asyncio.wait_for(self.worker, timeout=2.0)
        except asyncio.TimeoutError:
            pass
        
    def get_extra_info(self, name):
        if name == 'peername':
            return self.ws.remote_address
        return None

class GameServer:
    def __init__(self, db_manager, port=1338):
        self.db = db_manager
        self.port = port
        self.clients = {}  # char_name -> ClientState
        self.monsters = {}  # know_id -> MonsterInstance
        self.npcs = {
            1: {
                "npc_id": 1,
                "name": "Banker",
                "x": 12,
                "y": 12,
                "avatar": 12,  # tile graphic ID on AVATARS tileset (ID 3)
                "npc_type": "banker"
            }
        }
        self.bodies = {}  # body_id -> {id, name, x, y, decay_time}
        self.map_db = MapDatabase()
        self.map_db.load()
        
        # Load monster definitions
        from core.config import GameConfig
        editor_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        hairy_dir = os.path.join(editor_dir, "HAIRY")
        self.cfg = GameConfig(hairy_dir)
        self.cfg.load_all()
        self.monster_types = self.cfg.get_monster_types()
        
        self.game_loop = GameLoop(self)

    def update_monster_visibility(self, monster):
        """Broadcast monster coordinate updates or spawning packets to players within viewport range."""
        for client in self.clients.values():
            char = client.char_data
            is_nearby = abs(char.x - monster.x) <= 10 and abs(char.y - monster.y) <= 10
            knows = monster.know_id in client.know_monsters
            
            if is_nearby:
                if not knows:
                    # Spawn monster for client
                    client.know_monsters.add(monster.know_id)
                    client.send_packet({
                        "type": "monster_spawn",
                        "know_id": monster.know_id,
                        "name": monster.monster_type,
                        "x": monster.x,
                        "y": monster.y,
                        "hp": monster.hp_left,
                        "hp_max": self.monster_types.get(monster.monster_type, {}).get("hp_max", 10),
                        "graphic": self.monster_types.get(monster.monster_type, {}).get("graphic", [0, 0])
                    })
                else:
                    # Move monster for client
                    client.send_packet({
                        "type": "monster_move",
                        "know_id": monster.know_id,
                        "x": monster.x,
                        "y": monster.y
                    })
            else:
                if knows:
                    # Despawn monster for client
                    client.know_monsters.remove(monster.know_id)
                    client.send_packet({
                        "type": "monster_left",
                        "know_id": monster.know_id
                    })

    def broadcast_to_nearby(self, x: int, y: int, packet_dict: dict):
        """Sends a packet to all connected clients within viewport range (10 tiles) of the coordinates."""
        for client in self.clients.values():
            char = client.char_data
            if abs(char.x - x) <= 10 and abs(char.y - y) <= 10:
                client.send_packet(packet_dict)

    def update_visibility_for_client(self, client: ClientState):
        char = client.char_data
        
        # 1. Update NPC visibility
        for npc in self.npcs.values():
            is_nearby = abs(char.x - npc["x"]) <= 10 and abs(char.y - npc["y"]) <= 10
            knows = npc["npc_id"] in client.know_npcs
            if is_nearby and not knows:
                client.know_npcs.add(npc["npc_id"])
                client.send_packet({
                    "type": "npc_spawn",
                    "npc_id": npc["npc_id"],
                    "name": npc["name"],
                    "x": npc["x"],
                    "y": npc["y"],
                    "avatar": npc["avatar"],
                    "npc_type": npc["npc_type"]
                })
            elif not is_nearby and knows:
                client.know_npcs.remove(npc["npc_id"])
                client.send_packet({
                    "type": "npc_left",
                    "npc_id": npc["npc_id"]
                })

        # 2. Update Ground Item visibility
        from server.item_database import ItemDatabaseManager
        item_db = ItemDatabaseManager()
        ground_items = item_db.get_ground_items()
        for item in ground_items:
            is_nearby = abs(char.x - item["x"]) <= 10 and abs(char.y - item["y"]) <= 10
            knows = item["id"] in client.know_items
            if is_nearby and not knows:
                client.know_items.add(item["id"])
                client.send_packet({
                    "type": "ground_item_spawn",
                    "item_id": item["id"],
                    "item_type": item["item_type"],
                    "x": item["x"],
                    "y": item["y"]
                })
            elif not is_nearby and knows:
                client.know_items.remove(item["id"])
                client.send_packet({
                    "type": "ground_item_despawn",
                    "item_id": item["id"]
                })

        # 3. Update Body visibility
        import time
        now = time.time()
        for body_id in list(self.bodies.keys()):
            body = self.bodies[body_id]
            if now > body.get("decay_time", 0):
                # Clean up expired corpses
                del self.bodies[body_id]
                self.broadcast_to_nearby(body["x"], body["y"], {
                    "type": "body_left",
                    "body_id": body_id
                })
                continue
            is_nearby = abs(char.x - body["x"]) <= 10 and abs(char.y - body["y"]) <= 10
            knows = body["id"] in client.know_bodies
            if is_nearby and not knows:
                client.know_bodies.add(body["id"])
                client.send_packet({
                    "type": "body_spawn",
                    "body_id": body["id"],
                    "name": body["name"],
                    "x": body["x"],
                    "y": body["y"]
                })
            elif not is_nearby and knows:
                client.know_bodies.remove(body["id"])
                client.send_packet({
                    "type": "body_left",
                    "body_id": body["id"]
                })

    async def handle_websocket_client(self, websocket):
        reader = WsStreamReader(websocket)
        writer = WsStreamWriter(websocket)
        await self.handle_client(reader, writer)

    async def start(self):
        self.game_loop.start()
        self.server = await asyncio.start_server(
            self.handle_client, '0.0.0.0', self.port
        )
        print(f"Async Socket Server listening on port {self.port}...")
        
        # websockets.serve returns a server object that runs in the background.
        self.ws_server = await websockets.serve(
            self.handle_websocket_client, '0.0.0.0', 1339
        )
        print(f"WebSocket Server listening on port 1339...")
        
        async with self.server:
            await self.server.serve_forever()

    def send_inventory(self, client: ClientState):
        from server.item_database import ItemDatabaseManager
        item_db = ItemDatabaseManager()
        db_items = item_db.get_items_for_owner(client.char_data.id)
        
        items_payload = []
        for item in db_items:
            items_payload.append({
                "id": item["id"],
                "item_type": item["item_type"],
                "quantity": item["quantity"],
                "durability": item["durability"],
                "container": item["container"],
                "slot": item["slot"]
            })
        
        client.send_packet({
            "type": "inventory_update",
            "items": items_payload
        })

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        print(f"Connection established from {addr}")
        
        active_client = None
        admin_authed = False
        
        try:
            while True:
                packet = await read_packet_async(reader)
                if not packet:
                    break
                
                packet_type = packet.get("type")
                
                if packet_type == "login":
                    username = packet.get("username", "")
                    password = packet.get("password", "")
                    version = packet.get("version", 0)
                    print(f"Login request: {username} / {password} (ver: {version})")
                    
                    # Find account
                    acc = None
                    for a in self.db.accounts:
                        if a.data.acc_name == username and a.data.acc_pass == password:
                            acc = a
                            break
                    
                    if acc:
                        print(f"User {username} successfully authenticated.")
                        # Send login success response with character slots
                        used = [c.used for c in acc.chars] + [False, False]
                        names = [c.name for c in acc.chars] + ["", ""]
                        levels = [c.level for c in acc.chars] + [0, 0]
                        avatars = [c.avatar for c in acc.chars] + [0, 0]
                        hps = [c.hp_left for c in acc.chars] + [0, 0]
                        hpmaxs = [c.hp_max for c in acc.chars] + [0, 0]
                        xs = [c.x for c in acc.chars] + [10, 10]
                        ys = [c.y for c in acc.chars] + [10, 10]
                        
                        editor_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                        hairy_dir = os.path.join(editor_dir, "HAIRY")
                        classes = []
                        try:
                            from core.config import GameConfig
                            cfg = GameConfig(hairy_dir)
                            cfg.load_all()
                            player_hry = cfg.hry_data.get("Player.hry", {})
                            classes = list(player_hry.get("objects", {}).keys())
                        except Exception as e:
                            print(f"[SERVER ERROR] Failed to load classes: {e}")

                        response = {
                            "type": "login_response",
                            "success": True,
                            "classes": classes,
                            "slots": {
                                "used": used[:4],
                                "names": names[:4],
                                "levels": levels[:4],
                                "avatars": avatars[:4],
                                "hps": hps[:4],
                                "hpmaxs": hpmaxs[:4],
                                "xs": xs[:4],
                                "ys": ys[:4]
                            }
                        }
                        writer.write(pack_json(response))
                        await writer.drain()
                    else:
                        print(f"Auth failed for {username}.")
                        response = {
                            "type": "login_response",
                            "success": False,
                            "error_code": 10
                        }
                        writer.write(pack_json(response))
                        await writer.drain()

                elif packet_type == "register":
                    username = packet.get("username", "").strip()
                    password = packet.get("password", "").strip()
                    print(f"Register request for: {username}")
                    
                    if not username or not password:
                        response = {
                            "type": "register_response",
                            "success": False,
                            "error": "Username or password cannot be blank."
                        }
                    else:
                        existing = self.db.sqlite_db.get_account_by_name(username)
                        if existing:
                            response = {
                                "type": "register_response",
                                "success": False,
                                "error": "Username already exists."
                            }
                            print(f"Register failed: account already exists for {username}")
                        else:
                            try:
                                self.db.sqlite_db.create_account(username, password)
                                self.db.load_accounts()  # Reload memory cache
                                response = {
                                    "type": "register_response",
                                    "success": True
                                }
                                print(f"Successfully registered account: {username}")
                            except Exception as e:
                                response = {
                                    "type": "register_response",
                                    "success": False,
                                    "error": f"Database error: {e}"
                                }
                    writer.write(pack_json(response))
                    await writer.drain()

                elif packet_type == "create_character":
                    username = packet.get("username", "")
                    char_name = packet.get("char_name", "").strip()
                    class_template = packet.get("class_template", "").strip()
                    print(f"Create character request for {username}: name='{char_name}', class='{class_template}'")
                    
                    if not char_name or not class_template:
                        response = {
                            "type": "create_character_response",
                            "success": False,
                            "error": "Character name and class must be provided."
                        }
                    else:
                        existing = self.db.sqlite_db.get_character_by_name(char_name)
                        if existing:
                            response = {
                                "type": "create_character_response",
                                "success": False,
                                "error": "Character name already exists."
                            }
                        else:
                            try:
                                slot = packet.get("slot", 0)
                                # Create character from template
                                success = self.db.create_character_from_template(
                                    account_name=username,
                                    slot=slot,
                                    name=char_name,
                                    class_template=class_template,
                                    avatar=0,
                                    race=0
                                )
                                if success:
                                    # Reload and return slots
                                    self.db.load_accounts()
                                    acc = None
                                    for a in self.db.accounts:
                                        if a.data.acc_name == username:
                                            acc = a
                                            break
                                    assert acc is not None
                                    used = [c.used for c in acc.chars] + [False, False]
                                    names = [c.name for c in acc.chars] + ["", ""]
                                    levels = [c.level for c in acc.chars] + [0, 0]
                                    avatars = [c.avatar for c in acc.chars] + [0, 0]
                                    hps = [c.hp_left for c in acc.chars] + [0, 0]
                                    hpmaxs = [c.hp_max for c in acc.chars] + [0, 0]
                                    xs = [c.x for c in acc.chars] + [10, 10]
                                    ys = [c.y for c in acc.chars] + [10, 10]
                                    
                                    response = {
                                        "type": "create_character_response",
                                        "success": True,
                                        "slots": {
                                            "used": used[:4],
                                            "names": names[:4],
                                            "levels": levels[:4],
                                            "avatars": avatars[:4],
                                            "hps": hps[:4],
                                            "hpmaxs": hpmaxs[:4],
                                            "xs": xs[:4],
                                            "ys": ys[:4]
                                        }
                                    }
                                  
                                else:
                                    response = {
                                        "type": "create_character_response",
                                        "success": False,
                                        "error": "Failed to create character from template."
                                    }
                            except Exception as e:
                                response = {
                                    "type": "create_character_response",
                                    "success": False,
                                    "error": f"Error: {e}"
                                }
                    writer.write(pack_json(response))
                    await writer.drain()

                elif packet_type == "enter_game":
                    username = packet.get("username", "")
                    password = packet.get("password", "")
                    char_slot = packet.get("char_slot", 0)
                    
                    acc = None
                    for a in self.db.accounts:
                        if a.data.acc_name == username and a.data.acc_pass == password:
                            acc = a
                            break
                    
                    if acc and 0 <= char_slot < len(acc.chars) and acc.chars[char_slot].used:
                        char = acc.chars[char_slot]
                        active_client = ClientState(reader, writer, acc, char_slot)
                        self.clients[char.name] = active_client
                        print(f"Player {char.name} has entered the game world at ({char.x}, {char.y})")
                        self.db.log_action(char.id, char.name, "login", f"Entered world at ({char.x}, {char.y})")
                        
                        response = {
                            "type": "enter_game_response",
                            "success": True,
                            "name": char.name,
                            "x": char.x,
                            "y": char.y,
                            "hp": char.hp_left,
                            "hp_max": active_client.temp_data.hp_max,
                            "mana": char.mana_left,
                            "level": char.level,
                            "avatar": char.avatar
                        }
                        writer.write(pack_json(response))
                        await writer.drain()
                        
                        self.send_inventory(active_client)
                        
                        # Send map data (WebClient needs this)
                        chunks_payload = {}
                        for cid, chunk_def in self.maps.chunks.items():
                            c_data = chunk_def.get("data")
                            if isinstance(c_data, dict):
                                chunks_payload[cid] = c_data.get("ground", [])
                            elif isinstance(c_data, list):
                                chunks_payload[cid] = c_data
                                
                        active_client.send_packet({
                            "type": "map_data",
                            "grid": self.maps.grid,
                            "chunks": chunks_payload
                        })
                        
                        # Tell others about this player, and tell this player about others (if nearby)
                        for other_name, other_client in self.clients.items():
                            if other_name != char.name:
                                other_char = other_client.char_data
                                if abs(other_char.x - char.x) <= 10 and abs(other_char.y - char.y) <= 10:
                                    other_client.send_packet({
                                        "type": "coordinates",
                                        "name": char.name,
                                        "x": char.x,
                                        "y": char.y,
                                        "avatar": char.avatar
                                    })
                                    active_client.send_packet({
                                        "type": "coordinates",
                                        "name": other_name,
                                        "x": other_char.x,
                                        "y": other_char.y,
                                        "avatar": other_char.avatar
                                    })
                        
                        # Tell this player about nearby monsters
                        for monster in self.monsters.values():
                            if abs(monster.x - char.x) <= 10 and abs(monster.y - char.y) <= 10:
                                active_client.know_monsters.add(monster.know_id)
                                active_client.send_packet({
                                    "type": "monster_spawn",
                                    "know_id": monster.know_id,
                                    "name": monster.monster_type,
                                    "x": monster.x,
                                    "y": monster.y,
                                    "hp": monster.hp_left,
                                    "hp_max": self.monster_types.get(monster.monster_type, {}).get("hp_max", 10),
                                    "graphic": self.monster_types.get(monster.monster_type, {}).get("graphic", [0, 0])
                                })
                        
                        # Tell this player about nearby NPCs, ground items, and bodies
                        self.update_visibility_for_client(active_client)
                    else:
                        response = {
                            "type": "enter_game_response",
                            "success": False,
                            "error": "Invalid account or character slot."
                        }
                        writer.write(pack_json(response))
                        await writer.drain()

                elif packet_type == "move":
                    if active_client:
                        dx = packet.get("dx", 0)
                        dy = packet.get("dy", 0)
                        char = active_client.char_data
                        
                        new_x = char.x + dx
                        new_y = char.y + dy
                        
                        if self.map_db.is_passable(new_x, new_y):
                            char.x = new_x
                            char.y = new_y
                            # Save position to database immediately
                            self.db.sqlite_db.update_character_coordinates(char.id, char.x, char.y)
                            
                            old_x = char.x - dx
                            old_y = char.y - dy
                            
                            response = {
                                "type": "move_response",
                                "success": True,
                                "x": char.x,
                                "y": char.y
                            }
                            # Broadcast visibility transition updates
                            for other_name, other_client in self.clients.items():
                                if other_name != char.name:
                                    other_char = other_client.char_data
                                    was_nearby = abs(other_char.x - old_x) <= 10 and abs(other_char.y - old_y) <= 10
                                    is_nearby = abs(other_char.x - char.x) <= 10 and abs(other_char.y - char.y) <= 10
                                    
                                    if was_nearby and is_nearby:
                                        # Case 1: Still visible -> Send simple coords update
                                        other_client.send_packet({
                                            "type": "coordinates",
                                            "name": char.name,
                                            "x": char.x,
                                            "y": char.y,
                                            "avatar": char.avatar
                                        })
                                    elif not was_nearby and is_nearby:
                                        # Case 2: Walked into view -> mutually exchange coordinates (spawn)
                                        other_client.send_packet({
                                            "type": "coordinates",
                                            "name": char.name,
                                            "x": char.x,
                                            "y": char.y,
                                            "avatar": char.avatar
                                        })
                                        active_client.send_packet({
                                            "type": "coordinates",
                                            "name": other_name,
                                            "x": other_char.x,
                                            "y": other_char.y,
                                            "avatar": other_char.avatar
                                        })
                                    elif was_nearby and not is_nearby:
                                        # Case 3: Walked out of view -> mutually send leave events (despawn)
                                        other_client.send_packet({
                                            "type": "player_left",
                                            "name": char.name
                                        })
                                        active_client.send_packet({
                                            "type": "player_left",
                                            "name": other_name
                                        })
                            
                            # Update monster visibility for the moving player
                            for monster in self.monsters.values():
                                is_nearby = abs(char.x - monster.x) <= 10 and abs(char.y - monster.y) <= 10
                                knows = monster.know_id in active_client.know_monsters
                                if is_nearby and not knows:
                                    active_client.know_monsters.add(monster.know_id)
                                    active_client.send_packet({
                                        "type": "monster_spawn",
                                        "know_id": monster.know_id,
                                        "name": monster.monster_type,
                                        "x": monster.x,
                                        "y": monster.y,
                                        "hp": monster.hp_left,
                                        "hp_max": self.monster_types.get(monster.monster_type, {}).get("hp_max", 10),
                                        "graphic": self.monster_types.get(monster.monster_type, {}).get("graphic", [0, 0])
                                    })
                                elif not is_nearby and knows:
                                    active_client.know_monsters.remove(monster.know_id)
                                    active_client.send_packet({
                                        "type": "monster_left",
                                        "know_id": monster.know_id
                                    })
                            
                            self.update_visibility_for_client(active_client)
                        else:
                            response = {
                                "type": "move_response",
                                "success": False,
                                "x": char.x,
                                "y": char.y
                            }
                        writer.write(pack_json(response))
                        await writer.drain()

                elif packet_type == "say":
                    if active_client:
                        from server.chat import handle_chat_message
                        handle_chat_message(active_client, packet, self)

                elif packet_type == "attack":
                    if active_client:
                        target_id = packet.get("target_id")
                        monster = self.monsters.get(target_id)
                        if monster:
                            char = active_client.char_data
                            # Validate adjacency (must be within 1 tile)
                            if abs(char.x - monster.x) <= 1 and abs(char.y - monster.y) <= 1:
                                m_type = self.monster_types.get(monster.monster_type, {})
                                from server.combat import attempt_player_attack_monster
                                outcome = attempt_player_attack_monster(active_client, monster, m_type, self)
                                
                                self.broadcast_to_nearby(monster.x, monster.y, {
                                    "type": "chat_broadcast",
                                    "sender": char.name,
                                    "message": f"Attacks {m_type.get('name', 'Monster')} for {outcome.get('damage', 0)} damage!"
                                })
                                
                                if outcome.get("killed"):
                                    self.broadcast_to_nearby(monster.x, monster.y, {
                                        "type": "monster_death",
                                        "know_id": monster.know_id
                                    })
                                    for c in self.clients.values():
                                        if monster.know_id in c.know_monsters:
                                            c.know_monsters.remove(monster.know_id)
                                    del self.monsters[monster.know_id]
                                else:
                                    self.broadcast_to_nearby(monster.x, monster.y, {
                                        "type": "monster_hp",
                                        "know_id": monster.know_id,
                                        "hp": monster.hp_left
                                    })

                elif packet_type == "guild_create":
                    if active_client:
                        name = packet.get("name", "")
                        tag = packet.get("tag", "")
                        from server.guilds import create_guild
                        success = create_guild(active_client, name, tag)
                        active_client.send_packet({
                            "type": "guild_create_response",
                            "success": success
                        })

                elif packet_type == "guild_invite":
                    if active_client:
                        target_name = packet.get("target_name", "")
                        target_client = self.clients.get(target_name)
                        if target_client:
                            from server.guilds import invite_to_guild
                            success = invite_to_guild(active_client, target_client)
                            active_client.send_packet({
                                "type": "guild_invite_response",
                                "success": success
                            })

                elif packet_type == "mine":
                    if active_client:
                        from server.tradeskills import execute_mine
                        res = execute_mine(active_client)
                        active_client.send_packet({
                            "type": "mine_response",
                            "success": res["success"],
                            "message": res.get("message") or res.get("error")
                        })

                elif packet_type == "smelt":
                    if active_client:
                        from server.tradeskills import execute_smelt
                        res = execute_smelt(active_client)
                        active_client.send_packet({
                            "type": "smelt_response",
                            "success": res["success"],
                            "message": res.get("message") or res.get("error")
                        })

                elif packet_type == "drop_item":
                    if active_client:
                        item_id = packet.get("item_id")
                        if item_id is not None:
                            x = active_client.char_data.x
                            y = active_client.char_data.y
                            from server.ground_items import drop_item_to_ground
                            success = drop_item_to_ground(active_client, int(item_id), x, y)
                            active_client.send_packet({
                                "type": "drop_item_response",
                                "success": success,
                                "item_id": item_id
                            })
                            if success:
                                self.send_inventory(active_client)
                                drop_broadcast = {
                                    "type": "ground_item_spawn",
                                    "item_id": item_id,
                                    "x": x,
                                    "y": y
                                }
                                for client in self.clients.values():
                                    client.send_packet(drop_broadcast)

                elif packet_type == "pickup_item":
                    if active_client:
                        item_id = packet.get("item_id")
                        if item_id is not None:
                            from server.ground_items import pickup_item_from_ground
                            success = pickup_item_from_ground(active_client, int(item_id))
                            active_client.send_packet({
                                "type": "pickup_item_response",
                                "success": success,
                                "item_id": item_id
                            })
                            if success:
                                self.send_inventory(active_client)
                                pickup_broadcast = {
                                    "type": "ground_item_despawn",
                                    "item_id": item_id
                                }
                                for client in self.clients.values():
                                    client.send_packet(pickup_broadcast)

                elif packet_type == "attack":
                    if active_client:
                        target_name = packet.get("target")
                        target_client = self.clients.get(target_name)
                        if target_client:
                            from server.combat import attempt_attack
                            result = attempt_attack(active_client, target_client)
                            # Notify target and attacker of damage
                            combat_msg = {
                                "type": "combat_result",
                                "attacker": active_client.char_data.name,
                                "target": target_name,
                                "hit": result["hit"],
                                "damage": result["damage"],
                                "killed": result["killed"]
                            }
                            active_client.send_packet(combat_msg)
                            target_client.send_packet(combat_msg)
                            
                            # Broadcast death if target killed
                            if result["killed"]:
                                self.db.log_kill(
                                    killer_id=active_client.char_data.id,
                                    killer_name=active_client.char_data.name,
                                    killer_type="player",
                                    victim_id=target_client.char_data.id,
                                    victim_name=target_client.char_data.name,
                                    victim_type="player",
                                    x=target_client.char_data.x,
                                    y=target_client.char_data.y,
                                    map_level=target_client.char_data.map_level
                                )
                                death_msg = {
                                    "type": "chat_broadcast",
                                    "sender": "System",
                                    "message": f"{target_name} was slain by {active_client.char_data.name}!"
                                }
                                for client in self.clients.values():
                                    client.send_packet(death_msg)
                elif packet_type == "item_move":
                    if active_client:
                        from_list = packet.get("from_list")
                        to_list = packet.get("to_list")
                        from_slot = packet.get("from_slot")
                        to_slot = packet.get("to_slot")
                        amount = packet.get("amount", 1)
                        
                        if (from_list is not None and to_list is not None and 
                                from_slot is not None and to_slot is not None):
                            from server.items import execute_move_item
                            success = execute_move_item(
                                active_client, 
                                int(from_list), 
                                int(to_list), 
                                int(from_slot), 
                                int(to_slot), 
                                int(amount) if amount is not None else 1
                            )
                            if success:
                                self.send_inventory(active_client)
                            
                            response = {
                                "type": "item_move_response",
                                "success": success,
                                "from_list": from_list,
                                "to_list": to_list,
                                "from_slot": from_slot,
                                "to_slot": to_slot
                            }
                            active_client.send_packet(response)

                elif packet_type == "interact_object":
                    if active_client:
                        ox = packet.get("x")
                        oy = packet.get("y")
                        char = active_client.char_data
                        
                        # Validate adjacency (must be within 1 tile)
                        if ox is not None and oy is not None and abs(char.x - ox) <= 1 and abs(char.y - oy) <= 1:
                            obj = None
                            for o in self.map_db.map_objects:
                                if o.x == ox and o.y == oy:
                                    obj = o
                                    break
                            
                            if obj:
                                o_type = self.map_db.object_types.get(obj.type_id)
                                name = o_type.name if o_type else "Object"
                                
                                if o_type and o_type.openable:
                                    obj.on = not obj.on
                                    # Broadcast state update to all nearby clients
                                    state_broadcast = {
                                        "type": "object_state",
                                        "x": ox,
                                        "y": oy,
                                        "on": obj.on
                                    }
                                    for c in self.clients.values():
                                        if abs(c.char_data.x - char.x) <= 10 and abs(c.char_data.y - char.y) <= 10:
                                            c.send_packet(state_broadcast)
                                            
                                    active_client.send_packet({
                                        "type": "chat_broadcast",
                                        "sender": "System",
                                        "message": f"You {'close' if obj.on else 'open'} the {name}."
                                    })
                                elif obj.text:
                                    active_client.send_packet({
                                        "type": "chat_broadcast",
                                        "sender": name,
                                        "message": obj.text
                                    })
                                else:
                                    active_client.send_packet({
                                        "type": "chat_broadcast",
                                        "sender": "System",
                                        "message": f"It is a {name}."
                                    })
                            else:
                                active_client.send_packet({
                                    "type": "chat_broadcast",
                                    "sender": "System",
                                    "message": "Nothing to interact with there."
                                })

                elif packet_type == "admin_init":
                    print("Admin Tool connected.")
                    response = {
                        "type": "admin_init_response",
                        "success": True
                    }
                    writer.write(pack_json(response))
                    await writer.drain()

                elif packet_type == "admin_auth":
                    from server.admin import authenticate_admin
                    success, res_data = authenticate_admin(self, packet)
                    if success:
                        admin_authed = True
                        print(f"Admin auth succeeded for: {res_data.get('username')}")
                        response = {
                            "type": "admin_auth_response",
                            "success": True,
                            "username": res_data.get("username")
                        }
                    else:
                        print(f"Admin auth failed: {res_data.get('error')}")
                        response = {
                            "type": "admin_auth_response",
                            "success": False,
                            "error": res_data.get("error")
                        }
                    writer.write(pack_json(response))
                    await writer.drain()

                elif packet_type == "admin_request_accounts":
                    if not admin_authed:
                        writer.write(pack_json({"type": "admin_error", "error": "Not authenticated."}))
                        await writer.drain()
                        continue
                    from server.admin import list_accounts_data
                    accounts = list_accounts_data(self)
                    writer.write(pack_json({
                        "type": "admin_accounts_list",
                        "accounts": accounts
                    }))
                    await writer.drain()

                elif packet_type == "admin_request_characters":
                    if not admin_authed:
                        writer.write(pack_json({"type": "admin_error", "error": "Not authenticated."}))
                        await writer.drain()
                        continue
                    from server.admin import list_characters_data
                    characters = list_characters_data(self)
                    writer.write(pack_json({
                        "type": "admin_characters_list",
                        "characters": characters
                    }))
                    await writer.drain()

                elif packet_type == "admin_edit_account":
                    if not admin_authed:
                        writer.write(pack_json({"type": "admin_error", "error": "Not authenticated."}))
                        await writer.drain()
                        continue
                    acc_id = packet.get("account_id")
                    field = packet.get("field")
                    value = packet.get("value")
                    if acc_id is not None and field is not None:
                        from server.admin import edit_account_field
                        success, msg = edit_account_field(self, int(acc_id), str(field), value)
                        writer.write(pack_json({
                            "type": "admin_edit_account_response",
                            "success": success,
                            "message": msg
                        }))
                    else:
                        writer.write(pack_json({
                            "type": "admin_edit_account_response",
                            "success": False,
                            "message": "Missing account_id or field."
                        }))
                    await writer.drain()

                elif packet_type == "admin_edit_character":
                    if not admin_authed:
                        writer.write(pack_json({"type": "admin_error", "error": "Not authenticated."}))
                        await writer.drain()
                        continue
                    char_id = packet.get("character_id")
                    field = packet.get("field")
                    value = packet.get("value")
                    if char_id is not None and field is not None:
                        from server.admin import edit_character_field
                        success, msg = edit_character_field(self, int(char_id), str(field), value)
                        writer.write(pack_json({
                            "type": "admin_edit_character_response",
                            "success": success,
                            "message": msg
                        }))
                    else:
                        writer.write(pack_json({
                            "type": "admin_edit_character_response",
                            "success": False,
                            "message": "Missing character_id or field."
                        }))
                    await writer.drain()

                elif packet_type == "admin_search_item":
                    if not admin_authed:
                        writer.write(pack_json({"type": "admin_error", "error": "Not authenticated."}))
                        await writer.drain()
                        continue
                    item_type = packet.get("item_type")
                    item_id = packet.get("item_id")
                    if item_type is not None and item_id is not None:
                        from server.admin import search_item_in_db
                        results = search_item_in_db(self, int(item_type), int(item_id))
                        writer.write(pack_json({
                            "type": "admin_search_item_response",
                            "results": results
                        }))
                    else:
                        writer.write(pack_json({
                            "type": "admin_search_item_response",
                            "results": []
                        }))
                    await writer.drain()

                elif packet_type == "admin_server_message":
                    if not admin_authed:
                        writer.write(pack_json({"type": "admin_error", "error": "Not authenticated."}))
                        await writer.drain()
                        continue
                    message = packet.get("message")
                    if message is not None:
                        from server.admin import broadcast_system_message
                        broadcast_system_message(self, str(message))
                        writer.write(pack_json({
                            "type": "admin_server_message_response",
                            "success": True
                        }))
                    else:
                        writer.write(pack_json({
                            "type": "admin_server_message_response",
                            "success": False
                        }))
                    await writer.drain()

                elif packet_type == "admin_forced_save":
                    if not admin_authed:
                        writer.write(pack_json({"type": "admin_error", "error": "Not authenticated."}))
                        await writer.drain()
                        continue
                    from server.admin import execute_forced_save
                    success = execute_forced_save(self)
                    writer.write(pack_json({
                        "type": "admin_forced_save_response",
                        "success": success
                    }))
                    await writer.drain()

        except (ConnectionResetError, ConnectionAbortedError) as e:
            print(f"Client {addr} disconnected cleanly.")
        except OSError as e:
            if e.errno in (64, 10054) or "64" in str(e) or "10054" in str(e):
                print(f"Client {addr} disconnected cleanly.")
            else:
                print(f"Exception handling client {addr}: {e}")
        except Exception as e:
            print(f"Exception handling client {addr}: {e}")
        finally:
            if active_client and active_client.char_data.name in self.clients:
                char = active_client.char_data
                self.db.log_action(char.id, char.name, "logout", f"Left world from ({char.x}, {char.y})")
                del self.clients[char.name]
                print(f"Player {char.name} removed from active clients.")
                # Broadcast player left message
                left_packet = {
                    "type": "player_left",
                    "name": active_client.char_data.name
                }
                for other_client in self.clients.values():
                    other_client.send_packet(left_packet)
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            print(f"Connection closed from {addr}")
