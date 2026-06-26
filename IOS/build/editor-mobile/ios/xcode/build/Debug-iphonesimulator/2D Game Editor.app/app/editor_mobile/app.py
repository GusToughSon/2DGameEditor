import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
import os
import sys

# Ensure we can import our logic modules
# In a packaged app, the current directory should be src/editor_mobile
# We can also use relative imports since we are in the same package
try:
    from .logic import SaveLogic, config
except ImportError:
    # Fallback for local dev
    import logic.SaveLogic as SaveLogic
    import logic.config as config

class EditorMobile(toga.App):
    def startup(self):
        """
        Construct and show the Toga application.
        """
        # Set up the data path for iOS mapping
        if self.paths.data:
            # On iOS, self.paths.data points to the Library/Application Support directory
            data_dir = str(self.paths.data)
            os.makedirs(data_dir, exist_ok=True)
            # Update config to point to the correct directory in the iOS Sandbox
            config.SAVES_DIR = os.path.join(data_dir, "Saves")
            os.makedirs(config.SAVES_DIR, exist_ok=True)

        main_box = toga.Box(style=Pack(direction=COLUMN, padding=10))

        name_label = toga.Label(
            "2D Game Editor Mobile",
            style=Pack(padding=(0, 5), font_size=20, font_weight="bold")
        )

        version_label = toga.Label(
            f"Version: {config.VERSION}",
            style=Pack(padding=(0, 5))
        )

        status_label = toga.Label(
            "Ready to Load Project",
            style=Pack(padding=(10, 5))
        )
        self.status_label = status_label

        info_label = toga.Label(
            f"Deployment Target: iOS 17.0 (Xcode 26 Compatible)",
            style=Pack(padding=(10, 5), font_size=10, color="gray")
        )

        button_box = toga.Box(style=Pack(direction=ROW, padding=10))

        load_button = toga.Button(
            "Open Project Manager",
            on_press=self.handle_load_project,
            style=Pack(padding=5, flex=1)
        )

        main_box.add(name_label)
        main_box.add(version_label)
        main_box.add(status_label)
        main_box.add(button_box)
        main_box.add(info_label)
        button_box.add(load_button)

        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_window.content = main_box
        self.main_window.show()

    def handle_load_project(self, widget):
        self.status_label.text = "Browsing Projects..."
        # Logic to list projects in config.SAVES_DIR would go here
        # For now, just a POC message
        self.main_window.info_dialog(
            "Project Loader",
            f"Scanning for databases in:\n{config.SAVES_DIR}"
        )

def main():
    return EditorMobile("2D Game Editor", "com.gustoughson.editor")
