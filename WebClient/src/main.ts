import './style.css'

// ─── Display constants (1:1 with Pygame) ───────────────────────────────────────────────────
const SCREEN_WIDTH = 800;
const SCREEN_HEIGHT = 600;
const TILE_SIZE = 16;
const SCALE = 2;
const DRAW_SIZE = TILE_SIZE * SCALE; // 32 px

const SIDEBAR_WIDTH = 180;
const VIEWPORT_W = SCREEN_WIDTH - SIDEBAR_WIDTH; // 620 px
const VIEWPORT_H = SCREEN_HEIGHT;
const TILES_ACROSS = Math.floor(VIEWPORT_W / DRAW_SIZE); // 19
const TILES_DOWN = Math.floor(VIEWPORT_H / DRAW_SIZE); // 18

const VIEWPORT_X = 0;
const VIEWPORT_Y = 0;
const PLAYER_TILE_X = Math.floor(TILES_ACROSS / 2); // 9
const PLAYER_TILE_Y = Math.floor(TILES_DOWN / 2); // 9

// ─── Tilesets ──────────────────────────────────────────────────────────────
const TILESET_FILES: Record<number, string> = {
    0: "/World_TILESET.png",
    1: "/ITEMS_TILESET.png",
    2: "/OBJECTS_TILESET.png",
    3: "/AVATARS_TILESET.png"
};

const tilesets: Record<number, { img: HTMLImageElement; stride: number }> = {};

// Load images
for (const [id, url] of Object.entries(TILESET_FILES)) {
    const img = new Image();
    img.src = url;
    img.onload = () => {
        tilesets[parseInt(id)] = { img, stride: Math.floor(img.width / TILE_SIZE) };
        console.log(`[ENGINE] Loaded Tileset ${id}: ${img.width}x${img.height}`);
    };
}

// ─── Engine State ──────────────────────────────────────────────────────────
const state = {
    username: "test",
    password: "test",
    char_slot: 0,
    
    player_x: 10,
    player_y: 10,
    player_avatar: 0,
    player_hp: 10,
    player_hp_max: 10,
    player_mana: 5,
    player_level: 1,
    player_name: "Unknown",
    
    other_players: {} as Record<string, any>,
    monsters: {} as Record<string, any>,
    npcs: {} as Record<string, any>,
    ground_items: {} as Record<string, any>,
    bodies: {} as Record<string, any>,
    target_monster_id: null as string | null,
    
    backpack: new Array(24).fill(null),
    bank: new Array(50).fill(null),
    worn: new Array(10).fill(null),
    bank_active: false,
    
    chat_log: [] as string[],
    chat_input: "",
    chat_active: false,
    
    is_dragging: false,
    dragged_item: null as any,
    
    // Mock map (we will request this from server later)
    map: new Map<string, number>()
};

// ─── Network Layer (Encryption & Sockets) ───────────────────────────────────
let socket: WebSocket | null = null;

const TCP_KEY = import.meta.env.VITE_TCP_KEY || "default_player_city_secret_salt_key";
const textEncoder = new TextEncoder();
const textDecoder = new TextDecoder();
const keyBytes = textEncoder.encode(TCP_KEY);

function xorData(data: Uint8Array): Uint8Array {
    const out = new Uint8Array(data.length);
    for (let i = 0; i < data.length; i++) {
        out[i] = data[i] ^ keyBytes[i % keyBytes.length];
    }
    return out;
}

function packJson(packet: any): ArrayBuffer {
    const jsonBytes = textEncoder.encode(JSON.stringify(packet));
    const encrypted = xorData(jsonBytes);
    
    const buffer = new ArrayBuffer(4 + encrypted.length);
    const view = new DataView(buffer);
    view.setUint32(0, encrypted.length, true); // Little endian
    
    const outArray = new Uint8Array(buffer);
    outArray.set(encrypted, 4);
    
    return buffer;
}

