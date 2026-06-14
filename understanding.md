# Codebase Understanding: 2DGameEditor

## 📖 High-Level Overview
**2DGameEditor** is a specialized, production-ready suite for designing assets, databases, and map chunks for 2D RPGs (specifically targeting Ultima-style top-down engines). It is built using **Python 3**, **Tkinter** for the desktop UI, and **Pillow (PIL)** for advanced image processing.

The suite integrates graphic design, database structure, and scriptable logic (`.hry` scripts) into a unified, bi-directionally synchronized workflow.

---

## 🏛️ Core Architecture and Design Patterns

### 💾 Project Persistence (The "Editing Pool")
Unlike editors that continuously write hundreds of tiny files, this editor packages projects into single folders or `.zip` files under `Saves/`:
* **Workspace Discovery**: Projects are loaded from directories or unzipped dynamically.
* **EditingPool**: When active, files reside in a temporary `EditingPool/` hidden directory for rapid manipulation and lock safety.
* **Atomic Save**: When saving, the pool is copied back to the workspace or re-zipped.
* **Cleanup**: Wipes the temporary `EditingPool/` upon closing.

### 🧵 Multi-threaded Background Asset Loading
To prevent blocking the main Tkinter thread (which causes GUI freezes or "Not Responding" hangs), the editor relies on daemon background threads:
* **Background Parsing**: `SaveLogic` pre-caches the entire Types database on startup.
* **Type Indexing**: Scanning the `HAIRY/` directory for script-defined types runs asynchronously in `TypeEditor` and `TilesetPalette`.
* **Tileset Preloading**: Heavy PIL image operations are threaded, loading sprite sheets on background threads and updating Tkinter `PhotoImage` objects via `.after(0, callback)`.

### 🔄 Bi-Directional Logic Bridge
Maintains strict consistency between game assets and logic scripts:
1. **Types Registry**: Definitions are read from modular family files `HAIRY/FAM_*.hry`.
2. **Auto-Generation**: Creating types in `TypeEditor` automatically writes `#Define` constants and generates `.hry` stub scripts based on `Template.hry`.
3. **Ghost Manifesting**: Creating `.hry` scripts directly on disk triggers automatic manifest ghost-creation in the editors so they are instantly placeable.

---

## 🗂️ Complete Directory & File-by-File Breakdown

Below is a detailed log of every file in the workspace directory and its inner workings:

### 🎮 Startup, Configuration & Automation Scripts
* **[GameEditor.py](GameEditor.py)**:
  * The main entry point and coordinator. It builds the primary application workspace window, handles global menus, configures taskbar/window icons (using `ctypes` on Windows), and orchestrates background saves.
  * Spawns all sub-editor windows and integrates a system tray icon via `pystray`.
* **[config.py](config.py)**:
  * Central configuration repository. Defines standard colors (Win95 silver, blue titles), classic fonts (`MS Sans Serif`), app versioning (`VERSION`), default chunk sizes, and the persistent tracking value for the last active project (`LAST_PROJECT`).
* **[EditorColors.py](EditorColors.py)**:
  * UI palette token system. Defines syntax-highlighting theme colors for comments, keywords, directives, brackets, and brackets in Hairy files, plus light/dark bezel shades.
* **[run.bat](run.bat)**:
  * Robust Windows bootstrap launcher. Automatically locates Python, installs missing libraries (`Pillow`, `pystray`), prevents active engine instance collision via `taskkill`, and safely runs `GameEditor.py`.
* **[build_exe.bat](build_exe.bat)**:
  * Production compiler using `PyInstaller`. Dynamically increments project version, embeds window resources, packages all sub-folders into a single standalone `.exe`, and clean-ups auxiliary build files.
* **[increment_version.py](increment_version.py)**:
  * Regex-based script that automatically increments the patch or minor version number in `config.py` as part of the PyInstaller build sequence.

---

### 🛠️ Specialized UI Editors
* **[TilesetEditor.py](TilesetEditor.py)**:
  * Manages the pixel coordinates, grid sizes, and physical collision/passability properties (e.g. solid, block magic, window, occlusion) of master tileset sheets.
  * Supports importing external PNG images directly into selected highlighted grid blocks and exporting updated sheets.
* **[TypeEditor.py](TypeEditor.py)**:
  * Win95-style metadata editor for designing item types.
  * Links type names to script families, custom characteristics (weight, mass, solid), animation timelines, and base tileset coordinates.
