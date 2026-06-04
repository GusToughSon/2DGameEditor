import re
import os

# 1. Read the config file
config_file = "config.py"
if not os.path.exists(config_file):
    print("0.1.0")
    exit()

with open(config_file, "r") as f:
    content = f.read()

# 2. Find and increment the version
# Pattern looks for VERSION = "X.Y" or "X.Y.Z"
match = re.search(r'VERSION\s*=\s*"(\d+)\.(\d+)(?:\.(\d+))?"', content)
if match:
    major = match.group(1)
    minor = match.group(2)
    patch = match.group(3)
    
    if patch is not None:
        new_version = f"{major}.{minor}.{int(patch)+1}"
    else:
        new_version = f"{major}.{int(minor)+1}.0"
    
    # Replace the actual version string
    new_content = re.sub(r'VERSION\s*=\s*"[\d.]+"', f'VERSION = "{new_version}"', content)
    
    with open(config_file, "w") as f:
        f.write(new_content)
    
    # Return to batch
    print(new_version)
else:
    # If no version found
    print("1.2.0")
