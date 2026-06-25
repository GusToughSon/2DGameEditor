# scratch/test_register.py
import os
import sys
import asyncio
from unittest.mock import MagicMock

# Add root directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.database import DatabaseManager
from server.network import GameServer

async def run_register_test():
    test_acc_db_path = r"e:\Vorila\ThePlayerCity\test_register_accounts.db"
    if os.path.exists(test_acc_db_path):
        os.remove(test_acc_db_path)
        
    db = DatabaseManager(db_path=test_acc_db_path)
    db.load_accounts()
    
    # Instantiate server
    game_server = GameServer(db)
    
    # Mock asyncio reader and writer for registration request
    reader = MagicMock()
    writer = MagicMock()
    
    async def mock_wait_closed():
        pass
    writer.wait_closed = mock_wait_closed
    
    async def mock_drain():
        pass
    writer.drain = mock_drain
    
    # Define request packet
    request = {
        "type": "register",
        "username": "NewClientUser",
        "password": "SecurePassword123"
    }
    
    # Mock read_packet_async in the server's network flow context
    import server.network
    original_read = server.network.read_packet_async
    
    # We will simulate reading the register request, then returning None to break the loop
    packets_to_read = [request, None]
    async def mock_read(r):
        return packets_to_read.pop(0)
    
    server.network.read_packet_async = mock_read
    
    # Capture written packet response
    written_data = []
    def mock_write(data):
        written_data.append(data)
        
    writer.write = mock_write
    
    # Run the client handler
    await game_server.handle_client(reader, writer)
    
    # Restore original function
    server.network.read_packet_async = original_read
    
    # Assertions
    assert len(written_data) == 1, "Should write response packet exactly once"
    
    # Decrypt response
    from core.packets import unpack_json
    # The prefix is 4-byte length prefix
    payload = written_data[0][4:]
    response = unpack_json(payload)
    print(f"Decrypted register response: {response}")
    
    assert response.get("type") == "register_response"
    assert response.get("success") is True
    
    # Check if account is actually in database
    db.load_accounts()
    accs = db.sqlite_db.get_all_accounts()
    assert len(accs) == 1
    assert accs[0]["acc_name"] == "NewClientUser"
    
    # Cleanup database references
    del db
    del game_server
    import gc
    gc.collect()
    
    try:
        if os.path.exists(test_acc_db_path):
            os.remove(test_acc_db_path)
    except PermissionError:
        pass
        
    print("Registration packet handler verification completed successfully!")

if __name__ == "__main__":
    asyncio.run(run_register_test())
