# server/chat.py
from server.client_state import ClientState
import os

def handle_chat_message(sender: ClientState, packet: dict, server):
    """Processes chat routing for different channels (say, whisper, guild)
    and executes developer slash commands for GMs."""
    message = packet.get("message", "").strip()
    if not message:
        return

    char = sender.char_data

    # Check for slash command
    if message.startswith("/"):
        if char.dev_mode < 1:
            sender.send_packet({
                "type": "chat_broadcast",
                "sender": "System",
                "message": "You do not have GM privileges.",
                "msg_type": "system"
            })
            return

        parts = message[1:].split()
        if not parts:
            return
        cmd = parts[0].lower()

        if cmd == "teleport":
            if len(parts) >= 3:
                try:
                    tx = int(parts[1])
                    ty = int(parts[2])
                    old_x, old_y = char.x, char.y
                    char.x = tx
                    char.y = ty
                    
                    # Save coordinates to database
                    server.db.save_accounts()
                    
                    # Update client coords
                    sender.send_packet({
                        "type": "move_response",
                        "success": True,
                        "x": tx,
                        "y": ty
                    })
                    
                    # Update visible monsters and players
                    server.update_monster_visibility(sender)
                    
                    # Tell nearby other players we teleported away
                    server.broadcast_to_nearby(old_x, old_y, {
                        "type": "player_left",
                        "name": char.name
                    })
                    
                    # Tell players in new area we arrived
                    server.broadcast_to_nearby(tx, ty, {
                        "type": "coordinates",
                        "name": char.name,
                        "x": tx,
                        "y": ty,
                        "avatar": char.avatar
                    })
                    
                    sender.send_packet({
                        "type": "chat_broadcast",
                        "sender": "System",
                        "message": f"Teleported to ({tx}, {ty}).",
                        "msg_type": "system"
                    })
                except Exception as e:
                    sender.send_packet({
                        "type": "chat_broadcast",
                        "sender": "System",
                        "message": f"Teleport failed: {e}",
                        "msg_type": "system"
                    })
            else:
                sender.send_packet({
                    "type": "chat_broadcast",
                    "sender": "System",
                    "message": "Usage: /teleport <x> <y>",
                    "msg_type": "system"
                })

        elif cmd == "spawn":
            if len(parts) >= 2:
                monster_type = parts[1]
                if monster_type not in server.monster_types:
                    # Look up species case-insensitively
                    found = None
                    for name in server.monster_types:
                        if name.lower() == monster_type.lower():
                            found = name
                            break
                    monster_type = found if found else monster_type

                if monster_type in server.monster_types:
                    try:
                        from core.creatures import MonsterInstance
                        m_id = server.game_loop.next_monster_id
                        server.game_loop.next_monster_id += 1
                        
                        stats = server.monster_types.get(monster_type, {})
                        monster = MonsterInstance(
                            know_id=m_id,
                            x=char.x,
                            y=char.y,
                            hp_left=stats.get("hp_max", 10),
                            monster_type=monster_type
                        )
                        monster.spawn_chunk = f"C_{char.x // 16}_{char.y // 16}"
                        
                        server.monsters[m_id] = monster
                        server.update_monster_visibility(monster)
                        
                        sender.send_packet({
                            "type": "chat_broadcast",
                            "sender": "System",
                            "message": f"Spawned {monster_type} (ID: {m_id}) at your location.",
                            "msg_type": "system"
                        })
                    except Exception as e:
                        sender.send_packet({
                            "type": "chat_broadcast",
                            "sender": "System",
                            "message": f"Spawn failed: {e}",
                            "msg_type": "system"
                        })
                else:
                    sender.send_packet({
                        "type": "chat_broadcast",
                        "sender": "System",
                        "message": f"Unknown monster type: {monster_type}",
                        "msg_type": "system"
                    })
            else:
                sender.send_packet({
                    "type": "chat_broadcast",
                    "sender": "System",
                    "message": "Usage: /spawn <monster_name>",
                    "msg_type": "system"
                })

        elif cmd == "give":
            if len(parts) >= 3:
                try:
                    family_id = int(parts[1])
                    item_type = int(parts[2])
                    qty = int(parts[3]) if len(parts) >= 4 else 1
                    
                    from server.item_database import ItemDatabaseManager
                    from core.items import ItemInstance
                    item_db = ItemDatabaseManager()
                    
                    # Find empty slot in sender's backpack (len=24)
                    empty_slot = -1
                    for i in range(24):
                        if sender.backpack[i] is None:
                            empty_slot = i
                            break
                            
                    if empty_slot == -1:
                        sender.send_packet({
                            "type": "chat_broadcast",
                            "sender": "System",
                            "message": "Backpack is full.",
                            "msg_type": "system"
                        })
                        return
                        
                    new_item = ItemInstance(
                        used=True,
                        item_type=item_type,
                        family=family_id,
                        quantity=qty,
                        durability=100
                    )
                    
                    db_id = item_db.add_item(new_item, owner_id=char.id, container="backpack", slot=empty_slot)
                    new_item.know_id = db_id
                    sender.backpack[empty_slot] = {
                        "id": db_id,
                        "item_type": item_type,
                        "family": family_id,
                        "quantity": qty,
                        "durability": 100,
                        "container": "backpack",
                        "slot": empty_slot
                    }
                    
                    server.send_inventory(sender)
                    sender.send_packet({
                        "type": "chat_broadcast",
                        "sender": "System",
                        "message": f"Gave item type {item_type} (qty: {qty}) in slot {empty_slot}.",
                        "msg_type": "system"
                    })
                except Exception as e:
                    sender.send_packet({
                        "type": "chat_broadcast",
                        "sender": "System",
                        "message": f"Give command failed: {e}",
                        "msg_type": "system"
                    })
            else:
                sender.send_packet({
                    "type": "chat_broadcast",
                    "sender": "System",
                    "message": "Usage: /give <family_id> <item_type> [qty]",
                    "msg_type": "system"
                })

        elif cmd == "heal":
            char.hp_left = sender.temp_data.hp_max
            sender.send_packet({
                "type": "stats_update",
                "hp": char.hp_left,
                "hp_max": sender.temp_data.hp_max,
                "mana": char.mana_left
            })
            sender.send_packet({
                "type": "chat_broadcast",
                "sender": "System",
                "message": "Healed to max health.",
                "msg_type": "system"
            })

        elif cmd == "announce":
            ann_text = " ".join(parts[1:])
            if ann_text:
                for client in server.clients.values():
                    client.send_packet({
                        "type": "chat_broadcast",
                        "sender": "Server Announcement",
                        "message": ann_text,
                        "msg_type": "system"
                    })
            else:
                sender.send_packet({
                    "type": "chat_broadcast",
                    "sender": "System",
                    "message": "Usage: /announce <message>",
                    "msg_type": "system"
                })
        return

    # Regular channels
    msg_type = packet.get("msg_type", "say")

    if msg_type == "say":
        broadcast_packet = {
            "type": "chat_broadcast",
            "sender": char.name,
            "message": message,
            "msg_type": "say"
        }
        for client in server.clients.values():
            client.send_packet(broadcast_packet)

    elif msg_type == "whisper":
        target_name = packet.get("target_name", "")
        target_client = server.clients.get(target_name)
        if target_client:
            whisper_packet = {
                "type": "chat_broadcast",
                "sender": char.name,
                "message": message,
                "msg_type": "whisper"
            }
            target_client.send_packet(whisper_packet)
            sender.send_packet(whisper_packet)
        else:
            sender.send_packet({
                "type": "chat_broadcast",
                "sender": "System",
                "message": f"Player {target_name} is not online.",
                "msg_type": "system"
            })

    elif msg_type == "guild":
        if char.guild > 0:
            guild_packet = {
                "type": "chat_broadcast",
                "sender": f"[{char.tag}] {char.name}",
                "message": message,
                "msg_type": "guild"
            }
            for client in server.clients.values():
                if client.char_data.guild == char.guild:
                    client.send_packet(guild_packet)
        else:
            sender.send_packet({
                "type": "chat_broadcast",
                "sender": "System",
                "message": "You are not in a guild.",
                "msg_type": "system"
            })
