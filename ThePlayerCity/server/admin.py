# server/admin.py
import json
from typing import Dict, Any, List, Optional
from server.item_database import ItemDatabaseManager

def authenticate_admin(server, packet: dict) -> (bool, dict):
    """Authenticates admin credentials and checks for character with dev_mode >= 1."""
    username = packet.get("username", "")
    password = packet.get("password", "")
    
    # Reload database cache to ensure fresh credentials
    server.db.load_accounts()
    
    acc = None
    for a in server.db.accounts:
        if a.data.acc_name == username and a.data.acc_pass == password:
            acc = a
            break
            
    if not acc:
        return False, {"error": "Invalid username or password."}
        
    is_admin = False
    for c in acc.chars:
        if c.used and c.dev_mode >= 1:
            is_admin = True
            break
            
    if not is_admin:
        return False, {"error": "Account does not have admin (dev_mode) privileges."}
        
    return True, {"username": username, "account_id": acc.data.id}

def list_accounts_data(server) -> List[Dict[str, Any]]:
    """Returns a list of all accounts for the admin tool."""
    server.db.load_accounts()
    acc_list = []
    for a in server.db.accounts:
        acc_list.append({
            "id": a.data.id,
            "acc_name": a.data.acc_name,
            "is_banned": a.data.is_banned,
            "is_premium": a.data.is_premium,
            "is_golden": a.data.is_golden
        })
    return acc_list

def list_characters_data(server) -> List[Dict[str, Any]]:
    """Returns a list of all characters for the admin tool."""
    server.db.load_accounts()
    char_list = []
    for a in server.db.accounts:
        for c in a.chars:
            if c.used:
                # Find if online
                is_online = any(client.char_data.id == c.id for client in server.clients.values())
                char_list.append({
                    "id": c.id,
                    "account_id": a.data.id,
                    "name": c.name,
                    "level": c.level,
                    "x": c.x,
                    "y": c.y,
                    "avatar": c.avatar,
                    "dev_mode": c.dev_mode,
                    "class_template": c.class_template,
                    "is_online": is_online
                })
    return char_list

def edit_account_field(server, account_id: int, field: str, value) -> (bool, str):
    """Edits a field on an account, synchronizing in-memory state and updating SQLite."""
    server.db.load_accounts()
    acc = None
    for a in server.db.accounts:
        if a.data.id == account_id:
            acc = a
            break
            
    if not acc:
        return False, "Account not found."
        
    # Translate value to correct type
    if field in ("is_banned", "is_premium", "is_golden"):
        try:
            val = bool(int(value))
        except (ValueError, TypeError):
            val = str(value).lower() in ("true", "1", "yes")
    else:
        return False, f"Unknown or uneditable account field: {field}"
        
    # Update object
    setattr(acc.data, field, val)
    
    # Save to database
    server.db.save_accounts()
    
    # Handle ban disconnect
    if field == "is_banned" and val:
        # Disconnect any online players on this account
        clients_to_disconnect = []
        for client in server.clients.values():
            if client.account.data.id == account_id:
                clients_to_disconnect.append(client)
        for client in clients_to_disconnect:
            client.send_packet({
                "type": "chat_broadcast",
                "sender": "System",
                "message": "Your account has been banned. Disconnecting.",
                "msg_type": "system"
            })
            client.writer.close()
            
    return True, "Account updated successfully."

def edit_character_field(server, character_id: int, field: str, value) -> (bool, str):
    """Edits a field on a character, synchronizing in-memory state and updating SQLite."""
    server.db.load_accounts()
    char = None
    owner_acc = None
    for a in server.db.accounts:
        for c in a.chars:
            if c.used and c.id == character_id:
                char = c
                owner_acc = a
                break
        if char:
            break
            
    if not char:
        return False, "Character not found."
        
    # Check if character is online
    online_client = None
    for client in server.clients.values():
        if client.char_data.id == character_id:
            online_client = client
            char = client.char_data  # edit online version
            break

    # Parse and validate fields
    try:
        if field in ("level", "x", "y", "str", "con", "dex", "int", "dev_mode", "avatar", "hp_left", "hp_max", "mana_left"):
            val = int(value)
        elif field in ("tag", "name"):
            val = str(value).strip()
        else:
            return False, f"Unknown or uneditable character field: {field}"
    except ValueError:
        return False, f"Invalid value for field {field}."

    # Perform edit
    setattr(char, field, val)
    
    # Save to database
    server.db.save_accounts()
    
    # Sync online client state if necessary
    if online_client:
        online_client.recalculate_temp_stats()
        # Send update packages to the online player
        online_client.send_packet({
            "type": "stats_update",
            "hp": char.hp_left,
            "hp_max": online_client.temp_data.hp_max,
            "mana": char.mana_left,
            "level": char.level
        })
        online_client.send_packet({
            "type": "chat_broadcast",
            "sender": "System",
            "message": f"An admin has updated your {field} to {value}.",
            "msg_type": "system"
        })
        # If coordinates changed, broadcast coordinates update
        if field in ("x", "y"):
            server.update_monster_visibility(online_client)
            # Send movement updates
            coord_packet = {
                "type": "coordinates",
                "name": char.name,
                "x": char.x,
                "y": char.y,
                "avatar": char.avatar
            }
            server.broadcast_to_nearby(char.x, char.y, coord_packet)
            
    return True, "Character updated successfully."

def search_item_in_db(server, item_type: int = None, item_id: int = None) -> List[Dict[str, Any]]:
    """Searches items.db and cross-references character owners to return search matches."""
    item_db = ItemDatabaseManager()
    matches = item_db.search_items(item_type, item_id)
    
    results = []
    # Cache character names mapping
    char_names = {}
    server.db.load_accounts()
    for a in server.db.accounts:
        for c in a.chars:
            if c.used:
                char_names[c.id] = c.name
                
    for item in matches:
        owner_name = char_names.get(item["owner_id"], "Unknown") if item["owner_id"] else "Ground/System"
        results.append({
            "id": item["id"],
            "item_type": item["item_type"],
            "quantity": item["quantity"],
            "container": item["container"],
            "slot": item["slot"],
            "owner_name": owner_name,
            "x": item["x"],
            "y": item["y"]
        })
    return results

def broadcast_system_message(server, message: str):
    """Sends system broadcast message to all online clients."""
    broadcast_packet = {
        "type": "chat_broadcast",
        "sender": "Global Admin Announcement",
        "message": message,
        "msg_type": "system"
    }
    for client in server.clients.values():
        client.send_packet(broadcast_packet)

def execute_forced_save(server) -> bool:
    """Saves all online and loaded characters/accounts back to SQLite database."""
    # Synchronize all active client states to DB manager accounts cache
    for client in server.clients.values():
        for a in server.db.accounts:
            if a.data.id == client.account.data.id:
                a.chars[client.char_slot] = client.char_data
                break
    return server.db.save_accounts()
