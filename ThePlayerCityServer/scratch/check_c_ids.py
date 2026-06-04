import sqlite3

world_db = r'c:\Users\gooro\OneDrive\Desktop\Test idea\LoadFolder\ThePlayerCity\Maps\World.db'
chunks_db = r'c:\Users\gooro\OneDrive\Desktop\Test idea\LoadFolder\ThePlayerCity\Maps\Chunks.db'

w_conn = sqlite3.connect(world_db)
w_cursor = w_conn.cursor()
w_cursor.execute("SELECT DISTINCT chunk_id FROM world_grid")
w_ids = [str(row[0]) for row in w_cursor.fetchall()]
w_conn.close()

c_conn = sqlite3.connect(chunks_db)
c_cursor = c_conn.cursor()
c_cursor.execute("SELECT id FROM chunks")
c_ids = set(str(row[0]) for row in c_cursor.fetchall())
c_conn.close()

print(f"Total Unique World IDs: {len(w_ids)}")
print(f"Total Unique Chunk IDs: {len(c_ids)}")

matches = 0
missing = []
for wid in w_ids:
    # Normalize
    norm_id = wid.replace('C_', '')
    if norm_id in c_ids:
        matches += 1
    else:
        missing.append(wid)

print(f"Matches after normalization: {matches}")
print(f"Still missing: {len(missing)}")
if missing:
    print("Sample missing:", missing[:10])