* **[PixelEditor.py](PixelEditor.py)**:
  * A retro-style 16x16 tile painter. Features grid view, color pickers, pencil, eraser, paint bucket tools, and multi-step Undo/Redo histories.
* **[AnimationEditor.py](AnimationEditor.py)**:
  * Visual timeline tool for sequencing multi-frame animations. Allows defining frame coordinates, playback durations, looping patterns, and real-time previews.
* **[WorldEditor.py](WorldEditor.py)**:
  * Large-scale map landscape painter. Orchestrates maps (Overworld, Dungeons) with coordinates, zoom/pan, culling, and Point of Interest (POI) management.
* **[ChunkEditor.py](ChunkEditor.py)**:
  * Prefab constructor for drafting 16x16 land modules. Allows copying, pasting, rotating, and stamp-painting pre-arranged layouts.
* **[Hairy.py](Hairy.py)**:
  * Built-in code IDE for Hairy (`.hry`) script writing. Features double-buffered text editors, custom line numbers, compile-checking, and syntax-based colorization.
* **[SkillEditor.py](SkillEditor.py)**:
  * Utility for establishing player character leveling paths, experience formulas, and unlockable abilities.
* **[ShopEditor.py](ShopEditor.py)**:
  * Visual editor for setting merchant stock lists, restock timers, buy/sell rate modifiers, and currency triggers.
* **[MonsterSpawnEditor.py](MonsterSpawnEditor.py)**:
  * Editor for setting monster spawns, spawn rates, boundaries, and maps.
* **[ObjectSheetEditor.py](ObjectSheetEditor.py)**:
  * Spreadsheet-style bulk list editor for rapid coordinate, text, and parameter adjustments across hundreds of items.
* **[LootEditor.py](LootEditor.py)**:
  * Configures loot drops, percentage chances, reward tiers, and dungeon chest spawners.

---

### 🗃️ Engine Logic, Databases & Serialization
* **[SaveLogic.py](SaveLogic.py)**:
  * Engine orchestrator for unpacking/compressing project files, syncing changes atomically, backing up active files, and pre-loading types databases on startup.
* **[ScriptParser.py](ScriptParser.py)**:
  * The syntax parser. Resolves script constants, extracts structured data from `.hry` files, and generates defines mappings for variables in the engine.
* **[DatabaseManager.py](DatabaseManager.py)**:
  * Read/write manager for storing 16x16 tile chunk packages in space-efficient formats.
* **[WorldDatabaseManager.py](WorldDatabaseManager.py)**:
  * Dedicated spatial data manager for reading and writing large world maps.
* **[BinaryDriver.py](BinaryDriver.py)**:
  * High-performance binary codec that serializes raw game assets, coordinates, and properties directly to custom byte streams.
* **[ChunkDatabase.py](ChunkDatabase.py)**:
  * Command-line processor that ingests raw CSV coordinates, maps ground/object tiles, and converts them into standardized 16x16 database structures.
* **[clean_types.py](clean_types.py)**:
  * Data hygiene tool that strips deprecated fields, normalizes family names, sorts alphabetically, and formats `Types.json`.

---

### 🛡️ Specialized Stat Sheets & Utilities
* **[NPCData.py](NPCData.py)**:
  * Creature statistics editor. Links combat statistics, levels, activities, and alignment properties directly to Hairy code defines.
* **[WeaponData.py](WeaponData.py)**:
  * Weapon statistics editor. Links class-based properties, damage bounds, and item requirements to Hairy code defines.
* **[ArmorData.py](ArmorData.py)**:
  * Shield and armor editor. Links durability parameters, magic modifiers, and skill requirements to Hairy code defines.
* **[TilesetSelector.py](TilesetSelector.py)**:
  * Sub-palette pop-up selector. Renders a single overlayed grid view of the tileset sheet, optimizing performance and eliminating rendering lag.
* **[EditorComponents.py](EditorComponents.py)**:
  * Common shared widgets. Includes `GameStatusBar`, `TilesetPalette`, `LoginNotification`, and window positioning helpers.
* **[DebugUtils.py](DebugUtils.py)**:
  * Console tracer with high-precision timestamping and context managers for performance benchmarking.
* **[SecurityUtils.py](SecurityUtils.py)**:
  * Security helpers. Generates SHA256 checksums and appends small random noise blocks to binary files to bypass antivirus heuristic false positives.

