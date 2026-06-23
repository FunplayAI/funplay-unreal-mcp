"""Actor tools: spawn / destroy / duplicate / transform / inspect / find."""

import unreal

from .common import (
    ROT3,
    VEC3,
    actor_subsystem,
    actor_summary,
    all_level_actors,
    component_summary,
    editor_world,
    parse_rotator,
    parse_vector,
    prop,
    resolve_actor,
    resolve_class,
    schema,
)


def _spawn_actor(args, ctx):
    class_name = args.get("class_name") or args.get("class")
    try:
        cls = resolve_class(class_name)
    except ValueError as exc:
        return ctx.err(str(exc))
    location = parse_vector(args.get("location"))
    rotation = parse_rotator(args.get("rotation"))
    actor = actor_subsystem().spawn_actor_from_class(cls, location, rotation)
    if actor is None:
        return ctx.err("failed to spawn actor of class %s" % class_name)
    if args.get("label"):
        actor.set_actor_label(args["label"])
    if args.get("scale") is not None:
        actor.set_actor_scale3d(parse_vector(args.get("scale"), (1.0, 1.0, 1.0)))
    return ctx.ok(actor_summary(actor))


def _spawn_actor_from_asset(args, ctx):
    asset_path = args.get("asset_path")
    if not asset_path:
        return ctx.err("'asset_path' is required")
    asset = unreal.EditorAssetLibrary.load_asset(asset_path)
    if asset is None:
        return ctx.err("asset not found: %s" % asset_path)
    location = parse_vector(args.get("location"))
    rotation = parse_rotator(args.get("rotation"))
    if isinstance(asset, unreal.Blueprint):
        actor = actor_subsystem().spawn_actor_from_class(
            asset.generated_class(), location, rotation
        )
    else:
        actor = actor_subsystem().spawn_actor_from_object(asset, location, rotation)
    if actor is None:
        return ctx.err("failed to spawn actor from asset %s" % asset_path)
    if args.get("label"):
        actor.set_actor_label(args["label"])
    if args.get("scale") is not None:
        actor.set_actor_scale3d(parse_vector(args.get("scale"), (1.0, 1.0, 1.0)))
    return ctx.ok(actor_summary(actor))


def _destroy_actor(args, ctx):
    try:
        actor = resolve_actor(args.get("actor"))
    except ValueError as exc:
        return ctx.err(str(exc))
    label = actor.get_actor_label()
    actor_subsystem().destroy_actor(actor)
    return ctx.text("Destroyed actor: %s" % label)


def _duplicate_actor(args, ctx):
    try:
        actor = resolve_actor(args.get("actor"))
    except ValueError as exc:
        return ctx.err(str(exc))
    offset = parse_vector(args.get("offset"), (0.0, 0.0, 0.0))
    duplicate = actor_subsystem().duplicate_actor(actor, editor_world(), offset)
    if duplicate is None:
        return ctx.err("failed to duplicate actor")
    if args.get("label"):
        duplicate.set_actor_label(args["label"])
    return ctx.ok(actor_summary(duplicate))


def _set_actor_transform(args, ctx):
    try:
        actor = resolve_actor(args.get("actor"))
    except ValueError as exc:
        return ctx.err(str(exc))
    if args.get("location") is not None:
        actor.set_actor_location(parse_vector(args.get("location")), False, False)
    if args.get("rotation") is not None:
        actor.set_actor_rotation(parse_rotator(args.get("rotation")), False)
    if args.get("scale") is not None:
        actor.set_actor_scale3d(parse_vector(args.get("scale"), (1.0, 1.0, 1.0)))
    return ctx.ok(actor_summary(actor))


def _set_actor_label(args, ctx):
    try:
        actor = resolve_actor(args.get("actor"))
    except ValueError as exc:
        return ctx.err(str(exc))
    new_label = args.get("label")
    if not new_label:
        return ctx.err("'label' is required")
    actor.set_actor_label(new_label)
    return ctx.ok(actor_summary(actor))


def _set_actor_property(args, ctx):
    try:
        actor = resolve_actor(args.get("actor"))
    except ValueError as exc:
        return ctx.err(str(exc))
    name = args.get("name")
    if not name:
        return ctx.err("'name' (property name) is required")
    if "value" not in args:
        return ctx.err("'value' is required")
    target = actor
    component_name = args.get("component")
    if component_name:
        target = None
        for comp in actor.get_components_by_class(unreal.ActorComponent):
            if comp.get_name() == component_name:
                target = comp
                break
        if target is None:
            return ctx.err("component not found on actor: %s" % component_name)
    try:
        target.set_editor_property(name, args["value"])
    except Exception as exc:  # noqa: BLE001
        return ctx.err("could not set property '%s': %s" % (name, exc))
    return ctx.ok(actor_summary(actor))


def _attach_actor(args, ctx):
    try:
        child = resolve_actor(args.get("child"))
        parent = resolve_actor(args.get("parent"))
    except ValueError as exc:
        return ctx.err(str(exc))
    rule = unreal.AttachmentRule.KEEP_WORLD
    child.attach_to_actor(
        parent, args.get("socket", ""), rule, rule, rule, False
    )
    return ctx.text(
        "Attached %s to %s" % (child.get_actor_label(), parent.get_actor_label())
    )


