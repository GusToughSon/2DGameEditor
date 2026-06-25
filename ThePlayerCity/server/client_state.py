# server/client_state.py
import time
from core.models import Account, CharacterData, TempData

class ClientState:
    """Tracks active client session state on the server.
    Mirrors the C++ ClientClass variables and tracks what the client currently knows
    about surrounding entities to optimize network traffic.
    """
    def __init__(self, reader, writer, account: Account, char_slot: int):
        self.reader = reader
        self.writer = writer
        self.account = account
        self.char_slot = char_slot
        self.char_data: CharacterData = account.chars[char_slot]
        self.temp_data = TempData()

        # Initialize known entities sets (instead of fixed-size boolean arrays)
        self.know_players = set()    # Set of character IDs/names known
        self.know_monsters = set()   # Set of monster know_ids known
        self.know_npcs = set()       # Set of NPC ids known
        self.know_items = set()      # Set of item know_ids known
        self.know_bodies = set()     # Set of body ids known

        # Time trackers (milliseconds)
        self.last_msg = time.time()
        self.last_move = time.time()
        self.last_attack = time.time()
        self.last_regen = time.time()
        self.last_tradeskill = time.time()
        self.last_jail_time = 0
        self.crim_timer = 0

        # Status states
        self.is_logging = False
        self.is_mute = False
        self.tradeskill_inuse = False
        self.trade_in_progress = False
        self.gm_mode = False
        self.is_in_jail = False
        self.browsing_shop = -1
        self.browsing_bank = -1

        # Combat Target
        self.pl_target = -1
        self.mon_target = None
        self.npc_target = None
        self.attack_target = -1

        # Initial stat calculation
        self.recalculate_temp_stats()

    def recalculate_temp_stats(self):
        """Recalculate runtime stats based on base character attributes and equipment.
        Mirrors C++ CheckStats / CheckStats_base logic.
        """
        # Copy base attributes
        self.temp_data.avatar = self.char_data.avatar
        self.temp_data.reputation = self.char_data.reputation
        self.temp_data.race = self.char_data.race
        self.temp_data.str = self.char_data.str
        self.temp_data.con = self.char_data.con
        self.temp_data.dex = self.char_data.dex
        self.temp_data.int_ = self.char_data.int
        self.temp_data.guild = self.char_data.guild
        self.temp_data.tag = self.char_data.tag

        # Base maximum HP: based on level and constitution
        self.temp_data.hp_max = self.char_data.level * 10 + self.temp_data.con * 5

        # Initialise defenses/AC
        self.temp_data.ac = 0
        self.temp_data.prot_fire = 0
        self.temp_data.prot_air = 0
        self.temp_data.prot_earth = 0
        self.temp_data.prot_water = 0

        # Adjust maximum weight
        self.temp_data.weight_max = 50 + self.temp_data.str * 4

        # Recalculate current weight based on worn/backpack inventory
        self.temp_data.weight = 0

    def send_packet(self, packet_dict: dict):
        """Helper to send a JSON packet to the client."""
        try:
            from core.packets import pack_json
            payload = pack_json(packet_dict)
            self.writer.write(payload)
        except Exception as e:
            print(f"[CLIENT STATE] Failed to send packet to {self.char_data.name}: {e}")
