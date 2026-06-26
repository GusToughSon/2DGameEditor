"""Test tile indexing with tile_size=20 instead of 16."""
from PIL import Image

ts = Image.open(r'E:\2DGameEditor\Saves\ThePlayerCity\TILESET\World_TILESET.png').convert("RGBA")
print(f"Tileset: {ts.size}")

# Test with tile_size = 20
tile_size = 20
stride = ts.width // tile_size  # 280 / 20 = 14
print(f"With tile_size=20: stride={stride}, 14 * 20 = {14*20} px (perfect!)")
print(f"With tile_size=16: stride={ts.width//16}, 17 * 16 = {17*16} px (8px leftover!)")

# Render chunk 1598 with tile_size=20 for source lookup, but draw at 16px (game tile size)
import sqlite3, json

CHUNK_SIZE = 16
SRC_TILE_SIZE = 20  # Source tile size in tileset
DRAW_TILE_SIZE = 16 # Game tile size

conn = sqlite3.connect(r'E:\2DGameEditor\Saves\ThePlayerCity\Maps\Chunks.db')
c = conn.cursor()
c.execute('SELECT data FROM chunks WHERE id=?', ('1598',))
raw = c.fetchone()
chunk_data = json.loads(raw[0])
conn.close()

ground = chunk_data['data']['ground']

# Render with 20px source tiles
full_sz = DRAW_TILE_SIZE * CHUNK_SIZE
img = Image.new("RGBA", (full_sz, full_sz), (0, 0, 0, 255))

for r in range(CHUNK_SIZE):
    for c_idx in range(CHUNK_SIZE):
        tid = ground[r][c_idx]
        if tid > 0:
            # Source position using 20px tiles
            src_x = (tid % stride) * SRC_TILE_SIZE
            src_y = (tid // stride) * SRC_TILE_SIZE
            if src_y + SRC_TILE_SIZE <= ts.height and src_x + SRC_TILE_SIZE <= ts.width:
                tile = ts.crop((src_x, src_y, src_x + SRC_TILE_SIZE, src_y + SRC_TILE_SIZE))
                # Scale 20x20 source to 16x16 game tile
                tile_scaled = tile.resize((DRAW_TILE_SIZE, DRAW_TILE_SIZE), Image.NEAREST)
                img.paste(tile_scaled, (c_idx * DRAW_TILE_SIZE, r * DRAW_TILE_SIZE), tile_scaled)

out = r'e:\2DGameEditor\ThePlayerCity\scratch\chunk_1598_20px_4x.png'
img_big = img.resize((full_sz * 4, full_sz * 4), Image.NEAREST)
img_big.save(out)
print(f"Saved: {out}")

# Also check: what does project.json say vs what the editor really uses?
# The project says tile_size=16, but the TILESET images use 20px tiles
# This means the game renders at 16px per tile but the source art is 20px per tile
# The editor must scale the 20px source down to 16px when rendering chunks
