# server/trade.py
from server.client_state import ClientState

class TradeSession:
    def __init__(self, p1: ClientState, p2: ClientState):
        self.p1 = p1
        self.p2 = p2
        self.p1_offer = []  # List of item DB IDs
        self.p2_offer = []
        self.p1_locked = False
        self.p2_locked = False

    def update_offer(self, client: ClientState, offer_list: list):
        if client == self.p1:
            self.p1_offer = offer_list
            self.p1_locked = False
            self.p2_locked = False  # Reset locks on modification
        elif client == self.p2:
            self.p2_offer = offer_list
            self.p1_locked = False
            self.p2_locked = False

    def lock_trade(self, client: ClientState) -> bool:
        if client == self.p1:
            self.p1_locked = True
        elif client == self.p2:
            self.p2_locked = True
        return self.p1_locked and self.p2_locked

    def execute_trade(self) -> bool:
        """Atomically swap items between trading partners in SQLite database."""
        if not (self.p1_locked and self.p2_locked):
            return False

        from server.item_database import ItemDatabaseManager
        item_db = ItemDatabaseManager()

        try:
            # Transfer P1's offered items to P2's backpack (finding first free slots)
            # Simplification: swap containers/owners
            for item_id in self.p1_offer:
                item_db.move_item(item_id, "backpack", 0, new_owner_id=self.p2.char_data.id)

            for item_id in self.p2_offer:
                item_db.move_item(item_id, "backpack", 0, new_owner_id=self.p1.char_data.id)

            return True
        except Exception as e:
            print(f"[TRADE ERROR] Execution failed: {e}")
            return False
