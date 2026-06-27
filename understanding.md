# Codebase Understanding: 2DGameEditor

## 📖 High-Level Overview
**2DGameEditor** is a specialized, production-ready suite for designing assets, databases, and map chunks for 2D RPGs (specifically targeting Ultima-style top-down engines). It is built using **Python 3**, **Tkinter** for the desktop UI, and **Pillow (PIL)** for advanced image processing.

The suite integrates graphic design, database structure, and scriptable logic (`.hry` scripts) into a unified, bi-directionally synchronized workflow.

---

## 🗺️ Interactive Visual Node Reference

You can explore the entire codebase visually! Graphify has generated an interactive 3D node-graph map of the codebase architecture.
👉 **[Open the Visual Graph](file:///e:/2DGameEditor/graphify-out/graph.html)** (Click to open `graph.html` in your web browser)

---

## 🏛️ Graphify Architectural Insights (Auto-Generated)

Based on the knowledge graph extraction via [Graphify](https://github.com/safishamsi/graphify), the architecture exhibits highly cohesive communities with several dominant coordinator modules (God Nodes).

### 🌌 God Nodes & Central Coordinators
These are the most highly-connected files and form the backbone of the application architecture:
1. **`GameEditor.py` (62 edges):** The master orchestrator. Bridging almost all UI features (Tileset Editor, World Editor, Pixel Editor).
2. **`TilesetEditor.py` (59 edges):** The primary asset coordinator and visual manager. 
3. **`WorldEditor.py` (53 edges):** Handles the massive spatial canvas and layout interactions.
4. **`PixelEditor.py` (49 edges):** Advanced graphics suite heavily reliant on sub-components.
5. **`center_window()` (48 edges):** A globally utilized UI helper representing high component interdependence.
6. **`ChunkEditor.py` (44 edges)**
7. **`TilesetPalette` (35 edges)**
8. **`SaveLogic.py` (34 edges):** The persistence bridge between memory and the file system.

### 🌉 Cross-Community Bridges
- **`GameEditor`** acts as a bridge spanning across 25 different logical communities, orchestrating initialization, windows, background saves, and component launching.
- **`TilesetEditor`** spans across 10 distinct communities handling graphics rendering, metadata application, and database loading.
- **`center_window()`** is highly central, connecting UI windows spanning across the entire suite (Type Editors, Map Selectors, Notifications).

### 🔍 Hidden & Inferred Connections (Design Insights)
Graphify inferred several non-explicit architectural couplings:
- **`ChunkEditor`** heavily relies on **`TilesetPalette`** implicitly within `EditorComponents.py`.
- **`SaveLogic`** and **`WorldEditor`** are tightly coupled with **`DatabaseManager`** to execute atomic writes and large spatial array operations.
- The **`DebugUtils`** module acts as a shadow-dependency across multiple editors (`GameEditor`, `PixelEditor`) for tracer benchmarking.

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

## 🗂️ Module & Component Breakdown

### 🎮 Startup, Configuration & Automation Scripts
* **`GameEditor.py`**: The main entry point and coordinator. Builds the primary application workspace window, handles global menus, and orchestrates background saves.
* **`config.py`**: Central configuration repository. Defines standard colors, classic fonts (`MS Sans Serif`), app versioning (`VERSION`).
* **`run.bat` & `build_exe.bat`**: Windows bootstrap launcher and PyInstaller compiler script.
* **`increment_version.py`**: Automatic version incrementer script for the PyInstaller build sequence.

### 🛠️ Specialized UI Editors
* **`TilesetEditor.py`**: Manages pixel coordinates, grid sizes, and physical properties (solid, occlusion).
* **`TypeEditor.py`**: Win95-style metadata editor for designing item types.
* **`PixelEditor.py`**: Retro-style 16x16 tile painter with multi-step Undo/Redo histories.
* **`WorldEditor.py` & `ChunkEditor.py`**: Map landscape painters and prefab constructors.
* **`AnimationEditor.py`**: Visual timeline tool for sequencing multi-frame animations.
* **`SkillEditor.py`, `ShopEditor.py`, `MonsterSpawnEditor.py`, `LootEditor.py`**: Editors for establishing player progression, economy, mob spawns, and rewards.

### 🗃️ Engine Logic, Databases & Serialization
* **`SaveLogic.py`**: Engine orchestrator for unpacking/compressing project files and syncing changes atomically.
* **`ScriptParser.py` & `Hairy.py`**: Built-in IDE and parser for `.hry` logic scripts.
* **`DatabaseManager.py` & `WorldDatabaseManager.py`**: Read/write managers for 16x16 chunk packages and large world maps.
* **`BinaryDriver.py`**: High-performance binary codec that serializes raw game assets.

### 🛡️ Specialized Stat Sheets & Utilities
* **`NPCData.py`, `WeaponData.py`, `ArmorData.py`**: Creature and equipment statistics editors.
* **`TilesetSelector.py`**: Sub-palette pop-up selector rendering optimized grid views of tileset sheets.
* **`EditorComponents.py`**: Common shared widgets (e.g. `GameStatusBar`, `TilesetPalette`).
* **`SecurityUtils.py` & `DebugUtils.py`**: Security checks, hashing, and console performance tracing.
