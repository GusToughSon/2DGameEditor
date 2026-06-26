# scratch/inspect_dimensions.py
import os
from PIL import Image

GF_BMP_DIR = r"E:\2DGameEditor\Assets"

def inspect():
    files = ["tiles.bmp", "objects.bmp", "avatars.bmp", "itemgraph.bmp"]
    for f in files:
        path = os.path.join(GF_BMP_DIR, f)
        if os.path.exists(path):
            img = Image.open(path)
            print(f"{f}: {img.width}x{img.height}")
        else:
            print(f"{f} not found!")

if __name__ == "__main__":
    inspect()
