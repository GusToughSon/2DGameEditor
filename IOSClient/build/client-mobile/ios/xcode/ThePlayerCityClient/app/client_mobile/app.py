import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

class PlayerCityClient(toga.App):
    def startup(self):
        main_box = toga.Box(style=Pack(direction=COLUMN, padding=10))

        name_label = toga.Label(
            "ThePlayerCity Client",
            style=Pack(padding=(0, 5), font_size=20, font_weight="bold")
        )

        status_label = toga.Label(
            "Welcome to ThePlayerCity Mobile Client",
            style=Pack(padding=(10, 5))
        )

        main_box.add(name_label)
        main_box.add(status_label)

        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_window.content = main_box
        self.main_window.show()

def main():
    return PlayerCityClient("ThePlayerCity Client", "com.gustoughson.client")
