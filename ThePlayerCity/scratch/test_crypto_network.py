# scratch/test_crypto_network.py
import os
import sys
import asyncio
import socket
import threading
import time

# Add root directory to sys.path so we can import core and server
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.crypto import get_tcp_key, encrypt_data, decrypt_data
from core.packets import pack_json, unpack_json, read_packet_sync, read_packet_async

from core.models import Account, CharacterData

class DummyDB:
    def __init__(self):
        acc = Account()
        acc.data.acc_name = "testuser"
        acc.data.acc_pass = "testpass"
        
        char = CharacterData()
        char.used = True
        char.name = "Hero"
        char.level = 5
        char.avatar = 1
        char.hp_left = 80
        char.hp_max = 100
        char.x = 15
        char.y = 15
        
        acc.chars = [char, CharacterData()]
        self.accounts = [acc]

async def run_server():
    from server.network import GameServer
    db = DummyDB()
    server = GameServer(db, port=1339)
    # Start server
    asyncio_server = await asyncio.start_server(server.handle_client, '127.0.0.1', 1339)
    async with asyncio_server:
        await asyncio.sleep(2) # Run for 2 seconds to let client finish test

def start_server_in_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_server())

def test_crypto():
    print("--- Testing Cryptography ---")
    key = get_tcp_key()
    print(f"Loaded TCPKEY salt: {key}")
    assert key == b"MyConfigurableSuperSecretXORSaltKey123", "Should load from constants.md"
    
    original = b"Hello, Player City!"
    encrypted = encrypt_data(original)
    decrypted = decrypt_data(encrypted)
    print(f"Original: {original}")
    print(f"Encrypted: {encrypted}")
    print(f"Decrypted: {decrypted}")
    assert decrypted == original, "Encryption and decryption must be symmetric"
    print("Crypto test passed!")

def test_json_packing():
    print("\n--- Testing JSON Packing/Unpacking ---")
    packet_dict = {"type": "login", "username": "testuser", "password": "testpass", "version": 3309}
    packed = pack_json(packet_dict)
    print(f"Packed size: {len(packed)} bytes")
    # Verify length prefix (first 4 bytes)
    import struct
    length = struct.unpack("<I", packed[:4])[0]
    print(f"Length prefix specifies payload size: {length} bytes")
    assert length + 4 == len(packed)
    
    unpacked = unpack_json(packed[4:])
    print(f"Unpacked dictionary: {unpacked}")
    assert unpacked == packet_dict, "JSON unpacked packet must match original"
    print("JSON packing test passed!")

def test_network_client():
    print("\n--- Testing Network Client-Server Flow ---")
    # Start server in background thread
    t = threading.Thread(target=start_server_in_thread, daemon=True)
    t.start()
    time.sleep(0.5) # Wait for server to bind and listen
    
    # Connect client with retries to allow the server to finish loading maps
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connected = False
    for i in range(10):
        try:
            s.connect(('127.0.0.1', 1339))
            connected = True
            break
        except ConnectionRefusedError:
            time.sleep(0.5)
    if not connected:
        s.connect(('127.0.0.1', 1339))
    print("[Client] Connected to server.")
    
    # Send login packet
    login_req = {"type": "login", "username": "testuser", "password": "testpass", "version": 3309}
    s.sendall(pack_json(login_req))
    print(f"[Client] Sent login request: {login_req}")
    
    # Read response
    resp = read_packet_sync(s)
    print(f"[Client] Received response: {resp}")
    assert resp is not None, "Response should not be None"
    assert resp.get("success") is True, "Login should succeed"
    assert resp.get("slots").get("names")[0] == "Hero", "Should load Character 'Hero'"
    print("[Client] Client-Server test passed successfully!")
    s.close()

if __name__ == "__main__":
    test_crypto()
    test_json_packing()
    test_network_client()
