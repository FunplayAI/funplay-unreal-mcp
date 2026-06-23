#!/usr/bin/env python3
"""Package a funplay-unreal-mcp release into dist/v<version>/.

Produces: the plugin zip (FunplayMCP/ + LICENSE), a copy of server.json,
release-notes.md (extracted from CHANGELOG), release-manifest.json, and
SHA256SUMS.txt."""

import argparse
import hashlib
import json
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN_DIR = os.path.join(ROOT, "FunplayMCP")
PACKAGE_PREFIX = "Funplay.UnrealMcp"
REPOSITORY = "FunplayAI/funplay-unreal-mcp"

EXCLUDE_NAMES = {".DS_Store", "Thumbs.db"}
EXCLUDE_PARTS = {
    ".git",
    "__pycache__",
    "Binaries",
    "Intermediate",
    "Saved",
    "node_modules",
    "dist",
}


def read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def detect_version():
    text = read(os.path.join(PLUGIN_DIR, "Content", "Python", "funplay_mcp", "constants.py"))
    match = re.search(r'^SERVER_VERSION\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise SystemExit("could not detect SERVER_VERSION")
    return match.group(1)


def collect_plugin_files():
    files = []
    for dirpath, dirnames, filenames in os.walk(PLUGIN_DIR):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_PARTS]
        for name in filenames:
            if name in EXCLUDE_NAMES:
                continue
            abs_path = os.path.join(dirpath, name)
            if os.path.islink(abs_path):
                continue
            arc = os.path.relpath(abs_path, ROOT)  # keeps "FunplayMCP/..."
            files.append((abs_path, arc))
    files.append((os.path.join(ROOT, "LICENSE"), "LICENSE"))
    return sorted(files, key=lambda pair: pair[1])


def write_zip(zip_path, files):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for abs_path, arc in files:
            if ".." in arc.split("/") or arc.startswith("/") or "\\" in arc:
                raise SystemExit("unsafe archive member: %s" % arc)
            zf.write(abs_path, arc)


def extract_release_notes(version):
    changelog = read(os.path.join(ROOT, "CHANGELOG.md"))
    pattern = re.compile(
        r"^##\s*\[%s\].*?(?=^##\s*\[|\Z)" % re.escape(version), re.DOTALL | re.MULTILINE
    )
    match = pattern.search(changelog)
    return match.group(0).strip() if match else "Release %s" % version


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Package a funplay-unreal-mcp release.")
    parser.add_argument("--version", default=None)
    parser.add_argument("--output-dir", default=os.path.join(ROOT, "dist"))
    args = parser.parse_args()

    version = (args.version or detect_version()).lstrip("v")
    out_dir = os.path.join(args.output_dir, "v%s" % version)
    os.makedirs(out_dir, exist_ok=True)

    zip_name = "%s.v%s.zip" % (PACKAGE_PREFIX, version)
    zip_path = os.path.join(out_dir, zip_name)
    files = collect_plugin_files()
    write_zip(zip_path, files)

    # copy server.json
    server_src = os.path.join(ROOT, "server.json")
    server_dst = os.path.join(out_dir, "server.json")
    with open(server_dst, "w", encoding="utf-8") as fh:
        fh.write(read(server_src))

    notes_path = os.path.join(out_dir, "release-notes.md")
    with open(notes_path, "w", encoding="utf-8") as fh:
        fh.write(extract_release_notes(version) + "\n")

    manifest = {
        "version": version,
        "tag": "v%s" % version,
        "repository": {"url": "https://github.com/%s" % REPOSITORY, "source": "github"},
        "githubReleaseUrl": "https://github.com/%s/releases/tag/v%s" % (REPOSITORY, version),
        "unrealPlugin": {
            "file": zip_name,
            "sha256": sha256(zip_path),
            "size": os.path.getsize(zip_path),
            "installRoot": "FunplayMCP",
        },
        "stdioWrapper": {
            "package": "funplay-unreal-mcp",
            "version": version,
            "command": "npx -y funplay-unreal-mcp@%s" % version,
            "mcpName": "io.github.FunplayAI/funplay-unreal-mcp",
        },
    }
    manifest_path = os.path.join(out_dir, "release-manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")

    sums_path = os.path.join(out_dir, "SHA256SUMS.txt")
    with open(sums_path, "w", encoding="utf-8") as fh:
        for artifact in (zip_path, server_dst, notes_path, manifest_path):
            fh.write("%s  %s\n" % (sha256(artifact), os.path.basename(artifact)))

    print("Packaged funplay-unreal-mcp v%s -> %s" % (version, out_dir))
    for name in sorted(os.listdir(out_dir)):
        print("  - %s" % name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
