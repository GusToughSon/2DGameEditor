import os
import struct

class WorldBinaryDriver:
    """
    WORLD BINARY FORMAT (WBF) - PYTHON DRIVER
    - 256x256 Grid (Fixed)
    - 4 Bytes per Cell: [2 Bytes ChunkID][2 Bytes WorldData]
    - Header: 16 Bytes (Magic, Version, TileMap, Dimensions)
    - Total File Size: 262,160 Bytes (Header + 65,536 cells * 4 bytes)
    """
    def __init__(self, file_path):
        self.path = file_path
        self.fd = None
        self.MAGIC = 0x57424621  # ASCII "WBF!"
        self.HEADER_SIZE = 16
        self.WIDTH = 256
        self.STRIDE = 4  # Bytes per cell

    def create(self, version=1, tile_map_id=1):
        """ Initializes a new 256x256 world file filled with zeros. """
        total_size = self.HEADER_SIZE + (self.WIDTH * self.WIDTH * self.STRIDE)
        
        # Build Header
        header = struct.pack("<IIHHH", 
            self.MAGIC,      # 0: Magic
            version,         # 4: Version
            tile_map_id,     # 8: TileMap Reference ID
            self.WIDTH,      # 12: Width
            self.WIDTH       # 14: Height
        )
        # Pad to 16 bytes just in case (the above is 4+4+4+2+2 = 16)
        
        # Pre-allocate full file with zeros
        with open(self.path, "wb") as f:
            f.write(header)
            # Efficiently write the rest as zeros
            f.write(b'\x00' * (self.WIDTH * self.WIDTH * self.STRIDE))
            
        print(f"[WBF] New world initialized at {self.path}")
        self.connect()

    def connect(self):
        """ Opens the file handle for high-speed r+ access. """
        if not os.path.exists(self.path):
            self.create()
            return

        # Open in 'rb+' mode (read/write binary)
        self.fd = open(self.path, "rb+")

        # Security Check
        self.fd.seek(0)
        magic = struct.unpack("<I", self.fd.read(4))[0]
        if magic != self.MAGIC:
            self.fd.close()
            self.fd = None
            raise ValueError(f"SECURITY ALERT: Magic Number mismatch in {self.path}!")

    def set_cell(self, x, y, chunk_id, world_data=0):
        """ Updates one specific cell: [u16 ChunkID][u16 WorldData] """
        if not self.fd: self.connect()
        
        if not (0 <= x < self.WIDTH and 0 <= y < self.WIDTH):
            return

        offset = self.HEADER_SIZE + ((y * self.WIDTH) + x) * self.STRIDE
        data = struct.pack("<hh", chunk_id, world_data)
        
        self.fd.seek(offset)
        self.fd.write(data)

    def get_cell(self, x, y):
        """ Jumps to offset and reads 4 bytes. Returns (chunk_id, world_data) """
        if not self.fd: self.connect()
        
        if not (0 <= x < self.WIDTH and 0 <= y < self.WIDTH):
            return 0, 0

        offset = self.HEADER_SIZE + ((y * self.WIDTH) + x) * self.STRIDE
        self.fd.seek(offset)
        raw = self.fd.read(self.STRIDE)
        chunk_id, world_data = struct.unpack("<hh", raw)
        return chunk_id, world_data

    def export_full(self):
        """ Returns the entire grid as a 2D list for UI compatibility. """
        if not self.fd: self.connect()
        self.fd.seek(self.HEADER_SIZE)
        raw = self.fd.read(self.WIDTH * self.WIDTH * self.STRIDE)
        
        grid = []
        for y in range(self.WIDTH):
            row = []
            for x in range(self.WIDTH):
                idx = (y * self.WIDTH + x) * self.STRIDE
                chunk_id, world_data = struct.unpack("<hh", raw[idx:idx+4])
                row.append(chunk_id) # For now, UI only expects ChunkID
            grid.append(row)
        return grid

    def close(self):
        if self.fd:
            self.fd.close()
            self.fd = None

