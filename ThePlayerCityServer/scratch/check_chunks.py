import sqlite3
import os

db_path = r'c:\Users\gooro\OneDrive\Desktop\Test idea\LoadFolder\ThePlayerCity\Maps\Chunks.db'
if not os.path.exists(db_path):
    print("DB not found")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT sql FROM sqlite_master WHERE name='chunks'")
    print("Chunks Table SQL:", cursor.fetchone())
    
    cursor.execute("SELECT id, data FROM chunks LIMIT 1")
    row = cursor.fetchone()
    if row:
        print("ID:", row[0])
        print("Data Type:", type(row[1]))
        print("Data Sample:", row[1][:100])
    conn.close()
