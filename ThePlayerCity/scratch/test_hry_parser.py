# scratch/test_hry_parser.py
import os
import sys

# Add root directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import HryParser, GameConfig

def test_parser():
    hairy_dir = r"E:\2DGameEditor\Saves\ThePlayerCity\HAIRY"
    print(f"Testing HAIRY directory: {hairy_dir}")
    
    # 1. Test individual parse of Shops.hry
    shops_file = os.path.join(hairy_dir, "Shops.hry")
    print(f"\nParsing: {shops_file}")
    parsed_shops = HryParser.parse(shops_file)
    print("Parsed Shops Output:")
    print(parsed_shops.get("shops"))
    assert "Blacksmith" in parsed_shops["shops"], "Should parse Blacksmith shop"
    assert len(parsed_shops["shops"]["Blacksmith"]) == 3, "Blacksmith shop should have 3 items"
    
    # 2. Test GameConfig loading
    config = GameConfig(hairy_dir)
    config.load_all()
    
    # Check monsters
    monsters = config.get_monster_types()
    print(f"\nTotal monster types loaded: {len(monsters)}")
    if "Abberation" in monsters:
        print("Abberation config:")
        print(monsters["Abberation"])
        assert monsters["Abberation"]["hp_max"] == 2225
        assert monsters["Abberation"]["level"] == 75
        assert monsters["Abberation"]["graphic"] == [880, 64]
        
    # Check weapons
    weapons = config.get_weapon_types()
    print(f"\nTotal weapon types loaded: {len(weapons)}")
    if "1_Axe" in weapons:
        print("1_Axe config:")
        print(weapons["1_Axe"])
        assert weapons["1_Axe"]["dam_min"] == 13
        assert weapons["1_Axe"]["dam_max"] == 37
        
    # Check shops
    shops = config.get_shops()
    print(f"\nTotal shops loaded: {len(shops)}")
    print("Shops:")
    for shop_name, items in shops.items():
        print(f"  Shop '{shop_name}': {items}")
        
    print("\nAll HryParser tests passed successfully!")

if __name__ == "__main__":
    test_parser()
