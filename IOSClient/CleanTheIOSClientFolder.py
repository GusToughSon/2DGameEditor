#!/usr/bin/env python3
import os
import shutil

# Define paths relative to this script
IOS_CLIENT_DIR = os.path.dirname(os.path.abspath(__file__))

# List of folders/files to clean up
PATHS_TO_REMOVE = [
    # RebuildAssets.py copies
    os.path.join(IOS_CLIENT_DIR, "src", "client_mobile", "client"),
    os.path.join(IOS_CLIENT_DIR, "src", "client_mobile", "core"),
    os.path.join(IOS_CLIENT_DIR, "src", "HAIRY"),
    os.path.join(IOS_CLIENT_DIR, "src", "Saves"),
    
    # Briefcase build artifacts and logs
    os.path.join(IOS_CLIENT_DIR, "build"),
    os.path.join(IOS_CLIENT_DIR, "logs"),
]

def main():
    print("=== Cleaning IOSClient Build and Copied Resources ===")
    
    cleaned_count = 0
    for path in PATHS_TO_REMOVE:
        if os.path.exists(path):
            rel_path = os.path.relpath(path, IOS_CLIENT_DIR)
            print(f"Removing: {rel_path} ...")
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                print("  ...Removed successfully.")
                cleaned_count += 1
            except Exception as e:
                print(f"  ...Failed to remove: {e}")
        else:
            rel_path = os.path.relpath(path, IOS_CLIENT_DIR)
            # Skip print if it's already clean
            
    print(f"=== Clean completed! Removed {cleaned_count} items. ===")

if __name__ == "__main__":
    main()
