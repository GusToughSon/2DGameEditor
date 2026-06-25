# server/game_loop.py
import asyncio
import time
import random
from typing import Dict, List, Optional
from server.client_state import ClientState
from core.creatures import MonsterInstance

def find_path(start_x: int, start_y: int, target_x: int, target_y: int, map_db, max_depth: int = 15) -> tuple:
    """Finds a path from start to target using BFS. Returns next step (dx, dy)."""
    if start_x == target_x and start_y == target_y:
        return 0, 0
        
    queue = [(start_x, start_y, [])]
    visited = {(start_x, start_y)}
    
    while queue:
        x, y, path = queue.pop(0)
        
        if len(path) > max_depth:
            continue
            
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if nx == target_x and ny == target_y:
                if path:
                    return path[0]
                else:
                    return dx, dy
                    
            if (nx, ny) not in visited and map_db.is_passable(nx, ny):
                visited.add((nx, ny))
                queue.append((nx, ny, path + [(dx, dy)]))
                
    return 0, 0

class GameLoop:
    def __init__(self, server):
        self.server = server
        self.running = False
        self._task = None
        self.last_regen_time = time.time()
        self.last_save_time = time.time()
        self.last_spawn_time = time.time()
        self.last_ai_tick_time = time.time()

        # Configurable intervals in seconds
        self.tick_interval = 0.05      # 50ms standard tick
        self.regen_interval = 3.0      # HP/Mana regen every 3s
        self.autosave_interval = 300.0  # Auto-save every 5 mins
        self.spawn_interval = 10.0      # Check spawns every 10s
        self.ai_interval = 0.5         # Run monster AI updates every 500ms
        
        self.next_monster_id = 20000

    def start(self):
        if not self.running:
            self.running = True
            self._task = asyncio.create_task(self._loop())
            print("[GAME LOOP] Server game loop started.")

    def stop(self):
        self.running = False
        if self._task:
            self._task.cancel()
            print("[GAME LOOP] Server game loop stopped.")

    async def _loop(self):
        while self.running:
            start_time = time.time()
            try:
                await self._tick()
            except Exception as e:
                print(f"[GAME LOOP ERROR] Exception in tick: {e}")
            
            elapsed = time.time() - start_time
            sleep_time = max(0.0, self.tick_interval - elapsed)
            await asyncio.sleep(sleep_time)

    async def _tick(self):
        now = time.time()
        clients: Dict[str, ClientState] = self.server.clients
        
        # 1. Periodically spawn monsters near players
        if now - self.last_spawn_time >= self.spawn_interval:
            self.last_spawn_time = now
            self._handle_spawning(clients)

        # 2. Periodically run Monster AI
        if now - self.last_ai_tick_time >= self.ai_interval:
            self.last_ai_tick_time = now
            self._handle_monster_ai(clients)

        # 3. HP / Mana Regeneration Tick
        if now - self.last_regen_time >= self.regen_interval:
            self.last_regen_time = now
            self._handle_regeneration(clients)

        # 4. Database Auto-Save Tick
        if now - self.last_save_time >= self.autosave_interval:
            self.last_save_time = now
            self._handle_autosave()

    def _handle_spawning(self, clients: Dict[str, ClientState]):
        """Spawns monsters inside configured encounter chunks on passable coordinates."""
        map_db = self.server.map_db
        if not hasattr(map_db, 'chunk_encounters') or not map_db.chunk_encounters:
            return
            
        now = time.time()
        if not hasattr(self, 'chunk_spawn_timers'):
            self.chunk_spawn_timers = {} # (cx, cy) -> float
            
        rows = len(map_db.chunk_encounters)
        cols = len(map_db.chunk_encounters[0]) if rows > 0 else 0
        
        # Count current monsters per chunk
        monsters_per_chunk = {} # (cx, cy) -> count
        for m in self.server.monsters.values():
            if hasattr(m, 'spawn_chunk') and m.spawn_chunk:
                monsters_per_chunk[m.spawn_chunk] = monsters_per_chunk.get(m.spawn_chunk, 0) + 1
                
        # Limit per chunk: e.g., 2 monsters max
        max_per_chunk = 2
        
        for cy in range(rows):
            for cx in range(cols):
                eid = map_db.chunk_encounters[cy][cx]
                if eid is None or eid not in map_db.encounters:
                    continue
                    
                # Skip if already at capacity
                chunk_key = (cx, cy)
                curr_count = monsters_per_chunk.get(chunk_key, 0)
                if curr_count >= max_per_chunk:
                    continue
                    
                enc = map_db.encounters[eid]
                rate = enc.get("spawn_rate", 30)
                last_spawn = self.chunk_spawn_timers.get(chunk_key, 0)
                
                if now - last_spawn >= rate:
                    # Time to spawn!
                    self.chunk_spawn_timers[chunk_key] = now
                    
                    # Find passable spot in 16x16 tile chunk region
                    # Chunk bounds: x from cx*16 to (cx+1)*16-1, y from cy*16 to (cy+1)*16-1
                    tile_size = 16
                    found = False
                    for _ in range(25):
                        rx = cx * tile_size + random.randint(0, tile_size - 1)
                        ry = cy * tile_size + random.randint(0, tile_size - 1)
                        if map_db.is_passable(rx, ry):
                            # Instantiate monster
                            chosen_species = enc.get("mob_species", "Goblin")
                            stats = self.server.monster_types.get(chosen_species, {})
                            
                            m_id = self.next_monster_id
                            self.next_monster_id += 1
                            
                            monster = MonsterInstance(
                                know_id=m_id,
                                x=rx,
                                y=ry,
                                hp_left=stats.get("hp_max", 10),
                                monster_type=chosen_species
                            )
                            monster.spawn_chunk = chunk_key
                            monster.treasure_type = enc.get("treasure_type", "Default")
                            
                            self.server.monsters[m_id] = monster
                            print(f"[SPAWNER] Spawned {chosen_species} (ID: {m_id}) in chunk {chunk_key} at ({rx}, {ry}) with loot table {monster.treasure_type}")
                            
                            # Viewport update
                            self.server.update_monster_visibility(monster)
                            found = True
                            break

    def _handle_monster_ai(self, clients: Dict[str, ClientState]):
        """Updates targets, movement, pathfinding, and attacks for all monsters."""
        now_ms = int(time.time() * 1000)
        
        for m_id, monster in list(self.server.monsters.items()):
            stats = self.server.monster_types.get(monster.monster_type, {})
            
            # 1. Target check
            target_client = None
            if monster.target_client is not None:
                # Check if target player is still online
                for c in clients.values():
                    if c.char_data.id == monster.target_client:
                        target_client = c
                        break
                if not target_client:
                    monster.target_client = None # Player logged off
                    
            # 2. Acquire target if none
            if not target_client:
                # Scan for players in aggro range (7 tiles)
                for c in clients.values():
                    if abs(c.char_data.x - monster.x) <= 7 and abs(c.char_data.y - monster.y) <= 7:
                        monster.target_client = c.char_data.id
                        target_client = c
                        break
                        
            # 3. Action routing
            if target_client:
                tx, ty = target_client.char_data.x, target_client.char_data.y
                dx = tx - monster.x
                dy = ty - monster.y
                
                # Check if adjacent -> Attack!
                if abs(dx) <= 1 and abs(dy) <= 1:
                    atk_speed = stats.get("attack_speed", 1500) # Default 1500ms
                    if now_ms - monster.last_attack >= atk_speed:
                        monster.last_attack = now_ms
                        from server.combat import attempt_monster_attack_player
                        outcome = attempt_monster_attack_player(monster, stats, target_client, self.server)
                        
                        # Broadcast combat visuals
                        self.server.broadcast_to_nearby(monster.x, monster.y, {
                            "type": "chat_broadcast",
                            "sender": stats.get("name", "Monster"),
                            "message": f"Attacks {target_client.char_data.name} for {outcome.get('damage', 0)} damage!"
                        })
                        
                        if outcome.get("killed"):
                            # Player died, remove target
                            monster.target_client = None
                else:
                    # Move towards player
                    move_speed = stats.get("moving_speed", 1000) # Default 1000ms
                    if now_ms - monster.last_move >= move_speed:
                        monster.last_move = now_ms
                        p_dx, p_dy = find_path(monster.x, monster.y, tx, ty, self.server.map_db)
                        if p_dx or p_dy:
                            monster.x += p_dx
                            monster.y += p_dy
                            self.server.update_monster_visibility(monster)
            else:
                # Idle random walk
                if not stats.get("rnd_walk_off", False):
                    # 10% chance to move randomly each AI tick
                    if random.random() < 0.10:
                        rx = monster.x + random.choice([-1, 0, 1])
                        ry = monster.y + random.choice([-1, 0, 1])
                        if (rx != monster.x or ry != monster.y) and self.server.map_db.is_passable(rx, ry):
                            monster.x = rx
                            monster.y = ry
                            self.server.update_monster_visibility(monster)

    def _handle_regeneration(self, clients: Dict[str, ClientState]):
        for client_name, client in clients.items():
            char = client.char_data
            temp = client.temp_data
            
            hp_regen = 1 + (temp.con // 10)
            mana_regen = 1 + (temp.int_ // 10)
            
            hp_updated = False
            mana_updated = False

            if char.hp_left < temp.hp_max:
                char.hp_left = min(temp.hp_max, char.hp_left + hp_regen)
                hp_updated = True
                
            if char.mana_left < char.level * 5 + temp.int_ * 2:
                char.mana_left = min(char.level * 5 + temp.int_ * 2, char.mana_left + mana_regen)
                mana_updated = True

            if hp_updated or mana_updated:
                stats_packet = {
                    "type": "stats_update",
                    "hp": char.hp_left,
                    "hp_max": temp.hp_max,
                    "mana": char.mana_left
                }
                client.send_packet(stats_packet)

    def _handle_autosave(self):
        print("[GAME LOOP] Auto-save successfully synced (database writes are committed immediately).")
