import os
import csv
import json

class ChunkDatabase:
    """
    Foundational Chunk Processor. 
    Converts 16-byte source lines into full 16x16 game-compatible Chunks.
    """
    def __init__(self, project_path):
        self.project_path = project_path
        self.registry_path = os.path.join(project_path, "Maps", "Chunks.json")
        self.chunks = {}
        
    def rebuild_library(self, files):
        print(f"[FOUNDATION] Starting library rebuild from {len(files)} sources...")
        
        self.chunks = {}
        global_cid = 0
        
        ordered_files = []
        for f in files:
            if "chunk 2" not in f.lower(): ordered_files.append(f)
        for f in files:
            if "chunk 2" in f.lower(): ordered_files.append(f)

        for fpath in ordered_files:
            if not os.path.exists(fpath): continue
            print(f"[FOUNDATION] Harvesting from {os.path.basename(fpath)}...")
            
            with open(fpath, 'r') as f:
                reader = csv.reader(f)
                next(reader) # skip header
                
                for row in reader:
                    if not row or len(row) < 4: continue
                    bytes_data = [int(v) for v in row[3:]]
                    
                    # Convert to 16-bit Tile IDs (8 tiles available)
                    tiles_in_line = []
                    for i in range(0, 16, 2):
                        tiles_in_line.append(bytes_data[i] + (bytes_data[i+1] << 8))
                    
                    # LOGIC: Because the user has 16 bytes (8 tiles) but needs a 16x16 chunk (256 tiles),
                    # we build a 'Solid pattern' using these definitions.
                    # Layer 0 (Ground) = First Tile
                    # Layer 1 (Object) = Second Tile
                    
                    ground_tile = tiles_in_line[0] 
                    object_tile = tiles_in_line[1] if len(tiles_in_line) > 1 else 0
                    
                    # Generate 16x16 grid
                    g_grid = [[ground_tile for _ in range(16)] for _ in range(16)]
                    o_grid = [[object_tile for _ in range(16)] for _ in range(16)]
                    
                    cid = f"C_{global_cid}"
                    self.chunks[cid] = {
                        "name": cid,
                        "data": {
                            "ground": g_grid,
                            "objects": o_grid
                        }
                    }
                    global_cid += 1
                    
                    if global_cid % 10000 == 0:
                        print(f"[FOUNDATION] Processed {global_cid} chunks...")

        print(f"[FOUNDATION] Harvest complete. Total Chunks: {len(self.chunks)}")
        self.save()

    def save(self):
        print(f"[FOUNDATION] Committing registry to disk (this may take a moment)...")
        with open(self.registry_path, 'w') as f:
            json.dump(self.chunks, f) # No indent for speed/size
        print(f"[FOUNDATION] Rebuild SUCCESS: {self.registry_path}")

if __name__ == "__main__":
    project = r"e:\2DGameEditor\Saves\MyNewProject"
    sources = [
        r"c:\Users\gooro\OneDrive\Desktop\chunks\Chunk_processed.txt",
        r"c:\Users\gooro\OneDrive\Desktop\chunks\Chunk 2_processed.txt"
    ]
    db = ChunkDatabase(project)
    db.rebuild_library(sources)