def _get_actor_info(args, ctx):
    try:
        actor = resolve_actor(args.get("actor"))
    except ValueError as exc:
        return ctx.err(str(exc))
    info = actor_summary(actor)
    info["components"] = [
        component_summary(c)
        for c in actor.get_components_by_class(unreal.ActorComponent)
    ]
    return ctx.ok(info)


def _list_actors(args, ctx):
    class_filter = (args.get("class_name") or "").lower()
    out = []
    for actor in all_level_actors():
        class_name = actor.get_class().get_name()
        if class_filter and class_filter not in class_name.lower():
            continue
        out.append(
            {
                "label": actor.get_actor_label(),
                "class": class_name,
                "path": actor.get_path_name(),
            }
        )
    return ctx.ok({"count": len(out), "actors": out})


def _find_actors(args, ctx):
    query = (args.get("query") or "").lower()
    if not query:
        return ctx.err("'query' is required")
    out = []
    for actor in all_level_actors():
        haystack = "%s %s %s" % (
            actor.get_actor_label(),
            actor.get_name(),
            actor.get_class().get_name(),
        )
        if query in haystack.lower():
            out.append(actor_summary(actor))
    return ctx.ok({"count": len(out), "actors": out})


def register(reg):
    _actor_ref = prop("string", "Actor label, object name, or full path.")
    reg.register(
        "spawn_actor",
        "Spawn an actor from a class (native name like 'PointLight'/'CameraActor' "
        "or an asset/class path) at an optional location/rotation/scale.",
        schema(
            {
                "class_name": prop("string", "Class name or path to spawn."),
                "location": VEC3,
                "rotation": ROT3,
                "scale": VEC3,
                "label": prop("string", "Optional editor label for the new actor."),
            },
            required=["class_name"],
        ),
        _spawn_actor,
        profiles=("full",),
        group="actors",
    )
    reg.register(
        "spawn_actor_from_asset",
        "Spawn an actor from an asset (StaticMesh -> StaticMeshActor, Blueprint -> "
        "its actor) by content path.",
        schema(
            {
                "asset_path": prop("string", "Content path, e.g. /Game/Meshes/SM_Cube."),
                "location": VEC3,
                "rotation": ROT3,
                "scale": VEC3,
                "label": prop("string", "Optional editor label."),
            },
            required=["asset_path"],
        ),
        _spawn_actor_from_asset,
        profiles=("full",),
        group="actors",
    )
    reg.register(
        "destroy_actor",
        "Destroy (delete) a level actor.",
        schema({"actor": _actor_ref}, required=["actor"]),
        _destroy_actor,
        profiles=("full",),
        group="actors",
    )
    reg.register(
        "duplicate_actor",
        "Duplicate a level actor with an optional world-space offset.",
        schema(
            {"actor": _actor_ref, "offset": VEC3, "label": prop("string", "Label.")},
            required=["actor"],
        ),
        _duplicate_actor,
        profiles=("full",),
        group="actors",
    )
    reg.register(
        "set_actor_transform",
        "Set an actor's location, rotation, and/or scale.",
        schema(
            {"actor": _actor_ref, "location": VEC3, "rotation": ROT3, "scale": VEC3},
            required=["actor"],
        ),
        _set_actor_transform,
        profiles=("full",),
        group="actors",
    )
    reg.register(
        "set_actor_label",
        "Rename an actor's editor label.",
        schema({"actor": _actor_ref, "label": prop("string", "New label.")},
               required=["actor", "label"]),
        _set_actor_label,
        profiles=("full",),
        group="actors",
    )
    reg.register(
        "set_actor_property",
        "Set an editor property on an actor or one of its components.",
        schema(
            {
                "actor": _actor_ref,
                "name": prop("string", "Property name."),
                "value": {"description": "Property value (any JSON type)."},
                "component": prop("string", "Optional component name to target."),
            },
            required=["actor", "name", "value"],
        ),
        _set_actor_property,
        profiles=("full",),
        group="actors",
    )
    reg.register(
        "attach_actor",
        "Attach one actor to another (keeps world transform).",
        schema(
            {
                "child": prop("string", "Child actor ref."),
                "parent": prop("string", "Parent actor ref."),
                "socket": prop("string", "Optional socket name."),
            },
            required=["child", "parent"],
        ),
        _attach_actor,
        profiles=("full",),
        group="actors",
    )
    reg.register(
        "get_actor_info",
        "Inspect a level actor: transform, class, path, and its components.",
        schema({"actor": _actor_ref}, required=["actor"]),
        _get_actor_info,
        profiles=("core", "full"),
        group="actors",
    )
    reg.register(
        "list_actors",
        "List all actors in the current level (optionally filtered by class-name substring).",
        schema({"class_name": prop("string", "Class-name substring filter.")}),
        _list_actors,
        profiles=("core", "full"),
        group="actors",
    )
    reg.register(
        "find_actors",
        "Find actors whose label, name, or class contains the query substring.",
        schema({"query": prop("string", "Search substring.")}, required=["query"]),
        _find_actors,
        profiles=("core", "full"),
        group="actors",
    )
