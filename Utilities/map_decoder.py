"""
map_decoder.py
================

This script demonstrates how to decode the proprietary `Map.dat` format
used by the Vorlia client.  From analysing `main.h`, `FileHandling.cpp`
and `minimap.cpp`, we know the map file contains a 25‑byte header
followed by two complete layers of 4 096 chunk definitions and then a
512×512 chunk map.  Each chunk is a 16×16 grid of unsigned 16‑bit
values.  The low 10 bits of each value encode a tile index (0–1023),
which corresponds to an entry in the `Tiles` array loaded from
`data02.dat`.  The high bits encode flags for flipping, layering or
blocked/unblocked status.  This script demonstrates how to parse the
file and reconstruct a small region of the world.
"""

import struct
import os
from pathlib import Path
from typing import List, Tuple

try:
    from PIL import Image
except ImportError:
    raise SystemExit(
        "This script requires Pillow. Install it with `pip install pillow` and run again."
    )


TILE_SIZE = 16
NUM_CHUNKS = 4096
NUM_LAYERS = 2
CHUNK_DIM = 16  # tiles per chunk side
CHUNK_MAP_SIZE = 512  # number of chunks per side in the world


def load_tile_sheet(path: Path) -> List[Image.Image]:
    """
    Load a tile sheet from a PNG/BMP/VDF/DAT file and return a list of 16×16 RGBA tile images.
    """
    suffix = path.suffix.lower()
    if suffix in (".vdf", ".dat"):  # decode custom binary tile sheet
        with path.open("rb") as f:
            height4 = struct.unpack("<I", f.read(4))[0]
            height = height4 >> 2
            _random = f.read(4)  # random value, ignore
            width4 = struct.unpack("<I", f.read(4))[0]
            width = width4 >> 2
            data = f.read(height * width * 3)
            if len(data) != height * width * 3:
                raise ValueError(f"Unexpected length for pixel data in {path}")
            img = Image.frombytes("RGB", (width, height), data)
            img = img.convert("RGBA")
    else:
        img = Image.open(path).convert("RGBA")
        
    tiles: List[Image.Image] = []
    tiles_x = img.width // TILE_SIZE
    tiles_y = img.height // TILE_SIZE
    for ty in range(tiles_y):
        for tx in range(tiles_x):
            tile = img.crop(
                (tx * TILE_SIZE, ty * TILE_SIZE, (tx + 1) * TILE_SIZE, (ty + 1) * TILE_SIZE)
            )
            tiles.append(tile)
    return tiles


def read_map(path: Path) -> Tuple[List[List[List[List[int]]]], List[List[int]]]:
    """Parse the Map.dat file and return (chunks, chunk_map)."""
    with path.open("rb") as f:
        header = f.read(25)
        layers: List[List[List[List[int]]]] = []
        for layer_idx in range(NUM_LAYERS):
            layer_chunks: List[List[List[int]]] = []
            for chunk_id in range(NUM_CHUNKS):
                chunk: List[List[int]] = []
                for row in range(CHUNK_DIM):
                    row_vals = []
                    for col in range(CHUNK_DIM):
                        raw = f.read(2)
                        if len(raw) != 2:
                            raise ValueError(
                                f"Unexpected EOF while reading chunk {chunk_id} layer {layer_idx}"
                            )
                        val = struct.unpack("<H", raw)[0]
                        row_vals.append(val)
                    chunk.append(row_vals)
                layer_chunks.append(chunk)
            layers.append(layer_chunks)
            
        chunk_map: List[List[int]] = []
        for row in range(CHUNK_MAP_SIZE):
            row_vals = []
            for col in range(CHUNK_MAP_SIZE):
                raw = f.read(2)
                if len(raw) != 2:
                    raise ValueError("Unexpected EOF while reading chunk map")
                val = struct.unpack("<H", raw)[0]
                row_vals.append(val)
            chunk_map.append(row_vals)
    return layers, chunk_map


def decode_tile_value(val: int) -> Tuple[int, dict]:
    tile_id = val & 0x03FF  # 10 bits
    flags_val = (val >> 10) & 0x003F
    flags = {
        "flip_h": bool(flags_val & 0x01),
        "flip_v": bool(flags_val & 0x02),
        "block": bool(flags_val & 0x04),
    }
    return tile_id, flags


def render_preview(
    layers: List[List[List[List[int]]]],
    chunk_map: List[List[int]],
    ground_tiles: List[Image.Image],
    object_tiles: List[Image.Image],
    out_path: Path,
    chunks_w: int = 4,
    chunks_h: int = 4,
):
    width = chunks_w * CHUNK_DIM
    height = chunks_h * CHUNK_DIM
    out = Image.new("RGBA", (width * TILE_SIZE, height * TILE_SIZE))
    for cy in range(chunks_h):
        for cx in range(chunks_w):
            chunk_id = chunk_map[cy][cx]
            chunk = layers[0][chunk_id]
            for ty in range(CHUNK_DIM):
                for tx in range(CHUNK_DIM):
                    val = chunk[ty][tx]
                    tile_id, flags = decode_tile_value(val)
                    if tile_id < len(ground_tiles):
                        tile = ground_tiles[tile_id]
                    elif tile_id - len(ground_tiles) < len(object_tiles):
                        tile = object_tiles[tile_id - len(ground_tiles)]
                    else:
                        tile = Image.new(
                            "RGBA", (TILE_SIZE, TILE_SIZE), (255, 0, 255, 255)
                        )
                    if flags["flip_h"]:
                        tile = tile.transpose(Image.FLIP_LEFT_RIGHT)
                    if flags["flip_v"]:
                        tile = tile.transpose(Image.FLIP_TOP_BOTTOM)
                    out.paste(
                        tile,
                        (
                            (cx * CHUNK_DIM + tx) * TILE_SIZE,
                            (cy * CHUNK_DIM + ty) * TILE_SIZE,
                        ),
                    )
    out.save(out_path)
    print(f"Saved preview to {out_path}")


def main() -> None:
    map_path = Path("map.dat")
    tiles_path = Path("tiles.png")
    objects_path = Path("objects.png")

    # Adapt path lookups to try default project locations if local files aren't found
    if not map_path.exists():
        # Try checking in legacy master editor dat directory
        fallback_map = Path("../Legacy/Vorlia-Master-Editor/dat/map.dat")
        if fallback_map.exists():
            map_path = fallback_map

    if not tiles_path.exists():
        fallback_tiles = Path("../Saves/ThePlayerCity/TILESET/World_TILESET.png")
        if fallback_tiles.exists():
            tiles_path = fallback_tiles

    if not objects_path.exists():
        fallback_objects = Path("../Saves/ThePlayerCity/TILESET/OBJECTS_TILESET.png")
        if fallback_objects.exists():
            objects_path = fallback_objects

    if not map_path.exists():
        raise SystemExit("map.dat not found")
    if not tiles_path.exists() or not objects_path.exists():
        raise SystemExit(
            "tiles.png/World_TILESET.png and objects.png/OBJECTS_TILESET.png are required"
        )

    print(f"Decoding using:\n  Map: {map_path}\n  Tiles: {tiles_path}\n  Objects: {objects_path}")

    ground_tiles = load_tile_sheet(tiles_path)
    object_tiles = load_tile_sheet(objects_path)
    layers, chunk_map = read_map(map_path)

    render_preview(
        layers,
        chunk_map,
        ground_tiles,
        object_tiles,
        Path("preview.png"),
        chunks_w=4,
        chunks_h=4,
    )


if __name__ == "__main__":
    main()
