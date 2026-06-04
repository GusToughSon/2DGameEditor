import sys, os, re
sys.path.append('E:/2DGameEditor')
import ScriptParser

project_path = 'E:/2DGameEditor/Saves/MyNewProject'
skills_path = os.path.join(project_path, 'HAIRY', 'Skills.hry')
defines_path = os.path.join(project_path, 'HAIRY', 'Defines.hry')

# 1. Load current skills
current_skills = []
if os.path.exists(skills_path):
    with open(skills_path, 'r') as f:
        content = f.read()
    flat_matches = re.finditer(r'(?i)Skill\s+(.*?)\s+MaxLevel_(\d+)\s+([a-zA-Z0-9_]+)\s+(\d+)', content)
    for m in flat_matches:
        current_skills.append(m.group(1).strip().strip('"'))

# 2. Harvest from Defines
legacy_defines = ScriptParser.get_hairy_defines(defines_path)
new_entries = []
for key, val in legacy_defines.items():
    if key.startswith("SKILL_"):
        pretty_name = key.replace("SKILL_", "").replace("_", " ").title()
        if pretty_name not in current_skills:
            try:
                sid = int(val)
                new_entries.append(f'Skill "{pretty_name}"'.ljust(43) + f'MaxLevel_100   EXP_0                {sid}\n')
                print(f"Adding missing skill: {pretty_name} (ID {sid})")
            except: pass

# 3. Append to Skills.hry
if new_entries:
    with open(skills_path, 'a') as f:
        if not content.endswith('\n'): f.write('\n')
        f.writelines(new_entries)
    print(f"SUCCESS: Harvested {len(new_entries)} missing skills.")
else:
    print("No missing skills found.")