class ChunkBinaryDriver:
    """
    CHUNK BINARY FORMAT (CBF) - PRO-GRADE ENGINE
    - Each Chunk is 16x16 tiles.
    - Each Tile is 16 Bytes [b0...b15].
    - Chunk Offset = Header + (ChunkID * 4096)
    - Total Size for 4096 chunks: ~16MB
    """
    def __init__(self, file_path):
        self.path = file_path
        self.fd = None
        self.MAGIC = 0x43424621  # ASCII "CBF!"
        self.HEADER_SIZE = 32
        self.CHUNK_DIM = 16
        self.TILE_STRIDE = 16 # Bytes per tile (b0...b15)
        self.CHUNK_STRIDE = self.CHUNK_DIM * self.CHUNK_DIM * self.TILE_STRIDE # 4096 bytes
        self.MAX_CHUNKS = 4096

    def create(self, version=1):
        """ Initializes a massive null-filled database. """
        total_size = self.HEADER_SIZE + (self.MAX_CHUNKS * self.CHUNK_STRIDE)
        
        header = struct.pack("<IIII", 
            self.MAGIC, 
            version, 
            self.CHUNK_DIM, 
            self.MAX_CHUNKS
        )
        header = header.ljust(self.HEADER_SIZE, b'\x00')
        
        with open(self.path, "wb") as f:
            f.write(header)
            # Allocate space (sparse file behavior if OS supports it, but here we write zeros)
            # writing 16MB of zeros is fast enough.
            f.write(b'\x00' * (self.MAX_CHUNKS * self.CHUNK_STRIDE))
            
        print(f"[CBF] New Chunk Database initialized at {self.path}")
        self.connect()

    def connect(self):
        if not os.path.exists(self.path):
            self.create()
            return

        self.fd = open(self.path, "rb+")
        self.fd.seek(0)
        magic = struct.unpack("<I", self.fd.read(4))[0]
        if magic != self.MAGIC:
            self.fd.close()
            self.fd = None
            raise ValueError(f"SECURITY ALERT: Magic Number mismatch in {self.path}!")

    def set_tile(self, chunk_id, x, y, byte_data):
        """ 
        Updates a single tile (16 bytes). 
        byte_data must be a bytes object of length 16.
        """
        if not self.fd: self.connect()
        if not (0 <= chunk_id < self.MAX_CHUNKS): return
        
        offset = self.HEADER_SIZE + (chunk_id * self.CHUNK_STRIDE) + ((y * self.CHUNK_DIM) + x) * self.TILE_STRIDE
        self.fd.seek(offset)
        self.fd.write(byte_data[:16].ljust(16, b'\x00'))

    def get_chunk(self, chunk_id):
        """ Returns the raw 4096 bytes for a chunk. """
        if not self.fd: self.connect()
        if not (0 <= chunk_id < self.MAX_CHUNKS): return None
        
        offset = self.HEADER_SIZE + (chunk_id * self.CHUNK_STRIDE)
        self.fd.seek(offset)
        return self.fd.read(self.CHUNK_STRIDE)

    def save_chunk_from_layers(self, chunk_id, ground_layer, object_layer):
        """ 
        Converts two 16x16 arrays (IDs) into binary and saves it. 
        b0-b1: GroundID (u16)
        b2-b3: ObjectID (u16)
        b4-b15: Zeros
        """
        if not self.fd: self.connect()
        
        chunk_buf = bytearray(self.CHUNK_STRIDE)
        for y in range(self.CHUNK_DIM):
            for x in range(self.CHUNK_DIM):
                idx = (y * self.CHUNK_DIM + x) * self.TILE_STRIDE
                gid = ground_layer[y][x] if y < len(ground_layer) and x < len(ground_layer[y]) else 0
                oid = object_layer[y][x] if y < len(object_layer) and x < len(object_layer[y]) else 0
                
                # Packed as [h ground][h object][12 padding]
                struct.pack_into("<hh", chunk_buf, idx, gid, oid)
        
        offset = self.HEADER_SIZE + (chunk_id * self.CHUNK_STRIDE)
        self.fd.seek(offset)
        self.fd.write(chunk_buf)

    def load_chunk_to_layers(self, chunk_id):
        """ Returns (ground_layer, object_layer). """
        raw = self.get_chunk(chunk_id)
        if not raw: return None, None
        
        ground = [[0]*16 for _ in range(16)]
        objects = [[0]*16 for _ in range(16)]
        
        for y in range(16):
            for x in range(16):
                idx = (y * 16 + x) * 16
                gid, oid = struct.unpack("<hh", raw[idx:idx+4])
                ground[y][x] = gid
                objects[y][x] = oid
                
        return ground, objects

    def close(self):
        if self.fd:
            self.fd.close()
            self.fd = None
