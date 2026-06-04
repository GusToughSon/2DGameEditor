# 🕹️ 2D Game Editor v2.0

A professional, "Script-First" 2D Game Engine suite built for rapid RPG development. This editor unifies world design, pixel art creation, and complex scriptable logic into a single, bi-directionally synchronized environment.

![App Icon](Assets/EditorIcon.ico)

- **Proprietary .sav Archives**: Projects use a dedicated `.sav` extension for a professional game-engine identity (maintains ZIP compatibility for easy manual inspection).
- **High-Performance EditingPool**: Active projects are unzipped into a temporary hidden pool for lightning-fast manipulation.
- **Bi-Directional Logic Bridge**: Edit your `Types.hry` script or the Type Editor UI—changes flow both ways instantly to ensure object IDs never go out of sync.
- **POI Logic Sync**: Points of Interest placed on the World Map automatically generate logic constants (`POI_...`) in your scripting environment.

### 🖌️ Surgical Pixel Editor
- **Full Drawing Suite**: Pencil, Eraser, Color Picker, and Flood Fill tools optimized for 16x16 tiles.
- **Undo/Redo System**: Surgical history tracking for every pixel change.
- **Rapid Entry**: Double-click any tile in the Tileset Editor to instantly launch the Pixel suite.

### 📜 Hairy IDE
- **Master API Bible**: `Template.hry` acts as a live-seeding blueprint for all new scripts.
- **Math & Logic Suite**: Full support for both symbolic (+, -, *, /) and linguistic (Plus, Random, GreaterThan) script operations.
- **High-Contrast Highlighting**: Professional syntax engine for logic, engine methods, and character definitions.

### 🧩 Chunk & World Editor
- **The Piecemaker**: Create reusable 16x16 chunks with pencil, flood-fill, and eye-dropper tools.
- **Clipboard Management**: copy/paste tile blocks across chunks with precise visual previews.
- **World Map Grid**: Large-scale orchestration with ortho-navigation.
- **Multi-Map Support**: Define and manage multiple world grids (Overworld, Dungeons, Interiors) with instant bi-directional script synchronization.
- **POI Markers**: Integrated Logic Synchronization—place a point, and it’s instantly addressable in your hairy via `Teleport(ME, POI_LOCATION)`.

### 🎨 Tileset & Type Organization
- **Gameplay Tagging**: Tag tiles with logic like "Solid", "Window", or "Occlusion" directly on the sheet.
- **Family Sync**: The Type Editor family list synchronizes directly with `Defines.hry` (e.g., `FAM_TILES`, `FAM_NPC`).
- **Dynamic Types.hry**: A dedicated, auto-maintained script sidecar that organizes all your game objects by category for clean, professional logic development.
- **Clean Script Pipeline**: Retired the "Auto-Heal" engine to ensure user scripts remain exactly as written, while maintaining a robust manifest for new object types.

### 🛡️ Hardened & Robust I/O
- **Shared Locking System**: Prevents file access collisions between multiple open editors using a centralized I/O mutex.
- **Atomic File Swapping**: Protects master asset files from corruption by using temporary sidecar files for all disk writes.

---

## 🚀 Getting Started

### Prerequisites
- **Python 3.x**
- **Dependencies**:
  ```bash
  pip install Pillow pystray
  ```

### Running the Editor
#### Windows (Recommended)
Simply double-click **`run.bat`**. 
This script automatically locates your Python interpreter, verifies the environment, and launches the editor with a dedicated debug console.

#### Linux / macOS / Manual
```bash
python GameEditor.py
```

---

## 🛠️ Architecture

- **`GameEditor.py`**: Main controller and window manager.
- **`TilesetEditor.py`**: Asset management and property tagging.
- **`PixelEditor.py`**: Surgical 16x16 pixel-art creation.
- **`TypeEditor.py`**: Win95-style RPG object database manager.
- **`Hairy.py`**: Integrated IDE for scriptable logic.
- **`ChunkEditor.py`**: Tile-based 16x16 prefab designer.
- **`SaveLogic.py`**: ZIP-based project persistence and "EditingPool" logic.
- **`SkillsEditor.py`**: Progression and ability management.

---

## 📜 License
*This project is part of a custom 2D Game Engine suite.*