function unpackJson(payload: ArrayBuffer): any {
    const view = new DataView(payload);
    const length = view.getUint32(0, true);
    
    const encrypted = new Uint8Array(payload, 4, length);
    const decrypted = xorData(encrypted);
    
    const jsonStr = textDecoder.decode(decrypted);
    return JSON.parse(jsonStr);
}

let activeSlot = 0;
let launcherClasses: string[] = [];

function connectToServer() {
    const wsUrl = `ws://${window.location.hostname}:1339`;
    socket = new WebSocket(wsUrl);
    socket.binaryType = "arraybuffer";
    
    socket.onopen = () => {
        console.log("[NET] Connected to server (ws://...:1339). Ready for login.");
    };
    
    socket.onmessage = (event) => {
        if (!(event.data instanceof ArrayBuffer)) return;
        
        try {
            const packet = unpackJson(event.data);
            const ptype = packet.type;
            
            if (ptype === "login_response") {
                if (packet.success) {
                    console.log("[NET] Auth success! Loading slots...");
                    launcherClasses = packet.classes || [];
                    
                    document.getElementById('login-screen')!.style.display = 'none';
                    document.getElementById('char-select-screen')!.style.display = 'block';
                    
                    const slotsDiv = document.getElementById('char-slots-container')!;
                    slotsDiv.innerHTML = ''; // Clear existing
                    
                    // Display up to 2 slots like launcher.py
                    for (let i = 0; i < 2; i++) {
                        const isUsed = packet.slots?.used?.[i];
                        const slotDiv = document.createElement('div');
                        slotDiv.className = 'char-slot';
                        
                        if (isUsed) {
                            const name = packet.slots.names[i];
                            const level = packet.slots.levels[i];
                            const hp = packet.slots.hps[i];
                            const hpMax = packet.slots.hpmaxs[i];
                            
                            slotDiv.innerHTML = `
                                <h3>${name}</h3>
                                <p>Level: ${level}</p>
                                <p>HP: ${hp}/${hpMax}</p>
                                <button onclick="window.playGame(${i})">Play</button>
                            `;
                        } else {
                            slotDiv.innerHTML = `
                                <h3 style="text-align: center; color: #6c7086; margin-top: 10px;">Empty Slot</h3>
                                <button onclick="window.showCreate(${i})">Create</button>
                            `;
                        }
                        slotsDiv.appendChild(slotDiv);
                    }
                } else {
                    alert("Authentication failed! Error code: " + packet.error_code);
                }
            }
            else if (ptype === "register_response") {
                if (packet.success) {
                    alert("Registration successful! You may now login.");
                } else {
                    alert("Registration failed: " + packet.error);
                }
            }
            else if (ptype === "create_character_response") {
                if (packet.success) {
                    alert("Character created successfully!");
                    // Trigger login again to fetch updated slots
                    document.getElementById('btn-login')!.click();
                    
                    document.getElementById('char-create-screen')!.style.display = 'none';
                    document.getElementById('char-select-screen')!.style.display = 'block';
                } else {
                    alert("Creation failed: " + packet.error);
                }
            }
            else if (ptype === "enter_game_response" && packet.success) {
                document.getElementById('launcher-overlay')!.style.display = 'none';
                
                state.player_x = packet.x || 10;
                state.player_y = packet.y || 10;
                state.player_avatar = packet.avatar || 0;
                state.player_hp = packet.hp || 10;
                state.player_hp_max = packet.hp_max || 10;
                state.player_name = packet.name || "Unknown";
                
                // Start render loop
                requestAnimationFrame(render);
            }
            else if (ptype === "map_data") {
                const grid = packet.grid;
                const chunks = packet.chunks;
                
                state.map.clear();
                const CHUNK_SIZE = 16;
                
                for (let cy = 0; cy < grid.length; cy++) {
                    for (let cx = 0; cx < grid[cy].length; cx++) {
                        const chunkId = grid[cy][cx];
                        const chunkData = chunks[chunkId];
                        
                        if (chunkData && Array.isArray(chunkData)) {
                            for (let r = 0; r < chunkData.length; r++) {
                                // Sometimes the data is a flat list, sometimes a nested array, sometimes an object depending on old legacy formats
                                // Try array first
                                if (Array.isArray(chunkData[r])) {
                                    for (let c = 0; c < chunkData[r].length; c++) {
                                        const wx = cx * CHUNK_SIZE + c;
                                        const wy = cy * CHUNK_SIZE + r;
                                        const tileId = chunkData[r][c] || 0;
                                        if (tileId > 0) state.map.set(`${wx},${wy}`, tileId);
                                    }
                                } else if (typeof chunkData === 'object' && !Array.isArray(chunkData)) {
                                    // dict based rows (legacy mapping)
                                    const cd = chunkData as any;
                                    const row = cd[r] || cd[r.toString()];
                                    if (row) {
                                        if (Array.isArray(row)) {
                                            for (let c = 0; c < row.length; c++) {
                                                const wx = cx * CHUNK_SIZE + c;
                                                const wy = cy * CHUNK_SIZE + r;
                                                const tileId = row[c] || 0;
                                                if (tileId > 0) state.map.set(`${wx},${wy}`, tileId);
                                            }
                                        } else {
                                            // nested dict
                                            for (const cStr in row) {
                                                const c = parseInt(cStr);
                                                const wx = cx * CHUNK_SIZE + c;
                                                const wy = cy * CHUNK_SIZE + r;
                                                const tileId = row[cStr] || 0;
                                                if (tileId > 0) state.map.set(`${wx},${wy}`, tileId);
                                            }
                                        }
                                    }
                                }
                            }
                        } else if (chunkData && typeof chunkData === 'object') {
                            // dict based chunk
                            const cd = chunkData as any;
                            for (const rStr in cd) {
                                const r = parseInt(rStr);
                                const row = cd[rStr];
                                if (Array.isArray(row)) {
                                    for (let c = 0; c < row.length; c++) {
                                        const wx = cx * CHUNK_SIZE + c;
                                        const wy = cy * CHUNK_SIZE + r;
                                        const tileId = row[c] || 0;
                                        if (tileId > 0) state.map.set(`${wx},${wy}`, tileId);
                                    }
                                } else if (typeof row === 'object') {
                                    for (const cStr in row) {
                                        const c = parseInt(cStr);
                                        const wx = cx * CHUNK_SIZE + c;
                                        const wy = cy * CHUNK_SIZE + r;
                                        const tileId = row[cStr] || 0;
                                        if (tileId > 0) state.map.set(`${wx},${wy}`, tileId);
                                    }
                                }
                            }
                        }
                    }
                }
                console.log(`[MAP] Loaded map grid! Unique populated tiles: ${state.map.size}`);
            }
            else if (ptype === "move_response" && packet.success) {
                state.player_x = packet.x ?? state.player_x;
                state.player_y = packet.y ?? state.player_y;
            }
            else if (ptype === "coordinates") {
                if (packet.name) {
                    state.other_players[packet.name] = { x: packet.x, y: packet.y, avatar: packet.avatar || 0 };
                }
            }
            else if (ptype === "player_left") {
                delete state.other_players[packet.name];
            }
            else if (ptype === "stats_update") {
                state.player_hp = packet.hp ?? state.player_hp;
                state.player_hp_max = packet.hp_max ?? state.player_hp_max;
                state.player_mana = packet.mana ?? state.player_mana;
            }
            else if (ptype === "inventory_update") {
                state.backpack.fill(null);
                state.bank.fill(null);
                state.worn.fill(null);
                for (const item of (packet.items || [])) {
                    if (item.container === "backpack") state.backpack[item.slot] = item;
                    if (item.container === "bank") state.bank[item.slot] = item;
                    if (item.container === "worn") state.worn[item.slot] = item;
                }
            }
            else if (ptype === "chat_broadcast") {
                state.chat_log.push(`${packet.sender || "Server"}: ${packet.message}`);
                if (state.chat_log.length > 8) state.chat_log.shift();
            }
            else if (ptype === "monster_spawn") {
                state.monsters[packet.know_id] = packet;
            }
            else if (ptype === "monster_move") {
                if (state.monsters[packet.know_id]) {
                    state.monsters[packet.know_id].x = packet.x;
                    state.monsters[packet.know_id].y = packet.y;
                }
            }
            else if (ptype === "monster_death" || ptype === "monster_left") {
                delete state.monsters[packet.know_id];
                if (state.target_monster_id === packet.know_id) state.target_monster_id = null;
            }
            else if (ptype === "npc_spawn") {
                state.npcs[packet.npc_id] = packet;
            }
            else if (ptype === "ground_item_spawn") {
                state.ground_items[packet.item_id] = packet;
            }
            else if (ptype === "body_spawn") {
                state.bodies[packet.body_id] = packet;
            }
        } catch(e) {
            console.error("Failed to unpack packet:", e);
        }
    };
    
    socket.onclose = () => {
        console.log("[NET] Disconnected. Reconnecting in 3s...");
        setTimeout(connectToServer, 3000);
    };
}

