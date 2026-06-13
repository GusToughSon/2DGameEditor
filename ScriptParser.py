import os
import re

def parse_hairy_headers(filepath):
    """
    Scans a .hry file for the primary Type/Object declaration and its metadata.
    Returns a dictionary of attributes or None if no object found.
    """
    if not os.path.exists(filepath): return None
    
    result = {}
    defines = get_hairy_defines(filepath)
    
    # 1. Map Family (Look for FAM_XXX flags)
    result["family"] = "FAM_OBJ" # Default
    for key in defines:
        if key.startswith("FAM_"):
            result["family"] = key
            break
            
    # 2. Extract Attributes
    result["tileset"] = defines.get("TILESET", "World").strip('"')
    
    coords = defines.get("TILE_COORDS", "0,0").strip('"')
    try:
        result["tile_coords"] = [int(x) for x in coords.split(",")]
    except:
        result["tile_coords"] = [0, 0]
        
    # Full properties dict extraction
    props = {}
    props["solid"] = str(defines.get("SOLID", defines.get("LOCAL_SOLID", "1"))) == "1"
    props["not_moveable"] = str(defines.get("NOT_MOVEABLE", defines.get("LOCAL_NOT_MOVEABLE", "0"))) == "1"
    props["is_container"] = str(defines.get("IS_CONTAINER", defines.get("LOCAL_IS_CONTAINER", "0"))) == "1"
    props["collectable"] = str(defines.get("COLLECTABLE", defines.get("LOCAL_COLLECTABLE", "0"))) == "1"
    props["is_treasure"] = str(defines.get("IS_TREASURE", defines.get("LOCAL_IS_TREASURE", "0"))) == "1"
    props["can_reach_over"] = str(defines.get("CAN_REACH_OVER", defines.get("LOCAL_CAN_REACH_OVER", "0"))) == "1"
    props["illuminates"] = str(defines.get("ILLUMINATES", defines.get("LOCAL_ILLUMINATES", "0"))) == "1"
    
    def get_int_value(primary, fallback, default=0):
        val = defines.get(primary)
        if val is None:
            val = defines.get(fallback)
        if val is None:
            return default
        try:
            return int(val)
        except:
            return default

    props["weight"] = get_int_value("WEIGHT", "LOCAL_WEIGHT", 0)
    props["mass"] = get_int_value("MASS", "LOCAL_MASS", 0)
    props["use_delay"] = get_int_value("USE_DELAY", "LOCAL_USE_DELAY", 0)
    props["brightness"] = get_int_value("BRIGHTNESS", "LOCAL_BRIGHTNESS", 0)
    props["radius"] = get_int_value("ILLUMINATION_RADIUS", "LOCAL_RADIUS", 0)
    
    result["properties"] = props
    result["solid"] = props["solid"]
    
    # 3. Extract Animation
    anim = {}
    if "ANIM_MODE" in defines or "ANIM_FRAMES" in defines:
        anim["mode"] = defines.get("ANIM_MODE", "Cycle").strip('"')
        try: anim["speed"] = int(defines.get("ANIM_SPEED", "100"))
        except: anim["speed"] = 100
        try: anim["frames"] = int(defines.get("ANIM_FRAMES", "1"))
        except: anim["frames"] = 1
        anim["random_speed"] = str(defines.get("ANIM_RAND_SPEED", "0")) == "1"
        
        seq_str = defines.get("ANIM_SEQUENCE", "").strip('"')
        frame_seq = []
        if seq_str:
            parts = seq_str.split(";")
            for p in parts:
                if not p: continue
                subparts = p.split(",")
                if len(subparts) >= 3:
                    try:
                        frame_seq.append([int(subparts[0]), int(subparts[1]), subparts[2]])
                    except:
                        pass
        anim["frame_sequence"] = frame_seq
        result["animation"] = anim
    else:
        result["animation"] = {}
    
    # 3. Find the Name and Kind (The Trigger)
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                # Strip comments
                line = line.split("//")[0].split("/*")[0]
                m = re.search(r'\b(Type|Object)\b\s+"([^"]+)"', line, re.IGNORECASE)
                if m:
                    result["kind"] = m.group(1).capitalize()
                    result["name"] = m.group(2)
                    return result 
    except: pass
    
    return None if not result.get("name") else result

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
        # Improved Regex: Handle DEFINE [SCOPE] NAME and #Define NAME formats robustly.
        # This specifically avoids greedy matches that could swallow the prefix.
        pattern = rf"(?i)(?:#Define|DEFINE)\s+(?:[A-Z_]+\s+)?{re.escape(prefix)}([A-Z0-9_]+)"
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
        
    return sorted(list(set(results)))

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
            pure_fam = fam.upper()
            if pure_fam.startswith("FAM_"): pure_fam = pure_fam[4:]
            
            fam_filename = f"FAM_{pure_fam}.hry"
            active_fams.append(fam_filename)
            fam_path = os.path.join(hairy_dir, fam_filename)
            
            lines = [
                f"//==============================================================================",
                f"// {fam_filename} - AUTO-GENERATED FAMILY REGISTRY",
                f"//==============================================================================\n"
            ]
            
            for tid, name in sorted(by_family[fam], key=lambda x: x[1].lower()):
                def_name = _type_name_to_define(fam, name)
                lines.append(f"Define TYPE_{def_name:<30} {tid}")
            
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
    Registry logic removed as per user request. 
    Defines.hry is now manually managed.
    """
    pass

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
        for root, _, files in os.walk(hairy_dir):
            for f in files:
                if f.upper().startswith("FAM_") and f.lower().endswith(".hry"):
                    found_modern = True
                    path = os.path.join(root, f)
                    # We extract the family name directly from the filename for 100% accuracy
                    # e.g. FAM_NPC.hry means the family is FAM_NPC
                    fam_from_file = f[:-4].upper()
                    if fam_from_file.startswith("FAM_FAM_"): fam_from_file = fam_from_file[8:]
                    elif fam_from_file.startswith("FAM_"): fam_from_file = fam_from_file[4:]
                    
                    with open(path, "r", encoding="utf-8", errors="replace") as file:
                        for line in file:
                            # Improved Regex: Capture the TID and everything between TYPE_ and the ID
                            # Then we'll split it logically.
                            m_hier = re.search(r"(?i)(?:#Define|Define)\s+TYPE_([A-Z0-9_]+)\s+(\d+)", line)
                            if m_hier:
                                total_name = m_hier.group(1)
                                tid = m_hier.group(2)
                                
                                # If total_name is FAM_NPC_GUARD and file is FAM_NPC.hry
                                # then name is GUARD.
                                prefix_to_strip = f"FAM_{fam_from_file}_"
                                if total_name.upper().startswith(prefix_to_strip):
                                    name_raw = total_name[len(prefix_to_strip):]
                                else:
                                    # Fallback: assume the last part is the name
                                    parts = total_name.split("_")
                                    name_raw = parts[-1] if len(parts) > 1 else total_name
                                    
                                results[tid] = {
                                    "name": name_raw.replace("_", " ").title(),
                                    "family": f"FAM_{fam_from_file}"
                                }
                            
        # 2. Legacy Fallback: If no modern files found, try parsing the monolithic Types.hry
        if not found_modern:
            legacy_path = os.path.join(hairy_dir, "Types.hry")
            if os.path.exists(legacy_path):
                with open(legacy_path, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        m_hier = re.search(r"(?i)(?:#Define|Define)\s+TYPE_([A-Z0-9_]+)_([A-Z0-9_]+)\s+(\d+)", line)
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
                    content.append(f"Define TILE_{name:<25} {tid}")
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
                m = re.search(r'(?i)(?:#Define|DEFINE)(?:\s+(?:GLOBAL_TIMER|GLOBAL|LOCAL))?\s+([A-Z0-9_]+)(?:\s+([^/\n\r]+))?', line)
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

    # 1. Parse existing defines so we can merge/preserve them
    existing_headers = parse_hairy_headers(path) or {}
    
    # 2. Merge existing headers with new metadata
    merged = {
        "family": existing_headers.get("family", "FAM_OBJ"),
        "tileset": existing_headers.get("tileset", "World"),
        "tile_coords": existing_headers.get("tile_coords", [0, 0]),
        "solid": existing_headers.get("solid", True),
        "animation": existing_headers.get("animation", {}),
        "properties": existing_headers.get("properties", {})
    }
    
    # Overwrite with any values passed in metadata
    for k, v in metadata.items():
        if v is not None:
            if k == "properties" and isinstance(v, dict):
                # Deep merge properties
                merged["properties"] = dict(merged["properties"])
                merged["properties"].update(v)
            else:
                merged[k] = v

    # 3. Read the file lines
    with open(path, 'r', encoding='utf-8', errors='replace') as f: lines = f.readlines()
    
    # 4. Create the new header block
    header = []
    header.append(f"DEFINE {merged.get('family', 'FAM_OBJ')}\n")
    
    # Extract properties for writing
    props = merged.get("properties", {})
    
    # Update solid: prioritize props['solid'] if defined, otherwise check merged['solid']
    solid_val = props.get("solid") if "solid" in props else merged.get("solid", True)
    header.append(f"DEFINE SOLID {1 if solid_val else 0}\n")
    header.append(f"DEFINE NOT_MOVEABLE {1 if props.get('not_moveable') else 0}\n")
    header.append(f"DEFINE IS_CONTAINER {1 if props.get('is_container') else 0}\n")
    header.append(f"DEFINE COLLECTABLE {1 if props.get('collectable') else 0}\n")
    header.append(f"DEFINE IS_TREASURE {1 if props.get('is_treasure') else 0}\n")
    header.append(f"DEFINE CAN_REACH_OVER {1 if props.get('can_reach_over') else 0}\n")
    header.append(f"DEFINE ILLUMINATES {1 if props.get('illuminates') else 0}\n")
    
    header.append(f"DEFINE WEIGHT {props.get('weight', 0)}\n")
    header.append(f"DEFINE MASS {props.get('mass', 0)}\n")
    header.append(f"DEFINE USE_DELAY {props.get('use_delay', 0)}\n")
    header.append(f"DEFINE BRIGHTNESS {props.get('brightness', 0)}\n")
    header.append(f"DEFINE ILLUMINATION_RADIUS {props.get('radius', 0)}\n")
    
    if merged.get('tileset'):
        header.append(f"DEFINE TILESET \"{merged['tileset']}\"\n")
        
    if merged.get('tile_coords'):
        coords_str = ",".join(str(x) for x in merged['tile_coords'])
        header.append(f"DEFINE TILE_COORDS \"{coords_str}\"\n")
        
    # Animation properties
    anim = merged.get('animation')
    if anim:
        header.append(f"DEFINE ANIM_MODE \"{anim.get('mode', 'Cycle')}\"\n")
        header.append(f"DEFINE ANIM_SPEED {anim.get('speed', 100)}\n")
        header.append(f"DEFINE ANIM_FRAMES {anim.get('frames', 1)}\n")
        val_rand = 1 if anim.get('random_speed') else 0
        header.append(f"DEFINE ANIM_RAND_SPEED {val_rand}\n")
        
        seq_parts = []
        for frame in anim.get('frame_sequence', []):
            if len(frame) >= 3:
                seq_parts.append(f"{frame[0]},{frame[1]},{frame[2]}")
        seq_str = ";".join(seq_parts)
        header.append(f"DEFINE ANIM_SEQUENCE \"{seq_str}\"\n")
    
    # 5. Rebuild file (skipping old DEFINEs)
    new_lines = []
    in_header_block = True
    for line in lines:
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
            
    with open(path, 'w', encoding='utf-8') as f: f.writelines(new_lines)
    return True


def load_all_types_with_metadata(project_path):
    """
    Scans all Hairy scripts in HAIRY/ directory, extracting full metadata for each type.
    Returns: { tid: { name, family, tileset, tile_coords, properties, animation } }
    """
    hairy_dir = os.path.join(project_path, "HAIRY")
    if not os.path.exists(hairy_dir): return {}

    # 1. Map Names to IDs based on Types.hry/FAM_*.hry modular files
    id_map = {} # {Name.lower(): ID}
    script_ids = parse_types_use_sync(os.path.join(hairy_dir, "Types.hry"))
    for tid, s_data in script_ids.items():
        id_map[s_data["name"].lower()] = tid

    # 2. Scan every .hry for Metadata
    new_types = {}
    next_id = 9000
    
    system_files = {"defines.hry", "template.hry", "types.hry", "tables.hry", "skills.hry", "tiles.hry"}
    use_files = []
    for root, _, files in os.walk(hairy_dir):
        for f in files:
            if f.lower().endswith(".hry"):
                use_files.append(os.path.relpath(os.path.join(root, f), hairy_dir))
    
    processed_names = set()

    for use_file in use_files:
        if use_file.lower() in system_files: continue
        
        filepath = os.path.join(hairy_dir, use_file)
        headers = parse_hairy_headers(filepath)
        
        if not headers: continue # Not a valid Object/Type script
        
        name = headers["name"]
        name_lower = name.lower()
        if name_lower in processed_names: continue
        processed_names.add(name_lower)
        
        tid = id_map.get(name_lower)
        if not tid:
            while str(next_id) in new_types: next_id += 1
            tid = str(next_id)
        
        new_types[tid] = {
            "name": name,
            "family": headers.get("family", "FAM_OBJ"),
            "tileset": headers.get("tileset", "World"),
            "tile_coords": headers.get("tile_coords", [0, 0]),
            "properties": headers.get("properties", {}),
            "animation": headers.get("animation", {})
        }
    return new_types


