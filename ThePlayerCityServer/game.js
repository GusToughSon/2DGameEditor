const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');
const chatInput = document.getElementById('chat-input');
const chatLog = document.getElementById('chat-log');
const coordsDisplay = document.getElementById('coords');

let TILE_SIZE = 16;
let TILES_PER_ROW = 32;
let CHUNK_SIZE = 16;
let WORLD_CHUNKS_X = 256;
let WORLD_CHUNKS_Y = 256;

let player = {
    id: null, x: 410, y: 527, name: 'Player',
    hp: 100, maxHp: 100,
    animFrame: 0, lastAnimUpdate: 0, lastMove: 0,
    category: 'NPCs', type: 'player'
};

let players = {};
let entities = []; 
let entityAssets = {}; 
let chunkMap = new Uint16Array(0); 
let chunkData = new Uint16Array(0); 

let tilesetCanvas = document.createElement('canvas');
let objectCanvas = document.createElement('canvas');
let tilesetReady = false, objectReady = false, mapReady = false, loaded = false;
let tileMeta = {}; 
let worldProps = {};

async function init() {
    console.log("[SYSTEM] Initializing ThePlayerCity Engine...");
    
    // Start asset loads
    const ts = new Image(); const os = new Image();
    ts.src = '/save/TILESET/World_TILESET.png'; 
    os.src = '/save/TILESET/OBJECTS_TILESET.png'; 
    ts.onload = () => { 
        try {
            processTransparency(ts, tilesetCanvas); 
            tilesetReady = true; 
            console.log("[GFX] Tileset Ready"); 
        } catch (e) {
            console.warn("[GFX] Tileset processing failed, using raw image:", e);
            tilesetReady = true; // Still allow rendering
        }
    };
    os.onload = () => { 
        try {
            processTransparency(os, objectCanvas); 
            objectReady = true; 
            console.log("[GFX] Objects Ready"); 
        } catch (e) {
            console.warn("[GFX] Objects processing failed, using raw image:", e);
            objectReady = true;
        }
    };

    const startBtn = document.getElementById('start-btn');
    const nameInput = document.getElementById('username-input');

    const activateUI = () => {
        if (startBtn) {
            startBtn.disabled = false;
            startBtn.innerText = "ENTER WORLD";
            startBtn.onclick = () => {
                const name = nameInput ? nameInput.value.trim() || 'Player' : 'Player';
                player.name = name;
                document.getElementById('overlay').classList.remove('visible');
                loaded = true; 
                coordsDisplay.innerText = `X: ${player.x}, Y: ${player.y}`;
                connect(name);
                requestAnimationFrame(gameLoop);
            };
        }
        if (nameInput) {
            nameInput.onkeydown = (e) => { if (e.key === 'Enter') startBtn.onclick(); };
        }
    };

    try {
        console.log("[DATA] Fetching World Data from Server...");
        if (startBtn) startBtn.innerText = "SYNCING METADATA...";
        const [mResp, tResp, pResp] = await Promise.all([
            fetch('/map_data'),
            fetch('/tile_types'),
            fetch('/world_properties')
        ]);

        const mData = await mResp.json();
        const grid = mData.grid; 
        TILE_SIZE = mData.tile_size || TILE_SIZE;
        TILES_PER_ROW = mData.tiles_per_row || TILES_PER_ROW;
        
        tileMeta = await tResp.json();
        worldProps = await pResp.json();
        
        // Assemble grid first
        const rows = grid.length;
        const cols = grid[0] ? grid[0].length : 0;
        WORLD_CHUNKS_X = cols;
        WORLD_CHUNKS_Y = rows;
        chunkMap = new Uint16Array(rows * cols);
        // Map assembly is fast
        const chunkIdToIndex = new Map();
        const uniqueChunks = [];
        for (let y = 0; y < rows; y++) {
            for (let x = 0; x < cols; x++) {
                const cid = grid[y][x];
                if (!chunkIdToIndex.has(cid)) {
                    chunkIdToIndex.set(cid, uniqueChunks.length);
                    uniqueChunks.push(cid);
                }
                chunkMap[y * cols + x] = chunkIdToIndex.get(cid);
            }
        }

        if (startBtn) startBtn.innerText = "LOADING WORLD CHUNKS...";
        const cResp = await fetch('/chunks');
        const cData = await cResp.json();
        
        chunkData = new Uint16Array(uniqueChunks.length * 512); // 2 layers of 256 tiles
        let resolvedChunks = 0;
        const total = uniqueChunks.length;
        uniqueChunks.forEach((cid, idx) => {
            if (idx % 100 === 0 && startBtn) {
                const pct = Math.floor((idx / total) * 100);
                startBtn.innerText = `ASSEMBLING WORLD... ${pct}%`;
            }
            const chunk = cData[cid] || cData[cid.replace('C_', '')];
            const offset = idx * 512;
            if (chunk) {
                resolvedChunks++;
                const sz = 16 * 16;
                // Layer 0: Ground
                if (chunk.data && chunk.data.ground) {
                    const ground = chunk.data.ground;
                    for (let ty = 0; ty < 16; ty++) {
                        for (let tx = 0; tx < 16; tx++) {
                            const val = ground[ty] && ground[ty][tx] !== undefined ? ground[ty][tx] : 0;
                            chunkData[offset + (ty * 16 + tx)] = val;
                        }
                    }
                }
                // Layer 1: Objects
                if (chunk.data && chunk.data.objects) {
                    const objects = chunk.data.objects;
                    for (let ty = 0; ty < 16; ty++) {
                        for (let tx = 0; tx < 16; tx++) {
                            const val = objects[ty] && objects[ty][tx] !== undefined ? objects[ty][tx] : 0;
                            chunkData[offset + 256 + (ty * 16 + tx)] = val;
                        }
                    }
                }
            }
        });
        
        console.log(`[SYSTEM] Engine Sync Complete. Resolved ${resolvedChunks}/${uniqueChunks.length} unique chunks.`);
        console.log(`[SYSTEM] World Dimensions: ${WORLD_CHUNKS_X * CHUNK_SIZE} x ${WORLD_CHUNKS_Y * CHUNK_SIZE} tiles.`);
        mapReady = true;
        activateUI();
    } catch (e) { 
        console.error("[SYSTEM] Sync failed:", e);
        alert("CRITICAL ERROR: Failed to synchronize with game server. Check console for details.");
    } finally {
        // Ensure starting overlay is visible
        setTimeout(() => { document.getElementById('overlay').classList.add('visible'); }, 500);
    }
    
    window.addEventListener('resize', resize); resize();
}

