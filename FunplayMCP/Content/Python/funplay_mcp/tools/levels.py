"""Level tools: new / load / save / inspect / list."""

import unreal

from .common import (
    all_level_actors,
    asset_subsystem,
    editor_world,
    level_subsystem,
    normalize_content_path,
    prop,
    schema,
)


def _new_level(args, ctx):
    asset_path = args.get("asset_path")
    if not asset_path:
        return ctx.err("'asset_path' is required")
    ok = level_subsystem().new_level(asset_path)
    return ctx.text("Created level %s (ok=%s)" % (asset_path, ok))


def _load_level(args, ctx):
    asset_path = args.get("asset_path")
    if not asset_path:
        return ctx.err("'asset_path' is required")
    ok = level_subsystem().load_level(asset_path)
    return ctx.text("Loaded level %s (ok=%s)" % (asset_path, ok))


def _save_current_level(args, ctx):
    ok = level_subsystem().save_current_level()
    return ctx.text("Saved current level (ok=%s)" % ok)


def _save_all_dirty(args, ctx):
    ok = level_subsystem().save_all_dirty_levels()
    return ctx.text("Saved all dirty levels (ok=%s)" % ok)


def _get_level_info(args, ctx):
    world = editor_world()
    name = world.get_name() if world else None
    pie = level_subsystem().is_in_play_in_editor()
    count = len(all_level_actors())
    return ctx.ok({"world": name, "is_in_play": pie, "actor_count": count})


def _list_levels(args, ctx):
    path = args.get("path") or "/Game"
    try:
        root = normalize_content_path(path)
    except ValueError as exc:
        return ctx.err(str(exc))
    levels = []
    for p in asset_subsystem().list_assets(root, True, False):
        try:
            data = asset_subsystem().find_asset_data(p)
            if data.asset_class_path.asset_name == "World":
                levels.append(p)
        except Exception:  # noqa: BLE001
            continue
        if len(levels) >= 500:
            break
    return ctx.ok({"count": len(levels), "levels": levels})


def register(reg):
    reg.register(
        "new_level",
        "Create a new empty level at a content path (e.g. /Game/Maps/NewMap).",
        schema(
            {"asset_path": prop("string", "Content path for the new level.")},
            required=["asset_path"],
        ),
        _new_level,
        profiles=("full",),
        group="levels",
    )
    reg.register(
        "load_level",
        "Load (open) a level by content path.",
        schema(
            {"asset_path": prop("string", "Content path of the level to load.")},
            required=["asset_path"],
        ),
        _load_level,
        profiles=("full",),
        group="levels",
    )
    reg.register(
        "save_current_level",
        "Save the currently open level.",
        schema({}),
        _save_current_level,
        profiles=("full",),
        group="levels",
    )
    reg.register(
        "save_all_dirty",
        "Save all dirty (unsaved) levels.",
        schema({}),
        _save_all_dirty,
        profiles=("full",),
        group="levels",
    )
    reg.register(
        "get_level_info",
        "Inspect the current level: world name, play-in-editor state, and actor count.",
        schema({}),
        _get_level_info,
        profiles=("core", "full"),
        group="levels",
    )
    reg.register(
        "list_levels",
        "List level (World) assets under a content path (default /Game).",
        schema({"path": prop("string", "Content path to search (default /Game).")}),
        _list_levels,
        profiles=("core", "full"),
        group="levels",
    )
