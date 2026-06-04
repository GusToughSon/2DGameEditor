import sqlite3
import json
import os

db_path = r'c:\Users\gooro\OneDrive\Desktop\Test idea\LoadFolder\ThePlayerCity\Maps\Chunks.db'
world_db = r'c:\Users\gooro\OneDrive\Desktop\Test idea\LoadFolder\ThePlayerCity\Maps\World.db'

print(f"Checking World.db...")
w_conn = sqlite3.connect(world_db)
w_cursor = w_conn.cursor()
w_cursor.execute("SELECT chunk_id FROM world_grid WHERE x=10 AND y=10")
w_row = w_cursor.fetchone()
print(f"World at 10,10 has chunk_id: {w_row}")

if w_row:
    cid = w_row[0]
    print(f"Checking Chunks.db for {cid}...")
    c_conn = sqlite3.connect(db_path)
    c_cursor = c_conn.cursor()
    # Try multiple formats
    for query_id in [cid, cid.replace("C_", ""), f"C_{cid}"]:
        c_cursor.execute("SELECT id, length(data) FROM chunks WHERE id=?", (query_id,))
        row = c_cursor.fetchone()
        if row:
            print(f"FOUND: {row}")
            break
    else:
        print("NOT FOUND in Chunks.db")
