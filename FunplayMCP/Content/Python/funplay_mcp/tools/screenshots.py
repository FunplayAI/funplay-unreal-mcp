"""Screenshot tools: high-res viewport capture returned as an inline image."""

import base64
import os
import time

import unreal

from .common import prop, project_dir, schema


def _take_screenshot(args, ctx):
    width = args.get("width", 1920)
    height = args.get("height", 1080)
    filename = args.get("filename") or "funplay_mcp_capture.png"
    if not filename.lower().endswith(".png"):
        filename += ".png"

    def _trigger():
        out_dir = os.path.join(project_dir(), "Saved", "Screenshots", "FunplayMCP")
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, filename)
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass
        unreal.AutomationLibrary.take_high_res_screenshot(int(width), int(height), path)
        return path

    try:
        path = ctx.run_on_game_thread(_trigger)
        deadline = time.time() + 20.0
        ready = False
        while time.time() < deadline:
            if os.path.exists(path) and os.path.getsize(path) > 0:
                # Give the file a moment to finish flushing to disk.
                time.sleep(0.3)
                ready = True
                break
            time.sleep(0.25)
        if not ready:
            return ctx.err(
                "screenshot did not render within timeout (try during Play-In-Editor)"
            )
        with open(path, "rb") as handle:
            data = handle.read()
        b64 = base64.b64encode(data).decode("ascii")
        return "data:image/png;base64," + b64
    except Exception as exc:  # noqa: BLE001
        return ctx.err(str(exc))


def register(reg):
    reg.register(
        "take_screenshot",
        "Capture a high-res screenshot of the game viewport and return it as an "
        "inline image. High-res screenshots render the game viewport and work best "
        "during Play-In-Editor.",
        schema(
            {
                "width": prop("integer", "Capture width in pixels (default 1920)."),
                "height": prop("integer", "Capture height in pixels (default 1080)."),
                "filename": prop(
                    "string",
                    "Optional output filename (default 'funplay_mcp_capture.png'; "
                    "'.png' is appended if missing).",
                ),
            },
        ),
        _take_screenshot,
        profiles=("core", "full"),
        game_thread=False,
        group="screenshots",
        timeout=60.0,
    )
