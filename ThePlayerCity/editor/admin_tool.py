# editor/admin_tool.py
import socket
import struct
import sys
import threading
import queue
from typing import Optional
from core.packets import VERSION, pack_json, read_packet_sync

class AdminTool:
    def __init__(self):
        self.sock = None
        self.connected = False
        self.authed = False
        self.editing_mode = 0  # 0 = none, 1 = account, 2 = character
        self.edit_account_id = -1
        self.edit_char_id = -1
        self.accounts = []      # List of account dicts
        self.characters = []    # List of character dicts
        self.queues = {}        # Response type -> Queue
        self.pending_edits = {} # field -> value

    def connect(self, host="127.0.0.1", port=1338) -> bool:
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, port))
            
            # Send admin initialization packet as JSON
            admin_req = {"type": "admin_init"}
            self.sock.sendall(pack_json(admin_req))
            
            res = read_packet_sync(self.sock)
            if res and res.get("type") == "admin_init_response" and res.get("success"):
                self.connected = True
                print(f"Connected to admin server {host}:{port}")
                # Start listener thread for server responses
                threading.Thread(target=self.listen_responses, daemon=True).start()
                return True
            else:
                print("Server rejected admin initialization.")
                self.sock.close()
                return False
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def listen_responses(self):
        try:
            while self.connected:
                packet = read_packet_sync(self.sock)
                if not packet:
                    break
                p_type = packet.get("type")
                if p_type in self.queues:
                    self.queues[p_type].put(packet)
                else:
                    if p_type == "admin_error":
                        print(f"\n[SERVER ERROR] {packet.get('error')}")
                    else:
                        print(f"\n[SERVER NOTIFICATION] Received unexpected packet: {packet}")
        except Exception as e:
            print(f"\nAdmin connection closed: {e}")
            self.connected = False

    def send_request(self, req_packet: dict, resp_type: str, timeout=5.0) -> Optional[dict]:
        """Helper to send a packet and wait synchronously for the corresponding response."""
        q = queue.Queue()
        self.queues[resp_type] = q
        try:
            self.sock.sendall(pack_json(req_packet))
            return q.get(timeout=timeout)
        except queue.Empty:
            print(f"Request timeout waiting for response type '{resp_type}'")
            return None
        except Exception as e:
            print(f"Error during request: {e}")
            return None
        finally:
            self.queues.pop(resp_type, None)

    def run_cli(self):
        print("ThePlayerCity Admin Tool 1.0 (Python)")
        print("Type 'help' or '?' for commands.")
        
        while True:
            prompt = "# "
            if self.editing_mode == 1:
                # Find account name
                acc_name = "Unknown"
                for a in self.accounts:
                    if a["id"] == self.edit_account_id:
                        acc_name = a["acc_name"]
                        break
                prompt = f"{acc_name}.acc # "
            elif self.editing_mode == 2:
                # Find character name
                char_name = "Unknown"
                for c in self.characters:
                    if c["id"] == self.edit_char_id:
                        char_name = c["name"]
                        break
                prompt = f"{char_name}.char # "
                
            try:
                line = input(prompt).strip()
            except (KeyboardInterrupt, EOFError):
                print("\nExiting.")
                break
                
            cmd = line.split()
            if not cmd:
                continue
                
            base_cmd = cmd[0].lower()
            
            if base_cmd in ("quit", "exit"):
                if self.editing_mode != 0:
                    self.editing_mode = 0
                    self.pending_edits.clear()
                    print("Exited editing mode.")
                else:
                    break
                    
            elif base_cmd == "connect":
                host = cmd[1] if len(cmd) > 1 else "127.0.0.1"
                self.connect(host)
                
            elif base_cmd == "auth":
                if not self.connected:
                    print("You must connect to the server first.")
                    continue
                if len(cmd) < 3:
                    print("Usage: auth <username> <password>")
                    continue
                username, password = cmd[1], cmd[2]
                res = self.send_request({
                    "type": "admin_auth",
                    "username": username,
                    "password": password
                }, "admin_auth_response")
                if res and res.get("success"):
                    self.authed = True
                    print(f"Successfully authenticated as admin '{username}'.")
                else:
                    print(f"Authentication failed: {res.get('error') if res else 'No response'}")
                    
            elif base_cmd == "listaccounts":
                if not self.authed:
                    print("Please auth first.")
                    continue
                res = self.send_request({"type": "admin_request_accounts"}, "admin_accounts_list")
                if res:
                    self.accounts = res.get("accounts", [])
                    print("\nEdit ID: Account Name | Banned | Premium | Golden")
                    print("--------------------------------------------------")
                    for idx, a in enumerate(self.accounts):
                        print(f"{idx:3d} : {a['acc_name']:16s} | {a['is_banned']} | {a['is_premium']} | {a['is_golden']}")
                    print(f"Listed {len(self.accounts)} accounts.\n")
                    
            elif base_cmd == "listcharacters":
                if not self.authed:
                    print("Please auth first.")
                    continue
                res = self.send_request({"type": "admin_request_characters"}, "admin_characters_list")
                if res:
                    self.characters = res.get("characters", [])
                    print("\nEdit ID: Character Name | Level | Position | Dev Mode | Online")
                    print("-----------------------------------------------------------------")
                    for idx, c in enumerate(self.characters):
                        print(f"{idx:3d} : {c['name']:16s} | Lvl {c['level']:3d} | ({c['x']:3d}, {c['y']:3d}) | Dev={c['dev_mode']} | {c['is_online']}")
                    print(f"Listed {len(self.characters)} characters.\n")
                    
            elif base_cmd == "edit":
                if not self.authed:
                    print("Please auth first.")
                    continue
                if len(cmd) < 2:
                    print("Usage: edit <idx>")
                    continue
                try:
                    idx = int(cmd[1])
                    if 0 <= idx < len(self.accounts):
                        self.editing_mode = 1
                        self.edit_account_id = self.accounts[idx]["id"]
                        self.pending_edits.clear()
                        print(f"Now editing account: {self.accounts[idx]['acc_name']}")
                        print("Type 'accinfo' to view, 'set <field> <val>' to edit, and 'save' to commit.")
                    else:
                        print("Account index out of range. Run listaccounts first.")
                except ValueError:
                    print("Invalid index format.")
                    
            elif base_cmd == "cedit":
                if not self.authed:
                    print("Please auth first.")
                    continue
                if len(cmd) < 2:
                    print("Usage: cedit <idx>")
                    continue
                try:
                    idx = int(cmd[1])
                    if 0 <= idx < len(self.characters):
                        self.editing_mode = 2
                        self.edit_char_id = self.characters[idx]["id"]
                        self.pending_edits.clear()
                        print(f"Now editing character: {self.characters[idx]['name']}")
                        print("Type 'charinfo' to view, 'set <field> <val>' to edit, and 'save' to commit.")
                    else:
                        print("Character index out of range. Run listcharacters first.")
                except ValueError:
                    print("Invalid index format.")
                    
            elif base_cmd == "accinfo":
                if self.editing_mode != 1:
                    print("You must be in account edit mode (edit <idx>) to run this command.")
                    continue
                # Display account info
                for a in self.accounts:
                    if a["id"] == self.edit_account_id:
                        print(f"\nAccount Info (ID: {a['id']}):")
                        print(f"  Name:       {a['acc_name']}")
                        print(f"  Banned:     {a['is_banned']}")
                        print(f"  Premium:    {a['is_premium']}")
                        print(f"  Golden:     {a['is_golden']}")
                        if self.pending_edits:
                            print("  Pending Changes:")
                            for f, v in self.pending_edits.items():
                                print(f"    {f} -> {v}")
                        print("")
                        break
                        
            elif base_cmd == "charinfo":
                if self.editing_mode != 2:
                    print("You must be in character edit mode (cedit <idx>) to run this command.")
                    continue
                # Display character info
                for c in self.characters:
                    if c["id"] == self.edit_char_id:
                        print(f"\nCharacter Info (ID: {c['id']}):")
                        print(f"  Name:           {c['name']}")
                        print(f"  Level:          {c['level']}")
                        print(f"  Position:       ({c['x']}, {c['y']})")
                        print(f"  Avatar ID:      {c['avatar']}")
                        print(f"  Dev Mode Flag:  {c['dev_mode']}")
                        print(f"  Class Template: {c['class_template']}")
                        print(f"  Online:         {c['is_online']}")
                        if self.pending_edits:
                            print("  Pending Changes:")
                            for f, v in self.pending_edits.items():
                                print(f"    {f} -> {v}")
                        print("")
                        break
                        
            elif base_cmd == "set":
                if self.editing_mode == 0:
                    print("You must enter edit mode (edit or cedit) before using set.")
                    continue
                if len(cmd) < 3:
                    print("Usage: set <field> <value>")
                    continue
                field, value = cmd[1], cmd[2]
                self.pending_edits[field] = value
                print(f"Staged edit: {field} = {value}")
                
            elif base_cmd == "save":
                if self.editing_mode == 0:
                    print("Nothing to save. Enter edit mode (edit or cedit) first.")
                    continue
                if not self.pending_edits:
                    print("No pending changes to save.")
                    continue
                
                success_all = True
                for field, value in list(self.pending_edits.items()):
                    if self.editing_mode == 1:
                        # Account
                        res = self.send_request({
                            "type": "admin_edit_account",
                            "account_id": self.edit_account_id,
                            "field": field,
                            "value": value
                        }, "admin_edit_account_response")
                    else:
                        # Character
                        res = self.send_request({
                            "type": "admin_edit_character",
                            "character_id": self.edit_char_id,
                            "field": field,
                            "value": value
                        }, "admin_edit_character_response")
                        
                    if res and res.get("success"):
                        self.pending_edits.pop(field)
                    else:
                        success_all = False
                        print(f"Failed to save {field}: {res.get('message') if res else 'No response'}")
                        
                if success_all:
                    print("All edits successfully saved to server database.")
                else:
                    print("Some changes could not be saved.")
                    
            elif base_cmd == "sitem":
                if not self.authed:
                    print("Please auth first.")
                    continue
                if len(cmd) < 3:
                    print("Usage: sitem <item_type> <item_id>")
                    print("  e.g. sitem 1 50  (search weapons with id 50)")
                    continue
                try:
                    item_type = int(cmd[1])
                    item_id = int(cmd[2])
                    res = self.send_request({
                        "type": "admin_search_item",
                        "item_type": item_type,
                        "item_id": item_id
                    }, "admin_search_item_response")
                    if res:
                        results = res.get("results", [])
                        print(f"\nFound {len(results)} matching items:")
                        print("Item DB ID | Qty | Container | Slot | Owner Name | Position")
                        print("------------------------------------------------------------")
                        for r in results:
                            print(f"{r['id']:10d} | {r['quantity']:3d} | {r['container']:9s} | {r['slot']:4d} | {r['owner_name']:10s} | ({r['x']}, {r['y']})")
                        print("")
                except ValueError:
                    print("Invalid item_type or item_id format.")
                    
            elif base_cmd == "servermessage":
                if not self.authed:
                    print("Please auth first.")
                    continue
                if len(cmd) < 2:
                    print("Usage: servermessage <text>")
                    continue
                text = " ".join(cmd[1:])
                res = self.send_request({
                    "type": "admin_server_message",
                    "message": text
                }, "admin_server_message_response")
                if res and res.get("success"):
                    print("Server message broadcasted successfully.")
                else:
                    print("Failed to broadcast server message.")
                    
            elif base_cmd == "forcedsave":
                if not self.authed:
                    print("Please auth first.")
                    continue
                res = self.send_request({"type": "admin_forced_save"}, "admin_forced_save_response")
                if res and res.get("success"):
                    print("Server database forced save executed successfully.")
                else:
                    print("Server database forced save failed.")
                    
            elif base_cmd in ("help", "?"):
                print("\nAvailable CLI commands:")
                print("  connect [host]                 Connect to server (default: 127.0.0.1)")
                print("  auth <username> <password>     Log in as admin")
                print("  listaccounts                   Retrieve and display account list")
                print("  listcharacters                 Retrieve and display character list")
                print("  edit <idx>                     Edit account at specified index")
                print("  cedit <idx>                    Edit character at specified index")
                print("  accinfo                        View currently selected account details")
                print("  charinfo                       View currently selected character details")
                print("  set <field> <value>            Stage an update to a field")
                print("  save                           Commit all staged edits to the server")
                print("  sitem <type> <id>              Search items across all owners/locations")
                print("  servermessage <text>           Broadcast a system announcement to all players")
                print("  forcedsave                     Force server to save all player progress")
                print("  exit / quit                    Exit current edit mode or quit the tool")
                print("")
            else:
                print(f"Unknown command: {base_cmd}. Type 'help' for details.")

if __name__ == "__main__":
    tool = AdminTool()
    tool.run_cli()
