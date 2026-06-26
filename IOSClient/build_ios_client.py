#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys
import zipfile

# Set up paths
IOS_CLIENT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.dirname(IOS_CLIENT_DIR)
DIST_DIR = os.path.join(WORKSPACE_DIR, "dist")
OUTPUT_DIR = os.path.join(DIST_DIR, "IOSClient")
XCODE_PROJ_PATH = os.path.join(
    IOS_CLIENT_DIR, 
    "build", 
    "client-mobile", 
    "ios", 
    "xcode", 
    "ThePlayerCity Client.xcodeproj"
)
# Scratch path outside iCloud for safe codesigning
TEMP_SIGN_DIR = "/Users/kylebishop/.gemini/antigravity-ide/brain/6f925333-11bd-4aff-97f0-6f2d8d207527/scratch/temp_ios_build"

def run_command(args, cwd=None):
    print(f"Running: {' '.join(args)}")
    result = subprocess.run(args, cwd=cwd, stdout=sys.stdout, stderr=sys.stderr)
    if result.returncode != 0:
        print(f"Error: Command failed with exit code {result.returncode}")
        sys.exit(result.returncode)

def increment_version():
    toml_path = os.path.join(IOS_CLIENT_DIR, "pyproject.toml")
    if not os.path.exists(toml_path):
        return "0.1.0"
    
    with open(toml_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    version = "0.1.0"
    for i, line in enumerate(lines):
        if line.strip().startswith("version ="):
            parts = line.split("=")
            version = parts[1].strip().strip('"').strip("'")
            v_parts = version.split(".")
            if len(v_parts) == 3:
                try:
                    patch = int(v_parts[2]) + 1
                    new_version = f"{v_parts[0]}.{v_parts[1]}.{patch}"
                except ValueError:
                    new_version = version
            else:
                new_version = version + ".1"
            
            lines[i] = f'version = "{new_version}"\n'
            version = new_version
            break
            
    with open(toml_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
        
    return version

def main():
    print("=== Starting TrollStore .tipa build pipeline ===")
    
    # 0. Sync latest code and assets from 2DGameEditor root
    print("Syncing game resources to IOSClient...")
    rebuild_script = os.path.join(IOS_CLIENT_DIR, "RebuildAssets.py")
    run_command([sys.executable, rebuild_script])
    
    # 1. Increment version in pyproject.toml
    version = increment_version()
    print(f"Iterated version to: {version}")
    
    # 2. Ensure output folders exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 3. Check if Briefcase Xcode project exists, create or update it
    if not os.path.exists(XCODE_PROJ_PATH):
        print("Xcode project not found. Running 'briefcase create ios'...")
        run_command([sys.executable, "-m", "briefcase", "create", "ios", "--no-input"], cwd=IOS_CLIENT_DIR)
    else:
        print("Xcode project found. Running 'briefcase update ios' to sync latest changes...")
        run_command([sys.executable, "-m", "briefcase", "update", "ios", "--no-input"], cwd=IOS_CLIENT_DIR)

    # 3.5 Fix Briefcase path-with-spaces bug in project.pbxproj
    pbxproj_path = os.path.join(
        IOS_CLIENT_DIR, 
        "build", 
        "client-mobile", 
        "ios", 
        "xcode", 
        "ThePlayerCity Client.xcodeproj",
        "project.pbxproj"
    )
    if os.path.exists(pbxproj_path):
        print("Fixing unquoted path bug in project.pbxproj...")
        with open(pbxproj_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        bad_line = 'source $PROJECT_DIR/Support/Python.xcframework/build/utils.sh'
        good_line = 'source \\"$PROJECT_DIR/Support/Python.xcframework/build/utils.sh\\"'
        if bad_line in content:
            content = content.replace(bad_line, good_line)
            with open(pbxproj_path, "w", encoding="utf-8") as f:
                f.write(content)
            print("Successfully patched project.pbxproj!")
        else:
            print("Path bug not found or already patched.")

    # 3.6 Fix utils.sh signing identity fallback when xcodebuild codesigning is disabled
    utils_sh_path = os.path.join(
        IOS_CLIENT_DIR,
        "build",
        "client-mobile",
        "ios",
        "xcode",
        "Support",
        "Python.xcframework",
        "build",
        "utils.sh"
    )
    if os.path.exists(utils_sh_path):
        print("Fixing signing identity fallback in utils.sh...")
        with open(utils_sh_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        old_sign_block = '    /usr/bin/codesign --force --sign "$EXPANDED_CODE_SIGN_IDENTITY"'
        new_sign_block = '    SIGN_IDENTITY="${EXPANDED_CODE_SIGN_IDENTITY:--}"\n    /usr/bin/codesign --force --sign "$SIGN_IDENTITY"'
        if old_sign_block in content:
            content = content.replace(old_sign_block, new_sign_block)
            with open(utils_sh_path, "w", encoding="utf-8") as f:
                f.write(content)
            print("Successfully patched utils.sh!")
        else:
            print("utils.sh patch not needed or already applied.")

    # 4. Compile the app for iOS Device SDK (iphoneos) with signing disabled
    print("Compiling iOS application via xcodebuild (signing disabled to prevent iCloud drive errors)...")
    app_build_dir = os.path.join(
        IOS_CLIENT_DIR, 
        "build", 
        "client-mobile", 
        "ios", 
        "xcode", 
        "build", 
        "Debug-iphoneos"
    )
    xcode_build_args = [
        "xcodebuild",
        "-project", XCODE_PROJ_PATH,
        "-scheme", "ThePlayerCity Client",
        "-configuration", "Debug",
        "-sdk", "iphoneos",
        "CODE_SIGNING_ALLOWED=NO",
        "CODE_SIGNING_REQUIRED=NO",
        "CODE_SIGN_IDENTITY=",
        "AD_HOC_CODE_SIGNING_ALLOWED=YES",
        f"CONFIGURATION_BUILD_DIR={app_build_dir}",
        "clean", "build"
    ]
    run_command(xcode_build_args)

    # 5. Locate the compiled .app bundle
    app_bundle_path = os.path.join(app_build_dir, "ThePlayerCity Client.app")
    if not os.path.exists(app_bundle_path):
        print(f"Error: Compiled app bundle not found at {app_bundle_path}")
        sys.exit(1)

    # 6. Copy app bundle to non-iCloud scratch directory for codesigning
    print("Copying compiled app bundle to sandboxed temp directory...")
    shutil.rmtree(TEMP_SIGN_DIR, ignore_errors=True)
    os.makedirs(TEMP_SIGN_DIR, exist_ok=True)
    temp_app_path = os.path.join(TEMP_SIGN_DIR, "ThePlayerCity Client.app")
    shutil.copytree(app_bundle_path, temp_app_path, symlinks=True)

    # 7. Clean extended attributes and sign the app manually (avoids iCloud detritus error)
    print("Clearing extended attributes and ad-hoc signing the app bundle manually...")
    subprocess.run(f'find "{temp_app_path}" -print0 | xargs -0 xattr -crs', shell=True)
    run_command(["/usr/bin/codesign", "--force", "--sign", "-", temp_app_path])
        
    # 8. Package as a .tipa file (TrollStore IPA) with version suffix
    print("Packaging app into TrollStore .tipa format...")
    temp_payload_dir = os.path.join(TEMP_SIGN_DIR, "Payload")
    os.makedirs(temp_payload_dir, exist_ok=True)
    
    # Move signed app bundle into Payload/
    dest_app_path = os.path.join(temp_payload_dir, "ThePlayerCity Client.app")
    shutil.move(temp_app_path, dest_app_path)
    
    # Create the zip archive renamed as .tipa
    tipa_name = f"ThePlayerCity_Client_v{version}.tipa"
    temp_tipa_path = os.path.join(TEMP_SIGN_DIR, tipa_name)
    print(f"Creating zip archive at {temp_tipa_path}...")
    
    with zipfile.ZipFile(temp_tipa_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(temp_payload_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.dirname(temp_payload_dir))
                zip_file.write(file_path, arcname)
                
    # Copy completed .tipa back to workspace dist/IOSClient folder
    final_tipa_path = os.path.join(OUTPUT_DIR, tipa_name)
    shutil.copy2(temp_tipa_path, final_tipa_path)
    
    # Clean up temporary scratch folders
    shutil.rmtree(TEMP_SIGN_DIR)
    
    # 9. Clean up old builds (only keep last 4 builds, deleting the 5th oldest)
    cleanup_old_builds()
    
    print(f"=== Build successful! output saved to: {final_tipa_path} ===")

def cleanup_old_builds():
    if not os.path.exists(OUTPUT_DIR):
        return
    
    # List all .tipa files in the output directory
    files = [os.path.join(OUTPUT_DIR, f) for f in os.listdir(OUTPUT_DIR) if f.startswith("ThePlayerCity_Client_v") and f.endswith(".tipa")]
    
    # Sort files by modification time (oldest first)
    files.sort(key=os.path.getmtime)
    
    # If we have more than 4 builds, delete the oldest
    if len(files) > 4:
        files_to_delete = files[:-4] # Keep the last 4
        for f in files_to_delete:
            try:
                print(f"Deleting old build: {os.path.basename(f)}")
                os.remove(f)
            except Exception as e:
                print(f"Failed to delete {f}: {e}")

if __name__ == "__main__":
    main()
