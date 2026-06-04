# Codebase Understanding: 2DGameEditor

## High-Level Overview
2DGameEditor is a specialized, production-ready suite for creating assets for 2D RPGs (specifically targeting Ultima-style top-down engines). It is built with Python 3, Tkinter for the UI, and Pillow (PIL) for heavy-duty image manipulation.

The editor is designed to handle Tilesets, NPC/Object Data, Animations, and Scripting (Hairy) in a unified, modular interface.

---

## Core Architecture and Design Patterns

### Project Persistence (The "Editing Pool")
Unlike editors that save hundreds of tiny files continuously, this editor uses a ZIP-based archival system:
- Zip Storage: Projects are stored as single .zip files in the Saves/ directory.
- EditingPool: When a project is opened, it is extracted into a temporary folder called EditingPool/. All active editing happens here.
- Atomic Saving: When the user clicks "Save", the EditingPool is re-zipped and replaces the original project file.
- Cleanup: On application exit, the EditingPool is wiped to ensure a clean state for the next session.

### Data Linking and Synchronization
The project maintains a tight link between graphics, metadata, and logic:
1. Tileset (PNG): The raw art.
2. TilesetTypes.json: Stores metadata about the tiles (e.g., "Is this tile solid?", "Does it block light?").
3. Types.json: The "Object Database". Defines RPG entities (e.g., "Iron Sword", "Human Guard"). A Type links to a specific tile in a tileset.
4. Hairy (.hry): Every Type can have a matching script file in the HAIRY/ directory. The editor automatically generates and syncs these scripts based on Type names.

---

## File-by-File Breakdown

### Controllers and Main Entry
- GameEditor.py: The "Grand Central Station". It manages the main window, project loading/creation, and launching sub-editors.
- config.py: The "Makeup Bag". Contains global UI constants (colors, fonts, versioning).
- run.bat / build_exe.bat: Windows scripts for running the app or building a standalone executable.

### Specialized Editors
- TilesetEditor.py: 
  - Manages world-level tiles.
  - Controls grid sizing (adding/removing rows/columns).
  - Handles "Gameplay Tagging" (Block Move, Occlusion, etc.).
  - Includes a "Zoom & Pan" canvas for browsing large sheets.
- TypeEditor.py:
  - A Win95-style database manager.
  - Creates and manages Types (Items, Monsters, Objects).
  - Synchronizes Type definitions with Hairy constants.
- PixelEditor.py:
  - A surgical 1-pixel-at-a-time editor (typically for 16x16 tiles).
  - Features Undo/Redo, Flood Fill, Color Picking, and an Asset Sidebar.
- AnimationEditor.py:
  - Manages sequences of frames.
  - Allows previewing animations and creating sequence metadata.
- Hairy.py:
  - A built-in code editor (IDE) for writing .hry scripts.
  - Includes basic syntax highlighting and file management.
- SkillEditor.py:
  - The Skills Editor.
  - Manages player skills, experience tables, and progression logic.

### Engine Logic and Utilities
- SaveLogic.py: The backbone of the persistence system. Handles ZIP compression, Extraction, and Workspace seeding.
- ScriptParser.py: Utility for parsing Hairy files and updating #Define constants in Defines.hry.
- NPCData.py: Dedicated module for editing complex NPC attributes.
- SecurityUtils.py: Cleanup and validation for file operations.
- EditorComponents.py: Small, reusable UI pieces (Status bars, custom dialogs).
- TilesetSelector.py: A specialized popup for picking a specific tile from a sheet.

---

## Key Workflows

### 1. The "Type-to-Script" Sync
When a new Type is created in TypeEditor.py:
1. It is assigned a unique ID.
2. An entry is added to Types.json.
3. ScriptParser.py adds a #Define TYPE_FAM_NAME [ID] to HAIRY/Defines.hry.
4. A stub .hry script is created in HAIRY/ using Template.hry as a guide.

### 2. Surgical Pixel Editing
A user can select a tile in the Tileset Editor and click "Pixel Edit". This launches PixelEditor.py with that specific tile. Once saved, the PixelEditor sends a callback to the TilesetEditor to update the master PNG sheet.

---

## Roadmap and Future Modules (Planned)
- Chunk Editor: Logic for grouping tiles into reusable 16x16 map chunks.
- World Map Editor: Grid stitcher for massive world maps (256x256).
- Hairy Engine: The runtime interpreter for executing the .hry scripts inside a game world.
