#!/usr/bin/env python3
import argparse
import json
import os
import urllib.request
from pathlib import Path

import requests
try:
    import tomlkit
except ImportError:
    tomlkit = None
    print("⚠️ tomlkit not installed, TOML config patches will be skipped.")

# -----------------------------
# Default remote manifest
# -----------------------------
DEFAULT_REMOTE_MANIFEST = "https://raw.githubusercontent.com/wrldmap/gtnhpatcher/refs/heads/main/manifest.json"

# -----------------------------
# Load manifest (local or remote)
# -----------------------------
def load_manifest(local=None, remote=None):
    if local:
        path = Path(local)
        if not path.exists():
            raise FileNotFoundError(f"Local manifest not found: {local}")
        with open(path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        print(f"✅ Loaded local manifest: {local}")
        return manifest
    else:
        url = remote or DEFAULT_REMOTE_MANIFEST
        r = requests.get(url)
        r.raise_for_status()
        manifest = r.json()
        print(f"✅ Loaded remote manifest: {url}")
        return manifest

# -----------------------------
# Patch mods
# -----------------------------
def patch_mods(instance_dir, manifest):
    mods_dir = instance_dir / "mods"
    mods_dir.mkdir(exist_ok=True)

    # Remove mods
    for mod in manifest.get("remove_mods", []):
        target = mods_dir / mod
        if target.exists():
            print(f"🗑 Removing {mod}")
            target.unlink()

    # Add/update mods
    for mod_info in manifest.get("add_mods", []):
        url = mod_info["url"]
        name = url.split("/")[-1]
        dest = mods_dir / name
        if not dest.exists():
            print(f"⬇️ Downloading {name}")
            urllib.request.urlretrieve(url, dest)

# -----------------------------
# Edit configs dynamically
# -----------------------------
def edit_configs(instance_dir, patches):
    config_dir = instance_dir / "config"
    for patch in patches:
        config_path = os.path.join(config_dir, patch["file"])
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

        # Load existing config or create a new one
        config_data = {}
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                for line in f:
                    if "=" in line:
                        key, value = line.strip().split("=", 1)
                        config_data[key.strip()] = value.strip()

        # Apply changes
        for key, value in patch["changes"].items():
            config_data[key] = str(value).lower() if isinstance(value, bool) else str(value)

        # Save back to file in key=value style
        with open(config_path, "w", encoding="utf-8") as f:
            for key, value in config_data.items():
                f.write(f"{key}={value}\n")

        print(f"✔ Patched config: {config_path}")

def download_configs(instance_dir, downloads):
    config_dir = instance_dir / "config"
    for entry in downloads:
        url = entry["url"]
        file_path = os.path.join(config_dir, entry["file"])
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        print(f"⬇ Downloading config {entry['file']} ...")
        r = requests.get(url)
        r.raise_for_status()
        with open(file_path, "wb") as f:
            f.write(r.content)
        print(f"✔ Saved {entry['file']}")

# -----------------------------
# Main
# -----------------------------
def main():
    parser = argparse.ArgumentParser(description="Instance-local Modpack Patcher")
    parser.add_argument("--local", help="Path to local manifest JSON")
    parser.add_argument("--remote", help="URL to remote manifest JSON (overrides default)")
    args = parser.parse_args()

    instance_dir = Path.cwd()
    print(f"🔹 Running patcher in instance folder: {instance_dir}")

    manifest = load_manifest(local=args.local, remote=args.remote)
    patch_mods(instance_dir, manifest)
    # Apply config patches
    if "config_patches" in manifest:
        edit_configs(instance_dir, manifest["config_patches"])

    # Download configs from GitHub
    if "config_downloads" in manifest:
        download_configs(instance_dir, manifest["config_downloads"])

    print("\n✅ GTNH has been patched or whatever. Don't run this again or it'll break.")

if __name__ == "__main__":
    main()
