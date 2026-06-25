# scratch/test_map_db.py
import sys
import os

# Add root folder to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.maps import MapDatabase, ObjectType, MapObject

def test_map():
    print("Initializing MapDatabase...")
    db = MapDatabase()
    db.load()
    
    print("\n--- Map Metadata ---")
    print(f"Grid size: {len(db.grid)}x{len(db.grid[0]) if db.grid else 0} chunks")
    print(f"Loaded Chunks: {len(db.chunks)}")
    print(f"Loaded Properties: {len(db.properties)}")
    print(f"Loaded Types: {len(db.types)}")
    
    # 1. Test SafeZones configuration initialization
    print("\n--- Testing Safe Zones ---")
    print(f"SafeZones grid shape: {len(db.safe_zones)}x{len(db.safe_zones[0]) if db.safe_zones else 0}")
    # Let's set chunk (0,0) as a safe zone (type 1) and test
    db.safe_zones[0][0] = 1
    sz_type = db.is_safe_zone(5, 5) # tile (5,5) falls inside chunk (0,0)
    print(f"Safe zone type at tile (5,5): {sz_type}")
    assert sz_type == 1, "Should be inside safe zone chunk (0,0)"
    
    # 2. Test MapObject visibility blocking
    print("\n--- Testing Map Objects & Visibility Blocking ---")
    # Register an ObjectType with block_light / vis_block enabled
    db.object_types[15] = ObjectType(name="Stone Wall", block=True, vis_block=True)
    # Add a MapObject at (10, 12)
    db.map_objects.append(MapObject(x=10, y=12, type_id=15, on=True))
    
    # Check if visibility blocking works at (10, 12)
    is_blocked = db.is_visibility_blocking(10, 12)
    print(f"Is tile (10, 12) blocking visibility by default? {is_blocked}")
    
    # 3. Test Line of Sight calculations
    print("\n--- Testing Local Line of Sight viewport (21x21) ---")
    # Calculate visibility from (10, 10)
    vis_matrix = db.calculate_local_los(10, 10)
    print("Visibility around player (10,10):")
    # Print a small section of the grid to verify the center is visible (type 4/5) and the wall (10,12) is mapped
    for y in range(8, 14):
        row_str = " ".join(str(vis_matrix[y][x]) for x in range(8, 14))
        print(f"  Row y={y-10:2d}: {row_str}")
        
    # The player tile at (10,10) (which is matrix index 10,10) should be fully visible (5)
    assert vis_matrix[10][10] == 5, "Player's own tile must be fully visible"
    
    # 4. Try querying some coords
    print("\n--- Querying Tile Coordinates ---")
    test_coords = [(300, 300), (0, 0), (10, 10)]
    for wx, wy in test_coords:
        g_id = db.get_tile_at(wx, wy, 0)
        o_id = db.get_tile_at(wx, wy, 1)
        passable = db.is_passable(wx, wy)
        print(f"Coords ({wx}, {wy}) -> Ground ID: {g_id}, Object ID: {o_id}, Passable: {passable}")

    print("\nAll map tests completed successfully!")

if __name__ == "__main__":
    test_map()
