from PIL import Image, ImageDraw, ImageFont
import math, os

tileset_path = "tiles.png"
out_path = "tile_id_map.png"

TILE_SIZE = 16
SCALE = 3          # make it easier to read
LABEL_H = 14       # extra space under each tile for tile id text
PADDING = 2

if not os.path.exists(tileset_path):
    # Try looking in default project folders if running inside editor structure
    default_world_tileset = r"../Saves/ThePlayerCity/TILESET/World_TILESET.png"
    if os.path.exists(default_world_tileset):
        tileset_path = default_world_tileset
        print(f"tiles.png not found, defaulting to project tileset: {tileset_path}")
    else:
        print(f"Error: {tileset_path} not found.")
        exit(1)

tileset = Image.open(tileset_path).convert("RGBA")
w, h = tileset.size
tiles_x = w // TILE_SIZE
tiles_y = h // TILE_SIZE
total_tiles = tiles_x * tiles_y

cell_w = TILE_SIZE * SCALE
cell_h = TILE_SIZE * SCALE + LABEL_H

sheet = Image.new("RGBA", (tiles_x * cell_w, tiles_y * cell_h), (255, 255, 255, 255))
draw = ImageDraw.Draw(sheet)
font = ImageFont.load_default()

for ty in range(tiles_y):
    for tx in range(tiles_x):
        tile_id = ty * tiles_x + tx
        left = tx * cell_w
        top = ty * cell_h
        
        tile = tileset.crop((tx * TILE_SIZE, ty * TILE_SIZE, (tx + 1) * TILE_SIZE, (ty + 1) * TILE_SIZE))
        tile = tile.resize((TILE_SIZE * SCALE, TILE_SIZE * SCALE), Image.NEAREST)
        sheet.paste(tile, (left, top), tile)
        
        # border around tile
        draw.rectangle(
            [left, top, left + TILE_SIZE * SCALE - 1, top + TILE_SIZE * SCALE - 1],
            outline=(0, 0, 0, 255),
            width=1
        )
        
        label = str(tile_id)
        bbox = draw.textbbox((0, 0), label, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        text_x = left + max(0, (cell_w - tw) // 2)
        text_y = top + TILE_SIZE * SCALE + max(0, (LABEL_H - th) // 2) - 1
        
        # white backing for readability
        draw.rectangle([left, top + TILE_SIZE * SCALE, left + cell_w - 1, top + cell_h - 1], fill=(255, 255, 255, 255))
        draw.text((text_x, text_y), label, fill=(0, 0, 0, 255), font=font)

sheet.save(out_path)
print(f"Saved {out_path} with {tiles_x}x{tiles_y} tiles ({total_tiles} total).")
