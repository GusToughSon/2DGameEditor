# core/creatures.py — Monster, NPC, and Body System for ThePlayerCity Python Port
# Ported from Memoria C++ Monsters.h / Client.h / main.h
from enum import IntEnum
from dataclasses import dataclass, field
from typing import List, Optional


# ─── Walk Types ──────────────────────────────────────────────────────────────
class WalkType(IntEnum):
    NONE       = 0
    RANDOM     = 1
    CHECKPOINT = 2
    LIMITS     = 3


# ─── Monster/NPC State ──────────────────────────────────────────────────────
class CreatureState(IntEnum):
    DEAD  = 0
    ALIVE = 1


# ─── Constants (matching C++ limits) ────────────────────────────────────────
MAX_MONSTERS       = 256
MAX_NPC            = 64
MAX_MONSTER_TYPES  = 250
MAX_NPC_TYPES      = 150
MAX_MONSTER_SPAWNS = 256
MAX_SHOP_STORAGES  = 20
MAX_STORE_ITEMS    = 100
MAX_MONSTER_IDS    = 10000
MAX_NPC_IDS        = 2048
MAX_BODIES         = 128
BODY_DECAY_TIME    = 60000   # ms
BODY_DECAY_STAGES  = 4       # 0,1,(2),[3],4 — () lootable, [] items drop
MONSTER_SPAWN_RATE = 100
MONSTER_ACTION_CHECK_TIME = 50      # ms
MONSTER_SPAWN_TIME_CHECK  = 180000  # ms
PLAYER_ACTION_TIME_CHECK  = 25      # ms


# ─── Loot Table Entry ───────────────────────────────────────────────────────

@dataclass
class LootEntry:
    """A single loot drop definition for a monster type.
    Mirrors C++ LootStruct."""
    drop_probability: int = 0    # Higher = rarer (1 in N chance)
    item_type: int = 0
    item_id: int = 0
    family: int = 0
    amount_min: int = 1
    amount_max: int = 1


# ─── Monster Type Definition ────────────────────────────────────────────────

@dataclass
class MonsterType:
    """Monster species definition — mirrors C++ MonsterTypesStruct.
    Loaded from JSON (replaces .dat binary)."""
    name: str = ""
    used: bool = False
    ghost: bool = False
    fly: bool = False
    rnd_walk_off: bool = False
    rnd_walk_range: int = 0

    dam_min: int = 0
    dam_max: int = 0
    hp_max: int = 0
    ac: int = 0
    dex: int = 0
    con: int = 0

    moving_speed: int = 0
    attack_speed: int = 0
    level: int = 0

    elemental_defence: int = 0
    defence_amount: int = 0
    elemental_attack: int = 0
    attack_amount: int = 0

    loot: List[LootEntry] = field(default_factory=lambda: [LootEntry() for _ in range(10)])

    # Animation
    animated: bool = False
    anim_speed: int = 0
    num_frames: int = 0
    anim_type: int = 0


# ─── Monster Instance (live state) ──────────────────────────────────────────

@dataclass
class MonsterInstance:
    """A single live monster in the world.
    Mirrors C++ MonsterClass."""
    know_id: int = 0
    x: int = 0
    y: int = 0
    hp_left: int = 0
    monster_type: str = ""          # Name of the monster type (or species string)

    # Runtime state
    target_client: Optional[int] = None    # Client index being targeted
    target_npc: Optional[int] = None       # NPC index being targeted
    spawn_ref: Optional[int] = None        # Which spawn point created this
    spawn_chunk: Optional[tuple] = None    # Origin (cx, cy) chunk of this spawn
    treasure_type: str = "Default"         # Treasure drop table type

    last_move: int = 0             # Timestamp of last movement
    last_attack: int = 0           # Timestamp of last attack
    last_regen: int = 0            # Timestamp of last HP regeneration


# ─── Monster Spawn Point ────────────────────────────────────────────────────

