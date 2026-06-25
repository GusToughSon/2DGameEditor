# server/ground_items.py
from server.client_state import ClientState
from server.item_database import ItemDatabaseManager
from core.items import ItemInstance

def drop_item_to_ground(client: ClientState, item_db_id: int, x: int, y: int) -> bool:
    """Drops an item from the character's backpack onto world ground coordinates."""
    char = client.char_data
    item_db = ItemDatabaseManager()

    # Find the item in character's backpack
    slot_idx = -1
    for i, user_item in enumerate(char.backpack):
        if user_item.item_id == item_db_id:
            slot_idx = i
            break

    if slot_idx == -1:
        return False

    item_data = item_db.get_item_by_id(item_db_id) or {}

    # Remove from backpack slot
    char.backpack[slot_idx].item_id = 0

    # Update item container to 'ground' in items.db
    item_db.move_item(item_db_id, "ground", 0, new_owner_id=0, new_x=x, new_y=y)
    
    # Log SQL transaction
    item_db.log_item_transaction(
        action="drop",
        char_id=char.id,
        char_name=char.name,
        item_db_id=item_db_id,
        item_type=item_data.get("item_type", 0),
        x=x,
        y=y,
        details=f"Dropped from backpack slot {slot_idx}"
    )
    return True

def pickup_item_from_ground(client: ClientState, item_db_id: int) -> bool:
    """Picks up an item from the ground and inserts it into character's backpack."""
    char = client.char_data
    item_db = ItemDatabaseManager()

    # Check for free backpack slot
    free_slot = -1
    for i, user_item in enumerate(char.backpack):
        if user_item.item_id == 0:
            free_slot = i
            break

    if free_slot == -1:
        return False

    item_data = item_db.get_item_by_id(item_db_id)
    if not item_data or item_data.get("container") != "ground":
        return False

    # Move item to character's backpack in items.db
    item_db.move_item(item_db_id, "backpack", free_slot, new_owner_id=char.id)
    char.backpack[free_slot].item_id = item_db_id
    
    # Log SQL transaction
    item_db.log_item_transaction(
        action="pickup",
        char_id=char.id,
        char_name=char.name,
        item_db_id=item_db_id,
        item_type=item_data.get("item_type", 0),
        x=item_data.get("x", 0),
        y=item_data.get("y", 0),
        details=f"Picked up into backpack slot {free_slot}"
    )
    return True
