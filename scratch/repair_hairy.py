import os
import re

def repair_hairy():
    project_path = r"E:\2DGameEditor\Saves\MyNewProject\HAIRY"
    if not os.path.exists(project_path):
        print(f"Path not found: {project_path}")
        return

    # Markers for documentation we want to skip/truncate
    unwanted_markers = [
        "// --- NPC DATA", "// --- AUTO-GENERATED ", "// MASTER OBJECT TEMPLATE",
        "// This file explains how", "// Anything defined here", "// ENGINE API ROADMAP",
        "//   ENGINE COMMAND REFERENCE", "// SECTION ", "//   Delete hooks you don't need"
    ]

    for filename in os.listdir(project_path):
        if filename.endswith(".hry") or filename == "Shops.hry":
            filepath = os.path.join(project_path, filename)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
                
                defines = []
                hooks = []
                other_text = []
                
                # 1. Parsing and extracting components
                in_hook = False
                hook_buffer = []
                brace_count = 0
                
                for line in lines:
                    s = line.strip().upper()
                    
                    # Detect Doc Truncation
                    if "// ENGINE API ROADMAP" in line or "//   ENGINE COMMAND REFERENCE" in line:
                        break

                    # Collect Defines (Modernized)
                    if s.startswith("#DEFINE") or s.startswith("DEFINE"):
                        normalized = line.replace("#Define", "DEFINE").replace("#define", "DEFINE").replace("define", "DEFINE")
                        normalized = normalized.replace("DEFINE FAMILY ", "DEFINE ").replace("DEFINE LOCAL ", "DEFINE ")
                        defines.append(normalized)
                        continue

                    # Collect Logic Hooks (OnUse, OnNew, etc.)
                    # This logic handles hooks whether they are inside an Object block or not
                    if s.startswith("ON") and not s.startswith("ONLY") and "{" in line:
                        in_hook = True
                        brace_count += line.count("{") - line.count("}")
                        hook_buffer = [line]
                        if brace_count == 0 and "}" in line:
                            hooks.append("".join(hook_buffer))
                            in_hook = False
                        continue
                    
                    if in_hook:
                        hook_buffer.append(line)
                        brace_count += line.count("{") - line.count("}")
                        if brace_count <= 0:
                            hooks.append("".join(hook_buffer))
                            in_hook = False
                        continue

                    # Filter out boilerplate and non-essential comments
                    if any(m in line for m in unwanted_markers): continue
                    if s.startswith("OBJECT \""): continue # We will regenerate the Object line
                    if s == "}" or s == "{": continue # We will regenerate the main brackets
                    
                    if line.strip():
                        other_text.append(line)

                # 2. Reassembly - following the "Apprentice Leggings" layout
                obj_name = filename.replace(".hry", "")
                
                # Header
                new_content = f"//{'='*68}\n//\n//\n// {filename}\n//\n//\n//{'='*68}\n\n"
                
                # Defines (Deduplicated)
                unique_defines = []
                seen_keys = set()
                for d in defines:
                    parts = d.strip().split()
                    if len(parts) >= 2:
                        key = parts[1]
                        if key not in seen_keys:
                            unique_defines.append(d)
                            seen_keys.add(key)
                
                # Ensure core properties
                if "FAM_" not in "".join(unique_defines): unique_defines.insert(0, "DEFINE FAM_OBJ\n")
                if "TILESET" not in "".join(unique_defines): unique_defines.append("DEFINE TILESET World\n")
                if "GRAPHIC" not in "".join(unique_defines): unique_defines.append("DEFINE GRAPHIC 0, 0\n")
                if "SOLID" not in "".join(unique_defines): unique_defines.append("DEFINE SOLID TRUE\n")
                
                new_content += "".join(unique_defines) + "\n"
                
                # Syntax Reference
                new_content += "// --- Syntax Reference ---\n"
                new_content += "// Math: Health += 10 | Health Plus 10\n"
                new_content += "// Math: Gold -= 5 | Gold Minus 5\n"
                new_content += "// Logic: If (Level > 10) { ... }\n"
                new_content += "// Choice: DEFINE HasClicked 0 | DEFINE IsActivated 0\n\n"
                
                # Main Object Wrap
                new_content += f"Object \"{obj_name}\"\n{{\n"
                
                # Add all hooks inside (indented)
                for hook in hooks:
                    # Deduplicate hooks (like OnNew showing up twice)
                    header = hook.split("{")[0].strip()
                    if header in ["OnNew", "OnSpawn", "OnDeath", "OnTalk", "OnUse"] and any(header in h for h in new_content.splitlines()):
                        continue # Skip duplicate empty hooks
                        
                    indented_hook = ""
                    for hline in hook.splitlines():
                        indented_hook += "    " + hline + "\n"
                    new_content += indented_hook
                
                new_content += "}\n"
                
                # Final pass: Remove leftover #Defines or trash
                final_content = []
                for line in new_content.splitlines():
                    if "#Define" in line: line = line.replace("#Define", "DEFINE")
                    final_content.append(line)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write("\n".join(final_content) + "\n")
                print(f"Repaired & Wrapped: {filename}")

            except Exception as e:
                print(f"Failed repairing {filename}: {e}")

if __name__ == "__main__":
    repair_hairy()
