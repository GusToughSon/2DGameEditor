# server/items.py
from server.client_state import ClientState
from server.item_database import ItemDatabaseManager
from core.items import ItemList

def execute_move_item(client: ClientState, from_list: int, to_list: int, from_slot: int, to_slot: int, amount: int) -> bool:
    """Handles logic to move, stack, or swap items between lists.
    Lists follow the core/items.py ItemList enum:
    1 = BACKPACK, 2 = BANK, 3 = WORN, 4 = GROUND
    """
    char = client.char_data
    item_db = ItemDatabaseManager()

    # Determine lists
    def get_list_ref(lst_type: int):
        if lst_type == ItemList.BACKPACK:
            return char.backpack, "backpack"
        elif lst_type == ItemList.BANK:
            return char.bank, "bank"
        elif lst_type == ItemList.WORN:
            return char.worn, "worn"
        return None, None

    src_list, src_name = get_list_ref(from_list)
    dst_list, dst_name = get_list_ref(to_list)

    if src_list is None or dst_list is None:
        return False

    if not (0 <= from_slot < len(src_list)) or not (0 <= to_slot < len(dst_list)):
        return False

    src_db_id = src_list[from_slot].item_id
    if src_db_id == 0:
        return False

    # Fetch item metadata
    item_data = item_db.get_item_by_id(src_db_id)
    if not item_data:
        return False

    dst_db_id = dst_list[to_slot].item_id

    # Case 1: Target slot is empty
    if dst_db_id == 0:
        # Update references
        src_list[from_slot].item_id = 0
        dst_list[to_slot].item_id = src_db_id
        
        # Update SQL database
        item_db.move_item(src_db_id, dst_name, to_slot)
        return True

    # Case 2: Target slot is occupied
    else:
        # Swap items
        src_list[from_slot].item_id = dst_db_id
        dst_list[to_slot].item_id = src_db_id

        # Update SQL database for both
        item_db.move_item(src_db_id, dst_name, to_slot)
        item_db.move_item(dst_db_id, src_name, from_slot)
        return True
