import csv
import os
from PIL import Image

TILE_SIZE = 16
TILESET_FILE = "tiles.png"

tileset = Image.open(TILESET_FILE)

tileset_width, tileset_height = tileset.size
tiles_per_row = tileset_width // TILE_SIZE

def build_chunk(csv_file):

    grid = []

    with open(csv_file, newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            grid.append([int(x) for x in row])

    map_h = len(grid)
    map_w = len(grid[0])

    output = Image.new("RGBA", (map_w * TILE_SIZE, map_h * TILE_SIZE))

    for y in range(map_h):
        for x in range(map_w):

            tile_id = grid[y][x]

            tile_x = (tile_id % tiles_per_row) * TILE_SIZE
            tile_y = (tile_id // tiles_per_row) * TILE_SIZE

            tile = tileset.crop((
                tile_x,
                tile_y,
                tile_x + TILE_SIZE,
                tile_y + TILE_SIZE
            ))

            output.paste(tile, (x * TILE_SIZE, y * TILE_SIZE))

    outname = csv_file.replace(".csv", ".png")
    output.save(outname)

    print("built:", outname)


for file in os.listdir("."):

    if file.lower().endswith(".csv"):
        build_chunk(file)