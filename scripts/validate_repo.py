#!/usr/bin/env python3
"""Repository validation -- the CI gate for funplay-unreal-mcp.

Checks required files exist, versions are in sync across all manifests, the MCP
default protocol version is correct, the documented tool counts match the real
registry, and there is no junk committed. Exits non-zero on the first failure."""

import json
import os
import re
import sys
import types

sys.dont_write_bytecode = True  # don't create __pycache__ when we import the plugin

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN = os.path.join(ROOT, "FunplayMCP")
PY_ROOT = os.path.join(PLUGIN, "Content", "Python")
PKG = os.path.join(PY_ROOT, "funplay_mcp")

_errors = []


def fail(msg):
    _errors.append(msg)


def read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


REQUIRED_FILES = [
    "README.md",
    "README_CN.md",
    "LICENSE",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "RELEASE_CHECKLIST.md",
    "server.json",
    ".github/workflows/ci.yml",
    ".github/workflows/release.yml",
    "scripts/package_release.py",
    "FunplayMCP/FunplayMCP.uplugin",
    "FunplayMCP/Content/Python/init_unreal.py",
    "FunplayMCP/Content/Python/funplay_mcp/__init__.py",
    "FunplayMCP/Content/Python/funplay_mcp/constants.py",
    "FunplayMCP/Content/Python/funplay_mcp/server.py",
    "FunplayMCP/Content/Python/funplay_mcp/tools/__init__.py",
    "stdio-wrapper/package.json",
    "stdio-wrapper/bin/funplay-unreal-mcp.js",
    "stdio-wrapper/README.md",
]


def check_required_files():
    for rel in REQUIRED_FILES:
        if not os.path.isfile(os.path.join(ROOT, rel)):
            fail("missing required file: %s" % rel)


def get_constant(name):
    text = read(os.path.join(PKG, "constants.py"))
    match = re.search(r'^%s\s*=\s*"([^"]+)"' % name, text, re.MULTILINE)
    return match.group(1) if match else None


def check_versions():
    version = get_constant("SERVER_VERSION")
    if not version:
        fail("could not read SERVER_VERSION from constants.py")
        return None

    uplugin = json.loads(read(os.path.join(PLUGIN, "FunplayMCP.uplugin")))
    if uplugin.get("VersionName") != version:
        fail("FunplayMCP.uplugin VersionName %r != %r" % (uplugin.get("VersionName"), version))

    wrapper = json.loads(read(os.path.join(ROOT, "stdio-wrapper", "package.json")))
    if wrapper.get("version") != version:
        fail("stdio-wrapper/package.json version %r != %r" % (wrapper.get("version"), version))
    if wrapper.get("name") != "funplay-unreal-mcp":
        fail("stdio-wrapper package name must be 'funplay-unreal-mcp'")
    if wrapper.get("mcpName") != "io.github.FunplayAI/funplay-unreal-mcp":
        fail("stdio-wrapper mcpName mismatch")
    bin_map = wrapper.get("bin") or {}
    if bin_map.get("funplay-unreal-mcp") != "bin/funplay-unreal-mcp.js":
        fail("stdio-wrapper bin mapping mismatch")

    server = json.loads(read(os.path.join(ROOT, "server.json")))
    if server.get("name") != "io.github.FunplayAI/funplay-unreal-mcp":
        fail("server.json name mismatch")
    if server.get("version") != version:
        fail("server.json version %r != %r" % (server.get("version"), version))
    packages = server.get("packages") or []
    if len(packages) != 1:
        fail("server.json must declare exactly one package")
    else:
        pkg = packages[0]
        if pkg.get("identifier") != "funplay-unreal-mcp" or pkg.get("registryType") != "npm":
            fail("server.json package must be the npm 'funplay-unreal-mcp'")
        if pkg.get("version") != version:
            fail("server.json package version %r != %r" % (pkg.get("version"), version))
        if (pkg.get("transport") or {}).get("type") != "stdio":
            fail("server.json transport must be stdio")

    changelog = read(os.path.join(ROOT, "CHANGELOG.md"))
    if ("## [%s]" % version) not in changelog:
        fail("CHANGELOG.md has no '## [%s]' section" % version)

    return version


