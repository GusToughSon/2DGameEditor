import sqlite3, json

# Check what chunks are near the spawn (10,10)
# Player at tile (10,10) => chunk (0,0) => grid[0][0]
# With 19x18 viewport centered on player:
#   tiles shown: x from 10-9=1 to 10+9=19, y from 10-9=1 to 10+8=18
#   chunks involved: (0,0) to (1,1)

wconn = sqlite3.connect(r'E:\2DGameEditor\Saves\ThePlayerCity\Maps\World.db')
wc = wconn.cursor()
cconn = sqlite3.connect(r'E:\2DGameEditor\Saves\ThePlayerCity\Maps\Chunks.db')
cc = cconn.cursor()

print("=== Chunks near spawn ===")
for y in range(3):
    for x in range(3):
        wc.execute('SELECT chunk_id FROM world_grid WHERE map_name=? AND x=? AND y=?', ('WORLD', x, y))
        r = wc.fetchone()
        cid = r[0] if r else '?'
        # Normalize
        raw_cid = str(cid)
        if raw_cid.startswith("C_"):
            db_id = raw_cid[2:]
        else:
            db_id = raw_cid
        cc.execute('SELECT data FROM chunks WHERE id=?', (db_id,))
        cr = cc.fetchone()
        if cr:
            d = json.loads(cr[0])
            name = d.get('name', '?')
            ground = d.get('data', {}).get('ground', [])
            # Get unique tiles in ground layer
            unique = set()
            for row in ground:
                if isinstance(row, list):
                    unique.update(row)
            print(f"  Grid({x},{y}): cid={cid} (db={db_id}), name='{name}', unique_tiles={sorted(unique)[:10]}")
        else:
            print(f"  Grid({x},{y}): cid={cid} (db={db_id}), NOT FOUND IN CHUNKS.DB!")

# Now check: can the renderer actually look up C_1598?
# The load_chunks normalizes to C_# format
# World grid normalizes to C_# format
# So C_1598 from world.db stays as C_1598
# And chunk 1598 from chunks.db becomes C_1598
# These should match

print("\n=== Chunk ID format check ===")
# Check what IDs are in chunks.db
cc.execute('SELECT id FROM chunks WHERE id LIKE ?', ('%1598%',))
results = cc.fetchall()
print(f"Chunks.db entries matching '1598': {[r[0] for r in results]}")

# Check what IDs are in world.db
wc.execute('SELECT chunk_id FROM world_grid WHERE chunk_id LIKE ?', ('%1598%',))
results = wc.fetchall()
print(f"World.db entries matching '1598': {[r[0] for r in results][:5]}")

wconn.close()
cconn.close()