// ─── Rendering Engine ──────────────────────────────────────────────────────
const canvas = document.getElementById("game-canvas") as HTMLCanvasElement;
const ctx = canvas.getContext("2d")!;

function _blit_tile(ts_id: number, tile_id: number, screen_x: number, screen_y: number) {
    if (tile_id <= 0) return;
    const ts = tilesets[ts_id];
    if (!ts || !ts.img.complete) return;
    
    const src_col = tile_id % ts.stride;
    const src_row = Math.floor(tile_id / ts.stride);
    const src_x = src_col * TILE_SIZE;
    const src_y = src_row * TILE_SIZE;
    
    ctx.drawImage(ts.img, src_x, src_y, TILE_SIZE, TILE_SIZE, screen_x, screen_y, DRAW_SIZE, DRAW_SIZE);
}

function render() {
    ctx.fillStyle = "black";
    ctx.fillRect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT);
    
    // ── Map viewport (play area on LEFT) ─────────────────────────────
    for (let vy = 0; vy < TILES_DOWN; vy++) {
        for (let vx = 0; vx < TILES_ACROSS; vx++) {
            const wx = state.player_x - PLAYER_TILE_X + vx;
            const wy = state.player_y - PLAYER_TILE_Y + vy;
            const px = VIEWPORT_X + vx * DRAW_SIZE;
            const py = VIEWPORT_Y + vy * DRAW_SIZE;
            
            // Draw dummy grass (ID 1) if no map data loaded
            const ground_tid = state.map.get(`${wx},${wy}`) || 1;
            _blit_tile(0, ground_tid, px, py);
        }
    }
    
    // ── Render Entities ──────────────────────────────────────────────
    // Other Players
    for (const p of Object.values(state.other_players)) {
        const vx = p.x - state.player_x + PLAYER_TILE_X;
        const vy = p.y - state.player_y + PLAYER_TILE_Y;
        if (vx >= 0 && vx < TILES_ACROSS && vy >= 0 && vy < TILES_DOWN) {
            _blit_tile(3, p.avatar || 0, VIEWPORT_X + vx * DRAW_SIZE, VIEWPORT_Y + vy * DRAW_SIZE);
        }
    }
    
    // Player
    const player_px = VIEWPORT_X + PLAYER_TILE_X * DRAW_SIZE;
    const player_py = VIEWPORT_Y + PLAYER_TILE_Y * DRAW_SIZE;
    if (tilesets[3]) {
        _blit_tile(3, state.player_avatar, player_px, player_py);
    } else {
        ctx.fillStyle = "red";
        ctx.fillRect(player_px, player_py, DRAW_SIZE, DRAW_SIZE);
    }
    
    // Monsters
    for (const [mid, m] of Object.entries(state.monsters)) {
        const vx = m.x - state.player_x + PLAYER_TILE_X;
        const vy = m.y - state.player_y + PLAYER_TILE_Y;
        if (vx >= 0 && vx < TILES_ACROSS && vy >= 0 && vy < TILES_DOWN) {
            const mx = VIEWPORT_X + vx * DRAW_SIZE;
            const my = VIEWPORT_Y + vy * DRAW_SIZE;
            
            ctx.fillStyle = "green";
            ctx.fillRect(mx, my, DRAW_SIZE, DRAW_SIZE);
            
            // HP Bar
            if (m.hp_max > 0) {
                const hp_pct = Math.max(0, Math.min(1, m.hp / m.hp_max));
                ctx.fillStyle = "gray";
                ctx.fillRect(mx, my - 6, DRAW_SIZE, 3);
                ctx.fillStyle = "red";
                ctx.fillRect(mx, my - 6, DRAW_SIZE * hp_pct, 3);
            }
            if (state.target_monster_id === mid) {
                ctx.strokeStyle = "red";
                ctx.lineWidth = 1;
                ctx.strokeRect(mx - 2, my - 2, DRAW_SIZE + 4, DRAW_SIZE + 4);
            }
        }
    }
    
    // ── Right Sidebar HUD ────────────────────────────────────────────
    const sidebar_x = SCREEN_WIDTH - SIDEBAR_WIDTH;
    ctx.fillStyle = "#181825"; // Pygame sidebar bg
    ctx.fillRect(sidebar_x, 0, SIDEBAR_WIDTH, SCREEN_HEIGHT);
    ctx.strokeStyle = "#45475a";
    ctx.lineWidth = 2;
    ctx.strokeRect(sidebar_x, 0, SIDEBAR_WIDTH, SCREEN_HEIGHT);
    
    ctx.font = 'bold 14px "Segoe UI", Arial';
    ctx.fillStyle = "#cdd6f4";
    ctx.fillText(state.player_name, sidebar_x + 12, 28);
    
    ctx.font = '12px "Segoe UI", Arial';
    ctx.fillStyle = "#f38ba8";
    ctx.fillText(`HP: ${state.player_hp} / ${state.player_hp_max}`, sidebar_x + 12, 60);
    ctx.fillStyle = "#89b4fa";
    ctx.fillText(`Mana: ${state.player_mana}`, sidebar_x + 12, 78);
    ctx.fillStyle = "#f9e2af";
    ctx.fillText(`Level: ${state.player_level}`, sidebar_x + 12, 96);
    ctx.fillStyle = "#a6e3a1";
    ctx.fillText(`X: ${state.player_x}  Y: ${state.player_y}`, sidebar_x + 12, 114);
    
    // Equipment slots placeholder
    ctx.fillStyle = "#cdd6f4";
    ctx.fillText("Equipment", sidebar_x + 12, 138);
    for (let i = 0; i < 4; i++) {
        const slot_x = sidebar_x + 15 + i * 38;
        const slot_y = 150;
        ctx.fillStyle = "#313244";
        ctx.fillRect(slot_x, slot_y, 32, 32);
        ctx.strokeStyle = "#89b4fa";
        ctx.lineWidth = 1;
        ctx.strokeRect(slot_x, slot_y, 32, 32);
        
        if (state.worn[i]) {
            _blit_tile(1, state.worn[i].item_type, slot_x, slot_y);
        }
    }
    
    // Backpack slots placeholder
    ctx.fillStyle = "#cdd6f4";
    ctx.fillText("Backpack", sidebar_x + 12, 208);
    for (let i = 0; i < 24; i++) {
        const row = Math.floor(i / 4);
        const col = i % 4;
        const slot_x = sidebar_x + 15 + col * 38;
        const slot_y = 220 + row * 38;
        
        ctx.fillStyle = "#313244";
        ctx.fillRect(slot_x, slot_y, 32, 32);
        ctx.strokeStyle = "#89b4fa";
        ctx.lineWidth = 1;
        ctx.strokeRect(slot_x, slot_y, 32, 32);
        
        if (state.backpack[i]) {
            _blit_tile(1, state.backpack[i].item_type, slot_x, slot_y);
        }
    }
    
    // ── Render Chat ────────────────────────────────────────────
    let chat_y = VIEWPORT_H - 120;
    ctx.font = '12px "Segoe UI", Arial';
    ctx.fillStyle = "#f5c2e7";
    for (const log of state.chat_log) {
        ctx.fillText(log, 15, chat_y);
        chat_y += 14;
    }
    
    // Only continue loop if launcher is hidden
    if (document.getElementById('launcher-overlay')!.style.display === 'none') {
        requestAnimationFrame(render);
    }
}

