# models.py
from typing import List

class UserItem:
    def __init__(self, item_id: int = 0):
        self.item_id = item_id

class SkillData:
    def __init__(self, exp: int = 0, level: int = 0, bonus: int = 0):
        self.exp = exp
        self.level = level
        self.bonus = bonus

class CharacterData:
    def __init__(self):
        self.used = False
        self.wanted = False
        self.marked = False
        self.name = ""
        self.x = 0
        self.y = 0
        self.map_level = 0
        self.hp_left = 10
        self.hp_max = 10
        self.mana_left = 5
        self.char_update = 0
        self.shrine_x = 0
        self.shrine_y = 0
        self.status = [0] * 5
        self.status_mode = [0] * 5
        self.tag = ""
        self.dev_mode = 0
        self.avatar = 0
        self.reputation = 0
        self.race = 0
        self.guild = 0
        self.level = 1
        self.str = 5
        self.con = 5
        self.dex = 5
        self.int = 5
        self.cha = 5
        self.lck = 5
        self.stat_points = 15
        self.killed_monsters = 0
        self.crim_count = 0
        
        # Statistics counters
        self.overall_mon_count = 0
        self.overall_crim_count = 0
        self.overall_player_kills = 0
        self.overall_deaths_monster = 0
        self.overall_deaths_player = 0
        self.mon_count_since_death = 0
        self.exp_count_since_death = 0
        self.pk_since_death = 0

        self.backpack = [UserItem() for _ in range(100)]
        self.bank = [UserItem() for _ in range(250)]
        self.worn = [UserItem() for _ in range(20)]
        
        self.id = 0
        self.exp = 0
        self.exp_pool = 0
        
        self.skills = [SkillData() for _ in range(30)]
        self.class_template = ""
        self.hry_script = ""
        self.c_minute = 0
        self.c_hour = 0
        self.c_day = 0
        self.c_month = 0
        self.c_year = 0

class AccountData:
    def __init__(self):
        self.in_use = False
        self.is_banned = False
        self.is_premium = False
        self.is_golden = False
        self.acc_name = ""
        self.acc_pass = ""
        self.logged_in_id = -1
        self.c_minute = 0
        self.c_hour = 0
        self.c_day = 0
        self.c_month = 0
        self.c_year = 0
        self.id = 0

class Account:
    def __init__(self):
        self.data = AccountData()
        self.chars = [CharacterData(), CharacterData()]  # Two character slots supported by legacy layouts


# ─── Runtime Stat Cache ─────────────────────────────────────────────────────

class TempData:
    """Runtime stat bonuses for a connected character.
    Mirrors C++ TempData struct — recalculated when equipment changes."""
    def __init__(self):
        self.avatar = 0
        self.reputation = 0
        self.race = 0
        self.str = 0
        self.con = 0
        self.dex = 0
        self.int_ = 0
        self.status = [0] * 5
        self.status_mode = [0] * 5
        self.hp_max = 0
        self.guild = 0
        self.tag = ""
        self.prot_air = 0
        self.prot_fire = 0
        self.prot_earth = 0
        self.prot_water = 0
        self.ac = 0
        self.weight = 0
        self.weight_max = 0


# ─── Race / Avatar System ───────────────────────────────────────────────────

class AvatarInfo:
    """A single avatar appearance for a race — mirrors C++ Avatar struct."""
    def __init__(self):
        self.name = ""
        self.normal = False        # Available to normal accounts
        self.premium = False       # Available to premium accounts
        self.golden = False        # Available to golden accounts
        self.animation_type = 0
        self.num_frames = 0
        self.animation_speed = 0
        self.frames = []           # List of (x, y, w, h) frame rects

