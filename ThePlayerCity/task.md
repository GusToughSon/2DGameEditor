# Migration Task Tracker

## Priority 1 — Core Framework
- [x] `core/items.py` [NEW] — Item type definitions and enums
- [x] `core/creatures.py` [NEW] — Monster/NPC type definitions
- [x] `core/packets.py` — Expand with all packet formats
- [x] `core/models.py` — Add TempData, RaceInfo, GuildClass, enums
- [x] `core/config.py` [NEW] — HryParser for game config

## Priority 2 — Server Game Loop
- [x] `server/client_state.py` [NEW] — Connected client tracking
- [x] `server/game_loop.py` [NEW] — Main tick with monster AI, regen, spawns
- [x] `server/network.py` — Full packet routing
- [x] `server/combat.py` [NEW] — Damage calculations
- [x] `server/items.py` [NEW] — Inventory operations

## Priority 3 — Client Features
- [x] `client/renderer.py` — Other players, monsters, NPCs
- [x] `client/ui/` [NEW] — Backpack, stats, chat, equipment panels
- [x] `client/network.py` [NEW] — Live TCP connection to server

## Priority 4 — Advanced Systems
- [x] `server/chat.py`, `server/trade.py`, `server/guilds.py` [NEW]
- [x] `server/tradeskills.py` [NEW]
- [x] `server/admin.py` [NEW] — Full GM protocol

## Priority 5 — Editor Additions (2DGameEditor)
- [x] `UseableItemEditor.py`, `CollectableEditor.py` [NEW]
- [x] `MonsterTypeEditor.py` [NEW]
- [x] `SafeZoneEditor.py`, `NPCSpawnEditor.py` [NEW]

## Cleanup
- [x] Remove unused legacy directories (no legacy folder exists)
- [x] Remove git push-to-origin references
- [x] Copy editor implementation plan to `e:\2DGameEditor\`

