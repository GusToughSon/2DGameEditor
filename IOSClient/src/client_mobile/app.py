import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
import os
import sys
import socket
import threading

# Add root folder of client_mobile to sys.path so modules resolve correctly
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CURRENT_DIR)

from core.packets import VERSION, pack_json, read_packet_sync
import client.network

class PlayerCityClient(toga.App):
    @property
    def main_win(self) -> toga.MainWindow:
        assert isinstance(self.main_window, toga.MainWindow)
        return self.main_window

    def startup(self):
        self.last_register_time = 0.0
        self.main_window = toga.MainWindow(title=self.formal_name)
        self.show_login_screen()

    def show_login_screen(self):
        main_box = toga.Box(style=Pack(direction=COLUMN, padding=20, background_color='#1e1e2e'))

        title_label = toga.Label(
            "ThePlayerCity",
            style=Pack(padding=(20, 0), font_size=28, font_weight="bold", color="#89b4fa", text_align="center")
        )

        subtitle_label = toga.Label(
            "iOS Launcher",
            style=Pack(padding=(0, 0, 20, 0), font_size=16, color="#cdd6f4", text_align="center")
        )

        # Server IP Address Input (Crucial for mobile client testing!)
        ip_box = toga.Box(style=Pack(direction=COLUMN, padding=(5, 0)))
        ip_box.add(toga.Label("Server IP Address:", style=Pack(color="#cdd6f4", font_size=12)))
        self.ip_input = toga.TextInput(value="192.168.1.47", style=Pack(background_color="#313244", color="#cdd6f4", padding=(5, 0)))
        ip_box.add(self.ip_input)

        # Username Input
        user_box = toga.Box(style=Pack(direction=COLUMN, padding=(5, 0)))
        user_box.add(toga.Label("Username:", style=Pack(color="#cdd6f4", font_size=12)))
        self.user_input = toga.TextInput(style=Pack(background_color="#313244", color="#cdd6f4", padding=(5, 0)))
        user_box.add(self.user_input)

        # Password Input
        pass_box = toga.Box(style=Pack(direction=COLUMN, padding=(5, 0)))
        pass_box.add(toga.Label("Password:", style=Pack(color="#cdd6f4", font_size=12)))
        self.pass_input = toga.PasswordInput(style=Pack(background_color="#313244", color="#cdd6f4", padding=(5, 0)))
        pass_box.add(self.pass_input)

        # Action Buttons Box
        btn_box = toga.Box(style=Pack(direction=ROW, padding=(15, 0)))
        login_btn = toga.Button("Login", on_press=self.handle_login, style=Pack(flex=1, padding=(0, 5)))
        register_btn = toga.Button("Register", on_press=self.handle_register, style=Pack(flex=1, padding=(0, 5)))
        btn_box.add(login_btn)
        btn_box.add(register_btn)

        # Status output
        self.status_label = toga.Label(
            "",
            style=Pack(padding=(15, 0), color="#f38ba8", font_size=12, text_align="center")
        )

        main_box.add(title_label)
        main_box.add(subtitle_label)
        main_box.add(ip_box)
        main_box.add(user_box)
        main_box.add(pass_box)
        main_box.add(btn_box)
        main_box.add(self.status_label)

        self.main_win.content = main_box
        self.main_win.show()

    def handle_login(self, widget, **kwargs):
        server_ip = self.ip_input.value.strip()
        username = self.user_input.value.strip()
        password = self.pass_input.value.strip()

        if not server_ip or not username or not password:
            self.status_label.text = "Fields cannot be empty"
            return

        self.status_label.text = "Connecting..."
        self.status_label.style.color = "#89b4fa"

        # Delegate networking connection off main thread so UI stays responsive
        threading.Thread(target=self._async_login, args=(server_ip, username, password), daemon=True).start()

    def _async_login(self, server_ip, username, password):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5.0)
            s.connect((server_ip, 1338))
            
            login_req = {
                "type": "login",
                "username": username,
                "password": password,
                "version": VERSION
            }
            s.sendall(pack_json(login_req))
            resp = read_packet_sync(s)
            s.close()

            if resp and resp.get("type") == "login_response":
                if resp.get("success", False):
                    slots = resp.get("slots", {})
                    classes = resp.get("classes", ["Plr_Male_Warrior", "Plr_Mage", "Plr_Rogue"])
                    # Transition to slot selector on main thread
                    self.add_background_task(lambda app, **kwargs: self.show_char_select(server_ip, username, password, slots, classes))
                else:
                    self.update_status("Invalid username or password.", "#f38ba8")
            else:
                self.update_status("Host disconnected unexpectedly.", "#f38ba8")
        except Exception as e:
            self.update_status(f"Connection failed: {e}", "#f38ba8")

    def handle_register(self, widget, **kwargs):
        import time
        from client.constants_loader import get_registration_timeout
        current_time = time.time()
        timeout = get_registration_timeout()
        if current_time - getattr(self, 'last_register_time', 0.0) < timeout:
            remaining = int(timeout - (current_time - getattr(self, 'last_register_time', 0.0)))
            self.status_label.text = f"Please wait {remaining}s to register again."
            self.status_label.style.color = "#f38ba8"
            return

        server_ip = self.ip_input.value.strip()
        username = self.user_input.value.strip()
        password = self.pass_input.value.strip()

        if not server_ip or not username or not password:
            self.status_label.text = "Fields cannot be empty"
            return

        self.last_register_time = current_time
        self.status_label.text = "Registering..."
        self.status_label.style.color = "#89b4fa"

        threading.Thread(target=self._async_register, args=(server_ip, username, password), daemon=True).start()

    def _async_register(self, server_ip, username, password):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5.0)
            s.connect((server_ip, 1338))
            
            register_req = {
                "type": "register",
                "username": username,
                "password": password
            }
            s.sendall(pack_json(register_req))
            resp = read_packet_sync(s)
            s.close()

            if resp and resp.get("type") == "register_response":
                if resp.get("success", False):
                    self.update_status("Registered! You can now log in.", "#a6e3a1")
                else:
                    err_msg = resp.get("error", "Registration failed.")
                    self.update_status(err_msg, "#f38ba8")
            else:
                self.update_status("Connection closed unexpectedly.", "#f38ba8")
        except Exception as e:
            self.update_status(f"Connection failed: {e}", "#f38ba8")

    def update_status(self, text, color):
        def _update(app, **kwargs):
            self.status_label.text = text
            self.status_label.style.color = color
        self.add_background_task(_update)

    def show_char_select(self, server_ip, username, password, slots, classes):
        main_box = toga.Box(style=Pack(direction=COLUMN, padding=20, background_color='#1e1e2e'))

        title_label = toga.Label(
            "Select Your Character",
            style=Pack(padding=(10, 0, 20, 0), font_size=22, font_weight="bold", color="#89b4fa", text_align="center")
        )
        main_box.add(title_label)

        # Render slot options (Max 2 slots supported)
        for i in range(2):
            is_used = False
            if slots.get("used") and i < len(slots["used"]):
                is_used = slots["used"][i]

            slot_box = toga.Box(style=Pack(direction=COLUMN, padding=10, background_color="#313244"))
            slot_label = toga.Label(f"Slot {i + 1}", style=Pack(font_weight="bold", color="#89b4fa"))
            slot_box.add(slot_label)

            if is_used:
                name = slots["names"][i]
                level = slots["levels"][i]
                hp = slots["hps"][i]
                hp_max = slots["hpmaxs"][i]

                info_label = toga.Label(
                    f"Name: {name}\nLevel: {level}\nHP: {hp}/{hp_max}",
                    style=Pack(color="#cdd6f4", padding=(5, 0))
                )
                slot_box.add(info_label)

                # Set closure play action
                def make_play_handler(slot_idx=i):
                    return lambda widget, **kwargs: self.launch_game(server_ip, username, password, slot_idx)

                play_btn = toga.Button("Play", on_press=make_play_handler(i), style=Pack(padding=(5, 0)))
                slot_box.add(play_btn)
            else:
                info_label = toga.Label("Empty Slot", style=Pack(color="#a6adc8", font_style="italic", padding=(5, 0)))
                slot_box.add(info_label)

                def make_create_handler(slot_idx=i):
                    return lambda widget, **kwargs: self.show_char_creation(server_ip, username, password, slot_idx, classes)

                create_btn = toga.Button("Create", on_press=make_create_handler(i), style=Pack(padding=(5, 0)))
                slot_box.add(create_btn)

            main_box.add(slot_box)
            main_box.add(toga.Box(style=Pack(height=15)))

        back_btn = toga.Button("Back to Login", on_press=lambda widget, **kwargs: self.show_login_screen(), style=Pack(padding=(10, 0)))
        main_box.add(back_btn)

        self.main_win.content = main_box

    def show_char_creation(self, server_ip, username, password, slot, classes):
        main_box = toga.Box(style=Pack(direction=COLUMN, padding=20, background_color='#1e1e2e'))

        title_label = toga.Label(
            f"Create Character (Slot {slot + 1})",
            style=Pack(padding=(10, 0, 20, 0), font_size=20, font_weight="bold", color="#89b4fa", text_align="center")
        )

        name_box = toga.Box(style=Pack(direction=COLUMN, padding=(5, 0)))
        name_box.add(toga.Label("Character Name:", style=Pack(color="#cdd6f4", font_size=12)))
        self.char_name_input = toga.TextInput(style=Pack(background_color="#313244", color="#cdd6f4", padding=(5, 0)))
        name_box.add(self.char_name_input)

        class_box = toga.Box(style=Pack(direction=COLUMN, padding=(5, 0)))
        class_box.add(toga.Label("Choose Class:", style=Pack(color="#cdd6f4", font_size=12)))
        self.class_input = toga.Selection(items=classes, style=Pack(padding=(5, 0)))
        class_box.add(self.class_input)

        def create_submit(widget, **kwargs):
            char_name = self.char_name_input.value.strip()
            selected_class = self.class_input.value
            if not char_name:
                self.char_status.text = "Character name cannot be empty."
                return
            self.char_status.text = "Creating character..."
            self.char_status.style.color = "#89b4fa"
            threading.Thread(target=self._async_create_char, args=(server_ip, username, password, char_name, selected_class, slot), daemon=True).start()

        create_btn = toga.Button("Create Character", on_press=create_submit, style=Pack(padding=(15, 0)))
        
        self.char_status = toga.Label("", style=Pack(padding=(10, 0), color="#f38ba8", font_size=12, text_align="center"))

        def cancel_create(widget, **kwargs):
            self.status_label.text = ""
            # Re-fetch character slots to refresh the select view
            self.handle_login(None)

        cancel_btn = toga.Button("Cancel", on_press=cancel_create, style=Pack(padding=(5, 0)))

        main_box.add(title_label)
        main_box.add(name_box)
        main_box.add(class_box)
        main_box.add(create_btn)
        main_box.add(self.char_status)
        main_box.add(cancel_btn)

        self.main_win.content = main_box

    def _async_create_char(self, server_ip, username, password, char_name, selected_class, slot):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5.0)
            s.connect((server_ip, 1338))
            
            req = {
                "type": "create_character",
                "username": username,
                "char_name": char_name,
                "class_template": selected_class,
                "slot": slot
            }
            s.sendall(pack_json(req))
            resp = read_packet_sync(s)
            s.close()
            
            if resp and resp.get("type") == "create_character_response" and resp.get("success"):
                # If successfully created, boot directly into the game
                self.add_background_task(lambda app, **kwargs: self.launch_game(server_ip, username, password, slot))
            else:
                err = resp.get("error", "Failed to create character.") if resp else "Server disconnected."
                self.add_background_task(lambda app, **kwargs: setattr(self.char_status, "text", err))
        except Exception as e:
            self.add_background_task(lambda app, **kwargs: setattr(self.char_status, "text", f"Error: {e}"))

    def launch_game(self, server_ip, username, password, slot_idx):
        print(f"[LAUNCHER] Launching client game engine for {username} in slot {slot_idx}...")
        
        # Override GameClientNetwork configuration to point to custom Server IP dynamically
        orig_init = client.network.GameClientNetwork.__init__
        client.network.GameClientNetwork.__init__ = lambda self, host=server_ip, port=1338: orig_init(self, host, port)

        # Hide Toga main window
        self.main_win.hide()

        # Run Pygame in a background thread so Toga remains active in main thread
        def run_pygame():
            try:
                from client.renderer import GameClientEngine
                engine = GameClientEngine()
                engine.username = username
                engine.password = password
                engine.char_slot = slot_idx
                engine.run()
            except Exception as e:
                print(f"[PYGAME ERROR] {e}")
            finally:
                # Once Pygame loop finishes, return back to selection/login screen on main thread
                self.add_background_task(lambda app, **kwargs: self.main_win.show())

        threading.Thread(target=run_pygame, daemon=True).start()

def main():
    return PlayerCityClient("ThePlayerCity Client", "com.gustoughson.client")
