import sqlite3, json

# Inspect Chunks.db structure
conn = sqlite3.connect(r'E:\2DGameEditor\Saves\ThePlayerCity\Maps\Chunks.db')
c = conn.cursor()
c.execute('SELECT id, data FROM chunks LIMIT 5')
rows = c.fetchall()

for r in rows:
    d = json.loads(r[1])
    cid = r[0]
    if isinstance(d, dict):
        print(f"=== Chunk ID: {cid} ===")
        print(f"  Top-level keys: {list(d.keys())}")
        print(f"  Name: {d.get('name', 'N/A')}")
        data = d.get('data', {})
        if isinstance(data, dict):
            print(f"  Data keys: {list(data.keys())}")
            for layer_name in ['ground', 'objects']:
                layer = data.get(layer_name)
                if layer:
                    print(f"  Layer '{layer_name}' type: {type(layer).__name__}")
                    if isinstance(layer, dict):
                        keys = list(layer.keys())[:3]
                        print(f"    Sample row keys: {keys}")
                        for k in keys:
                            row = layer[k]
                            if isinstance(row, dict):
                                rkeys = list(row.keys())[:5]
                                vals = [row[rk] for rk in rkeys]
                                print(f"    Row {k}: dict, keys={rkeys}, vals={vals}")
                            elif isinstance(row, list):
                                print(f"    Row {k}: list, len={len(row)}, sample={row[:5]}")
                    elif isinstance(layer, list):
                        print(f"    Rows: {len(layer)}")
                        if layer:
                            r0 = layer[0]
                            print(f"    Row[0] type: {type(r0).__name__}, len={len(r0) if hasattr(r0,'__len__') else 'N/A'}")
                            if isinstance(r0, list):
                                print(f"    Row[0] sample: {r0[:8]}")
        elif isinstance(data, list):
            print(f"  Data is a list with {len(data)} rows")
    print()

# Also inspect World.db
print("="*60)
print("WORLD.DB INSPECTION")
print("="*60)
wconn = sqlite3.connect(r'E:\2DGameEditor\Saves\ThePlayerCity\Maps\World.db')
wc = wconn.cursor()
wc.execute('SELECT x, y, chunk_id FROM world_grid WHERE map_name = ? LIMIT 30', ('WORLD',))
wrows = wc.fetchall()
print(f"Sample world grid entries (x, y, chunk_id):")
for wr in wrows:
    print(f"  x={wr[0]}, y={wr[1]}, chunk_id={wr[2]}")

# Grid dimensions
wc.execute('SELECT MAX(x), MAX(y) FROM world_grid WHERE map_name = ?', ('WORLD',))
mx, my = wc.fetchone()
print(f"\nGrid dimensions: max_x={mx}, max_y={my} -> {mx+1}x{my+1} grid")

# Count non-zero chunks
wc.execute("SELECT COUNT(*) FROM world_grid WHERE map_name = ? AND chunk_id != '0' AND chunk_id != 'C_0'", ('WORLD',))
nz = wc.fetchone()[0]
print(f"Non-zero chunk entries: {nz}")

wconn.close()
conn.close()