def check_protocol():
    text = read(os.path.join(PKG, "constants.py"))
    match = re.search(
        r"SUPPORTED_PROTOCOL_VERSIONS\s*=\s*\[(.*?)\]", text, re.DOTALL
    )
    if not match:
        fail("SUPPORTED_PROTOCOL_VERSIONS not found in constants.py")
        return
    versions = re.findall(r'"([^"]+)"', match.group(1))
    if not versions:
        fail("SUPPORTED_PROTOCOL_VERSIONS is empty")
    elif versions[0] != "2025-11-25":
        fail("default protocol version must be 2025-11-25, got %r" % versions[0])


def count_tools():
    """Import the plugin with a stubbed 'unreal' module and register all tools."""
    unreal = types.ModuleType("unreal")

    class _Any:
        def __getattr__(self, _n):
            return _Any()

        def __call__(self, *a, **k):
            return _Any()

    unreal.__getattr__ = lambda _name: _Any()
    sys.modules["unreal"] = unreal
    sys.path.insert(0, PY_ROOT)
    try:
        from funplay_mcp.tool_registry import ToolRegistry
        from funplay_mcp import tools as tools_pkg

        reg = ToolRegistry(ctx=None)
        tools_pkg.register_all(reg)
    except Exception as exc:  # noqa: BLE001
        import traceback

        fail("tool registration failed: %s\n%s" % (exc, traceback.format_exc()))
        return None, None
    names = reg.names()
    if len(set(names)) != len(names):
        fail("duplicate tool names registered")
    core = [n for n in names if "core" in reg.get(n)["profiles"]]
    return len(names), len(core)


def check_doc_counts(total, core):
    if total is None:
        return
    en = read(os.path.join(ROOT, "README.md"))
    cn = read(os.path.join(ROOT, "README_CN.md"))

    en_counts = set(int(x) for x in re.findall(r"\*\*(\d+)\s+[Bb]uilt-in [Tt]ools", en))
    if not en_counts:
        fail("README.md must document '**N built-in tools**'")
    elif en_counts != {total}:
        fail("README.md tool count %s != actual %d" % (sorted(en_counts), total))

    cn_counts = set(int(x) for x in re.findall(r"\*\*(\d+)\s*个内置工具", cn))
    if not cn_counts:
        fail("README_CN.md must document '**N 个内置工具**'")
    elif cn_counts != {total}:
        fail("README_CN.md tool count %s != actual %d" % (sorted(cn_counts), total))


JUNK_NAMES = {".DS_Store", "Thumbs.db"}
JUNK_DIRS = {"__pycache__", ".idea", "Binaries", "Intermediate", "Saved", "node_modules"}


def check_junk():
    """Flag junk that is tracked by git (what actually gets committed / hits CI).

    Falls back to a working-tree scan when not in a git repo. This avoids false
    positives from gitignored, locally-regenerated files like macOS .DS_Store."""
    import subprocess

    try:
        out = subprocess.run(
            ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
        )
        for rel in out.stdout.splitlines():
            parts = rel.split("/")
            if os.path.basename(rel) in JUNK_NAMES:
                fail("junk file tracked by git: %s" % rel)
            elif any(d in parts for d in JUNK_DIRS):
                fail("junk path tracked by git: %s" % rel)
        return
    except Exception:  # noqa: BLE001 -- not a git repo; fall back to a FS scan
        pass

    for dirpath, dirnames, filenames in os.walk(ROOT):
        if ".git" in dirpath.split(os.sep) or "dist" in dirpath.split(os.sep):
            continue
        for name in filenames:
            if name in JUNK_NAMES:
                fail("junk file present: %s" % os.path.join(dirpath, name))
        for d in list(dirnames):
            if d in JUNK_DIRS:
                fail("junk dir present: %s" % os.path.join(dirpath, d))


def main():
    check_required_files()
    version = check_versions()
    check_protocol()
    total, core = count_tools()
    check_doc_counts(total, core)
    check_junk()

    if _errors:
        print("VALIDATION FAILED (%d issue(s)):" % len(_errors))
        for err in _errors:
            print("  - %s" % err)
        return 1
    print(
        "OK: funplay-unreal-mcp v%s -- %s tools (%s core), all checks passed."
        % (version, total, core)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
