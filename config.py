# ==============================================================================
# CONFIG.PY - THE PROJECT'S "MAKEUP BAG" (UI STYLES AND COLORS)
# ==============================================================================
# This file stores all the colors, fonts, and names so we don't have to 
# write them over and over again in the main code. 
# If you want to change how the app looks, change it HERE!
# ==============================================================================

# THE COLORS (Using "Hex Codes" like #RRGGBB)
# ------------------------------------------------------------------------------
COLOR_BG = "#c0c0c0"         # That classic medium-grey background (Classic Windows style)
COLOR_TITLE_BAR = "#000080"  # Dark Blue for the top of windows (Active window color)
COLOR_TITLE_TEXT = "white"   # White text so we can read it on the dark blue bar

# FRILLS AND BEZELS
COLOR_BEZEL_LIGHT = "#ffffff" # White for the highlights on buttons
COLOR_BEZEL_DARK = "#808080"  # Dark grey for the shadows on buttons

# THE FONTS (How the letters look)
# ------------------------------------------------------------------------------
# We use 'MS Sans Serif' because it looks like an old computer from the 90s.
# We added 'Arial' and 'sans-serif' as "backups" in case the first one is missing!
# 9 is the size (not too big, not too small).
FONT_UI = ("MS Sans Serif", 9, "normal")           # Standard text with fallbacks
FONT_TITLE = ("MS Sans Serif", 9, "bold")         # Thick text with fallbacks

# Note: Tkinter usually handles the list for us, but specifically naming fallbacks 
# in the string is better for some systems.
FONT_UI_LIST = ("MS Sans Serif", "Arial", "sans-serif")

# GENERAL APP INFO
# ------------------------------------------------------------------------------
APP_TITLE = "2DGameEditor" # The name that shows up at the very top of the window
VERSION = "2.0.3"           # The version number (Architectural Milestone)
CHUNK_SIZE = 16              # The size of a single chunk (16x16 tiles)
SAVES_DIR = "Saves"          # The folder where we keep all your project workspaces!

# EDITOR SETTINGS
UI_GRID_GAP = 3           # The space (in pixels) between images in the editor grid

# PERSISTENCE
LAST_PROJECT = "ThePlayerCity"
PROJECT_EXT = ".sav"

