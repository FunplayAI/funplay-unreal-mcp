"""Check GitHub for a newer plugin release (called on demand from the menu)."""

import json
import urllib.request

from . import constants


def _version_parts(version):
    out = []
    for piece in str(version).split(".")[:3]:
        digits = "".join(ch for ch in piece if ch.isdigit())
        out.append(int(digits) if digits else 0)
    while len(out) < 3:
        out.append(0)
    return out


def _is_newer(candidate, current):
    return _version_parts(candidate) > _version_parts(current)


def check_for_updates():
    url = "https://api.github.com/repos/%s/releases/latest" % constants.GITHUB_REPO
    try:
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "Funplay-Unreal-MCP",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc), "current": constants.SERVER_VERSION}

    latest = (data.get("tag_name") or "").lstrip("v")
    return {
        "ok": True,
        "current": constants.SERVER_VERSION,
        "latest": latest,
        "has_update": bool(latest) and _is_newer(latest, constants.SERVER_VERSION),
        "url": data.get("html_url"),
    }
