# crypto.py
import os

def get_tcp_key() -> bytes:
    """Reads TCPKEY from server/constants.md. Falls back to a default key if not found."""
    # Find path relative to this file: e:\Vorila\ThePlayerCity\core\crypto.py -> e:\Vorila\ThePlayerCity\server\constants.md
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'server', 'constants.md')
    if not os.path.exists(path):
        # Also check relative to CWD just in case
        path = os.path.join('server', 'constants.md')
        
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('TCPKEY:'):
                        # Extract the key value and strip whitespaces/quotes
                        key_str = line.split('TCPKEY:', 1)[1].strip()
                        if key_str:
                            return key_str.encode('utf-8')
        except Exception as e:
            print(f"[CRYPTO WARNING] Failed to read constants.md: {e}")
            
    # Default fallback XOR key if file or key not found
    return b"default_player_city_secret_salt_key"

def encrypt_data(data: bytes) -> bytes:
    """Encrypt byte data using XOR/salt key (cycle XOR)."""
    key = get_tcp_key()
    if not key:
        return data
    return bytes(data[i] ^ key[i % len(key)] for i in range(len(data)))

def decrypt_data(data: bytes) -> bytes:
    """Decrypt byte data (XOR is symmetric)."""
    return encrypt_data(data)

