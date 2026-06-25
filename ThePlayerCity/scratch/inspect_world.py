# scratch/inspect_world.py
import sqlite3
import json
import os

PROJECT_PATH = r"E:\2DGameEditor\Saves\ThePlayerCity"

def inspect():
    db_path = os.path.join(PROJECT_PATH, "Maps", "World.db")
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        print("Tables:", cursor.fetchall())
        
        cursor.execute("SELECT count(*) FROM world_grid")
        print("Grid size count:", cursor.fetchone()[0])
        
        cursor.execute("SELECT * FROM world_points")
        pts = cursor.fetchall()
        print(f"Points ({len(pts)} total):")
        for pt in pts:
            print(pt)
            
        conn.close()
        
    json_path = os.path.join(PROJECT_PATH, "Maps", "World.json")
    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            data = json.load(f)
            print("World.json keys:", list(data.keys()))
            if "points" in data:
                print("World.json points count:", len(data["points"]))
                for p in data["points"][:5]:
                    print(p)

if __name__ == "__main__":
    inspect()
