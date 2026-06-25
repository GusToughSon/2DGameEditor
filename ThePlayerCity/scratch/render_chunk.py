"""Render chunk 1598 exactly like the WorldEditor does and save to PNG for visual comparison."""
from PIL import Image
import sqlite3, json

TILE_SIZE = 16
CHUNK_SIZE = 16

# Load tileset
ts = Image.open(r'E:\2DGameEditor\Saves\ThePlayerCity\TILESET\World_TILESET.png').convert("RGBA")
stride = ts.width // TILE_SIZE  # 17
print(f"Tileset: {ts.size}, stride={stride}")

# Load chunk 1598
conn = sqlite3.connect(r'E:\2DGameEditor\Saves\ThePlayerCity\Maps\Chunks.db')
c = conn.cursor()
c.execute('SELECT data FROM chunks WHERE id=?', ('1598',))
raw = c.fetchone()
chunk_data = json.loads(raw[0])
conn.close()

ground = chunk_data['data']['ground']
print(f"Chunk 1598 ground: {len(ground)} rows x {len(ground[0])} cols")

# Render chunk exactly as WorldEditor does
full_sz = TILE_SIZE * CHUNK_SIZE
img = Image.new("RGBA", (full_sz, full_sz), (0, 0, 0, 255))

for r in range(CHUNK_SIZE):
    for c_idx in range(CHUNK_SIZE):
        tid = ground[r][c_idx]
        if tid > 0:
            tx = (tid % stride) * TILE_SIZE
            ty = (tid // stride) * TILE_SIZE
            if ty + TILE_SIZE <= ts.height:
                tile = ts.crop((tx, ty, tx + TILE_SIZE, ty + TILE_SIZE))
                img.paste(tile, (c_idx * TILE_SIZE, r * TILE_SIZE), tile)

out_path = r'e:\Vorila\ThePlayerCity\scratch\chunk_1598_rendered.png'
img.save(out_path)
print(f"Saved: {out_path}")

# Also render scaled up 4x for easy viewing
img_big = img.resize((full_sz * 4, full_sz * 4), Image.NEAREST)
out_big = r'e:\Vorila\ThePlayerCity\scratch\chunk_1598_4x.png'
img_big.save(out_big)
print(f"Saved 4x: {out_big}")

# Now do the same but also render what my pygame renderer would produce
# Check: same logic = same result
print("\n--- Verification ---")
for tid in sorted(set(t for row in ground for t in row if t > 0)):
    col = tid % stride
    row = tid // stride
    px_x = col * TILE_SIZE
    px_y = row * TILE_SIZE
    print(f"  TID {tid}: col={col}, row={row}, px=({px_x},{px_y})")
