import os
import sys
import json
import re

# Add current dir to path
sys.path.append(os.getcwd())

import ScriptParser

project_path = r"e:\2DGameEditor\Saves\MyNewProject"
props_path = os.path.join(project_path, "WorldProperties.json")

print(f"Migration started for {project_path}")

if os.path.exists(props_path):
    with open(props_path, 'r', encoding='utf-8') as f:
        props = json.load(f)
    print(f"Loaded {len(props)} tilesets from JSON.")
    
    # Force Sync
    ScriptParser.register_tile_define(project_path, props)
    print("register_tile_define called.")
    
    tiles_path = os.path.join(project_path, "HAIRY", "Tiles.hry")
    if os.path.exists(tiles_path):
        print(f"Success! Tiles.hry exists with size {os.path.getsize(tiles_path)}")
    else:
        print("Error: Tiles.hry was NOT created.")
else:
    print("Error: WorldProperties.json not found.")
