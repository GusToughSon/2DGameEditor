import tkinter as tk
from tkinter import font
import ctypes
import os

font_path = r"e:\2DGameEditor\Assets\abaddon.TTF"
res = ctypes.windll.gdi32.AddFontResourceExW(font_path, 0x10, 0)
print(f"Font loaded: {res > 0}")

root = tk.Tk()
all_fonts = font.families()
# Filter for anything starting with 'A'
a_fonts = [f for f in all_fonts if f.lower().startswith('a')]
print("Available A-Fonts:", a_fonts)
root.destroy()
