import os
import random
import hashlib

def changeChecksum(file_path):
    """
    Subtly alters the binary signature of a file by appending a small 
    random noise block. This changes the file's Hash/Checksum to 
    help mitigate heuristic false positives from sensitive AVs.
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
    """ Returns the SHA256 mash of a file for verification. """
    sha256_hash = hashlib.sha256()
    with open(file_path,"rb") as f:
        for byte_block in iter(lambda: f.read(4096),b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()