// ─── Input Controllers ─────────────────────────────────────────────────────
window.addEventListener("keydown", (e) => {
    if (!socket || socket.readyState !== WebSocket.OPEN) return;
    
    let direction = "";
    switch (e.key.toLowerCase()) {
        case "w": case "arrowup": direction = "up"; break;
        case "s": case "arrowdown": direction = "down"; break;
        case "a": case "arrowleft": direction = "left"; break;
        case "d": case "arrowright": direction = "right"; break;
    }
    if (direction) {
        socket.send(packJson({ type: "move", direction }));
    }
});

// ─── DOM Events (Launcher UI) ──────────────────────────────────────────────
document.getElementById('btn-login')!.addEventListener('click', () => {
    state.username = (document.getElementById('login-user') as HTMLInputElement).value.trim();
    state.password = (document.getElementById('login-pass') as HTMLInputElement).value.trim();
    
    if (!state.username || !state.password) return alert("Fields cannot be empty");
    
    socket!.send(packJson({
        type: "login",
        username: state.username,
        password: state.password,
        version: 3309
    }));
});

document.getElementById('btn-register')!.addEventListener('click', () => {
    state.username = (document.getElementById('login-user') as HTMLInputElement).value.trim();
    state.password = (document.getElementById('login-pass') as HTMLInputElement).value.trim();
    
    if (!state.username || !state.password) return alert("Fields cannot be empty");
    
    socket!.send(packJson({
        type: "register",
        username: state.username,
        password: state.password
    }));
});

