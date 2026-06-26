# scratch/convert_tilesets.py
import os
from PIL import Image

GF_BMP_DIR = r"E:\2DGameEditor\Assets"
TILESET_DIR = r"E:\2DGameEditor\Saves\ThePlayerCity\TILESET"

def convert():
    mappings = {
        "tiles.bmp": "World_TILESET.png",
        "objects.bmp": "OBJECTS_TILESET.png",
        "avatars.bmp": "AVATARS_TILESET.png",
        "itemgraph.bmp": "ITEMS_TILESET.png"
    }
    
    os.makedirs(TILESET_DIR, exist_ok=True)
    
    for bmp_name, png_name in mappings.items():
        bmp_path = os.path.join(GF_BMP_DIR, bmp_name)
        png_path = os.path.join(TILESET_DIR, png_name)
        
        if os.path.exists(bmp_path):
            print(f"Converting {bmp_name} -> {png_name}...")
            try:
                img = Image.open(bmp_path)
                # Ensure transparent background if black is used as transparent key (optional, but let's convert to RGBA)
                img = img.convert("RGBA")
                
                # In classic games, pure black (0,0,0) or magenta is often transparent. Let's make pure black transparent:
                # (Optional: check if client engine uses colorkey, Pygame's convert_alpha works if we set transparent pixels)
                datas = img.getdata()
                new_data = []
                for item in datas:
                    # If it's pure black, make it transparent
                    if item[0] == 0 and item[1] == 0 and item[2] == 0:
                        new_data.append((0, 0, 0, 0))
                    else:
                        new_data.append(item)
                img.putdata(new_data)
                
                img.save(png_path, "PNG")
                print(f"Successfully saved to {png_path}")
            except Exception as e:
                print(f"Error converting {bmp_name}: {e}")
        else:
            print(f"Source file {bmp_path} not found!")

if __name__ == "__main__":
    convert()