function processTransparency(img, canvas) {
    const octx = canvas.getContext('2d');
    canvas.width = img.width; canvas.height = img.height;
    octx.drawImage(img, 0, 0);
    const id = octx.getImageData(0, 0, canvas.width, canvas.height);
    for (let i = 0; i < id.data.length; i += 4) {
        if (id.data[i] === 255 && id.data[i+1] === 0 && id.data[i+2] === 255) id.data[i+3] = 0;
    }
    octx.putImageData(id, 0, 0);
}

function resize() { canvas.width = window.innerWidth; canvas.height = window.innerHeight; }

let ws;
function connect(name) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${window.location.host}/ws/${encodeURIComponent(name)}`;
    console.log(`[NETWORK] Connecting to: ${url}`);
    ws = new WebSocket(url);
    ws.onmessage = (e) => {
        const d = JSON.parse(e.data);
        if (d.type === 'init') { 
            player.id = d.player.id; 
            player.x = d.player.x; 
            player.y = d.player.y; 
            if (d.spawns) entities = d.spawns; 
            if (d.players) {
                players = d.players;
                delete players[player.id];
            }
        } else if (d.type === 'update' && d.player_id !== player.id) {
            if (!players[d.player_id]) {
                players[d.player_id] = { 
                    x: d.x, y: d.y, animFrame: 0, 
                    category: 'NPCs', type: 'player' 
                };
            }
            players[d.player_id].x = d.x; players[d.player_id].y = d.y;
        } else if (d.type === 'player_left') {
            delete players[d.player_id];
        } else if (d.type === 'player_joined') {
            if (d.player.id !== player.id) players[d.player.id] = d.player;
        } else if (d.type === 'config_update') {
            if (d.config.TILE_SIZE) TILE_SIZE = d.config.TILE_SIZE;
            console.log("[SYSTEM] Config Updated:", d.config);
        }
    };
    ws.onclose = () => {
        // Wait 2 seconds then flush the state by reloading
        setTimeout(() => window.location.reload(), 2000);
    };
}

const keys = {};
window.addEventListener('keydown', e => keys[e.key.toLowerCase()] = true);
window.addEventListener('keyup', e => keys[e.key.toLowerCase()] = false);

function getTileAt(wx, wy, layer = 0) {
    if (!mapReady || wx < 0 || wy < 0 || wx >= WORLD_CHUNKS_X * CHUNK_SIZE || wy >= WORLD_CHUNKS_Y * CHUNK_SIZE) return 0;
    const cx = Math.floor(wx / CHUNK_SIZE); const cy = Math.floor(wy / CHUNK_SIZE);
    const tx = wx % CHUNK_SIZE; const ty = wy % CHUNK_SIZE;
    const chunkIdx = chunkMap[cy * WORLD_CHUNKS_X + cx];
    const offset = chunkIdx * 512 + (layer * 256);
    return chunkData[offset + (ty * CHUNK_SIZE + tx)];
}

function isPassable(x, y) {
    for (let l = 0; l < 2; l++) {
        const tId = getTileAt(x, y, l);
        if (tId === 0) {
            if (l === 0) return false; // Water/void is blocked
            continue;
        }

        // 1. Check Tile Meta
        const meta = tileMeta[tId];
        if (meta && meta.properties && (meta.properties.block_move || meta.properties.blocking)) return false;
        
        // 2. Check World Properties (for specific tileset coordinates)
        const pr = TILES_PER_ROW; 
        const tilesetIdx = tId; // No -1
        const ctx = (tilesetIdx % pr) + 1;
        const cty = Math.floor(tilesetIdx / pr) + 1;
        const props = worldProps[`${cty},${ctx}`];
        if (props && props.block_move) return false;
    }
    
    // 3. Check Entity Collision
    const solidEntity = entities.find(ent => ent.x === x && ent.y === y && ent.blockmove !== 0);
    if (solidEntity) return false;
    
    return true;
}

let globalAnimFrame = 0;
let lastGlobalAnim = 0;

function update(now) {
    if (!loaded) return;
    
    // Global animation clock for everything
    if (now - lastGlobalAnim > 250) { 
        globalAnimFrame = (globalAnimFrame + 1) % 4; 
        lastGlobalAnim = now; 
        player.animFrame = globalAnimFrame; // Keep player in sync
    }
    
    if (now - player.lastMove > 150) {
        let dx = 0, dy = 0;
        if (keys['w'] || keys['arrowup']) dy = -1; else if (keys['s'] || keys['arrowdown']) dy = 1;
        if (keys['a'] || keys['arrowleft']) dx = -1; else if (keys['d'] || keys['arrowright']) dx = 1;
        if (dx || dy) {
            let moved = false;
            // Try X movement independently
            if (dx !== 0 && isPassable(player.x + dx, player.y)) {
                player.x += dx;
                moved = true;
            }
            // Try Y movement independently
            if (dy !== 0 && isPassable(player.x, player.y + dy)) {
                player.y += dy;
                moved = true;
            }

            if (moved) {
                player.lastMove = now;
                coordsDisplay.innerText = `X: ${player.x}, Y: ${player.y}`;
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({ type: 'move', x: player.x, y: player.y }));
                }
            }
        }
    }
}

function draw() {
    if (!loaded || !mapReady) return;
    ctx.fillStyle = '#0a0a0b'; 
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    if (Date.now() % 5000 < 50) { // Log every 5 seconds
        console.log(`[DEBUG] Draw - TILE_SIZE: ${TILE_SIZE}, Pos: ${player.x},${player.y}`);
    }

    const camX = player.x * TILE_SIZE - canvas.width / 2; 
    const camY = player.y * TILE_SIZE - canvas.height / 2;
    
    // 1.8x the view range (0.4x margin on each side)
    const viewWidth = canvas.width / TILE_SIZE;
    const viewHeight = canvas.height / TILE_SIZE;
    const marginX = viewWidth * 0.4;
    const marginY = viewHeight * 0.4;

    const sX = Math.max(0, Math.floor(camX / TILE_SIZE - marginX));
    const eX = Math.min(WORLD_CHUNKS_X * CHUNK_SIZE, Math.ceil((camX + canvas.width) / TILE_SIZE + marginX));
    const sY = Math.max(0, Math.floor(camY / TILE_SIZE - marginY));
    const eY = Math.min(WORLD_CHUNKS_Y * CHUNK_SIZE, Math.ceil((camY + canvas.height) / TILE_SIZE + marginY));

    const drawS = (sId, x, y) => {
        if (!objectReady) return;
        const pr = TILES_PER_ROW;
        ctx.drawImage(objectCanvas, (sId % pr) * TILE_SIZE, Math.floor(sId / pr) * TILE_SIZE, TILE_SIZE, TILE_SIZE, x * TILE_SIZE - camX, y * TILE_SIZE - camY, TILE_SIZE, TILE_SIZE);
    };

    const drawEntity = (ent) => {
        let type = ent.name || ent.type;
        // Optimization: all human players use the core 'player' asset
        if (ent.type === 'player') type = 'player';
        
        const assetKey = `${ent.category}/${type}`;
        if (!entityAssets[assetKey]) {
            entityAssets[assetKey] = { loaded: false, img: new Image(), canvas: document.createElement('canvas') };
            const cleanType = type.replace(/_/g, ' '); 
            entityAssets[assetKey].img.src = `/AnimImages/${ent.category}/${cleanType}.png`;
            entityAssets[assetKey].img.onload = () => {
                processTransparency(entityAssets[assetKey].img, entityAssets[assetKey].canvas);
                entityAssets[assetKey].loaded = true;
            };
            entityAssets[assetKey].img.onerror = () => { entityAssets[assetKey].failed = true; };
        }
        const asset = entityAssets[assetKey];
        if (asset && asset.loaded) {
            // Assume vertical strip for high-fidelity assets
            const frameY = (ent.animFrame || 0) * TILE_SIZE;
            // Bound check to prevent sampling outside image if it only has 1 frame
            const safeY = frameY < asset.canvas.height ? frameY : 0;
            ctx.drawImage(asset.canvas, 0, safeY, TILE_SIZE, TILE_SIZE, ent.x * TILE_SIZE - camX, ent.y * TILE_SIZE - camY, TILE_SIZE, TILE_SIZE);
        } else {
            drawS(ent.sprite || 86, ent.x, ent.y);
        }
    };

    const drawTiles = (layer) => {
        for (let y = sY; y < eY; y++) {
            for (let x = sX; x < eX; x++) {
                let t = getTileAt(x, y, layer); 
                if (t === 0) continue;

                let drawX = x * TILE_SIZE - camX;
                let drawY = y * TILE_SIZE - camY;
                

                const meta = tileMeta[t] || {};
                
                // Handle Animations
                if (meta.animation && meta.animation.frames > 0) {
                    const speed = meta.animation.speed || 500;
                    const frameIdx = Math.floor(Date.now() / speed) % meta.animation.frames;
                    const seq = meta.animation.frame_sequence[frameIdx];
                    if (seq) {
                        const tx = seq[0], ty = seq[1], ts = seq[2];
                        const pr = TILES_PER_ROW;
                        const srcX = tx * TILE_SIZE;
                        const srcY = ty * TILE_SIZE;
                        const canvas = ts === "Object" ? objectCanvas : tilesetCanvas;
                        ctx.drawImage(canvas, srcX, srcY, TILE_SIZE, TILE_SIZE, drawX, drawY, TILE_SIZE, TILE_SIZE);
                        continue;
                    }
                }

                if (layer === 0 && tilesetReady) {
                    const pr = TILES_PER_ROW; 
                    const tilesetIdx = t; // No -1
                    const srcX = (tilesetIdx % pr) * TILE_SIZE;
                    const srcY = Math.floor(tilesetIdx / pr) * TILE_SIZE;
                    ctx.drawImage(tilesetCanvas, srcX, srcY, TILE_SIZE, TILE_SIZE, drawX, drawY, TILE_SIZE, TILE_SIZE);
                } else if (layer === 1 && objectReady) {
                    const pr = TILES_PER_ROW; 
                    const tilesetIdx = t; // No -1
                    const srcX = (tilesetIdx % pr) * TILE_SIZE;
                    const srcY = Math.floor(tilesetIdx / pr) * TILE_SIZE;
                    ctx.drawImage(objectCanvas, srcX, srcY, TILE_SIZE, TILE_SIZE, drawX, drawY, TILE_SIZE, TILE_SIZE);
                }
            }
        }
    };

    drawTiles(0);
    ctx.font = 'bold 11px Inter, sans-serif'; ctx.textAlign = 'center';
    entities.forEach(ent => {
        if (ent.x >= sX && ent.x <= eX && ent.y >= sY && ent.y <= eY) {
            ent.animFrame = globalAnimFrame;
            drawEntity(ent);
            ctx.fillStyle = 'white';
            ctx.fillText(ent.name || ent.type, ent.x * TILE_SIZE - camX + TILE_SIZE/2, ent.y * TILE_SIZE - camY - 5);
        }
    });

    for (let id in players) {
        players[id].animFrame = globalAnimFrame;
        drawEntity(players[id]);
        ctx.fillStyle = '#00ffed';
        ctx.fillText(players[id].name || 'Player', players[id].x * TILE_SIZE - camX + TILE_SIZE/2, players[id].y * TILE_SIZE - camY - 5);
    }
    
    drawEntity(player);
    ctx.fillStyle = '#f7ff00';
    ctx.fillText(player.name, player.x * TILE_SIZE - camX + TILE_SIZE/2, player.y * TILE_SIZE - camY - 5);
    
    drawTiles(1);
}

function makeDraggable(el) {
    let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
    const header = el.querySelector('.panel-header');
    if (header) {
        header.onmousedown = dragMouseDown;
    } else {
        el.onmousedown = dragMouseDown;
    }

    function dragMouseDown(e) {
        e = e || window.event;
        e.preventDefault();
        pos3 = e.clientX;
        pos4 = e.clientY;
        document.onmouseup = closeDragElement;
        document.onmousemove = elementDrag;
    }

    function elementDrag(e) {
        e = e || window.event;
        e.preventDefault();
        pos1 = pos3 - e.clientX;
        pos2 = pos4 - e.clientY;
        pos3 = e.clientX;
        pos4 = e.clientY;
        el.style.top = (el.offsetTop - pos2) + "px";
        el.style.left = (el.offsetLeft - pos1) + "px";
        el.style.right = 'auto'; // Disable the right anchoring
    }

    function closeDragElement() {
        document.onmouseup = null;
        document.onmousemove = null;
    }
}

function gameLoop(now) { update(now); draw(); requestAnimationFrame(gameLoop); }
init();
