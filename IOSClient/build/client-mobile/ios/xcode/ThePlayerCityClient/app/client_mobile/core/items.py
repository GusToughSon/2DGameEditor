# Ported from legacy C++ Items.h / Monsters.h
from enum import IntEnum
from dataclasses import dataclass, field
from typing import List, Optional


# ─── Item Family Enums ──────────────────────────────────────────────────────
class ItemFamily(IntEnum):
    NONE      = 0
    WEAPON    = 1
    ARMOR     = 2
    COLLECTABLE = 3
    USEABLE   = 4
    CONTAINER = 5


class WeaponType(IntEnum):
    NONE     = 0
    SWORD    = 1
    AXE      = 2
    BLUNT    = 3
    POLEARM  = 4
    BOW      = 5


class ArmorType(IntEnum):
    NONE    = 0
    ARMOR   = 11
    HELM    = 12
    SHIELD  = 13
    LEGS    = 14
    GAUNTS  = 15
    RING    = 16
    AMULET  = 17
    ROBE    = 18
    BELT    = 19


class CollectableType(IntEnum):
    COLLECTABLE = 20


class UseableType(IntEnum):
    USEABLE = 21


# ─── Item List (where it lives) ─────────────────────────────────────────────
class ItemList(IntEnum):
    NONE      = 0
    BACKPACK  = 1
    BANK      = 2
    WORN      = 3
    GROUND    = 4
    IN_BODY   = 5


# ─── Use Types (tradeskill interaction) ─────────────────────────────────────
class UseType(IntEnum):
    NONE          = 0
    MINE          = 1
    SMELT         = 2
    FORGE         = 3
    BOOST         = 4
    REPAIR        = 5
    TELEPORT      = 6
    TELEP_AND_SPAWN = 7
    SPAWN_GATE    = 8


# ─── Elemental Types ────────────────────────────────────────────────────────
class ElementalType(IntEnum):
    NONE     = 0
    FIRE     = 1
    LIGHTNING = 2  # AIR in server
    ICE      = 3   # EARTH in server
    DARK     = 4   # WATER in server
    LIGHT    = 5


# ─── Requirement Types ──────────────────────────────────────────────────────
class RequirementType(IntEnum):
    NONE = 0
    STR  = 1
    DEX  = 2
    CON  = 3
    INT  = 4
    LVL  = 5
    SKL  = 6
    REP_EVIL = 7
    REP_GOOD = 8


REQUIREMENT_NAMES = {
    RequirementType.NONE: "none",
    RequirementType.STR:  "strength",
    RequirementType.DEX:  "dexterity",
    RequirementType.CON:  "constitution",
    RequirementType.INT:  "intelligence",
    RequirementType.LVL:  "level",
    RequirementType.SKL:  "skill",
    RequirementType.REP_EVIL: "evil rep",
    RequirementType.REP_GOOD: "good rep",
}

REQUIREMENT_FAIL_MESSAGES = {
    RequirementType.STR:  "You are not strong enough to use this.",
    RequirementType.DEX:  "Your dexterity is not high enough to use this.",
    RequirementType.CON:  "Your constitution is not high enough to use this.",
    RequirementType.INT:  "Your intelligence is not high enough to use this.",
    RequirementType.LVL:  "You are not high enough level to use this.",
    RequirementType.SKL:  "You are too weak in this skill to use this.",
    RequirementType.REP_EVIL: "You are not evil enough to use this.",
    RequirementType.REP_GOOD: "Your heart is not pure enough to use this.",
}

USE_TYPE_PROMPTS = {
    UseType.NONE:   "none",
    UseType.MINE:   "Where do you wish to mine at?",
    UseType.SMELT:  "Where do you wish to smelt at?",
    UseType.FORGE:  "Choose ingots to forge.",
    UseType.BOOST:  "Select target",
    UseType.REPAIR: "What do you wish to repair?",
}

ELEMENTAL_NAMES = {
    ElementalType.NONE:      "none",
    ElementalType.FIRE:      "fire",
    ElementalType.LIGHTNING: "air",
    ElementalType.ICE:       "earth",
    ElementalType.DARK:      "water",
    ElementalType.LIGHT:     "light",
}


# ─── Item Type Definitions (loaded from JSON, replaces .dat files) ───────────

@dataclass
class AnimationData:
    """Animation info shared by all item/creature types."""
    animated: bool = False
    num_frames: int = 0
    anim_speed: int = 0
    anim_type: int = 0
    frames: list = field(default_factory=list)  # List of (x, y, w, h) rects


@dataclass
class BlacksmithingData:
    """Crafting recipe data for blacksmithing."""
    metal_type: int = 0
    amount: int = 0
    difficulty: int = 0
    requirement: int = 0


@dataclass
class WeaponInfo:
    """Weapon type definition — mirrors C++ WeaponInfo struct."""
    name: str = ""
    dam_min: int = 0
    dam_max: int = 0
    value: int = 0
    weight: int = 0
    speed: int = 0
    use_req_amount: int = 0
    use_req_type: int = 0       # RequirementType enum
    use_req_skill: int = 0
    level: int = 0
    speciality: int = 0
    speciality_amount: int = 0
    elemental_damage_type: int = 0   # ElementalType enum
    elemental_damage_min: int = 0
    elemental_damage_max: int = 0
    max_durability: int = 0
    blacksmithing: BlacksmithingData = field(default_factory=BlacksmithingData)
    animation: AnimationData = field(default_factory=AnimationData)


