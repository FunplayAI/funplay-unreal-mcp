"""Write MCP client config files pointing at the npx stdio bridge.

Each AI client launches ``npx -y funplay-unreal-mcp@<ver>`` with
FUNPLAY_UNREAL_MCP_URL / FUNPLAY_UNREAL_MCP_TOKEN env vars; the bridge forwards
stdio JSON-RPC to this editor's local HTTP server."""

import json
import os
import re
import sys

from . import constants

SERVER_KEY = "funplay-unreal"


def _home():
    return os.path.expanduser("~")


def _vscode_path():
    if sys.platform == "darwin":
        mac = os.path.join(
            _home(), "Library", "Application Support", "Code", "User", "mcp.json"
        )
        if os.path.isdir(os.path.dirname(mac)):
            return mac
        return os.path.join(_home(), ".vscode", "mcp.json")
    if os.name == "nt":
        appdata = os.environ.get("APPDATA", os.path.join(_home(), "AppData", "Roaming"))
        return os.path.join(appdata, "Code", "User", "mcp.json")
    return os.path.join(_home(), ".config", "Code", "User", "mcp.json")


def _targets():
    return {
        "claude": {
            "label": "Claude Code",
            "path": os.path.join(_home(), ".claude.json"),
            "format": "json",
            "root_key": "mcpServers",
            "include_type": True,
        },
        "cursor": {
            "label": "Cursor",
            "path": os.path.join(_home(), ".cursor", "mcp.json"),
            "format": "json",
            "root_key": "mcpServers",
            "include_type": False,
        },
        "vscode": {
            "label": "VS Code",
            "path": _vscode_path(),
            "format": "json",
            "root_key": "servers",
            "include_type": True,
        },
        "codex": {
            "label": "Codex",
            "path": os.path.join(_home(), ".codex", "config.toml"),
            "format": "toml",
            "root_key": "mcp_servers",
            "include_type": False,
        },
    }


def _entry(endpoint, token, include_type):
    entry = {
        "command": "npx",
        "args": ["-y", constants.WRAPPER_PACKAGE],
        "env": {constants.ENV_URL: endpoint},
    }
    if token:
        entry["env"][constants.ENV_TOKEN] = token
    if include_type:
        entry["type"] = "stdio"
    return entry


class ClientConfigWriter:
    def list_targets(self):
        return {key: t["label"] for key, t in _targets().items()}

    def build_snippet(self, client, endpoint, token=""):
        target = _targets().get(client)
        if target is None:
            return None
        if target["format"] == "toml":
            return _toml_section(endpoint, token)
        entry = _entry(endpoint, token, target["include_type"])
        return json.dumps({target["root_key"]: {SERVER_KEY: entry}}, indent=2)

    def configure(self, client, endpoint, token=""):
        target = _targets().get(client)
        if target is None:
            return {"ok": False, "error": "unknown client: %s" % client}
        try:
            os.makedirs(os.path.dirname(target["path"]), exist_ok=True)
            if target["format"] == "toml":
                _write_toml(target["path"], endpoint, token)
            else:
                _write_json(
                    target["path"],
                    target["root_key"],
                    _entry(endpoint, token, target["include_type"]),
                )
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc), "path": target["path"]}
        return {"ok": True, "path": target["path"]}


def _write_json(path, root_key, entry):
    root = {}
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as fh:
            raw = fh.read().strip()
        if raw:
            parsed = json.loads(raw)  # abort (raise) if invalid -- do not clobber
            if not isinstance(parsed, dict):
                raise ValueError("existing config root is not an object: %s" % path)
            root = parsed
    root.setdefault(root_key, {})
    if not isinstance(root[root_key], dict):
        raise ValueError("existing '%s' is not an object" % root_key)
    root[root_key][SERVER_KEY] = entry
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(root, fh, indent=2)
        fh.write("\n")


def _toml_section(endpoint, token):
    lines = [
        '[%s."%s"]' % ("mcp_servers", SERVER_KEY),
        'command = "npx"',
        'args = ["-y", "%s"]' % constants.WRAPPER_PACKAGE,
        "",
        '[%s."%s".env]' % ("mcp_servers", SERVER_KEY),
        '%s = "%s"' % (constants.ENV_URL, endpoint),
    ]
    if token:
        lines.append('%s = "%s"' % (constants.ENV_TOKEN, token))
    return "\n".join(lines)


def _write_toml(path, endpoint, token):
    section = _toml_section(endpoint, token)
    existing = ""
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as fh:
            existing = fh.read()
    pattern = re.compile(
        r'\[mcp_servers\."%s"\].*?(?=\n\[[^\n]*\]\n|\Z)' % re.escape(SERVER_KEY),
        re.DOTALL,
    )
    if pattern.search(existing):
        merged = pattern.sub(section + "\n", existing)
    else:
        merged = existing.rstrip()
        merged = (merged + "\n\n" + section + "\n") if merged else (section + "\n")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(merged)
