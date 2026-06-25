# core/packets.py
import struct
import json
import asyncio
from enum import IntEnum
from core.crypto import encrypt_data, decrypt_data

PORT = 1338
VERSION = 3309

class PacketType(IntEnum):
    # Auth & Setup
    LOGIN = 1
    LOGIN_RESPONSE = 2
    REGISTER = 3
    REGISTER_RESPONSE = 4
    CREATE_CHARACTER = 5
    CREATE_CHARACTER_RESPONSE = 6
    ENTER_GAME = 7
    ENTER_GAME_RESPONSE = 8
    
    # Coordinates & Movement
    COORDINATES = 10
    MOVE = 11
    MOVE_RESPONSE = 12
    TELEPORT = 13
    
    # World Update Broadcasting
    PLAYERINFO = 20
    MONSTER = 21
    NPC = 22
    BODY = 23
    
    # Combat
    ATTACK = 30
    COMBAT_RESULT = 31
    
    # Items & Shops
    ITEMMOVE = 40
    ITEM_MOVE_RESPONSE = 41
    SHOPITEM = 42
    BUY = 43
    
    # Statistics & Attributes
    STATS = 50
    STATS_UPDATE = 51
    SKILL = 52
    LEVELUP = 53
    
    # Social & Communications
    CHATMESSAGE = 60
    SAY = 61
    CHAT_BROADCAST = 62
    WHISPERTO = 63
    GUILDMSGTO = 64
    MOTDLINE = 65
    
    # Guild Management
    GUILD_CREATE = 70
    GUILD_CREATE_RESPONSE = 71
    GUILD_INVITE = 72
    GUILD_INVITE_RESPONSE = 73
    
    # Tradeskills
    MINE = 80
    MINE_RESPONSE = 81
    SMELT = 82
    SMELT_RESPONSE = 83

    # Administration
    ADMIN_INIT = 125
    ADMIN_INIT_RESPONSE = 126

# ─── Packet Pack/Unpack Core Helpers ──────────────────────────────────────────

def pack_json(packet_dict: dict) -> bytes:
    """Serializes packet dictionary to JSON, encrypts it, and prefixes with 4-byte length prefix."""
    json_bytes = json.dumps(packet_dict).encode('utf-8')
    encrypted = encrypt_data(json_bytes)
    length_prefix = struct.pack("<I", len(encrypted))
    return length_prefix + encrypted

def unpack_json(payload: bytes) -> dict:
    """Decrypts and deserializes a JSON packet payload."""
    decrypted = decrypt_data(payload)
    return json.loads(decrypted.decode('utf-8'))

async def read_packet_async(reader) -> dict:
    """Reads a JSON packet asynchronously from an asyncio StreamReader."""
    try:
        length_data = await reader.readexactly(4)
        length = struct.unpack("<I", length_data)[0]
        payload = await reader.readexactly(length)
        return unpack_json(payload)
    except (asyncio.IncompleteReadError, ConnectionResetError, OSError):
        return None

def read_packet_sync(sock) -> dict:
    """Reads a JSON packet synchronously from a socket."""
    try:
        length_data = sock.recv(4)
        if not length_data or len(length_data) < 4:
            return None
        length = struct.unpack("<I", length_data)[0]
        payload = b""
        while len(payload) < length:
            chunk = sock.recv(length - len(payload))
            if not chunk:
                break
            payload += chunk
        if len(payload) < length:
            return None
        return unpack_json(payload)
    except (ConnectionResetError, OSError):
        return None

# ─── Structured Packet Builders ──────────────────────────────────────────────

def create_coordinates_packet(name: str, x: int, y: int) -> dict:
    return {
        "type": "coordinates",
        "packet_id": int(PacketType.COORDINATES),
        "name": name,
        "x": x,
        "y": y
    }

def create_chat_packet(sender: str, message: str, msg_type: str = "say") -> dict:
    return {
        "type": "chat_broadcast",
        "packet_id": int(PacketType.CHAT_BROADCAST),
        "sender": sender,
        "message": message,
        "msg_type": msg_type
    }

def create_stats_packet(hp: int, hp_max: int, mana: int, level: int) -> dict:
    return {
        "type": "stats_update",
        "packet_id": int(PacketType.STATS_UPDATE),
        "hp": hp,
        "hp_max": hp_max,
        "mana": mana,
        "level": level
    }

def create_levelup_packet(level: int, stat_points: int, hp_max: int) -> dict:
    return {
        "type": "levelup",
        "packet_id": int(PacketType.LEVELUP),
        "level": level,
        "stat_points": stat_points,
        "hp_max": hp_max
    }