document.getElementById('btn-back-login')!.addEventListener('click', () => {
    document.getElementById('char-select-screen')!.style.display = 'none';
    document.getElementById('login-screen')!.style.display = 'block';
});

document.getElementById('btn-back-select')!.addEventListener('click', () => {
    document.getElementById('char-create-screen')!.style.display = 'none';
    document.getElementById('char-select-screen')!.style.display = 'block';
});

document.getElementById('btn-create-char')!.addEventListener('click', () => {
    const charName = (document.getElementById('create-name') as HTMLInputElement).value.trim();
    const className = (document.getElementById('create-class') as HTMLSelectElement).value;
    
    if (!charName) return alert("Character name cannot be empty.");
    
    socket!.send(packJson({
        type: "create_character",
        username: state.username,
        char_name: charName,
        class_template: className,
        slot: activeSlot
    }));
});

// Expose these to window so inline onclick handlers in HTML work
(window as any).playGame = (slot: number) => {
    state.char_slot = slot;
    socket!.send(packJson({
        type: "enter_game",
        username: state.username,
        password: state.password,
        char_slot: slot
    }));
};

(window as any).showCreate = (slot: number) => {
    activeSlot = slot;
    document.getElementById('char-select-screen')!.style.display = 'none';
    document.getElementById('char-create-screen')!.style.display = 'block';
    
    const classSelect = document.getElementById('create-class') as HTMLSelectElement;
    classSelect.innerHTML = '';
    for (const c of launcherClasses) {
        const opt = document.createElement('option');
        opt.value = c;
        opt.text = c;
        classSelect.appendChild(opt);
    }
};

// Boot
connectToServer();
