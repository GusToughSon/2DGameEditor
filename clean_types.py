import os
import json
import collections

PROJECT_PATH = r"e:\2DGameEditor\Saves\MyNewProject"
TYPES_JSON_PATH = os.path.join(PROJECT_PATH, "Types.json")

def clean_database():
    print("=== DATABASE CLEANING & STANDARDIZATION ===")
    
    if not os.path.exists(TYPES_JSON_PATH):
        print("Types.json not found!")
        return

    with open(TYPES_JSON_PATH, 'r') as f:
        data = json.load(f)

    # 1. Strip unwanted fields and normalize
    cleaned_items = []
    for tid, item in data.items():
        # Preserve Name and Family
        name = item.get("name", "Unnamed") or "Unnamed"
        family = item.get("family", "FAM_OBJ") or "FAM_OBJ"
        
        # Standardize Family Names (FAM_ prefix should be consistent if present)
        if family.lower() in ["object", "objects"]: family = "FAM_OBJ"
        
        cleaned_item = {
            "id": tid,
            "name": name,
            "family": family,
            "tileset": item.get("tileset", "World"), # Keep tileset but it might default to World
            # We REMOVE tile_coords and solid as requested
        }
        cleaned_items.append(cleaned_item)

    # 2. Sort by Name (Case-Insensitive)
    sorted_items = sorted(cleaned_items, key=lambda x: x["name"].lower())

    # 3. Rebuild Dictionary (using numeric IDs as keys)
    final_output = collections.OrderedDict()
    print(f"\n[SUMMARY] Processing {len(sorted_items)} entries...")
    
    print(f"{'ID':<6} | {'NAME':<40} | {'FAMILY':<20}")
    print("-" * 75)
    
    for item in sorted_items:
        tid = item.pop("id")
        final_output[tid] = item
        # Print first 20 for validation
        if len(final_output) <= 50:
             print(f"{tid:<6} | {item['name']:<40} | {item['family']:<20}")
    
    if len(final_output) > 50:
        print(f"... and {len(final_output) - 50} more items.")

    # 4. Save to disk
    with open(TYPES_JSON_PATH, 'w') as f:
        json.dump(final_output, f, indent=4)

    print("\n[SUCCESS] Types.json cleaned, sorted, and fields stripped.")

if __name__ == "__main__":
    clean_database()