@dataclass
class MonsterSpawn:
    """A spawn point that periodically creates monsters.
    Mirrors C++ MonsterSpawnStruct."""
    x: int = 0
    y: int = 0
    used: bool = False             # True if a monster from this spawn is alive
    monster_type: int = 0
    max_dist_x: int = 0
    max_dist_y: int = 0
    last_spawned: int = 0          # Timestamp


# ─── NPC Type Definition ────────────────────────────────────────────────────

@dataclass
class NPCType:
    """NPC species definition — mirrors C++ NPCTypesStruct.
    Loaded from JSON (replaces .dat binary)."""
    name: str = ""
    used: bool = False
    print_name: bool = False

    walking: bool = False
    fly: bool = False
    ghost: bool = False
    walking_type: int = 0          # WalkType enum
    walking_range: int = 0

    is_shop: bool = False
    is_guard: bool = False
    alignment: int = 0

    dam_min: int = 0
    dam_max: int = 0
    max_hp: int = 0
    atk_type: int = 0
    dex: int = 0
    con: int = 0
    ac: int = 0
    speed: int = 0
    atk_speed: int = 0

    conversation: str = ""
    adv_conv: bool = False
    adv_conv_id: int = 0

    # Animation
    animated: bool = False
    anim_speed: int = 0
    num_frames: int = 0
    anim_type: int = 0


# ─── NPC Instance (live state) ──────────────────────────────────────────────

@dataclass
class NPCInstance:
    """A single live NPC in the world.
    Mirrors C++ NPCClass."""
    npc_type: int = 0
    shop_id: int = 0
    conv_id: int = 0
    hp_left: int = 0
    npc_id: int = 0

    x: int = 0
    y: int = 0
    origin_x: int = 0             # Starting position for walk limits
    origin_y: int = 0
    max_dist_x: int = 0
    max_dist_y: int = 0

    spawn_ref: Optional[int] = None

    # Targeting
    target_player: int = -1
    target_monster: Optional[int] = None

    # Timers
    last_attack: int = 0
    last_move: int = 0
    last_regen: int = 0


# ─── NPC Spawn Point ────────────────────────────────────────────────────────

@dataclass
class NPCSpawn:
    """NPC spawn point — mirrors C++ NPCSpawnStruct."""
    x: int = 0
    y: int = 0
    used: bool = False
    npc_type: int = 0
    shop_id: int = 0
    conv_id: int = 0
    max_dist_x: int = 0
    max_dist_y: int = 0
    last_spawned: int = 0


# ─── Shop Storage ───────────────────────────────────────────────────────────

@dataclass
class ShopItem:
    """A single item in a shop inventory."""
    item_type: int = 0
    item_id: int = 0
    family: int = 0


@dataclass
class ShopStorage:
    """An NPC shop's inventory — mirrors C++ ShopStorageClass."""
    used: bool = False
    name: str = ""
    bonus: int = 0                 # Price modifier
    items: List[ShopItem] = field(default_factory=lambda: [ShopItem() for _ in range(MAX_STORE_ITEMS)])
    item_count: int = 0


# ─── Body / Corpse System ───────────────────────────────────────────────────

@dataclass
class BodyInstance:
    """A player corpse in the world — mirrors C++ BodyClass."""
    used: bool = False
    x: int = 0
    y: int = 0

    looted: bool = False
    looter_name: str = ""
    looter_is_criminal: bool = False

    owner_id: int = 0
    owner_slot: int = 0
    owner_guild: int = 0
    owner_name: str = ""

    decay_state: int = 0          # 0..4 — stage of decay
    decay_state_time: int = 0     # Timestamp of last decay change

    items: List[int] = field(default_factory=lambda: [0] * 84)  # Item IDs


# ─── Criminal Spawn Point ───────────────────────────────────────────────────

@dataclass
class CrimSpawn:
    """Spawn location for criminal players — mirrors C++ CrimSpawnList."""
    x: int = 0
    y: int = 0
