import json

path = r"e:\2DGameEditor\Saves\ThePlayerCity\WorldProperties.json"
with open(path, "r") as f:
    data = json.load(f)

# Search for 1858 in data
for ts_name, ts_data in data.items():
    for coord, info in ts_data.items():
        if "1858" in coord or info.get("name", "") == "1858":
            print(f"Found in {ts_name} {coord}: {info}")
            
# Let's search Tiles.hry for 1858
tiles_hry_path = r"e:\2DGameEditor\Saves\ThePlayerCity\HAIRY\Tiles.hry"
with open(tiles_hry_path, "r") as f:
    for line in f:
        if "1858" in line:
            print("Tiles.hry:", line.strip())
