import os, re
path = r'E:\2DGameEditor\Saves\MyNewProject\HAIRY\Skills.hry'
with open(path, 'r') as f: content = f.read()

# 1. Capture Table section
# It starts at the top and goes until the last } before a "Skill" keyword
first_skill = content.find('Skill "')
tables_part = content[:first_skill].strip()
skills_part = content[first_skill:]

# 2. Extract and format all skills
new_skills_list = []
# Find: Skill "Any Name" { Any Content }
matches = re.finditer(r'(?i)Skill\s+"([^"]+)"\s*\{([^}]+)\}', skills_part)

for m in matches:
    name = m.group(1)
    body = m.group(2).strip()
    
    # Extract key-value pairs from the body
    # We look for ID MaxLevel Table etc.
    pairs = re.findall(r'(ID\s+\d+|MaxLevel\s+\d+|Table\s+"[^"]+")', body, re.IGNORECASE)
    
    formatted_body = "\n".join([f"    {p}" for p in pairs])
    formatted_skill = f'Skill "{name}"\n{{\n{formatted_body}\n}}\n\n'
    new_skills_list.append(formatted_skill)

final_out = tables_part + "\n\n" + "".join(new_skills_list)

with open(path, 'w') as f:
    f.write(final_out)

print(f"COMPLETE: Reformatted {len(new_skills_list)} skills.")
