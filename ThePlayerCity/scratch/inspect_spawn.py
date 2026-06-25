import sqlite3, json

# What chunk is at player spawn (x=10, y=10)?
# x=10, y=10 in world tile coords => chunk_col=10//16=0, chunk_row=10//16=0
# Actually x=10, y=10 are tile coordinates. Let's check what this means.

# Chunk at grid position (0,0) 
wconn = sqlite3.connect(r'E:\2DGameEditor\Saves\ThePlayerCity\Maps\World.db')
wc = wconn.cursor()
wc.execute('SELECT chunk_id FROM world_grid WHERE map_name = ? AND x = 0 AND y = 0', ('WORLD',))
cid_at_00 = wc.fetchone()
print(f"Chunk at grid (0,0): {cid_at_00}")

# Look at a wider area around 0,0
for y in range(4):
    row = []
    for x in range(4):
        wc.execute('SELECT chunk_id FROM world_grid WHERE map_name = ? AND x = ? AND y = ?', ('WORLD', x, y))
        r = wc.fetchone()
        row.append(r[0] if r else 'N/A')
    print(f"Grid row y={y}: {row}")

wconn.close()

# Now examine a non-zero chunk to see real tile data
cconn = sqlite3.connect(r'E:\2DGameEditor\Saves\ThePlayerCity\Maps\Chunks.db')
cc = cconn.cursor()

# Look at chunk C_2 (Grass) data more carefully 
cc.execute('SELECT data FROM chunks WHERE id = ?', ('2',))
row = cc.fetchone()
d = json.loads(row[0])
print(f"\n=== Chunk C_2 (Grass) ===")
ground = d['data']['ground']
print(f"Ground grid ({len(ground)} rows x {len(ground[0])} cols):")
for i, r in enumerate(ground):
    print(f"  Row {i}: {r}")

# Also look at a more complex chunk
# Find a chunk with mixed tile IDs
cc.execute('SELECT id, data FROM chunks')
all_chunks = cc.fetchall()
for cid, cdata in all_chunks:
    cd = json.loads(cdata)
    g = cd.get('data', {}).get('ground', [])
    if g:
        unique_tiles = set()
        for r in g:
            if isinstance(r, list):
                unique_tiles.update(r)
        if len(unique_tiles) > 3:
            print(f"\n=== Complex chunk ID={cid}, name={cd.get('name','')} ===")
            print(f"  Unique tiles: {sorted(unique_tiles)[:20]}")
            for i, r in enumerate(g[:3]):
                print(f"  Ground row {i}: {r}")
            break

# Check HAIRY/Defines for map constants
import os
defines_path = r'E:\2DGameEditor\Saves\ThePlayerCity\HAIRY\Defines.hry'
if os.path.exists(defines_path):
    print(f"\n=== HAIRY/Defines.hry ===")
    with open(defines_path, 'r') as f:
        print(f.read()[:1000])

cconn.close()