class RaceInfo:
    """Race definition — mirrors C++ RaceInfo struct."""
    def __init__(self):
        self.name = ""
        self.stat_limits = [0] * 4       # STR, CON, DEX, INT caps
        self.starting_stats = [0] * 4    # STR, CON, DEX, INT starting values
        self.skill_limits = [0] * 30     # Max skill level per skill
        self.resistance_bonus = [0] * 6  # Elemental resistance bonuses
        # Avatars[gender][variant] — 2 genders × 5 variants
        self.avatars = [[AvatarInfo() for _ in range(5)] for _ in range(2)]


# ─── Guild System ────────────────────────────────────────────────────────────

MAX_GUILDS = 1000
MAX_GUILD_MEMBERS = 50
GUILD_COST = 500000
GUILD_LEVEL_REQ = 1

class GuildMember:
    """A single guild member entry — mirrors C++ GuildMember struct."""
    def __init__(self):
        self.name = ""
        self.acc_id = 0
        self.slot = 0
        self.active = 0
        self.rank = 0

class GuildClass:
    """A guild definition — mirrors C++ GuildClass."""
    def __init__(self):
        self.name = ""
        self.tag = ""
        self.active = 0
        self.leader_acc_id = 0
        self.leader_slot = 0
        self.members = [GuildMember() for _ in range(MAX_GUILD_MEMBERS)]

    def amount_at_rank(self, rank: int) -> int:
        """Count members at a given rank."""
        return sum(1 for m in self.members if m.active and m.rank == rank)

    def promote(self, member_idx: int) -> bool:
        """Promote a member (lower rank number = higher rank)."""
        if 0 <= member_idx < MAX_GUILD_MEMBERS and self.members[member_idx].active:
            if self.members[member_idx].rank > 0:
                self.members[member_idx].rank -= 1
                return True
        return False

    def demote(self, member_idx: int) -> bool:
        """Demote a member."""
        if 0 <= member_idx < MAX_GUILD_MEMBERS and self.members[member_idx].active:
            self.members[member_idx].rank += 1
            return True
        return False


# ─── Alignment / Reputation ─────────────────────────────────────────────────

ALIGNMENT_NAMES = [
    "scourge", "evil", "hated", "disliked", "neutral",
    "liked", "good", "hero", "divine", "nothing", "normal"
]

# Reputation system constants (from Client.h)
REPU_POINTS_LIMIT   = 21000
REPU_KILL_PENALTY   = 1000
REPU_LOOT_PENALTY   = 200
CRIM_KILL_PENALTY   = 4
CRIM_LOOT_PENALTY   = 1
NEWBIE_PROTECTION_LEVEL = 10

# Stat caps
STR_MAX = 100
DEX_MAX = 100
CON_MAX = 100
INT_MAX = 100
LVL_MAX = 200
MAX_LEVEL = 205
MAX_SKILL_LEVEL = 105
MAX_SKILLS = 20


# ─── Skill Types ─────────────────────────────────────────────────────────────

class SkillType:
    NONE      = 0
    COMBAT    = 1
    DEFENDING = 2
    TRADE     = 3
    KNOWLEDGE = 4

SKILL_TYPE_NAMES = {
    SkillType.NONE:      "no type",
    SkillType.COMBAT:    "Combat",
    SkillType.DEFENDING: "Defending",
    SkillType.TRADE:     "Trade",
    SkillType.KNOWLEDGE: "Knowledge",
}

class SkillInfo:
    """Skill definition — mirrors C++ skillinfo struct."""
    def __init__(self, name: str = "", skill_type: int = 0, used: bool = False):
        self.used = used
        self.name = name
        self.skill_type = skill_type


# ─── NPC Conversations ──────────────────────────────────────────────────────

NPC_CONVERSATIONS = [
    "Obey the law of the land!",
    "Welcome to my shop, adventurer!",
    "Welcome to bank!",
    "Hello.",
    "Mrrr...",
    "Covad ownz definitely.",
    "Good day adventurer!",
    "My shop isn't open yet.. Maybe it'll be someday.",
    "Grr.. Go away.",
    "Hahaha, you are a n00b.",
]
