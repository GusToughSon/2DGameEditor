# 🕹️✨ 2D Game Editor v2.1 ✨🕹️

Hello there, game maker! 🌸 Welcome to the **2D Game Editor**! This is a magical toolbox 🧰 that helps you create your very own retro 2D RPG games! ⚔️🛡️ 

Normally, making a game is hard because you have to draw pictures 🎨, design maps 🗺️, write databases 📊, and code code code 📜. But here, everything is linked together like magic! ✨ If you change a script file, the editor updates automatically! 🔄 And if you click buttons in the editor, your scripts update too! No messy setups! 🎀

---

## 🌟 Super Fun Features 🌟

### ⚡ Speedy Loading (No More Freezy Windows!) 🚀🌸
* **Soft & Smooth Transitions** 🍃: Before, when you clicked to open a window, the program would sometimes freeze and say "Not Responding" 😢. Now, the heavy stuff (loading files and images from your hard drive) is done secretly in the background by tiny helper threads! 🧵 The windows pop open immediately and smoothly! 🐇
* **Pre-Caching Magic** 🧠✨: The program starts loaded types in the background as soon as you open a project, making sure everything is ready to go when you are! ⏰
* **Background Image Loading** 🖼️💨: Huge tileset sheets are read in the background, so your tabs switch instantly with zero lag! 🏎️

### 🗺️ Smart World Editor Menu (Show Me the Real Items!) 🎒⚔️
* **Hairy Types Display** 🧸: When you are designing your maps and want to place a chest, tree, or sword, you don't just see a grid of nameless squares anymore! Now, the sidebar shows the actual **Names** (like "Longsword" or "Red Tree") and their icons! 🌲🗡️
* **Perfect Category Filters** 📂🌈:
  * **Objects Tab** 🪵: Shows all of your placeable obstacles, doors, chests, and scenery! 🗝️
  * **Items Tab** 🍎: Shows all of your cool gear! This includes Armor 🛡️, Gauntlets 🥊, Helmets 🪖, Leggings 👖, Plates 🔩, Shields 🛡️, Trinkets 💍, Weapons 🗡️, Consumables 🍞, and generic Items 🔑!
* **Moving Pictures (Animations!)** 🎬🍿: If your object has a moving sprite (like a flickering campfire 🔥), the sidebar will show the animation frame so you know exactly what it looks like in action! 🎬
* **Hidden Math Converter** 🔢🪄: When you click a cute item, the editor automatically converts it to its technical index number behind the scenes. This keeps your save files clean and working perfectly! 💾

### 🖌️ Cute Pixel Editor 🎨👾
* **Paint Like a Pro** 🖍️: Use the Pencil ✏️, Eraser 🧼, Eyedropper 👁️, and Paint Bucket 🪣 to draw custom 16x16 pixel sprites!
* **Mistake Protector** 🔄: Made a mistake? Just hit Undo ↩️ to go back in time! Or Redo ↪️ to go forward!
* **Fast Start** ⚡: Double-click any tile on your tileset sheet to pop open the drawing window instantly! 🚪

### 📜 Hairy Script Editor (The Game Brain) 🧠✍️
* **Template Generator** 📄🌱: Starting a new script? The editor spawns a template script file containing all the event hooks (like `OnUse`, `OnLook`, `OnTalk`) ready for you to customize! 🛠️
* **Simple Math & Words** ➕🗣️: Write scripts using normal signs (`+`, `-`) or easy words (`Plus`, `Random`, `GreaterThan`) so anyone can learn to code!
* **Rainbow Colors** 🌈: Your scripts are color-coded (syntax highlighted) so variables, commands, and comments are easy to read! 🎨

### 🧩 Prefabs & Map Grid 🧱🗺️
* **Chunk Maker** 🧱: Glue tiles together to make reusable 16x16 prefabs (like houses 🏠 or ponds 🐟) so you don't have to place tiles one by one!
* **Copy & Paste Grid** 📋: Copy blocks of tiles and paste them with a live outline helper showing where they will land! 🎯
* **Multi-Map Support** 🗺️🌐: Create huge Overworlds 🌲, dark Dungeons 💀, or cosy shop interiors 🏪 and swap between them instantly!
* **Points of Interest (POI)** 📍: Click to place warp points or spawn points, and refer to them in scripts instantly (e.g., `Teleport(ME, POI_TOWN_SQUARE)`)! 🌌

### 🛡️ Safe & Secure Saving 🔒💾
* **Central Lock System** 🔑: Multiple editors can be open at the same time without overwriting each other's work!
* **Atomic File Swapping** ⚛️: Saves are written to temporary sidecars first, so if your power cuts out, your main files are never corrupted! 🛡️
* **Cute `.sav` Files** 🎁: Your project packs up neatly into a single `.sav` file (which is actually a friendly `.zip` file in disguise if you want to open it manually)! 📦

---

## 🚀 How to Run the App! 🚀

### 🎒 What you need first
1. **Python 3** installed on your computer 🐍
2. The pillow library for handling images 🖼️:
   ```bash
   pip install Pillow pystray
   ```

### 🏁 Starting up
#### Windows Users (Super Easy!) 💻
* Just double-click the **`run.bat`** file! It finds Python, checks everything, and launches the app! 🚀

#### macOS & Linux Users 🐧🍎
* Open your terminal and type:
  ```bash
  python GameEditor.py
  ```

---

## 🏗️ Inside the Magic Toolbox (File Structure) 🏗️

* 🎮 **`GameEditor.py`**: The big boss window that manages all the other tools!
* 🎨 **`TilesetEditor.py`**: Manage your sprite sheets and tag solid/passable zones!
* 🖌️ **`PixelEditor.py`**: Your custom pixel drawing board!
* 🏷️ **`TypeEditor.py`**: Win95-style database manager for all your items and enemies!
* 📜 **`Hairy.py`**: The cute text editor where you write your game logic!
* 🧱 **`ChunkEditor.py`**: The prefabs room where you assemble 16x16 map chunks!
* 💾 **`SaveLogic.py`**: The brain that compresses and packages files safely!
* 📊 **`SkillsEditor.py`**: Define stats, experience curves, and level-ups!

---
Have fun building your dream worlds! 🌸✨ Let's make some games! 🕹️🎉
