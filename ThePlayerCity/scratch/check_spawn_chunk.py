# scratch/check_spawn_chunk.py
import sqlite3
import json
import os

PROJECT_PATH = r"E:\2DGameEditor\Saves\ThePlayerCity"

def find_active():
    db_path = os.path.join(PROJECT_PATH, "Maps", "World.db")
    if not os.path.exists(db_path):
        print("World.db not found!")
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT x, y, chunk_id FROM world_grid WHERE chunk_id != '0' AND chunk_id != 'C_0'")
    active_chunks = cursor.fetchall()
    conn.close()
    
    print(f"Total active chunks in world: {len(active_chunks)}")
    for x, y, cid in active_chunks[:20]:
        print(f"Grid coordinate ({x}, {y}) -> Chunk ID: {cid}")
        # Let's inspect this chunk
        
    # Check if there is any chunk that contains non-zero tiles
    print("\nLoading Chunks.db to find populated chunks...")
    chunks_db = os.path.join(PROJECT_PATH, "Maps", "Chunks.db")
    if os.path.exists(chunks_db):
        conn = sqlite3.connect(chunks_db)
        cursor = conn.cursor()
        cursor.execute("SELECT id, data FROM chunks")
        count = 0
        for cid, data_str in cursor.fetchall():
            data = json.loads(data_str)
            ground = data.get("data", {}).get("ground", [])
            objects = data.get("data", {}).get("objects", [])
            
            # Check if there are non-zero tiles
            has_ground = any(any(val > 0 for val in row) for row in ground if isinstance(row, list))
            has_objects = any(any(val > 0 for val in row) for row in objects if isinstance(row, list))
            
            if has_ground or has_objects:
                count += 1
                if count <= 10:
                    print(f"Populated Chunk ID: {cid} (has_ground: {has_ground}, has_objects: {has_objects})")
        conn.close()
        print(f"Total populated chunks: {count}")

if __name__ == "__main__":
    find_active()
