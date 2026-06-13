import os
import random
import hashlib

def changeChecksum(file_path):
    """
    Appends a small random salt to the end of a file to modify its hash/checksum.
    """
    if not os.path.exists(file_path):
        return False, "File not found."
    
    try:
        # Generate a small random salt (1-64 bytes)
        salt_size = random.randint(1, 64)
        noise = os.urandom(salt_size)
        
        # Append noise to the end of the file. 
        # Most file formats (ZIP, EXE, PNG) ignore trailing data.
        with open(file_path, "ab") as f:
            f.write(noise)
            
        print(f"[SECURITY] Mutated signature for {os.path.basename(file_path)}. Checksum rotated.")
        return True, None
    except Exception as e:
        return False, str(e)

def get_file_hash(file_path):
    """ Returns the SHA256 hash of a file for verification. """
    if not os.path.exists(file_path):
        return None
    try:
        sha256_hash = hashlib.sha256()
        with open(file_path,"rb") as f:
            for byte_block in iter(lambda: f.read(4096),b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception:
        return None