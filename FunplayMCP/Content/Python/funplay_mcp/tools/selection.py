"""Selection tools: inspect / set / clear the editor's actor and asset selection."""

import unreal

from .common import (
    actor_subsystem,
    actor_summary,
    object_ref,
    prop,
    resolve_actor,
    schema,
)


def _get_selection(args, ctx):
    actors = actor_subsystem().get_selected_level_actors()
    return ctx.ok(
        {"count": len(actors), "actors": [actor_summary(a) for a in actors]}
    )


def _set_selection(args, ctx):
    refs = args.get("actors")
    if not isinstance(refs, list):
        return ctx.err("'actors' (a list of actor refs) is required")
    resolved = []
    for ref in refs:
        try:
            resolved.append(resolve_actor(ref))
        except ValueError as exc:
            return ctx.err(str(exc))
    actor_subsystem().set_selected_level_actors(resolved)
    return ctx.ok({"selected": [a.get_actor_label() for a in resolved]})


def _select_none(args, ctx):
    actor_subsystem().set_selected_level_actors([])
    return ctx.text("Selection cleared.")


def _get_selected_assets(args, ctx):
    assets = unreal.EditorUtilityLibrary.get_selected_assets()
    return ctx.ok(
        {"count": len(assets), "assets": [object_ref(a) for a in assets]}
    )


def register(reg):
    reg.register(
        "get_selection",
        "Get the actors currently selected in the level editor.",
        schema({}),
        _get_selection,
        profiles=("core", "full"),
        group="selection",
    )
    reg.register(
        "set_selection",
        "Replace the level-editor selection with the given actors.",
        schema(
            {
                "actors": {
                    "type": "array",
                    "description": "Actor refs (label, object name, or path) to select.",
                    "items": {"type": "string"},
                }
            },
            required=["actors"],
        ),
        _set_selection,
        profiles=("full",),
        group="selection",
    )
    reg.register(
        "select_none",
        "Clear the level-editor actor selection.",
        schema({}),
        _select_none,
        profiles=("full",),
        group="selection",
    )
    reg.register(
        "get_selected_assets",
        "Get the assets currently selected in the Content Browser.",
        schema({}),
        _get_selected_assets,
        profiles=("core", "full"),
        group="selection",
    )
