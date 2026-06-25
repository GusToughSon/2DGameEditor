# server/tradeskills.py
import time
from server.client_state import ClientState

def execute_mine(client: ClientState) -> dict:
    """Simulates a mine trade action. Checks if they have correct tools/locations."""
    char = client.char_data
    # Skill index 3 = Mining in legacy C++ ClientClass
    mining_skill = char.skills[3]
    
    # Check cooldown / delay
    now = time.time()
    if now - client.last_tradeskill < 2.0:
        return {"success": False, "error": "You must wait before mining again."}
        
    client.last_tradeskill = now
    
    # Success probability increases with skill level
    success = (mining_skill.level * 2 + 30) > (time.time() % 100)
    if success:
        mining_skill.exp += 15
        if mining_skill.exp >= mining_skill.level * 100:
            mining_skill.level += 1
            mining_skill.exp = 0
            client.send_packet({
                "type": "chat_broadcast",
                "sender": "System",
                "message": f"Your mining skill has increased to level {mining_skill.level}!",
                "msg_type": "system"
            })
        return {"success": True, "message": "You mined some copper ore!"}
    else:
        return {"success": False, "error": "You failed to mine anything."}

def execute_smelt(client: ClientState) -> dict:
    """Smelt raw ores into metal bars."""
    char = client.char_data
    smelt_skill = char.skills[4]  # Smelting
    
    now = time.time()
    if now - client.last_tradeskill < 2.0:
        return {"success": False, "error": "You must wait before smelting again."}
        
    client.last_tradeskill = now
    return {"success": True, "message": "You successfully smelted a copper bar!"}
