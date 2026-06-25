# server/progression.py
from server.client_state import ClientState

# Create experience requirement lookup table
EXP_TABLE = {}
for lvl in range(1, 201):
    # Level-up experience requirement formula
    EXP_TABLE[lvl] = int(100 * (lvl ** 2.2))

def grant_experience(client: ClientState, amount: int) -> bool:
    """Grants experience to a character. Handles level up increments."""
    char = client.char_data
    if char.level >= 200:
        return False
        
    char.exp += amount
    req_exp = EXP_TABLE.get(char.level, 1000)
    
    leveled_up = False
    while char.exp >= req_exp and char.level < 200:
        char.exp -= req_exp
        char.level += 1
        char.stat_points += 5
        client.recalculate_temp_stats()
        char.hp_left = client.temp_data.hp_max
        leveled_up = True
        req_exp = EXP_TABLE.get(char.level, 1000)

        # Notify client of level-up
        client.send_packet({
            "type": "levelup",
            "level": char.level,
            "stat_points": char.stat_points,
            "hp_max": client.temp_data.hp_max
        })
        
        # Broadcast level up message to everyone
        client.send_packet({
            "type": "chat_broadcast",
            "sender": "System",
            "message": f"Congratulations! {char.name} has reached level {char.level}!",
            "msg_type": "system"
        })
        
    return leveled_up
