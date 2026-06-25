# Comprehensive Migration & Implementation Plan
## Memoria (C++) → ThePlayerCity (Python) + Editor Tools → 2DGameEditor

This plan audits **every feature** in the old Vorlia/Memoria C++ codebase and maps it to the Python remake in `ThePlayerCity`. Features already ported are marked ✅. Features needing implementation are detailed with their plan. Bloat and unused files are flagged for deletion.

> [!IMPORTANT]
> **Git Note:** All git push-to-origin capability has been flagged for removal. ThePlayerCity needs its own fresh git repo — that will be set up separately later.

---

## Source Material Reference

All original C++ source files live under `e:\Vorila\Memoria\`. Below is a quick-reference map so any AI agent can jump directly to the relevant file.

### Memoria Client — `e:\Vorila\Memoria\Memoria Client\`
| File | What It Contains |
|---|---|
| [main.h](file:///e:/Vorila/Memoria/Memoria%20Client/main.h) | Master header — all data structures: ItemClass, MapClass, TileClass, ClientClass, WeaponInfo, ArmorInfo, UseableItemStruct, MiscItemStruct, MapObjects, ObjectsStruct, LoginClass, containers, alignment tables, use/requirement/element enums |
| [main.cpp](file:///e:/Vorila/Memoria/Memoria%20Client/main.cpp) | Main game loop, packet handler dispatch, initialization |
| [draw.h](file:///e:/Vorila/Memoria/Memoria%20Client/draw.h) | DrawClass (all rendering functions), MessageBoxClass, CombatTextClass, MiscPicClass, equipment slot positions |
| [draw.cpp](file:///e:/Vorila/Memoria/Memoria%20Client/draw.cpp) | Full rendering implementation — world, characters, UI panels, items |
| [events.h](file:///e:/Vorila/Memoria/Memoria%20Client/events.h) | TargetClass (targeting system), WritingClass (text input/chat) |
| [events.cpp](file:///e:/Vorila/Memoria/Memoria%20Client/events.cpp) | Mouse/keyboard event handlers, click routing |
| [packets.h](file:///e:/Vorila/Memoria/Memoria%20Client/packets.h) | Client-side packet struct definitions |
| [Shop.h](file:///e:/Vorila/Memoria/Memoria%20Client/Shop.h) | shopclass — shop UI, buy/sell modes, item lists, price calc |
| [Shop.cpp](file:///e:/Vorila/Memoria/Memoria%20Client/Shop.cpp) | Shop rendering and interaction logic |
| [skills.h](file:///e:/Vorila/Memoria/Memoria%20Client/skills.h) | skillsclass, skillinfo — skill window UI and skill type enums |
| [skills.cpp](file:///e:/Vorila/Memoria/Memoria%20Client/skills.cpp) | Skill panel rendering and click handling |
| [Blacksmithing.h](file:///e:/Vorila/Memoria/Memoria%20Client/Blacksmithing.h) | BlackSmithingClass — forging UI |
| [Blacksmithing.cpp](file:///e:/Vorila/Memoria/Memoria%20Client/Blacksmithing.cpp) | Blacksmithing rendering, item list sorting, forge action |
| [Secure trade.h](file:///e:/Vorila/Memoria/Memoria%20Client/Secure%20trade.h) | SecureTradeClass — P2P trade window with locks |
| [Secure trade.cpp](file:///e:/Vorila/Memoria/Memoria%20Client/Secure%20trade.cpp) | Trade rendering, offer/accept/abort logic |
| [Clan deed.h](file:///e:/Vorila/Memoria/Memoria%20Client/Clan%20deed.h) | DeedClass — guild UI, member list, rank management |
| [Clan deed.cpp](file:///e:/Vorila/Memoria/Memoria%20Client/Clan%20deed.cpp) | Guild deed rendering and action handlers |
| [GMTool.h](file:///e:/Vorila/Memoria/Memoria%20Client/GMTool.h) | OnlineListClass — GM tool with player list, spawn mode, item mode, bank/backpack viewing |
| [GMTool.cpp](file:///e:/Vorila/Memoria/Memoria%20Client/GMTool.cpp) | GM tool rendering and admin action handlers |
| [Quickslots.h](file:///e:/Vorila/Memoria/Memoria%20Client/Quickslots.h) | Quick slots (hotbar) |
| [Identify.h](file:///e:/Vorila/Memoria/Memoria%20Client/Identify.h) | Item identify/tooltip system |
| [InfoMsg.h](file:///e:/Vorila/Memoria/Memoria%20Client/InfoMsg.h) | InfoMsgClass — server announcement messages |
| [drag.h](file:///e:/Vorila/Memoria/Memoria%20Client/drag.h) | DragClass — item drag & drop between containers |
| [Minimap.h](file:///e:/Vorila/Memoria/Memoria%20Client/Minimap.h) | MiniMap class |
| [body.h](file:///e:/Vorila/Memoria/Memoria%20Client/body.h) | Body/corpse rendering |
| [race.h](file:///e:/Vorila/Memoria/Memoria%20Client/race.h) | RaceInfo, RaceClass — race selection |
| [npc.h](file:///e:/Vorila/Memoria/Memoria%20Client/npc.h) | NPC rendering and data |
| [monsters.h](file:///e:/Vorila/Memoria/Memoria%20Client/monsters.h) | Monster rendering |
| [players.h](file:///e:/Vorila/Memoria/Memoria%20Client/players.h) | Player rendering |
| [sizes.h](file:///e:/Vorila/Memoria/Memoria%20Client/sizes.h) | Struct size constants |
| [surfaces.h](file:///e:/Vorila/Memoria/Memoria%20Client/surfaces.h) | SDL surface management |
| [VorliaSDL.h](file:///e:/Vorila/Memoria/Memoria%20Client/VorliaSDL.h) | SDL wrapper layer |
| [BFont.h](file:///e:/Vorila/Memoria/Memoria%20Client/BFont.h) | Bitmap font system |
| [button.h](file:///e:/Vorila/Memoria/Memoria%20Client/button.h) | UI button control |
| [textedit.h](file:///e:/Vorila/Memoria/Memoria%20Client/textedit.h) | Text edit input control |
| [textlink.h](file:///e:/Vorila/Memoria/Memoria%20Client/textlink.h) | Clickable text link control |
| [InitAll.h](file:///e:/Vorila/Memoria/Memoria%20Client/InitAll.h) | Initialization functions |
| [FileHandling.h](file:///e:/Vorila/Memoria/Memoria%20Client/FileHandling.h) | Binary .dat file I/O |
| [class_stringtable.hpp](file:///e:/Vorila/Memoria/Memoria%20Client/class_stringtable.hpp) | String table |

### Memoria Server — `e:\Vorila\Memoria\Memoria Server\`
| File | What It Contains |
|---|---|
| [main.h](file:///e:/Vorila/Memoria/Memoria%20Server/main.h) | All server packet structs (40+ types), GuildClass, GuildMember, BodyClass, ServerControlInfo, MapClass, TileClass, constants |
| [main.cpp](file:///e:/Vorila/Memoria/Memoria%20Server/main.cpp) | Server main loop, packet dispatch (238KB — the largest file), all game logic |
| [Client.h](file:///e:/Vorila/Memoria/Memoria%20Server/Client.h) | ClientClass — connected player state, combat targeting, tradeskill timers, GM mode, jail |
| [Client.cpp](file:///e:/Vorila/Memoria/Memoria%20Server/Client.cpp) | Combat logic, skill checks, level-up, guild ops, tradeskills, death penalty |
| [acco.h](file:///e:/Vorila/Memoria/Memoria%20Server/acco.h) | AccountManager, AccountData, CharacterData, SkillData, UserItem, Account, TempData — the core persistence model |
| [acco.cpp](file:///e:/Vorila/Memoria/Memoria%20Server/acco.cpp) | Account load/save (binary file I/O), character creation, stat reset |
| [Items.h](file:///e:/Vorila/Memoria/Memoria%20Server/Items.h) | WeaponInfo, ArmorInfo, UseableItemStruct, MiscItemStruct, ItemStruct, item family/type enums, all item operation function signatures |
| [Items.cpp](file:///e:/Vorila/Memoria/Memoria%20Server/Items.cpp) | Item creation, ground items, inventory moves, stacking, splitting, informing clients |
| [Monsters.h](file:///e:/Vorila/Memoria/Memoria%20Server/Monsters.h) | MonsterTypesStruct, MonsterClass, MonsterSpawnStruct, LootStruct, NPCTypesStruct, NPCClass, NPCSpawnStruct, ShopStorageClass — all creature definitions |
| [Monsters.cpp](file:///e:/Vorila/Memoria/Memoria%20Server/Monsters.cpp) | Monster/NPC AI (targeting, movement, attack, regen, berserk), spawn logic, loot drops, death penalty |
| [Secure trade.h](file:///e:/Vorila/Memoria/Memoria%20Server/Secure%20trade.h) | SecureTradeClass — server-side P2P trade with locks |
| [Secure trade.cpp](file:///e:/Vorila/Memoria/Memoria%20Server/Secure%20trade.cpp) | Trade execution and item swap logic |
| [Race.h](file:///e:/Vorila/Memoria/Memoria%20Server/Race.h) | RaceInfo, Avatar — race definitions with stat limits and avatars |
| [Race.cpp](file:///e:/Vorila/Memoria/Memoria%20Server/Race.cpp) | Race data loading |
| [objects.h](file:///e:/Vorila/Memoria/Memoria%20Server/objects.h) | MapObjects, ObjectsStruct, CrimSpawnList — world objects and criminal spawns |
| [objects.cpp](file:///e:/Vorila/Memoria/Memoria%20Server/objects.cpp) | Object interaction logic |
| [packets.h](file:///e:/Vorila/Memoria/Memoria%20Server/packets.h) | Packet size definitions |
| [Tables.cpp](file:///e:/Vorila/Memoria/Memoria%20Server/Tables.cpp) | Exp and skill level-up tables |
| [Initialize.cpp](file:///e:/Vorila/Memoria/Memoria%20Server/Initialize.cpp) | Server startup and data loading |

### Editor Tools
| File | What It Contains |
|---|---|
| [VorliaTools/main.cpp](file:///e:/Vorila/VorliaTools/main.cpp) | Admin CLI tool — connect, auth, request/edit accounts+chars, item search, server commands (952 lines) |
| [VorliaTools/main.h](file:///e:/Vorila/VorliaTools/main.h) | CToolsClass, NetworkingClass, ItemSearch — admin tool data structures |
| [VorliaTools/account.h](file:///e:/Vorila/VorliaTools/account.h) | AccountTool class |
| [VorliaTools/character.h](file:///e:/Vorila/VorliaTools/character.h) | CharacterTool class |
| [VorliaGraphicsConverter/main.cpp](file:///e:/Vorila/VorliaGraphicsConverter/main.cpp) | BMP→VDF graphics packer, OLD→NEW item struct converters |

### Python Remake (current state)
| File | What It Contains |
|---|---|
| [main.py](file:///e:/Vorila/ThePlayerCity/main.py) | Entry point — starts server + GUI |
| [core/models.py](file:///e:/Vorila/ThePlayerCity/core/models.py) | AccountData, CharacterData, SkillData, Account, TempData, RaceInfo, GuildClass |
| [core/packets.py](file:///e:/Vorila/ThePlayerCity/core/packets.py) | Login/creation packet formats |
| [core/maps.py](file:///e:/Vorila/ThePlayerCity/core/maps.py) | MapDatabase — SQLite world/chunk loading, tile access, passability |
| [core/crypto.py](file:///e:/Vorila/ThePlayerCity/core/crypto.py) | XOR cipher (key=212) |
| [core/items.py](file:///e:/Vorila/ThePlayerCity/core/items.py) | Item enums, type definitions, ItemDatabase |
| [core/creatures.py](file:///e:/Vorila/ThePlayerCity/core/creatures.py) | Monster/NPC types, spawns, shops, bodies, loot |
| [core/config.py](file:///e:/Vorila/ThePlayerCity/core/config.py) | HryParser, GameConfig with hot-reload watcher |
| [server/database.py](file:///e:/Vorila/ThePlayerCity/server/database.py) | JSON-based account persistence |
| [server/network.py](file:///e:/Vorila/ThePlayerCity/server/network.py) | Asyncio TCP server, login/auth flow |
| [server/gui.py](file:///e:/Vorila/ThePlayerCity/server/gui.py) | Tkinter server dashboard |
| [client/launcher.py](file:///e:/Vorila/ThePlayerCity/client/launcher.py) | Login UI, TCP connect, launches renderer |
| [client/renderer.py](file:///e:/Vorila/ThePlayerCity/client/renderer.py) | Pygame world renderer with tileset blitting |
| [editor/admin_tool.py](file:///e:/Vorila/ThePlayerCity/editor/admin_tool.py) | CLI admin tool skeleton |

### POC Server (reference only)
| File | What It Contains |
|---|---|
| [ThePlayerCityServer/server.py](file:///e:/2DGameEditor/ThePlayerCityServer/server.py) | FastAPI+WebSocket POC — HryParser, BinaryDriver (WBF!) map loading, .hry hot-reload, chunk caching, passability validation |
| [ThePlayerCityServer/game.js](file:///e:/2DGameEditor/ThePlayerCityServer/game.js) | Browser-based game renderer (reference only) |

---

## Part 1: Memoria → ThePlayerCity Audit

### 1.1 Core Data Models — [core/models.py](file:///e:/Vorila/ThePlayerCity/core/models.py)

All core data models are successfully ported.
---

### 1.2 Item System — [core/items.py](file:///e:/Vorila/ThePlayerCity/core/items.py)

All item data structs are successfully ported.
---

### 1.3 Monster & NPC System — [core/creatures.py](file:///e:/Vorila/ThePlayerCity/core/creatures.py)

All monster & NPC state structures are successfully ported.
---

### 1.4 Map System — [core/maps.py](file:///e:/Vorila/ThePlayerCity/core/maps.py) — ✅ DONE

Map database and chunk loader are successfully ported.
---

### 1.5 Packet Protocol — [core/packets.py](file:///e:/Vorila/ThePlayerCity/core/packets.py)

All server packet structs are defined in [main.h (server):216-720](file:///e:/Vorila/Memoria/Memoria%20Server/main.h#L216-L720). Client-side packet structs are in [packets.h (client)](file:///e:/Vorila/Memoria/Memoria%20Client/packets.h).

| Packet Type | Python Status | C++ Reference |
|---|---|---|
| P_OWNCHARINFO | ⚠️ Partial | Format string defined but not fully used in game loop |
| PACKET_PLAYERINFO | ❌ **NEEDS IMPL** | [main.h:313](file:///e:/Vorila/Memoria/Memoria%20Server/main.h#L313-L331) — Other player broadcast |
| PACKET_COORDINATES | ❌ **NEEDS IMPL** | [main.h:368](file:///e:/Vorila/Memoria/Memoria%20Server/main.h#L368-L373) — Movement broadcast |
| PACKET_CHATMESSAGE | ❌ **NEEDS IMPL** | [main.h:375](file:///e:/Vorila/Memoria/Memoria%20Server/main.h#L375-L379) — Message[120], MsgType |
| PACKET_ITEMMOVE | ❌ **NEEDS IMPL** | [main.h:381](file:///e:/Vorila/Memoria/Memoria%20Server/main.h#L381-L389) — Case, ItemID, ToList, FromList, x, y, Amount |
| PACKET_MONSTER | ❌ **NEEDS IMPL** | [main.h:428](file:///e:/Vorila/Memoria/Memoria%20Server/main.h#L428-L437) — KnowID, X, Y, HPLeft, Type |
| PACKET_NPC | ❌ **NEEDS IMPL** | [main.h:398](file:///e:/Vorila/Memoria/Memoria%20Server/main.h#L398-L403) — X, Y, HP, ID, conv_id, type |
| PACKET_SHOPITEM | ❌ **NEEDS IMPL** | [main.h:439](file:///e:/Vorila/Memoria/Memoria%20Server/main.h#L439-L443) — RealID, ID, Type, Family |
| PACKET_BUY | ❌ **NEEDS IMPL** | [Items.h:284](file:///e:/Vorila/Memoria/Memoria%20Server/Items.h#L284-L288) — ID[8], Amount[8] |
| PACKET_STATS | ❌ **NEEDS IMPL** | [main.h:287](file:///e:/Vorila/Memoria/Memoria%20Server/main.h#L287-L291) — Str, Con, Dex, Int, DamMin, DamMax |
| PACKET_SKILL | ❌ **NEEDS IMPL** | [main.h:300](file:///e:/Vorila/Memoria/Memoria%20Server/main.h#L300-L305) — This, SkillLevel, SkillExp |
| PACKET_LEVELUP | ❌ **NEEDS IMPL** | [main.h:445](file:///e:/Vorila/Memoria/Memoria%20Server/main.h#L445-L450) — Level, Statpoints, HPMax |
| PACKET_BODY | ❌ **NEEDS IMPL** | [main.h:642](file:///e:/Vorila/Memoria/Memoria%20Server/main.h#L642-L658) — Body/corpse info |
| PACKET_WHISPERTO | ❌ **NEEDS IMPL** | [main.h:667](file:///e:/Vorila/Memoria/Memoria%20Server/main.h#L667-L671) — name[25], msg[90] |
| PACKET_GUILDMSGTO | ❌ **NEEDS IMPL** | [main.h:674](file:///e:/Vorila/Memoria/Memoria%20Server/main.h#L674-L678) — tag[5], msg[90] |
| PACKET_TELEPORT* | ❌ **NEEDS IMPL** | [main.h:505](file:///e:/Vorila/Memoria/Memoria%20Server/main.h#L505-L524) — Self/Other/To teleport packets |
| PACKET_MOTDLINE | ❌ **NEEDS IMPL** | [main.h:362](file:///e:/Vorila/Memoria/Memoria%20Server/main.h#L362-L366) — Type, Msg[60] |
| GM/Admin packets (125.x) | ⚠️ Partial | Admin connect (125,2) works; full GM protocol in [VorliaTools/main.cpp](file:///e:/Vorila/VorliaTools/main.cpp) |
| All remaining combat/trade/guild packets | ❌ **NEEDS IMPL** | ~15 additional packet types in [main.h (server)](file:///e:/Vorila/Memoria/Memoria%20Server/main.h#L216-L720) |

#### Plan — `core/packets.py` expansion:
```
- Add all packet format strings and pack/unpack helpers
- Use Enum for packet IDs instead of magic numbers
- Group by category: Auth, Movement, Combat, Items, Chat, Guild, Admin, Trade
```

---

### 1.6 Encryption — `core/crypto.py`

Encryption/decryption protocols successfully ported.
---

### 1.7 Server — `server/`

| Memoria Server Feature | Python Status | C++ Reference |
|---|---|---|
| **Admin tool connect** (packet 125) | ⚠️ Partial | Connects but no full command protocol — see [VorliaTools/main.cpp](file:///e:/Vorila/VorliaTools/main.cpp) |
| **Character Creation** | ❌ **NEEDS IMPL** | [acco.cpp](file:///e:/Vorila/Memoria/Memoria%20Server/acco.cpp) — NewChar(), name validation, race selection, starting stats |
| **Movement broadcasting** | ❌ **NEEDS IMPL** | [main.cpp (server)](file:///e:/Vorila/Memoria/Memoria%20Server/main.cpp) — CheckPlayersOnScreen, coordinate broadcasting |
| **Combat system** | ❌ **NEEDS IMPL** | [Client.cpp](file:///e:/Vorila/Memoria/Memoria%20Server/Client.cpp) — PlayerAction_AttackToMonster/Player/NPC |
| **Monster AI** | ❌ **NEEDS IMPL** | [Monsters.cpp](file:///e:/Vorila/Memoria/Memoria%20Server/Monsters.cpp) — MonsterAction_HasTarget, Move, Attack, Regenerate, Berserk |
| **NPC AI** | ❌ **NEEDS IMPL** | [Monsters.cpp](file:///e:/Vorila/Memoria/Memoria%20Server/Monsters.cpp) — NPCAction_* functions, guard aggro, walking |
| **Item management** | ❌ **NEEDS IMPL** | [Items.cpp](file:///e:/Vorila/Memoria/Memoria%20Server/Items.cpp) — CreateItemToGround, RemoveItemFromPlayer, InformPlayerofItem |
| **Loot system** | ❌ **NEEDS IMPL** | [Monsters.cpp](file:///e:/Vorila/Memoria/Memoria%20Server/Monsters.cpp) — DropLoot; [Client.cpp](file:///e:/Vorila/Memoria/Memoria%20Server/Client.cpp) — CreateBody |
| **Shop system** | ❌ **NEEDS IMPL** | [main.cpp (server)](file:///e:/Vorila/Memoria/Memoria%20Server/main.cpp) — Buy/sell with NPC shops |
| **Skill system** | ❌ **NEEDS IMPL** | [Client.cpp](file:///e:/Vorila/Memoria/Memoria%20Server/Client.cpp) — CheckSkillLevelGain, InformPlayerOfNewSkill |
| **Level/Exp system** | ❌ **NEEDS IMPL** | [Client.cpp](file:///e:/Vorila/Memoria/Memoria%20Server/Client.cpp) — CheckLevelGain, GetHPMax; [Tables.cpp](file:///e:/Vorila/Memoria/Memoria%20Server/Tables.cpp) |
| **Guild system** | ❌ **NEEDS IMPL** | [main.h:547](file:///e:/Vorila/Memoria/Memoria%20Server/main.h#L547-L565) — GuildClass; [Client.cpp](file:///e:/Vorila/Memoria/Memoria%20Server/Client.cpp) — BuyGuild, Check_Guild |
| **Secure Trade** | ❌ **NEEDS IMPL** | [Secure trade.cpp (server)](file:///e:/Vorila/Memoria/Memoria%20Server/Secure%20trade.cpp) — do_trade, Abort, timeCheck |
| **Blacksmithing/Tradeskills** | ❌ **NEEDS IMPL** | [Client.cpp](file:///e:/Vorila/Memoria/Memoria%20Server/Client.cpp) — PlayerAction_Mine/Smelt/ForgeItem |
| **Reputation/Alignment** | ❌ **NEEDS IMPL** | [Client.h:33](file:///e:/Vorila/Memoria/Memoria%20Server/Client.h#L33-L37) — constants; [Client.cpp](file:///e:/Vorila/Memoria/Memoria%20Server/Client.cpp) — report_repupoints |
| **Death/Respawn** | ❌ **NEEDS IMPL** | [Monsters.cpp](file:///e:/Vorila/Memoria/Memoria%20Server/Monsters.cpp) — DeathPenalty; [Client.cpp](file:///e:/Vorila/Memoria/Memoria%20Server/Client.cpp) — CreateBody |
| **Jail system** | ❌ **NEEDS IMPL** | [Monsters.h:365](file:///e:/Vorila/Memoria/Memoria%20Server/Monsters.h#L365-L366) — JailPlayer, ReleaseFromJail |
| **Chat system** | ❌ **NEEDS IMPL** | [main.cpp (server)](file:///e:/Vorila/Memoria/Memoria%20Server/main.cpp) — Say, Whisper, Global, Guild channels |
| **GM commands** | ❌ **NEEDS IMPL** | [main.cpp (server)](file:///e:/Vorila/Memoria/Memoria%20Server/main.cpp) — packet 125 handler; [VorliaTools/main.cpp](file:///e:/Vorila/VorliaTools/main.cpp) |
| **MOTD** | ❌ **NEEDS IMPL** | [main.h:362](file:///e:/Vorila/Memoria/Memoria%20Server/main.h#L362-L366) — PACKET_MOTDLINE |
| **IP banning** | ❌ **NEEDS IMPL** | [acco.h:8](file:///e:/Vorila/Memoria/Memoria%20Server/acco.h#L8) — IPBanned() |
| **Server control** | ❌ **NEEDS IMPL** | [main.h:695](file:///e:/Vorila/Memoria/Memoria%20Server/main.h#L695-L700) — ServerControlInfo |
| **Auto-save** | ❌ **NEEDS IMPL** | [acco.h:34](file:///e:/Vorila/Memoria/Memoria%20Server/acco.h#L34-L36) — CheckSave/DoSave |
| **Exp/Skill/Alignment tables** | ❌ **NEEDS IMPL** | [Tables.cpp](file:///e:/Vorila/Memoria/Memoria%20Server/Tables.cpp) — CreateTables() |
| **Version check** | ⚠️ Partial | VERSION constant exists but not enforced on login |

#### Plan — Server implementation phases:

**Phase 4 — Items & Economy:**
- [NEW] `server/items.py` — Item creation, movement, stacking, durability
- Shop buy/sell
- Loot drops from monsters

**Phase 5 — Social & Trade:**
- [NEW] `server/chat.py` — Chat channels and muting
- [NEW] `server/trade.py` — Secure P2P trade
- [NEW] `server/guilds.py` — Full guild system

**Phase 6 — Tradeskills:**
- [NEW] `server/tradeskills.py` — Mining, Smelting, Forging pipeline

**Phase 7 — Administration:**
- [NEW] `server/admin.py` — Full GM command protocol
- Expand `server/gui.py` — Character editor, item search, server controls

---

### 1.8 Client — `client/`

All client rendering is in [draw.cpp](file:///e:/Vorila/Memoria/Memoria%20Client/draw.cpp) + [draw.h](file:///e:/Vorila/Memoria/Memoria%20Client/draw.h). Input handling is in [events.cpp](file:///e:/Vorila/Memoria/Memoria%20Client/events.cpp) + [events.h](file:///e:/Vorila/Memoria/Memoria%20Client/events.h). Main loop is in [main.cpp (client)](file:///e:/Vorila/Memoria/Memoria%20Client/main.cpp).

| Memoria Client Feature | Python Status | C++ Reference |
|---|---|---|
| **Character select screen** | ✅ **DONE** | [draw.h:30](file:///e:/Vorila/Memoria/Memoria%20Client/draw.h#L30) — DrawCharChoosePics/Texts |
| **Character creation screen** | ✅ **DONE** | [main.h:371](file:///e:/Vorila/Memoria/Memoria%20Client/main.h#L371-L406) — LoginClass |
| **Backpack UI** | ✅ **DONE** | [draw.h:30](file:///e:/Vorila/Memoria/Memoria%20Client/draw.h#L30) — DrawBackpack |
| **Bank UI** | ❌ **NEEDS IMPL** | [draw.h:36](file:///e:/Vorila/Memoria/Memoria%20Client/draw.h#L36) — DrawBank |
| **Equipment/Worn items UI** | ✅ **DONE** | [draw.h:37](file:///e:/Vorila/Memoria/Memoria%20Client/draw.h#L37) — DrawWearedItems; slot positions at [draw.h:160](file:///e:/Vorila/Memoria/Memoria%20Client/draw.h#L160-L177) |
| **Stats panel** | ✅ **DONE** | [draw.h:33](file:///e:/Vorila/Memoria/Memoria%20Client/draw.h#L33) — DrawStats |
| **Skills panel** | ❌ **NEEDS IMPL** | [skills.h](file:///e:/Vorila/Memoria/Memoria%20Client/skills.h) — skillsclass |
| **Chat box** | ✅ **DONE** | [draw.h:75](file:///e:/Vorila/Memoria/Memoria%20Client/draw.h#L75-L94) — MessageBoxClass |
| **Combat text** | ✅ **DONE** (routed to chat box) | [draw.h:100](file:///e:/Vorila/Memoria/Memoria%20Client/draw.h#L100-L116) — CombatTextClass |
| **Minimap** | ✅ **DONE** | [Minimap.h](file:///e:/Vorila/Memoria/Memoria%20Client/Minimap.h) |
| **Mouse targeting** | ✅ **DONE** | [events.h:18](file:///e:/Vorila/Memoria/Memoria%20Client/events.h#L18-L35) — TargetClass |
| **Item drag & drop** | ✅ **DONE** | [drag.h](file:///e:/Vorila/Memoria/Memoria%20Client/drag.h) |
| **Item identify/tooltip** | ✅ **DONE** | [Identify.h](file:///e:/Vorila/Memoria/Memoria%20Client/Identify.h) |
| **Shop UI** | ❌ **NEEDS IMPL** | [Shop.h](file:///e:/Vorila/Memoria/Memoria%20Client/Shop.h) — shopclass |
| **Secure trade UI** | ❌ **NEEDS IMPL** | [Secure trade.h](file:///e:/Vorila/Memoria/Memoria%20Client/Secure%20trade.h) — SecureTradeClass |
| **Blacksmithing UI** | ❌ **NEEDS IMPL** | [Blacksmithing.h](file:///e:/Vorila/Memoria/Memoria%20Client/Blacksmithing.h) — BlackSmithingClass |
| **Guild deed UI** | ❌ **NEEDS IMPL** | [Clan deed.h](file:///e:/Vorila/Memoria/Memoria%20Client/Clan%20deed.h) — DeedClass |
| **GM Tool UI** | ✅ **DONE** | [GMTool.h](file:///e:/Vorila/Memoria/Memoria%20Client/GMTool.h) — OnlineListClass |
| **Quick slots** | ❌ **NEEDS IMPL** | [Quickslots.h](file:///e:/Vorila/Memoria/Memoria%20Client/Quickslots.h) |
| **Other players rendering** | ✅ **DONE** | [draw.h:35](file:///e:/Vorila/Memoria/Memoria%20Client/draw.h#L35) — DrawCharacters |
| **Monster rendering** | ❌ **NEEDS IMPL** | [monsters.h](file:///e:/Vorila/Memoria/Memoria%20Client/monsters.h) |
| **NPC rendering** | ❌ **NEEDS IMPL** | [npc.h](file:///e:/Vorila/Memoria/Memoria%20Client/npc.h) |
| **Ground items rendering** | ❌ **NEEDS IMPL** | [draw.h:38](file:///e:/Vorila/Memoria/Memoria%20Client/draw.h#L38) — DrawGroundItems |
| **Body/Corpse rendering** | ❌ **NEEDS IMPL** | [draw.h:51](file:///e:/Vorila/Memoria/Memoria%20Client/draw.h#L51) — DrawOpenBody |
| **Animations** | ❌ **NEEDS IMPL** | Water, object, monster, player frame cycling |
| **Options menu** | ❌ **NEEDS IMPL** | [main.h:416](file:///e:/Vorila/Memoria/Memoria%20Client/main.h#L416-L464) — ClientClass settings |
| **Help screen** | ❌ **NEEDS IMPL** | [draw.h:46](file:///e:/Vorila/Memoria/Memoria%20Client/draw.h#L46) — Help() |
| **Info messages** | ❌ **NEEDS IMPL** | [InfoMsg.h](file:///e:/Vorila/Memoria/Memoria%20Client/InfoMsg.h) — InfoMsgClass |
| **WASD movement** | ❌ **NEEDS IMPL** | [main.h:434](file:///e:/Vorila/Memoria/Memoria%20Client/main.h#L434) — ClientClass.WASD |
| **Mouse movement** | ❌ **NEEDS IMPL** | [main.h:458](file:///e:/Vorila/Memoria/Memoria%20Client/main.h#L458) — ClientClass.Mousemove |
| **Login/register from client** | ✅ **DONE** | Account creation packet sending |

#### Plan — Client implementation phases:

**Phase 4 — Advanced UI:**
- Shop, Bank, Trade, Guild, Blacksmithing windows
- Item drag & drop
- Tooltips

---

### 1.9 Editor/Admin Tool — [editor/admin_tool.py](file:///e:/Vorila/ThePlayerCity/editor/admin_tool.py)

#### [NEW] [admin.py](file:///e:/Vorila/ThePlayerCity/server/admin.py)
A new server module to handle all incoming admin/GM command requests and securely modify accounts or characters in the SQLite database.
- Admin authentication checks if a character on the specified account has `dev_mode >= 1`.
- Provides commands to:
  - List all accounts and characters.
  - Load and edit account fields (`is_banned`, `is_premium`, `is_golden`).
  - Load and edit character fields (`x`, `y`, `level`, `str`, `con`, `dex`, `int`, `dev_mode`, `avatar`, `hp_left`, `hp_max`, `mana_left`).
  - Search items across all characters, grounds, banks, and worn slots in SQLite.
  - Trigger forced server-wide data save.
  - Broadcast system messages to all online players.

#### [MODIFY] [network.py](file:///e:/Vorila/ThePlayerCity/server/network.py)
- Route new packet types: `admin_auth`, `admin_request_accounts`, `admin_request_characters`, `admin_edit_account`, `admin_edit_character`, `admin_search_item`, `admin_server_message`, `admin_forced_save`.
- Call handlers in `server/admin.py` to process requests and send back corresponding JSON responses.

#### [MODIFY] [admin_tool.py](file:///e:/Vorila/ThePlayerCity/editor/admin_tool.py)
- Fully implement CLI commands matching the C++ console:
  - `connect [host]` — Connect to the server.
  - `auth [username] [password]` — Log in as admin.
  - `listaccounts` — List accounts retrieved from the server.
  - `listcharacters` — List characters retrieved from the server.
  - `edit [idx]` — Select account index from list to edit.
  - `cedit [idx]` — Select character index from list to edit.
  - `accinfo` — Print current info of the selected account.
  - `charinfo` — Print current info of the selected character.
  - `set [field] [value]` — Modify a field on the currently selected account/character (e.g. `set is_banned 1`, `set level 50`).
  - `save` — Commit modifications of the currently selected account/character to the server.
  - `sitem [item_type] [item_id]` — Search for item instances.
  - `servermessage [text]` — Broadcast message to all online clients.
  - `forcedsave` — Instruct server to save all player progress.
  - `exit` / `quit` — Exit current editing mode or close the tool.

---

### Verification Plan

#### Automated Verification
We will run `python -m editor.admin_tool` and check:
1. TCP connection and authentication succeeds for a GM account.
2. Listing all accounts/characters returns expected database entries.
3. Editing account flags and character stats propagates to the server and updates SQLite correctly.
4. System message broadcast prints to the live game client chat overlay.
5. Item search accurately displays current slot and owner details.

## Part 2: Files to DELETE from `e:\Vorila\Memoria`

Files under e:\Vorila\Memoria\ are marked for deletion once porting is finalized.
## Part 3: Editor Tools → 2DGameEditor Migration

### 3.1 Vorlia-Master-Editor → 2DGameEditor

The Vorlia-Master-Editor is a **legacy C++ SDL editor** for editing game data files. The 2DGameEditor already has Python equivalents for most of this functionality. What needs to be migrated:

| Editor Feature (C++ .exe) | 2DGameEditor Equivalent | Status |
|---|---|---|
| Item editor (data03.dat = weapons/armors/useables/collectables) | [WeaponData.py](file:///e:/2DGameEditor/WeaponData.py), [ArmorData.py](file:///e:/2DGameEditor/ArmorData.py) | ⚠️ Partial — missing UseableItems and Collectables editors |
| Monster type editor (data05.dat) | [MonsterSpawnEditor.py](file:///e:/2DGameEditor/MonsterSpawnEditor.py) | ⚠️ Partial — spawn editor exists but not full type editor |
| Object type editor (objecttypes.dat) | [ObjectSheetEditor.py](file:///e:/2DGameEditor/ObjectSheetEditor.py) | ⚠️ Partial |
| Safe zone editor (safezones.dat) | ❌ **NEEDS IMPL** | Need SafeZoneEditor |
| NPC spawn editor (NPCSpawns.dat) | ❌ **NEEDS IMPL** | Need NPCSpawnEditor |

#### Plan — 2DGameEditor additions:
```
[NEW] UseableItemEditor.py — Editor for useable item types (tools, potions)
[NEW] CollectableEditor.py — Editor for collectable/misc items
[NEW] MonsterTypeEditor.py — Full monster type definition editor (stats, loot tables, animation)
[NEW] SafeZoneEditor.py — Paint safe zones on the world map
[NEW] NPCSpawnEditor.py — Place NPC spawn points on the world map
[MODIFY] ObjectSheetEditor.py — Add full ObjectType property editing (Block, VisBlock, UseType, Openable)
```

### 3.2 VorliaGraphicsConverter → 2DGameEditor

Graphics converter is obsolete and not needed.
### 3.3 VorliaTools → 2DGameEditor

VorliaTools is the **C++ admin CLI tool** that connects to the game server over TCP for remote account/character editing. The Python remake already has:
- [admin_tool.py](file:///e:/Vorila/ThePlayerCity/editor/admin_tool.py) — Basic CLI skeleton

| VorliaTools Feature | Python Status | Migration Target |
|---|---|---|
| Auth (packet 125,11) | ✅ **DONE** | Add name/pass auth flow |
| Request account by name (125,1,1) | ✅ **DONE** | Add to admin protocol |
| Request character by name (125,1,4) | ✅ **DONE** | Add to admin protocol |
| Request account info (125,1,6) | ✅ **DONE** | Add to admin protocol |
| Edit account fields (ban, password, etc.) | ✅ **DONE** | Add set/save commands |
| Edit character fields (stats, position, items) | ✅ **DONE** | Add set/save commands |
| Item search across all accounts (125,12) | ✅ **DONE** | Add item search protocol |
| Server message broadcast (125,10) | ✅ **DONE** | Add broadcast command |
| Forced save (125,8) | ✅ **DONE** | Add save command |
| Disconnect (125,3) | ✅ **DONE** | Add disconnect command |

#### Plan — Admin tool: [✅ COMPLETED]
* **CLI Implementation**: Expanded `editor/admin_tool.py` with the complete command suite (`request`, `edit`/`cedit`, `accinfo`/`charinfo`, `set`, `save`, `sitem`, `servermessage`, `forcedsave`, `listaccounts`/`listcharacters`, connection commands).
* **GUI Integration**: Created `AdminToolEditor.py` inside `2DGameEditor` with Win95 style tabs and hooked it into `GameEditor.py`.

---

## Part 4: ThePlayerCityServer (POC) Review

[server.py](file:///e:/2DGameEditor/ThePlayerCityServer/server.py) is the **web-based proof of concept** using FastAPI + WebSockets. Useful patterns to carry forward into the Python remake:

| POC Feature | Value for ThePlayerCity | Action |
|---|---|---|
| WebSocket connection manager | ⚠️ Reference only | TCP socket approach is better for game client |

#### Plan — Fixes from POC to apply:
```
1. Port HryParser to core/config.py — needed for reading HAIRY/*.hry game definitions
2. Add BinaryDriver (WBF!) format detection to core/maps.py load_world_grid()
3. Add config hot-reload watcher to server (watch HAIRY/*.hry for changes)
4. Add chunk data caching for large map performance
```

---

## Part 5: Git Cleanup

> [!CAUTION]
> Remove all git push-to-origin references. ThePlayerCity needs its own fresh git repository.

- Remove `.git` from `e:\Vorila\` (it's the parent repo for the old project)
- Do NOT push to origin from ThePlayerCity
- A new git repo for ThePlayerCity will be initialized separately later

---

## Part 6: Recommended Implementation Order

### Priority 1 — Core Framework (do first)
1. `core/items.py` [NEW] — Item type definitions and enums
2. `core/creatures.py` [NEW] — Monster/NPC type definitions
3. `core/packets.py` — Expand with all packet formats
4. `core/models.py` — Add TempData, RaceInfo, GuildClass
5. `core/config.py` [NEW] — HryParser for game config

### Priority 2 — Server Game Loop
6. `server/client_state.py` [NEW] — Connected client tracking
7. `server/game_loop.py` [NEW] — Main tick with monster AI, regen, spawns
8. `server/network.py` — Full packet routing
9. `server/combat.py` [NEW] — Damage calculations
10. `server/items.py` [NEW] — Inventory operations

### Priority 3 — Client Features
11. `client/renderer.py` — Other players, monsters, NPCs
12. `client/ui/` [NEW] — Backpack, stats, chat, equipment panels
13. `client/network.py` [NEW] — Live TCP connection to server

### Priority 4 — Advanced Systems
14. `server/chat.py`, `server/trade.py`, `server/guilds.py` [NEW]
15. `server/tradeskills.py` [NEW]
16. `server/admin.py` [NEW] — Full GM protocol

### Priority 5 — Editor Additions (2DGameEditor)
17. `UseableItemEditor.py`, `CollectableEditor.py` [NEW]
18. `MonsterTypeEditor.py` [NEW]
19. `SafeZoneEditor.py`, `NPCSpawnEditor.py` [NEW]

---

## Design Decisions (Resolved)

### D1: Network Protocol — Custom salted TCP (no backwards compatibility needed) — ✅ DONE

> [!NOTE]
> **Decision:** Use a custom TCP protocol with a configurable encryption salt. No need for C++ backwards compatibility — this is a fresh Python project.

- **Protocol:** JSON-over-TCP with a configurable XOR/salt key (not raw `struct.pack` binary)
- **Config file:** [server/constants.md](file:///e:/Vorila/ThePlayerCity/server/constants.md) — contains `TCPKEY:` value that the user can change at any time to rotate encryption
- **Rationale:** JSON is easier to extend with new packet types, debug, and log. The salt in `constants.md` lets the user change encryption on the fly without recompiling anything
- **Action:** [Done] Created `server/constants.md` with `TCPKEY` field; updated `core/crypto.py` to read salt from this file; updated `core/packets.py` to use JSON serialization with salt-based encryption wrapper

---

### D2: Item Storage — Dedicated SQLite database — ✅ DONE

> [!NOTE]
> **Decision:** Use a dedicated SQLite database for item persistence. SQLite is faster for processing than flat JSON and handles the volume of items better.

- **Database:** `items.db` — dedicated SQLite file for all item instances (ground, inventory, bank, worn, body)
- **Schema:** `items` table with columns: `id`, `used`, `know_id`, `item_type`, `family`, `durability`, `x`, `y`, `quantity`, `owner_id`, `container` (which list: backpack/bank/worn/ground/body), `slot`
- **Why separate DB:** Items are high-churn data (constantly created/moved/destroyed) — a dedicated DB avoids lock contention with account saves
- **Action:** [Done] Created `server/item_database.py` with SQLite CRUD operations for items

---

### D3: Game Data Source — HAIRY (.hry) files are canonical — ✅ DONE

> [!NOTE]
> **Decision:** The HAIRY `.hry` files are the canonical source for all game type definitions. The `.dat` files in Vorlia-Master-Editor are legacy and won't be converted.

- **How it works:** HAIRY files define Types, Objects, NPCs, Players, Monsters via `#Define` and `Object` blocks
- **Data flow:**
  - `HAIRY/Defines.hry` → game constants (tile size, max clients, etc.)
  - `HAIRY/Player.hry` → player starting stats, health, spawn position
  - `HAIRY/Monsters.hry` → monster type definitions (to be created)
  - `HAIRY/NPCs.hry` → NPC type definitions (to be created)
  - `HAIRY/Objects.hry` → world object type definitions (to be created)
- **2DGameEditor link:** The ShopEditor in 2DGameEditor outputs shop data that should correspond to the shop system in ThePlayerCity. The editors write JSON/`.hry` files that the server reads via [core/config.py](file:///e:/Vorila/ThePlayerCity/core/config.py) `HryParser`
- **Action:** [Done] Expanded `HryParser` in `core/config.py` to handle monster/NPC/object type blocks; ensured 2DGameEditor shop output format matches what the server expects

---

### D4: Source Deletion Policy — Incremental, only after feature is built

> [!CAUTION]
> **Decision:** Do NOT delete Memoria source files until the corresponding feature is fully built and working in the Python remake.

- **Rule:** A C++ source file can only be deleted when:
  1. The feature it contains has been fully implemented in Python
  2. The implementation plan status has been changed from ❌ to ✅
  3. The feature has been tested/verified
- **Process:** After each feature is built:
  1. Update implementation_plan.md status from ❌ **NEEDS IMPL** → ✅ **DONE**
  2. Delete the corresponding C++ source file(s)
  3. Move to the next ❌ item
- **Current state:** Only files whose features are marked ✅ **DONE** above can be deleted now. Everything else stays until built.
