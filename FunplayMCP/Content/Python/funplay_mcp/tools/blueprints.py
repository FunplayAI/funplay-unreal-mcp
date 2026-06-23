"""Blueprint tools: create / add component / compile / inspect / spawn."""

import unreal

from .common import (
    ROT3,
    VEC3,
    actor_subsystem,
    actor_summary,
    asset_tools,
    normalize_content_path,
    object_ref,
    parse_rotator,
    parse_vector,
    prop,
    resolve_class,
    schema,
)


def _create_blueprint(args, ctx):
    name = args.get("name")
    if not name:
        return ctx.err("'name' is required")
    path = args.get("path") or "/Game/Blueprints"
    parent_class = args.get("parent_class") or "Actor"
    try:
        parent = resolve_class(parent_class)
        package_path = normalize_content_path(path)
    except ValueError as exc:
        return ctx.err(str(exc))
    try:
        factory = unreal.BlueprintFactory()
        factory.set_editor_property("parent_class", parent)
        bp = asset_tools().create_asset(name, package_path, None, factory)
    except Exception as exc:  # noqa: BLE001
        return ctx.err("failed to create blueprint: %s" % exc)
    if bp is None:
        return ctx.err("failed to create blueprint: %s/%s" % (package_path, name))
    unreal.EditorAssetLibrary.save_loaded_asset(bp)
    return ctx.ok(object_ref(bp))


def _add_blueprint_component(args, ctx):
    blueprint_path = args.get("blueprint_path")
    if not blueprint_path:
        return ctx.err("'blueprint_path' is required")
    component_class = args.get("component_class")
    if not component_class:
        return ctx.err("'component_class' is required")
    bp = unreal.EditorAssetLibrary.load_asset(blueprint_path)
    if bp is None:
        return ctx.err("blueprint not found: %s" % blueprint_path)
    try:
        new_class = resolve_class(component_class)
    except ValueError as exc:
        return ctx.err(str(exc))
    name = args.get("name")
    try:
        sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        handles = sds.k2_gather_subobject_data_for_blueprint(bp)
        if not handles:
            return ctx.err("could not gather subobject data for blueprint")
        root = handles[0]
        params = unreal.AddNewSubobjectParams(
            parent_handle=root, new_class=new_class, blueprint_context=bp
        )
        sub_handle, fail_reason = sds.add_new_subobject(params)
        if fail_reason is not None and not fail_reason.is_empty():
            return ctx.err("failed to add component: %s" % fail_reason)
        if name:
            sds.rename_subobject(sub_handle, unreal.Text(name))
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        unreal.EditorAssetLibrary.save_loaded_asset(bp)
    except Exception as exc:  # noqa: BLE001
        return ctx.err("failed to add component: %s" % exc)
    return ctx.text(
        "Added %s component '%s' to %s"
        % (component_class, name or component_class, blueprint_path)
    )


def _compile_blueprint(args, ctx):
    blueprint_path = args.get("blueprint_path")
    if not blueprint_path:
        return ctx.err("'blueprint_path' is required")
    bp = unreal.EditorAssetLibrary.load_asset(blueprint_path)
    if bp is None:
        return ctx.err("blueprint not found: %s" % blueprint_path)
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    except Exception as exc:  # noqa: BLE001
        return ctx.err("failed to compile blueprint: %s" % exc)
    return ctx.text("Compiled blueprint: %s" % blueprint_path)


def _get_blueprint_info(args, ctx):
    blueprint_path = args.get("blueprint_path")
    if not blueprint_path:
        return ctx.err("'blueprint_path' is required")
    bp = unreal.EditorAssetLibrary.load_asset(blueprint_path)
    if bp is None:
        return ctx.err("blueprint not found: %s" % blueprint_path)
    parent = bp.get_editor_property("parent_class")
    try:
        parent_ref = object_ref(parent) if parent is not None else None
    except Exception:  # noqa: BLE001
        parent_ref = str(parent)
    info = {
        "path": bp.get_path_name(),
        "parent_class": parent_ref,
    }
    try:
        info["generated_class"] = str(bp.generated_class().get_name())
    except Exception:  # noqa: BLE001
        info["generated_class"] = None
    components = []
    try:
        sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        handles = sds.k2_gather_subobject_data_for_blueprint(bp)
        for handle in handles:
            try:
                data = sds.k2_find_subobject_data_from_handle(handle)
                obj = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(data)
                if obj is not None:
                    components.append(obj.get_name())
            except Exception:  # noqa: BLE001
                continue
    except Exception:  # noqa: BLE001
        pass
    info["components"] = components
    return ctx.ok(info)


def _spawn_blueprint(args, ctx):
    blueprint_path = args.get("blueprint_path")
    if not blueprint_path:
        return ctx.err("'blueprint_path' is required")
    bp = unreal.EditorAssetLibrary.load_asset(blueprint_path)
    if bp is None:
        return ctx.err("blueprint not found: %s" % blueprint_path)
    location = parse_vector(args.get("location"))
    rotation = parse_rotator(args.get("rotation"))
    try:
        actor = actor_subsystem().spawn_actor_from_class(
            bp.generated_class(), location, rotation
        )
    except Exception as exc:  # noqa: BLE001
        return ctx.err("failed to spawn blueprint: %s" % exc)
    if actor is None:
        return ctx.err("failed to spawn blueprint: %s" % blueprint_path)
    if args.get("label"):
        actor.set_actor_label(args["label"])
    return ctx.ok(actor_summary(actor))


def register(reg):
    reg.register(
        "create_blueprint",
        "Create a new Blueprint asset with a parent class (native name like "
        "'Actor'/'Pawn' or an asset/class path) in a content package directory.",
        schema(
            {
                "name": prop("string", "Asset name for the new Blueprint."),
                "path": prop(
                    "string", "Package directory (default '/Game/Blueprints')."
                ),
                "parent_class": prop(
                    "string", "Parent class name or path (default 'Actor')."
                ),
            },
            required=["name"],
        ),
        _create_blueprint,
        profiles=("full",),
        group="blueprints",
    )
    reg.register(
        "add_blueprint_component",
        "Add a component (class name like 'StaticMeshComponent' or a path) to a "
        "Blueprint, then compile and save it.",
        schema(
            {
                "blueprint_path": prop("string", "Content path to the Blueprint."),
                "component_class": prop("string", "Component class name or path."),
                "name": prop("string", "Optional name for the new component."),
            },
            required=["blueprint_path", "component_class"],
        ),
        _add_blueprint_component,
        profiles=("full",),
        group="blueprints",
    )
    reg.register(
        "compile_blueprint",
        "Compile a Blueprint asset.",
        schema(
            {"blueprint_path": prop("string", "Content path to the Blueprint.")},
            required=["blueprint_path"],
        ),
        _compile_blueprint,
        profiles=("full",),
        group="blueprints",
    )
    reg.register(
        "get_blueprint_info",
        "Inspect a Blueprint: parent class, generated class, and component names.",
        schema(
            {"blueprint_path": prop("string", "Content path to the Blueprint.")},
            required=["blueprint_path"],
        ),
        _get_blueprint_info,
        profiles=("core", "full"),
        group="blueprints",
    )
    reg.register(
        "spawn_blueprint",
        "Spawn an actor instance of a Blueprint into the level at an optional "
        "location/rotation.",
        schema(
            {
                "blueprint_path": prop("string", "Content path to the Blueprint."),
                "location": VEC3,
                "rotation": ROT3,
                "label": prop("string", "Optional editor label for the new actor."),
            },
            required=["blueprint_path"],
        ),
        _spawn_blueprint,
        profiles=("full",),
        group="blueprints",
    )
