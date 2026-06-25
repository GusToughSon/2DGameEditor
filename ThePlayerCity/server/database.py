# server/database.py
import os
from typing import List
from core.models import Account, AccountData, CharacterData, SkillData, UserItem
from server.account_database import AccountDatabaseManager

class DatabaseManager:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "accounts.db")
        self.sqlite_db = AccountDatabaseManager(db_path)
        self.accounts: List[Account] = []
        self.last_used_id = 0

    def load_accounts(self) -> bool:
        """Load accounts and characters from the SQLite database into Account objects."""
        try:
            self.accounts = []
            all_accs = self.sqlite_db.get_all_accounts()
            for acc_row in all_accs:
                acc = Account()
                acc.data.id = acc_row["id"]
                acc.data.acc_name = acc_row["acc_name"]
                acc.data.acc_pass = acc_row["acc_pass"]
                acc.data.is_banned = acc_row["is_banned"]
                acc.data.is_premium = acc_row["is_premium"]
                acc.data.is_golden = acc_row["is_golden"]
                acc.data.c_minute = acc_row["c_minute"]
                acc.data.c_hour = acc_row["c_hour"]
                acc.data.c_day = acc_row["c_day"]
                acc.data.c_month = acc_row["c_month"]
                acc.data.c_year = acc_row["c_year"]

                if acc.data.id > self.last_used_id:
                    self.last_used_id = acc.data.id

                # Load characters
                char_rows = self.sqlite_db.get_characters_by_account(acc.data.id)
                for char_row in char_rows:
                    slot = char_row["slot"]
                    if 0 <= slot < 2:
                        c = acc.chars[slot]
                        c.id = char_row["id"]
                        c.used = char_row["used"]
                        c.name = char_row["name"] or ""
                        c.wanted = char_row["wanted"]
                        c.marked = char_row["marked"]
                        c.x = char_row["x"]
                        c.y = char_row["y"]
                        c.map_level = char_row["map_level"]
                        c.hp_left = char_row["hp_left"]
                        c.hp_max = char_row["hp_max"]
                        c.mana_left = char_row["mana_left"]
                        c.char_update = char_row["char_update"]
                        c.shrine_x = char_row["shrine_x"]
                        c.shrine_y = char_row["shrine_y"]
                        c.status = char_row["status"]
                        c.status_mode = char_row["status_mode"]
                        c.tag = char_row["tag"] or ""
                        c.dev_mode = char_row["dev_mode"]
                        c.avatar = char_row["avatar"]
                        c.reputation = char_row["reputation"]
                        c.race = char_row["race"]
                        c.guild = char_row["guild"]
                        c.level = char_row["level"]
                        c.str = char_row["str"]
                        c.con = char_row["con"]
                        c.dex = char_row["dex"]
                        c.int = char_row["int"]
                        c.cha = char_row["cha"]
                        c.lck = char_row["lck"]
                        c.stat_points = char_row["stat_points"]
                        c.killed_monsters = char_row["killed_monsters"]
                        c.crim_count = char_row["crim_count"]
                        c.overall_mon_count = char_row["overall_mon_count"]
                        c.overall_crim_count = char_row["overall_crim_count"]
                        c.overall_player_kills = char_row["overall_player_kills"]
                        c.overall_deaths_monster = char_row["overall_deaths_monster"]
                        c.overall_deaths_player = char_row["overall_deaths_player"]
                        c.mon_count_since_death = char_row["mon_count_since_death"]
                        c.exp_count_since_death = char_row["exp_count_since_death"]
                        c.pk_since_death = char_row["pk_since_death"]
                        c.exp = char_row["exp"]
                        c.exp_pool = char_row["exp_pool"]
                        c.class_template = char_row["class_template"] or ""
                        c.hry_script = char_row.get("hry_script", "")
                        c.c_minute = char_row["c_minute"]
                        c.c_hour = char_row["c_hour"]
                        c.c_day = char_row["c_day"]
                        c.c_month = char_row["c_month"]
                        c.c_year = char_row["c_year"]

                        # Map skills list
                        db_skills = char_row["skills"]
                        for idx, s_data in enumerate(db_skills):
                            if idx < len(c.skills):
                                c.skills[idx].exp = s_data.get("exp", 0)
                                c.skills[idx].level = s_data.get("level", 1)
                                c.skills[idx].bonus = s_data.get("bonus", 0)

                        # Map items lists from items.db
                        from server.item_database import ItemDatabaseManager
                        item_db = ItemDatabaseManager()
                        db_items = item_db.get_items_for_owner(c.id)
                        for item in db_items:
                            container = item.get("container")
                            slot = item.get("slot", 0)
                            db_id = item.get("id", 0)
                            if container == "backpack" and 0 <= slot < len(c.backpack):
                                c.backpack[slot].item_id = db_id
                            elif container == "bank" and 0 <= slot < len(c.bank):
                                c.bank[slot].item_id = db_id
                            elif container == "worn" and 0 <= slot < len(c.worn):
                                c.worn[slot].item_id = db_id
                
                self.accounts.append(acc)
            return True
        except Exception as e:
            print(f"Error loading SQLite database: {e}")
            return False

    def save_accounts(self) -> bool:
        """Save the in-memory accounts list back into the SQLite database."""
        try:
            for acc in self.accounts:
                # 1. Upsert account row
                existing = self.sqlite_db.get_account_by_name(acc.data.acc_name)
                if not existing:
                    # Create account
                    acc_id = self.sqlite_db.create_account(acc.data.acc_name, acc.data.acc_pass)
                    acc.data.id = acc_id
                else:
                    acc_id = existing["id"]
                    acc.data.id = acc_id
                    # Update credentials / status
                    self.sqlite_db.update_account(acc_id, acc.data.is_banned, acc.data.is_premium, acc.data.is_golden)

                # 2. Upsert character rows
                existing_chars = self.sqlite_db.get_characters_by_account(acc_id)
                char_by_slot = {ec["slot"]: ec for ec in existing_chars}
                
                for slot_idx, c in enumerate(acc.chars):
                    if slot_idx in char_by_slot:
                        # Update existing
                        char_db_id = char_by_slot[slot_idx]["id"]
                        c.id = char_db_id
                        self.sqlite_db.update_character(char_db_id, c)
                    else:
                        # Create new character in that slot
                        if c.used:
                            char_db_id = self.sqlite_db.create_character(
                                account_id=acc_id,
                                slot=slot_idx,
                                name=c.name,
                                class_template=c.class_template,
                                avatar=c.avatar,
                                race=c.race,
                                hry_script=c.hry_script
                            )
                            c.id = char_db_id
                            self.sqlite_db.update_character(char_db_id, c)
            return True
        except Exception as e:
            print(f"Error saving SQLite database: {e}")
            return False

    def create_character_from_template(self, account_name: str, slot: int, name: str, class_template: str, avatar: int, race: int) -> bool:
        """Create a new character under an account using starting parameters and kit from Player.hry."""
        # Find account
        acc_row = self.sqlite_db.get_account_by_name(account_name)
        if not acc_row:
            print(f"Account {account_name} not found.")
            return False
        
        # Validate name
        name_clean = name.strip()
        if len(name_clean) < 3 or len(name_clean) > 16 or not name_clean.isalnum():
            print(f"Invalid character name: '{name_clean}'")
            return False

        existing = self.sqlite_db.get_character_by_name(name_clean)
        if existing:
            print(f"Character name already exists: '{name_clean}'")
            return False

        acc_id = acc_row["id"]
        
        editor_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        hairy_dir = os.path.join(editor_dir, "HAIRY")
        from core.config import GameConfig, HryParser
        config = GameConfig(hairy_dir)
        config.load_all()
        
        player_hry = config.hry_data.get("Player.hry", {})
        objects = player_hry.get("objects", {})
        
        body = objects.get(class_template, "")
        
        hry_script = f"#Define {class_template} 1\n\n{body}"
        
        # Create character in SQLite
        char_id = self.sqlite_db.create_character(
            account_id=acc_id,
            slot=slot,
            name=name,
            class_template=class_template,
            avatar=avatar,
            race=race,
            hry_script=hry_script
        )
        
        if not char_id:
            return False
            
        self.log_action(char_id, name, "create_character", f"Created character slot {slot} class {class_template}")
            
        # Parse starting items from the template body
        starting_items = HryParser.get_starting_items_from_body(body)
        
        from server.item_database import ItemDatabaseManager
        from core.items import ItemInstance, ItemFamily
        item_db = ItemDatabaseManager()
        
        slot_idx = 0
        for item_str in starting_items:
            # Create starting item instance
            item = ItemInstance(used=True)
            if "DAGGER" in item_str.upper():
                item.family = ItemFamily.WEAPON
                item.item_type = 9035  # TYPE_FAM_WEAPON_DAGGER
                item.durability = 100
                item.quantity = 1
            elif "GOLD" in item_str.upper():
                item.family = ItemFamily.COLLECTABLE
                item.item_type = 9412  # TYPE_FAM_ARMOR_BAG_OF_GOLD
                item.quantity = 100
            else:
                item.family = ItemFamily.NONE
                item.item_type = 0
                item.quantity = 1
                
            item_db.add_item(item, owner_id=char_id, container="backpack", slot=slot_idx)
            slot_idx += 1
            
        # Reload accounts into memory so they are updated
        self.load_accounts()
        return True

    def log_kill(self, killer_id: int, killer_name: str, killer_type: str, victim_id: int, victim_name: str, victim_type: str, x: int, y: int, map_level: int = 0):
        self.sqlite_db.log_kill(killer_id, killer_name, killer_type, victim_id, victim_name, victim_type, x, y, map_level)

    def log_spawn(self, entity_type: str, entity_id: int, entity_name: str, x: int, y: int, map_level: int = 0, details: str = ""):
        self.sqlite_db.log_spawn(entity_type, entity_id, entity_name, x, y, map_level, details)

    def log_action(self, char_id: int, char_name: str, action_type: str, details: str = ""):
        self.sqlite_db.log_action(char_id, char_name, action_type, details)


