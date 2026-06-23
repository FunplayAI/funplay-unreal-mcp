"""Organization tools: actor folders and editor layers.

LayersSubsystem method names vary across UE 5.3-5.8, so every layer call is
probed with hasattr/getattr and degrades to a clear error instead of crashing."""

import unreal

from .common import (
    actor_summary,
    prop,
    resolve_actor,
    schema,
    transaction,
)


def _layers_subsystem():
    """Return the LayersSubsystem or None if unavailable on this version."""
    cls = getattr(unreal, "LayersSubsystem", None)
    if cls is None:
        return None
    try:
        return unreal.get_editor_subsystem(cls)
    except Exception:  # noqa: BLE001
        return None


def _set_actor_folder(args, ctx):
    try:
        actor = resolve_actor(args.get("actor"))
    except ValueError as exc:
        return ctx.err(str(exc))
    folder = args.get("folder")
    if not folder:
        return ctx.err("'folder' (e.g. 'Lights/Key') is required")
    try:
        with transaction("Funplay: Set Actor Folder"):
            actor.set_folder_path(unreal.Name(folder))
    except Exception as exc:  # noqa: BLE001
        return ctx.err("could not set folder '%s': %s" % (folder, exc))
    return ctx.ok(actor_summary(actor))


def _create_layer(args, ctx):
    name = args.get("name")
    if not name:
        return ctx.err("'name' (layer name) is required")
    layers = _layers_subsystem()
    if layers is None:
        return ctx.err("LayersSubsystem not available; enable the Layers feature and restart")
    fn = getattr(layers, "create_layer", None)
    if fn is None:
        return ctx.err("create_layer not supported on this engine version")
    try:
        fn(unreal.Name(name))
    except Exception as exc:  # noqa: BLE001
        return ctx.err(str(exc))
    return ctx.text("Created layer: %s" % name)


def _add_actors_to_layer(args, ctx):
    refs = args.get("actors")
    if not refs or not isinstance(refs, list):
        return ctx.err("'actors' (a list of actor refs) is required")
    layer = args.get("layer")
    if not layer:
        return ctx.err("'layer' (layer name) is required")
    resolved = []
    for ref in refs:
        try:
            resolved.append(resolve_actor(ref))
        except ValueError:
            continue
    if not resolved:
        return ctx.err("no actors resolved from: %r" % (refs,))
    layers = _layers_subsystem()
    if layers is None:
        return ctx.err("LayersSubsystem not available; enable the Layers feature and restart")
    layer_name = unreal.Name(layer)
    try:
        with transaction("Funplay: Add Actors To Layer"):
            batch = getattr(layers, "add_actors_to_layer", None)
            if batch is not None:
                batch(resolved, layer_name)
            else:
                single = getattr(layers, "add_actor_to_layer", None)
                if single is None:
                    return ctx.err("adding actors to layers not supported on this engine version")
                for actor in resolved:
                    single(actor, layer_name)
    except Exception as exc:  # noqa: BLE001
        return ctx.err(str(exc))
    return ctx.ok(
        {"added": [a.get_actor_label() for a in resolved], "layer": layer}
    )


def _list_layers(args, ctx):
    layers = _layers_subsystem()
    if layers is None:
        return ctx.err("LayersSubsystem not available; enable the Layers feature and restart")
    names = None
    try:
        if hasattr(layers, "add_all_layer_names_to"):
            out = unreal.Array(unreal.Name)
            layers.add_all_layer_names_to(out)
            names = [str(n) for n in out]
        elif hasattr(layers, "get_all_layers"):
            names = [
                str(l.get_editor_property("layer_name"))
                for l in layers.get_all_layers()
            ]
        else:
            return ctx.err("listing layers not supported on this engine version")
    except Exception as exc:  # noqa: BLE001
        return ctx.err(str(exc))
    return ctx.ok({"count": len(names), "layers": names})


def register(reg):
    _actor_ref = prop("string", "Actor label, object name, or full path.")
    reg.register(
        "set_actor_folder",
        "Move an actor into an outliner folder path (e.g. 'Lights/Key'). "
        "Creates the folder hierarchy if needed.",
        schema(
            {
                "actor": _actor_ref,
                "folder": prop("string", "Folder path, e.g. 'Lights/Key'."),
            },
            required=["actor", "folder"],
        ),
        _set_actor_folder,
        profiles=("full",),
        group="organization",
    )
    reg.register(
        "create_layer",
        "Create a new (empty) editor layer.",
        schema({"name": prop("string", "Layer name.")}, required=["name"]),
        _create_layer,
        profiles=("full",),
        group="organization",
    )
    reg.register(
        "add_actors_to_layer",
        "Add one or more level actors to an editor layer (created if missing).",
        schema(
            {
                "actors": {
                    "type": "array",
                    "description": "Actor refs (label/name/path) to add.",
                    "items": {"type": "string"},
                },
                "layer": prop("string", "Target layer name."),
            },
            required=["actors", "layer"],
        ),
        _add_actors_to_layer,
        profiles=("full",),
        group="organization",
    )
    reg.register(
        "list_layers",
        "List all editor layer names in the current world.",
        schema({}),
        _list_layers,
        profiles=("full",),
        group="organization",
    )
