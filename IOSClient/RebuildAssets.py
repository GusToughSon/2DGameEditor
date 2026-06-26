#!/usr/bin/env python3
import os
import shutil
import sys

# Define base paths relative to this script
IOS_CLIENT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.dirname(IOS_CLIENT_DIR)

# Source directories
SRC_CLIENT = os.path.join(WORKSPACE_DIR, "ThePlayerCity", "client")
SRC_CORE = os.path.join(WORKSPACE_DIR, "ThePlayerCity", "core")
SRC_HAIRY = os.path.join(WORKSPACE_DIR, "HAIRY")
SRC_SAVES = os.path.join(WORKSPACE_DIR, "Saves", "ThePlayerCity")

# Destination directories (inside IOSClient/src/)
DST_CLIENT = os.path.join(IOS_CLIENT_DIR, "src", "client_mobile", "client")
DST_CORE = os.path.join(IOS_CLIENT_DIR, "src", "client_mobile", "core")
DST_HAIRY = os.path.join(IOS_CLIENT_DIR, "src", "HAIRY")
DST_SAVES = os.path.join(IOS_CLIENT_DIR, "src", "Saves", "ThePlayerCity")

def ignore_patterns(path, names):
    ignored = []
    for name in names:
        if name == "__pycache__" or name.endswith(".pyc") or name == ".DS_Store":
            ignored.append(name)
    return ignored

def sync_directory(src, dst):
    print(f"Syncing: {os.path.relpath(src, WORKSPACE_DIR)} -> {os.path.relpath(dst, WORKSPACE_DIR)}")
    
    if not os.path.exists(src):
        print(f"Error: Source directory does not exist: {src}")
        return False
        
    try:
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst, ignore=ignore_patterns)
        print("  ...Success!")
        return True
    except Exception as e:
        print(f"  ...Failed: {e}")
        return False

def main():
    print("=== Starting iOS Client Resource Rebuild Pipeline ===")
    
    # 1. Sync source code
    success = sync_directory(SRC_CLIENT, DST_CLIENT)
    success = sync_directory(SRC_CORE, DST_CORE) and success
    
    # 2. Sync game database configs (.hry)
    success = sync_directory(SRC_HAIRY, DST_HAIRY) and success
    
    # 3. Sync project save files (maps, tilesets, configs)
    success = sync_directory(SRC_SAVES, DST_SAVES) and success
    
    if success:
        print("=== iOS Client resources successfully rebuilt! ===")
        print("You can now build/export the iOS client using Briefcase or Xcode.")
    else:
        print("=== Rebuild completed with warnings/errors. ===")
        sys.exit(1)

if __name__ == "__main__":
    main()
