# Checklist for Implementing Independent Object Layer

- [x] Load `OBJECTS_TILESET.png` in `WorldEditor.py`
- [x] Refactor `_get_rendered_chunk` to support layer-specific rendering
- [x] Update cache invalidation methods to support layer-specific cache keys
- [x] Refactor `_draw_canvas` to render ground and object layers separately
- [x] Verify functionality (object placement, deletion, rendering, saving/loading)
