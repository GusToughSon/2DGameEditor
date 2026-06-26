# scratch/test_item_db_crud.py
import os
import sys

# Add root directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.items import ItemInstance, ItemFamily
from server.item_database import ItemDatabaseManager

def test_db():
    db_path = r"e:\2DGameEditor\ThePlayerCity\scratch\test_items.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        
    print(f"Initializing database at: {db_path}")
    manager = ItemDatabaseManager(db_path)
    
    # 1. Create a dummy ItemInstance
    item = ItemInstance(
        used=True,
        know_id=101,
        item_id=12,
        item_type=2, # AXE
        family=int(ItemFamily.WEAPON),
        durability=85,
        x=0,
        y=0,
        quantity=1
    )
    
    # 2. Add item to backpack of player 42 at slot 3
    print("\nAdding item to database...")
    db_id = manager.add_item(item, owner_id=42, container="backpack", slot=3)
    print(f"Item added with database ID: {db_id}")
    assert db_id == 1, "First item should have ID 1"
    
    # 3. Retrieve item and verify
    print("\nRetrieving item by ID...")
    fetched = manager.get_item_by_id(db_id)
    print(f"Fetched: {fetched}")
    assert fetched["know_id"] == 101
    assert fetched["durability"] == 85
    assert fetched["container"] == "backpack"
    assert fetched["slot"] == 3
    
    # 4. Move item to ground at coordinates (15, 25)
    print("\nMoving item to ground...")
    manager.move_item(db_id, new_container="ground", new_slot=0, new_owner_id=0, new_x=15, new_y=25)
    
    # 5. Fetch ground items
    print("\nFetching ground items...")
    ground_items = manager.get_ground_items()
    print(f"Ground items: {ground_items}")
    assert len(ground_items) == 1
    assert ground_items[0]["id"] == db_id
    assert ground_items[0]["x"] == 15
    assert ground_items[0]["y"] == 25
    assert ground_items[0]["container"] == "ground"
    
    # 6. Delete item
    print("\nDeleting item...")
    manager.delete_item(db_id)
    fetched_after = manager.get_item_by_id(db_id)
    assert fetched_after is None, "Item should be deleted"
    
    print("\nAll Item Database CRUD tests passed successfully!")
    
    # Clean up test DB
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except PermissionError:
        pass

if __name__ == "__main__":
    test_db()
