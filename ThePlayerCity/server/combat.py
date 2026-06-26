# server/combat.py
import random
import os
from server.client_state import ClientState
from core.creatures import MonsterInstance
from server.progression import grant_experience

def calculate_damage_to_monster(attacker: ClientState, monster: MonsterInstance, monster_type: dict) -> int:
    """Calculates combat damage from a player to a monster."""
    char = attacker.char_data
    temp = attacker.temp_data
    
    # Calculate base damage based on player strength
    base_dmg = random.randint(temp.str // 5 + 1, temp.str // 2 + 5)
    
    # Simple defense mitigation using monster's Armor Class (ac)
    monster_ac = monster_type.get("ac", 0)
    damage = max(1, base_dmg - (monster_ac // 2))
    return damage

def calculate_damage_to_player(monster: MonsterInstance, monster_type: dict, target: ClientState) -> int:
    """Calculates combat damage from a monster to a player."""
    dam_min = monster_type.get("dam_min", 1)
    dam_max = monster_type.get("dam_max", 5)
    
    base_dmg = random.randint(dam_min, dam_max)
    target_ac = target.temp_data.ac
    damage = max(1, base_dmg - (target_ac // 2))
    return damage

def attempt_player_attack_monster(attacker: ClientState, monster: MonsterInstance, monster_type: dict, server) -> dict:
    """Attempts an attack from a player to a monster.
    Handles experience gain and loot drops on monster defeat.
    """
    player_dex = attacker.temp_data.dex
    monster_dex = monster_type.get("dex", 10)
    
    # Check hit accuracy
    acc_chance = 50 + (player_dex - monster_dex)
    acc_chance = max(10, min(95, acc_chance))
    
    if random.randint(0, 100) > acc_chance:
        return {"hit": False, "damage": 0, "killed": False}
        
    damage = calculate_damage_to_monster(attacker, monster, monster_type)
    monster.hp_left = max(0, monster.hp_left - damage)
    
    killed = False
    if monster.hp_left <= 0:
        killed = True
        monster.hp_left = 0
        
        # Award experience
        monster_level = monster_type.get("level", 1)
        exp_gain = monster_level * 15 + 10
        grant_experience(attacker, exp_gain)
        
        # Increment stats counters
        attacker.char_data.killed_monsters += 1
        attacker.char_data.overall_mon_count += 1
        
        # Save player progress immediately
        server.db.sqlite_db.update_character_stats(attacker.char_data)
        
        # Log to SQL accounts.db kill log
        try:
            server.db.sqlite_db.log_kill(
                killer_id=attacker.char_data.id,
                killer_name=attacker.char_data.name,
                killer_type="player",
                killed_id=monster.know_id,
                killed_name=monster_type.get("name", "Monster"),
                killed_type="monster",
                x=monster.x,
                y=monster.y,
                map_level=0
            )
        except Exception as e:
            print(f"[COMBAT ERROR] Failed to log monster kill: {e}")
            
        # Spawn loot drop (Random item roll or gold drop on ground)
        try:
            from core.items import ItemInstance, ItemFamily
            from server.item_database import ItemDatabaseManager
            item_db = ItemDatabaseManager()
            
            # Load loot tables json
            loot_tables = {}
            loot_path = os.path.join(server.map_db.project_path, "Maps", "LootTables.json")
            if os.path.exists(loot_path):
                try:
                    import json
                    with open(loot_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        loot_tables = data.get("loot_tables", {})
                except Exception as e:
                    print(f"[COMBAT WARNING] Failed to load LootTables.json: {e}")
            
            # Get items list for this treasure type
            t_type = getattr(monster, 'treasure_type', 'Default')
            items_to_roll = loot_tables.get(t_type, [])
            if not items_to_roll and t_type != "Default" and "Default" in loot_tables:
                items_to_roll = loot_tables["Default"]
                
            drops = []
            if items_to_roll:
                for item_spec in items_to_roll:
                    chance = item_spec.get("chance", 50)
                    if random.randint(1, 100) <= chance:
                        qty = random.randint(item_spec.get("min_qty", 1), item_spec.get("max_qty", 1))
                        if qty > 0:
                            drops.append({
                                "family": item_spec.get("family", 1),
                                "item_type": item_spec.get("item_type", 1),
                                "item_id": item_spec.get("item_id", 1),
                                "quantity": qty
                            })
            else:
                # Fallback default hardcoded roll
                if random.random() < 0.50:
                    family = random.choice([ItemFamily.WEAPON, ItemFamily.ARMOR])
                    if family == ItemFamily.WEAPON:
                        item_type = random.randint(1, 5)
                        item_id = random.randint(1, 10)
                    else:
                        item_type = random.choice([11, 12, 13, 18])
                        item_id = random.randint(1, 10)
                    drops.append({
                        "family": family,
                        "item_type": item_type,
                        "item_id": item_id,
                        "quantity": 1
                    })
                    
            for drop in drops:
                loot_item = ItemInstance(
                    used=True,
                    know_id=random.randint(1000, 99999),
                    item_type=drop["item_type"],
                    family=drop["family"],
                    durability=50,
                    x=monster.x,
                    y=monster.y,
                    quantity=drop["quantity"]
                )
                db_id = item_db.add_item(loot_item, owner_id=0, container="ground", slot=0)
                
                # Notify players around the area of the drop
                drop_notify = {
                    "type": "chat_broadcast",
                    "sender": "Loot",
                    "message": f"The defeated {monster_type.get('name')} dropped an item on the ground!"
                }
                server.broadcast_to_nearby(monster.x, monster.y, drop_notify)
        except Exception as e:
            print(f"[COMBAT ERROR] Failed to drop loot: {e}")
            
    return {
        "hit": True,
        "damage": damage,
        "killed": killed
    }

def attempt_monster_attack_player(monster: MonsterInstance, monster_type: dict, target: ClientState, server) -> dict:
    """Attempts an attack from a monster to a player."""
    monster_dex = monster_type.get("dex", 10)
    player_dex = target.temp_data.dex
    
    # Check hit accuracy
    acc_chance = 50 + (monster_dex - player_dex)
    acc_chance = max(10, min(95, acc_chance))
    
    if random.randint(0, 100) > acc_chance:
        return {"hit": False, "damage": 0, "killed": False}
        
    damage = calculate_damage_to_player(monster, monster_type, target)
    target.char_data.hp_left = max(0, target.char_data.hp_left - damage)
    
    killed = False
    if target.char_data.hp_left <= 0:
        killed = True
        target.char_data.hp_left = 0
        target.char_data.overall_deaths_monster += 1
        
        # Log to SQL accounts.db kill log
        try:
            server.db.sqlite_db.log_kill(
                killer_id=monster.know_id,
                killer_name=monster_type.get("name", "Monster"),
                killer_type="monster",
                killed_id=target.char_data.id,
                killed_name=target.char_data.name,
                killed_type="player",
                x=target.char_data.x,
                y=target.char_data.y,
                map_level=0
            )
        except Exception as e:
            print(f"[COMBAT ERROR] Failed to log player death: {e}")
            
        # Send death packet and reset coords
        target.send_packet({
            "type": "chat_broadcast",
            "sender": "System",
            "message": "You have been slain! Respawning at start shrine."
        })
        
        # Spawn player body/corpse
        old_x = target.char_data.x
        old_y = target.char_data.y
        body_id = int(time.time() * 1000)
        body_name = f"{target.char_data.name}'s corpse"
        server.bodies[body_id] = {
            "id": body_id,
            "name": body_name,
            "x": old_x,
            "y": old_y,
            "decay_time": time.time() + 60.0
        }
        server.broadcast_to_nearby(old_x, old_y, {
            "type": "body_spawn",
            "body_id": body_id,
            "name": body_name,
            "x": old_x,
            "y": old_y
        })

        # Apply death penalty: reset position to (10, 10)
        target.char_data.x = 10
        target.char_data.y = 10
        target.char_data.hp_left = target.temp_data.hp_max
        server.db.sqlite_db.update_character_coordinates(target.char_data.id, 10, 10)
        server.db.sqlite_db.update_character_stats(target.char_data)
        
        # Force stats update packet
        target.send_packet({
            "type": "stats_update",
            "hp": target.char_data.hp_left,
            "hp_max": target.temp_data.hp_max,
            "mana": target.char_data.mana_left
        })
        
        # Teleport response/coords update
        target.send_packet({
            "type": "move_response",
            "success": True,
            "x": 10,
            "y": 10
        })
        
    else:
        # Send stats update packet
        target.send_packet({
            "type": "stats_update",
            "hp": target.char_data.hp_left,
            "hp_max": target.temp_data.hp_max,
            "mana": target.char_data.mana_left
        })
        
    return {
        "hit": True,
        "damage": damage,
        "killed": killed
    }

def attempt_attack(attacker: ClientState, target: ClientState) -> dict:
    """Attempts an attack from one player to another player (PvP)."""
    attacker_dex = attacker.temp_data.dex
    target_dex = target.temp_data.dex
    
    # Check hit accuracy
    acc_chance = 50 + (attacker_dex - target_dex)
    acc_chance = max(10, min(95, acc_chance))
    
    if random.randint(0, 100) > acc_chance:
        return {"hit": False, "damage": 0, "killed": False}
        
    # Calculate damage: attacker STR vs target AC
    attacker_str = attacker.temp_data.str
    base_dmg = random.randint(attacker_str // 5 + 1, attacker_str // 2 + 5)
    target_ac = target.temp_data.ac
    damage = max(1, base_dmg - (target_ac // 2))
    
    target.char_data.hp_left = max(0, target.char_data.hp_left - damage)
    
    killed = False
    if target.char_data.hp_left <= 0:
        killed = True
        target.char_data.hp_left = 0
        target.char_data.overall_deaths_player += 1
        attacker.char_data.overall_player_kills += 1
        
        # Teleport dead player to start shrine (10, 10)
        target.char_data.x = 10
        target.char_data.y = 10
        
        target.send_packet({
            "type": "chat_broadcast",
            "sender": "System",
            "message": "You have been slain in PvP! Respawning at start shrine."
        })
        target.send_packet({
            "type": "stats_update",
            "hp": target.char_data.hp_left,
            "hp_max": target.temp_data.hp_max,
            "mana": target.char_data.mana_left
        })
        target.send_packet({
            "type": "move_response",
            "success": True,
            "x": 10,
            "y": 10
        })
    else:
        target.send_packet({
            "type": "stats_update",
            "hp": target.char_data.hp_left,
            "hp_max": target.temp_data.hp_max,
            "mana": target.char_data.mana_left
        })
        
    return {
        "hit": True,
        "damage": damage,
        "killed": killed
    }

