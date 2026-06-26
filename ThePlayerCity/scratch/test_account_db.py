# scratch/test_account_db.py
import os
import sys
import shutil

# Add root directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.database import DatabaseManager
from server.item_database import ItemDatabaseManager

def run_tests():
    # Set up temp databases for testing
    test_acc_db_path = r"e:\2DGameEditor\ThePlayerCity\test_accounts.db"
    test_item_db_path = r"e:\2DGameEditor\ThePlayerCity\test_items.db"
    
    # Clean up existing test databases if present
    if os.path.exists(test_acc_db_path):
        os.remove(test_acc_db_path)
    if os.path.exists(test_item_db_path):
        os.remove(test_item_db_path)

    # Initialize Database Managers
    db = DatabaseManager(db_path=test_acc_db_path)
    # Patch the global DB path in item_database temporarily
    import server.item_database
    server.item_database.DB_FILE = test_item_db_path
    item_db = ItemDatabaseManager(db_path=test_item_db_path)
    
    print("1. Testing account creation...")
    # Add dummy account
    acc_id = db.sqlite_db.create_account("TestUser", "Pass123")
    assert acc_id is not None, "Failed to create account"
    print(f"Account created successfully with ID: {acc_id}")
    
    print("\n2. Testing load_accounts...")
    db.load_accounts()
    assert len(db.accounts) == 1, "Failed to load accounts"
    assert db.accounts[0].data.acc_name == "TestUser", "Loaded incorrect account details"
    print("Accounts loaded successfully.")

    print("\n3. Testing character creation from Player.hry templates...")
    # Test creating a Warrior character
    success = db.create_character_from_template(
        account_name="TestUser",
        slot=0,
        name="WarriorBob",
        class_template="Plr_Male_Warrior",
        avatar=1,
        race=1
    )
    assert success, "Character creation from template failed"
    
    # Reload and assert character is loaded
    db.load_accounts()
    char = db.accounts[0].chars[0]
    assert char.used is True, "Character slot should be marked as used"
    assert char.name == "WarriorBob", "Incorrect character name"
    assert char.class_template == "Plr_Male_Warrior", "Incorrect class template stored"
    assert "#Define Plr_Male_Warrior 1" in char.hry_script, f"hry_script does not have class define prepended: {char.hry_script}"
    assert "OnOpenInventory" in char.hry_script, "hry_script does not contain template body commands"
    print(f"Character {char.name} created successfully using template {char.class_template} and script: \n{char.hry_script[:100]}...")

    print("\n4. Verifying starting inventory in SQLite items database...")
    # Check items owned by the character
    items = item_db.get_items_for_owner(owner_id=char.id, container="backpack")
    print(f"Starting items in backpack: {items}")
    assert len(items) == 2, f"Should have 2 starting items, got {len(items)}"
    
    # Assert item details
    has_dagger = any("9035" in str(item["item_type"]) for item in items)
    has_gold = any("9412" in str(item["item_type"]) for item in items)
    assert has_dagger, "Missing starting dagger"
    assert has_gold, "Missing starting gold"
    print("Starting items verified successfully.")

    # Clean up test databases by first deleting references and forcing garbage collection
    del db
    del item_db
    import gc
    gc.collect()
    
    try:
        if os.path.exists(test_acc_db_path):
            os.remove(test_acc_db_path)
        if os.path.exists(test_item_db_path):
            os.remove(test_item_db_path)
    except PermissionError:
        pass  # Suppress clean up locking issues on Windows
    print("\nAll database integration tests passed successfully!")

if __name__ == "__main__":
    run_tests()