@dataclass
class ArmorInfo:
    """Armor type definition — mirrors C++ ArmorInfo struct."""
    name: str = ""
    ac: int = 0
    value: int = 0
    weight: int = 0
    use_req_amount: int = 0
    use_req_type: int = 0
    use_req_skill: int = 0
    level: int = 0
    speciality: int = 0
    speciality_amount: int = 0
    elemental_protection: int = 0
    elemental_protection_amount: int = 0
    max_durability: int = 0
    blacksmithing: BlacksmithingData = field(default_factory=BlacksmithingData)
    animation: AnimationData = field(default_factory=AnimationData)


@dataclass
class UseableItemInfo:
    """Useable item type definition — mirrors C++ UseableItemStruct."""
    name: str = ""
    value: int = 0
    weight: int = 0
    dam_min: int = 0
    dam_max: int = 0
    max_durability: int = 0
    use_type: int = 0           # UseType enum
    use_req_amount: int = 0
    use_req_type: int = 0
    use_req_skill: int = 0
    blacksmithing: BlacksmithingData = field(default_factory=BlacksmithingData)
    animation: AnimationData = field(default_factory=AnimationData)


@dataclass
class MiscItemInfo:
    """Collectable/misc item type definition — mirrors C++ MiscItemStruct."""
    name: str = ""
    value: int = 0
    weight: int = 0
    dam_min: int = 0
    dam_max: int = 0
    cure_type: int = 0
    max_durability: int = 0
    use_type: int = 0
    use_req_amount: int = 0
    use_req_type: int = 0
    use_req_skill: int = 0
    blacksmithing: BlacksmithingData = field(default_factory=BlacksmithingData)
    animation: AnimationData = field(default_factory=AnimationData)


# ─── Live Item Instance (runtime state) ─────────────────────────────────────

@dataclass
class ItemInstance:
    """A single live item in the world (ground, backpack, bank, worn, body).
    Mirrors C++ ItemStruct / ItemClass."""
    used: bool = False
    know_id: int = 0       # Unique runtime ID for client tracking
    item_id: int = 0       # Index into the global items array (server)
    item_type: int = 0     # Sub-type (sword=1, axe=2, ..., helm=12, ...)
    family: int = 0        # ItemFamily enum
    durability: int = 0
    x: int = 0
    y: int = 0
    quantity: int = 1


# ─── Item Database (holds all type definitions) ─────────────────────────────

# Constants matching C++ limits
M_ITEM_TYPES = 10
M_ITEMS_PER_TYPE = 200

class ItemDatabase:
    """Holds all item type definitions. In the C++ version these were loaded
    from .dat binary files. In the Python version they come from JSON."""

    def __init__(self):
        # Weapons[type_index][item_index] — e.g. Weapons[SWORD][0..199]
        self.weapons: List[List[WeaponInfo]] = [
            [WeaponInfo() for _ in range(M_ITEMS_PER_TYPE)]
            for _ in range(M_ITEM_TYPES)
        ]
        # Armors[type_index][item_index]
        self.armors: List[List[ArmorInfo]] = [
            [ArmorInfo() for _ in range(M_ITEMS_PER_TYPE)]
            for _ in range(M_ITEM_TYPES)
        ]
        # Useables[item_index]
        self.useables: List[UseableItemInfo] = [
            UseableItemInfo() for _ in range(M_ITEMS_PER_TYPE)
        ]
        # Collectables[item_index]
        self.collectables: List[MiscItemInfo] = [
            MiscItemInfo() for _ in range(M_ITEMS_PER_TYPE)
        ]

    def get_item_name(self, family: int, item_type: int, item_id: int) -> str:
        """Get the display name for an item by its family/type/id."""
        if family == ItemFamily.WEAPON:
            if 0 <= item_type < M_ITEM_TYPES and 0 <= item_id < M_ITEMS_PER_TYPE:
                return self.weapons[item_type][item_id].name
        elif family == ItemFamily.ARMOR:
            if 0 <= item_type < M_ITEM_TYPES and 0 <= item_id < M_ITEMS_PER_TYPE:
                return self.armors[item_type][item_id].name
        elif family == ItemFamily.USEABLE:
            if 0 <= item_id < M_ITEMS_PER_TYPE:
                return self.useables[item_id].name
        elif family == ItemFamily.COLLECTABLE:
            if 0 <= item_id < M_ITEMS_PER_TYPE:
                return self.collectables[item_id].name
        return "Unknown Item"

    def get_item_value(self, family: int, item_type: int, item_id: int) -> int:
        """Get the base gold value of an item."""
        if family == ItemFamily.WEAPON:
            if 0 <= item_type < M_ITEM_TYPES and 0 <= item_id < M_ITEMS_PER_TYPE:
                return self.weapons[item_type][item_id].value
        elif family == ItemFamily.ARMOR:
            if 0 <= item_type < M_ITEM_TYPES and 0 <= item_id < M_ITEMS_PER_TYPE:
                return self.armors[item_type][item_id].value
        elif family == ItemFamily.USEABLE:
            if 0 <= item_id < M_ITEMS_PER_TYPE:
                return self.useables[item_id].value
        elif family == ItemFamily.COLLECTABLE:
            if 0 <= item_id < M_ITEMS_PER_TYPE:
                return self.collectables[item_id].value
        return 0
