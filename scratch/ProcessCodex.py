import json
import os
import re

def clean_json_md(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    if '---' in content:
        content = content.split('---', 1)[1].strip()
    return json.loads(content)

def safe_name(name):
    return re.sub(r'[^a-zA-Z0-9_]', '_', name).strip('_')

def generate_hry(target_dir, stats, family, tileset):
    name = stats['name']
    fname = safe_name(name)
    path = os.path.join(target_dir, f"{fname}.hry")
    
    fields = stats['fields']
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write("//====================================================================\n")
        f.write("//\n")
        f.write("// " + name + "\n")
        f.write("//\n")
        f.write("//====================================================================\n\n")
        
        f.write("DEFINE " + family + "                    // The logic family\n")
        
        # Vital Stats
        health = fields.get('health', 100)
        f.write("DEFINE LOCAL_HEALTH          " + str(health) + "  // HP\n")
        f.write("DEFINE LOCAL_STRENGTH        10   // Str\n")
        f.write("DEFINE LOCAL_IS_USEABLE      1    // Interactive\n")
        
        # Family-specific defines
        if family == "FAM_WEAPON":
            f.write("DEFINE WEAPON_TO_HIT      " + str(fields.get('to_hit', 0)) + "\n")
            f.write("DEFINE WEAPON_MIN_DMG     " + str(fields.get('min_damage', 1)) + "\n")
            f.write("DEFINE WEAPON_MAX_DMG     " + str(fields.get('max_damage', 1)) + "\n")
            f.write("DEFINE WEAPON_SPEED       " + str(fields.get('attack_speed', 1000)) + "\n")
            f.write('DEFINE WEAPON_CLASS       "' + str(fields.get('subtype_label', 'Sword')) + '"\n')
            f.write("DEFINE WEAPON_REQ_LEVEL   " + str(fields.get('level_requirement', 0)) + "\n")
            f.write("DEFINE WEAPON_REQ_STR     " + str(fields.get('strength', 0)) + "\n")
            f.write("DEFINE LOCAL_ATTACK_TICK     0\n")
        elif family == "FAM_ARMOR":
            f.write("DEFINE ARMOR_AC           " + str(fields.get('armor', 0)) + "\n")
            f.write("DEFINE ARMOR_REQ_LEVEL    " + str(fields.get('player_level_requirement', 0)) + "\n")
            f.write("DEFINE ARMOR_REQ_STR      " + str(fields.get('strength', 0)) + "\n")
            f.write("DEFINE LOCAL_ATTACK_TICK     0\n")
        elif family in ["FAM_MONSTER", "FAM_NPC"]:
            f.write("DEFINE NPC_LEVEL          " + str(fields.get('level', 1)) + "\n")
            f.write("DEFINE NPC_MIN_DMG        " + str(fields.get('min_damage', 1)) + "\n")
            f.write("DEFINE NPC_MAX_DMG        " + str(fields.get('max_damage', 1)) + "\n")
            f.write("DEFINE NPC_ATK_SPEED      " + str(fields.get('attack_speed', 1000)) + "\n")
            f.write("DEFINE LOCAL_ATTACK_TICK     " + str(fields.get('attack_speed', 800)) + "\n")
        else:
            f.write("DEFINE LOCAL_ATTACK_TICK     0\n")

        f.write("// DEFINE LOCAL_REGEN_INTERVAL 5000\n\n")
        f.write("DEFINE HasClicked            0\n")
        f.write("DEFINE IsActivated           0\n\n")
        f.write("DEFINE TILESET " + tileset + "\n")
        f.write("DEFINE GRAPHIC " + str(fields.get('frame_1_x', 0)) + ", " + str(fields.get('frame_1_y', 0)) + "\n")
        f.write("DEFINE SOLID TRUE\n\n")

        # Logic Shell
        f.write('Object "' + fname + '"\n')
        f.write('{\n')
        f.write('    OnUse\n    {\n        Print "You used ' + name + '!\\n"\n        HasClicked += 1\n    }\n\n')
        f.write('    OnLook\n    {\n        Print "It is a ' + name + '.\\n"\n    }\n\n')
        f.write('    OnNew\n    {\n    }\n\n')
        f.write('    OnSpawn\n    {\n    }\n\n')
        f.write('    OnDeath\n    {\n        Print "The ' + name + ' is gone!\\n"\n    }\n\n')
        f.write('    OnTalk\n    {\n    }\n\n')
        f.write('    OnTouch\n    {\n    }\n\n')
        f.write('    OnEnterContainer\n    {\n    }\n\n')
        f.write('    OnRemoveFromContainer\n    {\n    }\n\n')
        f.write('    OnEquip\n    {\n    }\n\n')
        f.write('    OnUnEquip\n    {\n    }\n\n')
        f.write('    OnDrop\n    {\n    }\n\n')
        f.write('    OnDrag\n    {\n    }\n\n')
        f.write('    OnMove\n    {\n    }\n\n')
        f.write('    OnCollide\n    {\n    }\n\n')
        f.write('    OnHit\n    {\n    }\n\n')
        f.write('    OnCombat\n    {\n    }\n\n')
        f.write('    OnAnimate\n    {\n    }\n\n')
        f.write('    OnTimer LOCAL_ATTACK_TICK\n    {\n    }\n\n')
        f.write('    OnTimer GLOBAL_WORLD_TICK\n    {\n    }\n')
        f.write('}\n')

def main():
    hairy_dir = r"E:\2DGameEditor\Saves\MyNewProject\HAIRY"
    os.makedirs(hairy_dir, exist_ok=True)
    
    # Paths to JSON MD files
    weapons_path = r"C:\Users\gooro\.gemini\antigravity\brain\8cb2ef24-1286-4614-b199-f1f46141ca5e\.system_generated\steps\1110\content.md"
    armors_path = r"C:\Users\gooro\.gemini\antigravity\brain\8cb2ef24-1286-4614-b199-f1f46141ca5e\.system_generated\steps\1113\content.md"
    monsters_path = r"C:\Users\gooro\.gemini\antigravity\brain\8cb2ef24-1286-4614-b199-f1f46141ca5e\.system_generated\steps\1123\content.md"
    
    print("Processing Weapons...")
    weapons = clean_json_md(weapons_path)
    for w in weapons:
        generate_hry(hairy_dir, w, "FAM_WEAPON", "ITEMS")
        
    print("Processing Armor...")
    armors = clean_json_md(armors_path)
    for a in armors:
        generate_hry(hairy_dir, a, "FAM_ARMOR", "ITEMS")
        
    print("Processing Monsters...")
    monsters = clean_json_md(monsters_path)
    for m in monsters:
        family = "FAM_MONSTER" if m['fields'].get('level', 0) > 0 else "FAM_NPC"
        generate_hry(hairy_dir, m, family, "AVATAR")

    print("Success: 500+ scripts generated with literal string concatenation.")

if __name__ == "__main__":
    main()
