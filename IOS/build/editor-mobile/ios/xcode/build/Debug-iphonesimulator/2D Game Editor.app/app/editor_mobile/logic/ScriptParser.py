import os
import re

def parse_hairy_headers(filepath):
    """
    Scans a .hry file for Type "Name" or Object "Name" declarations.
    Handled cases where declarations are not at the start of the line.
    """
    results = []
    try:
        if not os.path.exists(filepath): return []
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                # Use search and word boundaries for better detection
                m = re.search(r'\b(Type|Object)\b\s+"([^"]+)"', line, re.IGNORECASE)
                if m:
                    results.append({"kind": m.group(1).capitalize(), "name": m.group(2)})
    except Exception as e:
        print(f"[ERROR] parse_hairy_headers failed on {filepath}: {e}")
    return results

def get_defines_from_script(project_path, prefix="FAM_"):
    """
    Surgically extracts #Define [prefix] identifiers from Defines.hry.
    Returns a sorted list of pretty names (e.g. FAM_NPC -> Npc)
    """
    defines_path = os.path.join(project_path, "HAIRY", "Defines.hry")
    if not os.path.exists(defines_path):
        return []

    results = []
    try:
        # Support both #Define NAME and DEFINE [SCOPE] NAME syntax
        # Using a more inclusive pattern that allows for optional scope keywords
        pattern = rf"(?i)(?:#Define|DEFINE(?:\s+[A-Z_]+)?)\s+{prefix}([A-Z0-9_]+)"
        with open(defines_path, "r", encoding='utf-8', errors='replace') as f:
            for line in f:
                # Strip comments to avoid false matches
                line = line.split("//")[0].split("/*")[0]
                match = re.search(pattern, line)
                if match:
                    # Capture raw name (e.g. FAM_NPC -> NPC)
                    raw = match.group(1).strip()
                    if raw not in results:
                        results.append(raw)
    except Exception as e:
        print(f"[ERROR] ScriptParser failed to read Defines.hry: {e}")
        
    return sorted(results)

def get_all_maps(project_path):
    """ Returns a list of Map names defined in script. """
    return get_defines_from_script(project_path, "MAP_")

def get_all_menus(project_path):
    """ Returns a list of UI Menu names defined in script. """
    return get_defines_from_script(project_path, "MENU_")

def get_all_tilesets(project_path):
    """ Returns a list of Tileset names defined in script (e.g. TILESET_WORLD -> World) """
    return get_defines_from_script(project_path, "TILESET_")

def _type_name_to_define(family, name):
    """ Converts a family + type name into a #Define constant.
    e.g. family='Npc', name='Human Guard' -> 'NPC_HUMAN_GUARD'
    """
    prefix = family.upper()
    suffix = re.sub(r'[^A-Za-z0-9]', '_', name).upper()
    return f"{prefix}_{suffix}"

def _hairy_filename(name):
    """ 
    Converts a type name into a safe .hry filename.
    Hardened to prevent illegal characters and collisions. 
    """
    if not name: return "Unnamed.hry"
    # Replace illegal filename characters with underscores
    safe = re.sub(r'[<>:"/\\|?*]', '_', name).strip()
    # Limit length to prevent OS errors
    safe = safe[:100]
    if not safe.lower().endswith(".hry"):
        safe += ".hry"
    return safe

