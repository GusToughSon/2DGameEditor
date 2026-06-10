# Implement Independent Object Layer in World Editor

This plan details the changes required to implement a distinct, separate object layer in the world editor. It ensures objects placed by the user are rendered and managed on top of the terrain layer using the correct objects tileset (`OBJECTS_TILESET.png`), integrating seamlessly with the existing chunk database system.

## Proposed Changes

### World Editor

#### [MODIFY] [WorldEditor.py](file:///e:/2DGameEditor/WorldEditor.py)

1. **Tileset Image Loading**:
   - In `__init__`, load `OBJECTS_TILESET.png` in addition to the ground tileset `World_TILESET.png`:
     ```python
     self.obj_tileset_img = self._load_obj_tileset()
     ```
   - Implement the helper method `_load_obj_tileset` to crop/load `OBJECTS_TILESET.png` from the project's `TILESET` directory.

2. **Separate Cache and Rendering**:
   - Refactor `_get_rendered_chunk(cid)` into a generic `_get_rendered_layer_chunk(self, cid, layer_name, tileset_img)` that renders a specific layer of a chunk using a specific tileset image.
   - Use composite cache keys:
     - PIL image cache key: `(cid, layer_name)`
     - PhotoImage cache key: `(cid, layer_name, zoom)`
   - Update `undo`, `redo`, and other methods that clear caches to clean up these keys properly.

3. **Layered Canvas Painting**:
   - In `_draw_canvas()`, render both layers for each visible chunk:
     - Render the `"ground"` layer using `World_TILESET.png` and add it to the canvas.
     - Render the `"objects"` layer using `OBJECTS_TILESET.png` and add it to the canvas on top of the terrain.

4. **Interaction Integrity**:
   - Ensure placing objects (in `"OBJECT"` mode) writes exclusively to the chunk's `"objects"` layer, and terrain tiles (in `"TILE"` mode) write to the `"ground"` layer. This is already supported by the editor's tool modes, but we will ensure it functions without interference.

---

## Verification Plan

### Automated Tests
- Since the codebase lacks automated UI tests, we will manually test the Tkinter UI.

### Manual Verification
- **Run the World Editor**:
  - Propose a command to run `GameEditor.py`.
  - Verify that the world map renders correctly (both ground and object layers are visible).
- **Test Object Placement**:
  - Switch tool mode to **Objects**.
  - Select an object from the palette (e.g. tree/decor) and paint it on the map.
  - Switch tool mode to **Tile**.
  - Paint a ground tile under/adjacent to the object and ensure the object remains intact on top.
  - Erase the object by painting a blank tile on the object layer and verify the ground tile is preserved underneath.
- **Verify Database Persistence**:
  - Save the project.
  - Restart the editor and verify the placed objects load back in their correct locations.
