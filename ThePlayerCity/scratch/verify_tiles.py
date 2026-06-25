from PIL import Image
import sqlite3, json

# Load tileset
ts = Image.open(r'E:\2DGameEditor\Saves\ThePlayerCity\TILESET\World_TILESET.png')
print(f"World_TILESET.png: {ts.size}")
print(f"Tile size: 16")
print(f"Stride (width // 16): {ts.width // 16}")
print(f"280 / 16 = {280 / 16}")
print(f"280 // 16 = {280 // 16}")
print(f"17 * 16 = {17 * 16} (272 px used, {280 - 272} px unused)")
print()

# Check: what does tile ID 32 look like?
stride = ts.width // 16
print(f"Tile ID 32:")
print(f"  col = 32 % {stride} = {32 % stride}")
print(f"  row = 32 // {stride} = {32 // stride}")
print(f"  px = ({(32 % stride) * 16}, {(32 // stride) * 16})")

# Check: tile 1 (Water uses this)
print(f"\nTile ID 1:")
print(f"  col = 1 % {stride} = {1 % stride}")
print(f"  row = 1 // {stride} = {1 // stride}")
print(f"  px = ({(1 % stride) * 16}, {(1 // stride) * 16})")

# Let's also check some non-trivial tile
print(f"\nTile ID 53 (Mountain chunk uses this):")
print(f"  col = 53 % {stride} = {53 % stride}")
print(f"  row = 53 // {stride} = {53 // stride}")
print(f"  px = ({(53 % stride) * 16}, {(53 // stride) * 16})")

# Now look at the ACTUAL pixel content at these positions
# Extract tile 32 and see if it's a grass tile
for tid in [1, 32, 53]:
    col = tid % stride
    row = tid // stride
    px_x = col * 16
    px_y = row * 16
    tile = ts.crop((px_x, px_y, px_x + 16, px_y + 16))
    # Get the dominant color of this tile
    pixels = list(tile.getdata())
    avg = tuple(sum(c) // len(pixels) for c in zip(*[(p[0], p[1], p[2]) for p in pixels]))
    print(f"Tile {tid} at ({px_x},{px_y}): avg color RGB={avg}")

# Also verify by checking the OBJECTS tileset
obj_ts = Image.open(r'E:\2DGameEditor\Saves\ThePlayerCity\TILESET\OBJECTS_TILESET.png')
print(f"\nOBJECTS_TILESET.png: {obj_ts.size}")
print(f"Stride: {obj_ts.width // 16}")

# AVATARS
av_ts = Image.open(r'E:\2DGameEditor\Saves\ThePlayerCity\TILESET\AVATARS_TILESET.png')
print(f"AVATARS_TILESET.png: {av_ts.size}")
print(f"Stride: {av_ts.width // 16}")

# Also let's check what happens with rendering
# The WorldEditor in _get_rendered_layer_chunk uses:
# tw = tileset_img.width // self.tile_size
# tx = (tid % tw) * self.tile_size
# ty = (tid // tw) * self.tile_size
# if ty + self.tile_size <= tileset_img.height:
#   tile = tileset_img.crop((tx, ty, tx+self.tile_size, ty+self.tile_size))

# So let me simulate this for tile 32
tw_editor = ts.width // 16
print(f"\n--- Editor simulation ---")
print(f"tw = {ts.width} // 16 = {tw_editor}")
for tid in [1, 32, 53, 478]:
    tx = (tid % tw_editor) * 16
    ty = (tid // tw_editor) * 16
    print(f"Tile {tid}: crop({tx}, {ty}, {tx+16}, {ty+16})")
    if ty + 16 <= ts.height:
        tile = ts.crop((tx, ty, tx+16, ty+16))
        pixels = list(tile.getdata())
        avg = tuple(sum(c) // len(pixels) for c in zip(*[(p[0], p[1], p[2]) for p in pixels]))
        print(f"  -> avg color: RGB{avg}")
    else:
        print(f"  -> OUT OF BOUNDS")

# Now let's see what MY renderer produces with the SAME logic
print(f"\n--- My renderer does the exact same thing, stride={tw_editor} ---")
print(f"MATCH: Both use tileset_width // tile_size = {tw_editor}")