def sync_all_types_to_hairy(project_path, types_data):
    """
    Modular Refactor: Splits Types.hry into individual FAM_*.hry files.
    This improves project structure and allows for easier script indexing.
    """
    hairy_dir = os.path.join(project_path, "HAIRY")
    try:
        # Group by family
        by_family = {}
        for tid, data in types_data.items():
            fam = data.get("family", "Tiles")
            if fam not in by_family: by_family[fam] = []
            by_family[fam].append((tid, data.get("name", "Unnamed")))
            
        active_fams = []
        for fam in sorted(by_family.keys()):
            fam_filename = f"FAM_{fam.upper()}.hry"
            active_fams.append(fam_filename)
            fam_path = os.path.join(hairy_dir, fam_filename)
            
            lines = [
                f"//==============================================================================",
                f"// {fam_filename} - AUTO-GENERATED FAMILY REGISTRY",
                f"//==============================================================================\n"
            ]
            
            for tid, name in sorted(by_family[fam], key=lambda x: x[1].lower()):
                def_name = _type_name_to_define(fam, name)
                lines.append(f"#Define TYPE_{def_name:<30} {tid}")
            
            with open(fam_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")

        # Cleanup: Delete the legacy monolithic Types.hry if it exists
        legacy_path = os.path.join(hairy_dir, "Types.hry")
        if os.path.exists(legacy_path):
            try: os.remove(legacy_path)
            except: pass
            
        # Update Defines.hry to include the new modular files
        _sync_modular_includes(project_path, active_fams)
        
    except Exception as e:
        print(f"[ERROR] sync_all_types_to_hairy failed: {e}")

def _sync_modular_includes(project_path, active_fams):
    """
    Ensures Defines.hry includes all active Family registries.
    Removes stale family includes and ensures #include "Types.hry" is swapped out.
    """
    defines_path = os.path.join(project_path, "HAIRY", "Defines.hry")
    if not os.path.exists(defines_path): return
    
    try:
        with open(defines_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        new_lines = []
        include_inserted = False
        
        for line in lines:
            # Drop legacy monolithic includes or existing FAM_ includes to rebuild them
            if '#include "Types.hry"' in line: continue
            if re.search(r'#include "FAM_[A-Z0-9_]+\.hry"', line): continue
            new_lines.append(line)
            
        if not include_inserted:
             for f in sorted(active_fams):
                 new_lines.insert(0, f'#include "{f}"\n')

        with open(defines_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    except Exception as e:
        print(f"[ERROR] _sync_modular_includes failed: {e}")

def parse_types_use_sync(filepath):
    """
    Discovery Refactor: Scans ALL FAM_*.hry files in the directory.
    Note: 'filepath' is now treated as a directory-reference for global discovery.
    """
    results = {}
    hairy_dir = os.path.dirname(filepath) if os.path.isfile(filepath) else filepath
    if not os.path.exists(hairy_dir): return results
    
    try:
        # 1. Discovery: Search for all FAM_*.hry files (Modern Modular Format)
        found_modern = False
        for f in os.listdir(hairy_dir):
            if f.upper().startswith("FAM_") and f.lower().endswith(".hry"):
                found_modern = True
                path = os.path.join(hairy_dir, f)
                with open(path, "r", encoding="utf-8", errors="replace") as file:
                    for line in file:
                        m_hier = re.search(r"(?i)#Define\s+TYPE_([A-Z0-9_]+)_([A-Z0-9_]+)\s+(\d+)", line)
                        if m_hier:
                            fam_raw, name_raw, tid = m_hier.group(1), m_hier.group(2), m_hier.group(3)
                            results[tid] = {
                                "name": name_raw.replace("_", " ").title(),
                                "family": fam_raw.title()
                            }
                            
        # 2. Legacy Fallback: If no modern files found, try parsing the monolithic Types.hry
        if not found_modern:
            legacy_path = os.path.join(hairy_dir, "Types.hry")
            if os.path.exists(legacy_path):
                with open(legacy_path, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        m_hier = re.search(r"(?i)#Define\s+TYPE_([A-Z0-9_]+)_([A-Z0-9_]+)\s+(\d+)", line)
                        if m_hier:
                            fam_raw, name_raw, tid = m_hier.group(1), m_hier.group(2), m_hier.group(3)
                            results[tid] = {"name": name_raw.replace("_", " ").title(), "family": fam_raw.title()}
    except Exception as e:
        print(f"[ERROR] parse_types_use_sync failed: {e}")
    return results

def register_type_define(project_path, family, name, type_id):
    """ Deprecated: Use sync_all_types_to_hairy for full file consistency instead. """
    pass

def rename_type_in_defines(project_path, family, old_name, new_name, type_id):
    """ Deprecated: Use sync_all_types_to_hairy for full file consistency instead. """
    pass

def sync_defines_block(project_path, section_header, prefix, data_dict):
    """
    Surgically updates a specific section of Defines.hry with new DEFINE constants.
    """
    defines_path = os.path.join(project_path, "HAIRY", "Defines.hry")
    if not os.path.exists(defines_path): return

    try:
        with open(defines_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        header_str = f"// --- {section_header.upper()} ---"
        
        # 1. Build the new block content using new DEFINE syntax
        new_lines = [f"{header_str}\n"]
        if section_header == "SKILLS":
            # Skills use [Table X] but for defines they are just IDs
            for name, val in sorted(data_dict.items()):
                new_lines.append(f"DEFINE GLOBAL {prefix}{name.upper():<20} {val}\n")
        else:
            for name, val in sorted(data_dict.items()):
                # Generic global logic
                tag = "GLOBAL" if "TIMER" not in section_header else "GLOBAL_TIMER"
                new_lines.append(f"DEFINE {tag} {prefix}{name.upper():<20} {val}\n")
        new_lines.append("\n")

        # 2. Find section start/end and swap
        start_idx = -1
        for i, line in enumerate(lines):
            if header_str in line:
                start_idx = i
                break
        
        if start_idx != -1:
            end_idx = start_idx + 1
            while end_idx < len(lines):
                if lines[end_idx].startswith("// ---") or (lines[end_idx].strip() == "" and end_idx + 1 < len(lines) and lines[end_idx+1].strip() == ""):
                    break
                end_idx += 1
            lines[start_idx:end_idx] = new_lines
        else:
            lines.append("\n" + "".join(new_lines))

        with open(defines_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
            
    except Exception as e:
        print(f"[ERROR] sync_defines_block failed: {e}")

def sync_maps(project_path, map_dict):
    """ Consolidated Maps Registry sync. """
    sync_defines_block(project_path, "MAPS", "MAP_", map_dict)
            
def parse_shops_hry(project_path):
    """
    Parses Shops.hry to extract merchant data and meta-configuration.
    Returns: { 'ShopName': { ... }, '_META_FAMILIES': [...] }
    """
    path = os.path.join(project_path, "HAIRY", "Shops.hry")
    shops = {}
    if not os.path.exists(path): return shops
    
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
            
        # Regex to find Shop "Name" { items }
        shop_blocks = re.findall(r'(?i)Shop\s+"([^"]+)"\s*\{([^}]+)\}', content)
        for name, body in shop_blocks:
            shops[name] = {
                "on_buy": "",
                "on_sell": "",
                "items": []
            }
            
            # Extract metadata from comments first
            on_buy_m = re.search(r'@BUY=([^\s@\n]+)', body)
            if on_buy_m: shops[name]["on_buy"] = on_buy_m.group(1).strip()
            
            on_sell_m = re.search(r'@SELL=([^\s@\n]+)', body)
            if on_sell_m: shops[name]["on_sell"] = on_sell_m.group(1).strip()
            
            # Extract items: TYPE, PRICE, STOCK;
            item_defs = re.findall(r'(\w+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*;', body)
            for itype, iprice, istock in item_defs:
                shops[name]["items"].append({
                    "type": itype,
                    "price": int(iprice),
                    "stock": int(istock)
                })
    except Exception as e:
        print(f"[ERROR] parse_shops_hry failed: {e}")
    return shops

def save_shops_hry(project_path, shops_data):
    """
    Writes the Shops.hry registry with provided data and meta-config.
    """
    path = os.path.join(project_path, "HAIRY", "Shops.hry")
    try:
        content = [
            "// ==============================================================================",
            "// SHOPS.HRY - GLOBAL MERCHANT REGISTRY",
            "// ==============================================================================\n"
        ]
        
        # Sort shops by name for stable file output
        for name in sorted(shops_data.keys()):
            if name == "_META_FAMILIES": continue
            data = shops_data[name]
            content.append(f'Shop "{name}"')
            content.append('{')
            
            meta = ""
            if data.get("on_buy"): meta += f"@BUY={data['on_buy']} "
            if data.get("on_sell"): meta += f"@SELL={data['on_sell']} "
            if meta: content.append(f"    // {meta.strip()}")
            
            for item in data.get("items", []):
                content.append(f"    {item.get('type', 'TYPE_NONE')}, {item.get('price', 0)}, {item.get('stock', -1)};")
            
            content.append('}\n')
            
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(content))
        return True
    except Exception as e:
        print(f"[ERROR] save_shops_hry failed: {e}")
        return False

def rename_hairy_file(project_path, old_name, new_name):
    """
    Renames a .hry file when its parent Type is renamed.
    Returns True on success.
    """
    hairy_dir = os.path.join(project_path, "HAIRY")
    old_file = os.path.join(hairy_dir, _hairy_filename(old_name))
    new_file = os.path.join(hairy_dir, _hairy_filename(new_name))
    
    try:
        if os.path.exists(old_file):
            os.rename(old_file, new_file)
            print(f"[DEBUG] Renamed hairy: {old_name}.hry -> {new_name}.hry")
            return True
    except Exception as e:
        print(f"[ERROR] rename_hairy_file failed: {e}")
def sync_skills_logic(project_path):
    """
    Surgically extracts Skill names and IDs from Skills.hry and syncs to Defines.hry.
    """
    skills_path = os.path.join(project_path, "HAIRY", "Skills.hry")
    if not os.path.exists(skills_path): return

    try:
        with open(skills_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Parse Skill "Name" { ID x ... }
        skills_dict = {}
        matches = re.finditer(r'(?i)Skill\s+"([^"]+)"\s*\{[^}]*ID\s+(\d+)', content)
        for m in matches:
            name = m.group(1).upper().replace(" ", "_")
            sid = m.group(2)
            skills_dict[name] = sid
            
        if skills_dict:
            sync_defines_block(project_path, "SKILLS", "SKILL_", skills_dict)
    except Exception as e:
        print(f"[ERROR] sync_skills_logic failed: {e}")

def harvest_project_globals(project_path):
    """
    SCANS ALL .HRY FILES for 'DEFINE GLOBAL' and 'DEFINE GLOBAL_TIMER'.
    Consolidates them into Defines.hry.
    """
    hairy_dir = os.path.join(project_path, "HAIRY")
    if not os.path.exists(hairy_dir): return

    global_vars = {}
    global_timers = {}
    discovered_types = {} # {Name: Family}

    for root, dirs, files in os.walk(hairy_dir):
        for f in files:
            lower_f = f.lower()
            if lower_f.endswith(".hry") and lower_f not in ["defines.hry", "skills.hry", "tables.hry", "template.hry"]:
                path = os.path.join(root, f)
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as sc:
                        content = sc.read()
                    
                    # 1. Harvest GLOBALS & TIMERS
                    vars_found = re.findall(r"(?i)DEFINE\s+GLOBAL\s+([A-Z0-9_]+)\s+(\w+)", content)
                    for name, val in vars_found: global_vars[name] = val
                    
                    timers_found = re.findall(r"(?i)DEFINE\s+GLOBAL_TIMER\s+([A-Z0-9_]+)\s+(\w+)", content)
                    for name, val in timers_found: global_timers[name] = val

                    # 2. Harvest OBJECT DEFINITION
                    # Find the 'Object "Name"' header
                    obj_match = re.search(r'(?i)Object\s+"([^"]+)"', content)
                    if obj_match:
                        obj_name = obj_match.group(1).replace(" ", "_").upper()
                        # Find the Family (Default to FAM_OBJECT if missing)
                        fam_match = re.search(r'(?i)DEFINE\s+(FAM_[A-Z0-9_]+)', content)
                        obj_family = fam_match.group(1) if fam_match else "FAM_OBJ"
                        discovered_types[obj_name] = obj_family

                except: continue

    # Sync consolidated findings to Defines.hry
    if global_vars: sync_defines_block(project_path, "GLOBAL_PROPERTIES", "", global_vars)
    if global_timers: sync_defines_block(project_path, "GLOBAL_TIMERS", "", global_timers)
    
    # Optional: We could also sync OBJ_ IDs here if we want Defines.hry to be the true master of IDs.
    # For now, we'll let the Type Editor handle the IDs to prevent collisions.

def register_tile_define(project_path, all_props):
    """
    Surgically rebuilds HAIRY/Tiles.hry based on named tiles in the property master.
    Uses nested structure: all_props[Tileset][CoordString]
    """
    tiles_path = os.path.join(project_path, "HAIRY", "Tiles.hry")
    defines_path = os.path.join(project_path, "HAIRY", "Defines.hry")
    
    # 2. Build the Tiles.hry content
    content = [
        "//==============================================================================",
        "// TILES.HRY - AUTO-GENERATED TILE CONSTANTS",
        "//==============================================================================\n"
    ]
    
    # Calculate ID based on (Tileset << 16) | (Y << 8) | X
    ts_id_map = {"World": 0, "Items": 1, "Objects": 2, "Avatars": 3}
    
    # Iterate nested: [Tileset][X,Y]
    ts_names = sorted(all_props.keys())
    for ts_name in ts_names:
        tiles = all_props[ts_name]
        ts_id = ts_id_map.get(ts_name, 0)
        coords = sorted(tiles.keys())
        for coord_str in coords:
            p = tiles[coord_str]
            import re
            name = p.get("name", "").strip().replace(" ", "_")
            name = re.sub(r'[^a-zA-Z0-9_]', '', name).upper()[:32]
            if name:
                try:
                    parts = coord_str.split(",")
                    py, px = int(parts[0]), int(parts[1])
                    # Unique ID: bits 16-17 Tileset | 8-15 Y | 0-7 X
                    # Shift to 0-indexed IDs for technical engine compatibility (JSON is 1-indexed)
                    tid = (ts_id << 16) | ((py - 1) << 8) | (px - 1)
                    content.append(f"#Define TILE_{name:<25} {tid}")
                except: continue
    
    # Save to disk
    try:
        os.makedirs(os.path.dirname(tiles_path), exist_ok=True)
        with open(tiles_path, "w", encoding="utf-8") as f:
            f.write("\n".join(content) + "\n")
            
        import json
        json_path = os.path.join(project_path, "WorldProperties.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(all_props, f, indent=4)
        
        return True
    except Exception as e:
        print(f"[ERROR] Failed to sync Tiles.hry or WorldProperties: {e}")
def get_hairy_defines(filepath):
    """
    Scans a .hry file for all #Define or DEFINE constants.
    Returns: { 'KEY': 'VALUE' } (Values are kept as strings, empty if flag)
    """
    results = {}
    if not os.path.exists(filepath): return results
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                # Matches both #Define KEY VAL and DEFINE [SCOPE] KEY VAL
                # We normalize all to UPPERCASE keys for easier dictionary lookup.
                m = re.search(r'(?i)(?:#Define|DEFINE)(?:\s+[A-Z_]+)?\s+([A-Z0-9_]+)(?:\s+([^/\n\r]+))?', line)
                if m:
                    key = m.group(1).upper()
                    val = m.group(2).strip() if m.group(2) else ""
                    results[key] = val
    except: pass
    return results

def update_hairy_defines(filepath, props_dict):
    """
    Surgically updates specific DEFINE headers in a .hry file.
    Preserves comments and indentation where possible.
    """
    if not os.path.exists(filepath): return
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
            
        updated_lines = []
        found_keys = set()
        
        # Build normalized keys for matching
        normalized_props = {k.upper(): v for k, v in props_dict.items()}
        
        for line in lines:
            # Match existing define lines (including those with scopes)
            m = re.search(r'(?i)^((?:#Define|DEFINE)(?:\s+[A-Z_]+)?\s+)([A-Z0-9_]+)(\s*)([^/\n\r]*)(.*)', line)
            if m:
                prefix_block = m.group(1)
                key = m.group(2).upper()
                spacing = m.group(3)
                old_val = m.group(4).strip()
                suffix = m.group(5)
                
                if key in normalized_props:
                    new_val = str(normalized_props[key])
                    # Preserve wrapping for strings if old_val had them
                    if old_val.startswith('"') and not new_val.startswith('"'):
                        new_val = f'"{new_val}"'
                    
                    # Ensure at least one space if spacing was lost
                    if not spacing: spacing = " "
                    
                    updated_lines.append(f"{prefix_block}{key}{spacing}{new_val}{suffix}\n")
                    found_keys.add(key)
                else:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(updated_lines)
            
    except Exception as e:
        print(f"[ERROR] update_hairy_defines failed: {e}")

def get_shop_item_families(project_path):
    """
    Specifically looks for SHOP_ITEM_FAMILIES in Defines.hry.
    """
    path = os.path.join(project_path, "HAIRY", "Defines.hry")
    defines = get_hairy_defines(path)
    val = defines.get("SHOP_ITEM_FAMILIES", "")
    if val:
        return [f.strip() for f in val.split(",")]
    return ["FAM_WEAPON", "FAM_ARMOR", "FAM_CONSUMABLE", "FAM_OBJ"]

def parse_tile_properties(project_path):
    """ Loads WorldProperties.json to maintain 1-based Row,Column architecture. """
    import json
    path = os.path.join(project_path, "WorldProperties.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERROR] parse_tile_properties failed: {e}")
    return {}



def sync_metadata_to_hairy(project_path, type_name, metadata):
    """
    Updates the script metadata headers using the streamlined syntax.
    Syntax: DEFINE FAM_XXX, DEFINE LOCAL_XXX
    """
    hairy_dir = os.path.join(project_path, 'HAIRY')
    filename = type_name.replace(' ', '_') + '.hry'
    path = os.path.join(hairy_dir, filename)
    if not os.path.exists(path): return False

    with open(path, 'r') as f: lines = f.readlines()
    
    # 1. Create the new header block
    header = []
    header.append(f"DEFINE {metadata.get('family', 'FAM_OBJ')}\n")
    
    if metadata.get('solid') is not None:
        val = 1 if metadata['solid'] else 0
        header.append(f"DEFINE LOCAL_SOLID {val}\n")
    
    # 2. Rebuild file
    new_lines = []
    in_header_block = True
    for line in lines:
        # Once we hit 'Object' or any logic, the header block is over
        if line.strip().startswith('Object') or line.strip().startswith('On'):
            if in_header_block:
                new_lines.extend(header)
                new_lines.append("\n")
                in_header_block = False
            new_lines.append(line)
        elif in_header_block and (line.startswith('DEFINE') or line.startswith('#Define')):
            # Skip existing metadata lines so we can replace them
            continue
        else:
            new_lines.append(line)
            
    with open(path, 'w') as f: f.writelines(new_lines)
    return True

def _hairy_filename(name):
    return name.replace(' ', '_') + '.hry'
