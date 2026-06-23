"""Editor state tools: inspect the editor/project, tail the log, sync the browser."""

import glob
import os

import unreal

from .. import constants
from .common import (
    actor_subsystem,
    all_level_actors,
    asset_subsystem,
    editor_world,
    level_subsystem,
    object_ref,  # noqa: F401  (available for handlers)
    project_dir,
    prop,
    schema,
)


def _get_editor_state(args, ctx):
    state = {}
    try:
        world = editor_world()
        state["current_level"] = world.get_name() if world else None
    except Exception:  # noqa: BLE001
        state["current_level"] = None
    try:
        state["is_in_play"] = bool(level_subsystem().is_in_play_in_editor())
    except Exception:  # noqa: BLE001
        state["is_in_play"] = None
    try:
        state["selected_actor_count"] = len(
            actor_subsystem().get_selected_level_actors()
        )
    except Exception:  # noqa: BLE001
        state["selected_actor_count"] = None
    try:
        state["total_actor_count"] = len(all_level_actors())
    except Exception:  # noqa: BLE001
        state["total_actor_count"] = None
    return ctx.ok(state)


def _get_project_info(args, ctx):
    try:
        engine_version = unreal.SystemLibrary.get_engine_version()
    except Exception:  # noqa: BLE001
        engine_version = None
    return ctx.ok(
        {
            "project_name": ctx.settings.project_name,
            "project_dir": project_dir(),
            "project_identity": ctx.settings.project_identity,
            "engine_version": engine_version,
        }
    )


def _get_output_log(args, ctx):
    max_lines = int(args.get("max_lines", 200))
    contains = args.get("contains")
    logs_dir = os.path.join(project_dir(), "Saved", "Logs")
    logpath = os.path.join(logs_dir, ctx.settings.project_name + ".log")
    if not os.path.exists(logpath):
        candidates = glob.glob(os.path.join(logs_dir, "*.log"))
        if not candidates:
            return ctx.err("no log file found in %s" % logs_dir)
        logpath = max(candidates, key=os.path.getmtime)
    with open(logpath, "r", errors="replace") as handle:
        lines = handle.read().splitlines()
    if contains:
        needle = str(contains).lower()
        lines = [line for line in lines if needle in line.lower()]
    tail = lines[-max_lines:] if max_lines > 0 else lines
    return ctx.ok({"path": logpath, "matched": len(lines), "lines": tail})


def _health_status(args, ctx):
    try:
        engine_version = unreal.SystemLibrary.get_engine_version()
    except Exception:  # noqa: BLE001
        engine_version = None
    state = {}
    try:
        world = editor_world()
        state["current_level"] = world.get_name() if world else None
    except Exception:  # noqa: BLE001
        state["current_level"] = None
    try:
        state["is_in_play"] = bool(level_subsystem().is_in_play_in_editor())
    except Exception:  # noqa: BLE001
        state["is_in_play"] = None
    capabilities = {
        "transactions": hasattr(unreal, "ScopedEditorTransaction"),
        "niagara": hasattr(unreal, "NiagaraActor"),
        "umg": hasattr(unreal, "WidgetBlueprintFactory"),
        "layers": hasattr(unreal, "LayersSubsystem"),
        "data_tables": hasattr(unreal, "DataTableFactory"),
    }
    return ctx.ok(
        {
            "ok": True,
            "plugin_version": constants.SERVER_VERSION,
            "engine_version": engine_version,
            "project_name": ctx.settings.project_name,
            "project_dir": project_dir(),
            "tool_profile": ctx.settings.tool_profile,
            "tools": ctx.registry.exposure_summary(),
            "editor": state,
            "capabilities": capabilities,
        }
    )


def _undo(args, ctx):
    unreal.SystemLibrary.execute_console_command(editor_world(), "TRANSACTION UNDO")
    return ctx.text("Undo requested.")


def _redo(args, ctx):
    unreal.SystemLibrary.execute_console_command(editor_world(), "TRANSACTION REDO")
    return ctx.text("Redo requested.")


def _sync_content_browser(args, ctx):
    asset_paths = args.get("asset_paths")
    if not asset_paths:
        return ctx.err("'asset_paths' is required")
    asset_subsystem().sync_browser_to_objects(list(asset_paths))
    return ctx.text("Synced %d asset(s) in the Content Browser." % len(asset_paths))


def register(reg):
    reg.register(
        "get_editor_state",
        "Inspect the editor: current level, PIE state, and selected/total actor counts.",
        schema({}),
        _get_editor_state,
        profiles=("core", "full"),
        group="editor_state",
    )
    reg.register(
        "get_project_info",
        "Return project name, directory, identity, and the engine version.",
        schema({}),
        _get_project_info,
        profiles=("core", "full"),
        group="editor_state",
    )
    reg.register(
        "get_output_log",
        "Read the tail of the editor output log (newest *.log if the named one is "
        "missing), optionally filtered by a substring.",
        schema(
            {
                "max_lines": prop(
                    "integer", "Number of trailing lines to return (default 200)."
                ),
                "contains": prop(
                    "string", "Only return lines containing this substring (case-insensitive)."
                ),
            }
        ),
        _get_output_log,
        profiles=("core", "full"),
        group="diagnostics",
    )
    reg.register(
        "health_status",
        "One-shot readiness summary: plugin/engine version, project, current level, "
        "PIE state, tool profile/counts, and optional-plugin capability probes. Call "
        "this first to learn what is available.",
        schema({}),
        _health_status,
        profiles=("core", "full"),
        group="editor_state",
    )
    reg.register(
        "undo",
        "Undo the last editor transaction.",
        schema({}),
        _undo,
        profiles=("full",),
        group="editor_state",
    )
    reg.register(
        "redo",
        "Redo the last undone editor transaction.",
        schema({}),
        _redo,
        profiles=("full",),
        group="editor_state",
    )
    reg.register(
        "sync_content_browser",
        "Select (sync) one or more assets in the Content Browser by content path.",
        schema(
            {
                "asset_paths": {
                    "type": "array",
                    "description": "Content paths to sync, e.g. /Game/Meshes/SM_Cube.",
                    "items": {"type": "string"},
                }
            },
            required=["asset_paths"],
        ),
        _sync_content_browser,
        profiles=("full",),
        group="editor_state",
    )
