"""Component tools: add / list / inspect / set properties / mesh / material."""

import unreal

from .common import (
    ROT3,
    VEC3,
    actor_summary,
    component_summary,
    parse_rotator,
    parse_vector,
    prop,
    resolve_actor,
    resolve_class,
    schema,
    transaction,
)


def _find_component(actor, name):
    for comp in actor.get_components_by_class(unreal.ActorComponent):
        if comp.get_name() == name:
            return comp
    return None


def _add_component(args, ctx):
    try:
        actor = resolve_actor(args.get("actor"))
        cls = resolve_class(args.get("component_class"))
    except ValueError as exc:
        return ctx.err(str(exc))
    comp = actor.add_component_by_class(cls, False, unreal.Transform(), False)
    if comp is None:
        return ctx.err("failed to add component of class %s" % args.get("component_class"))
    if args.get("name"):
        try:
            comp.rename(args["name"])
        except Exception:  # noqa: BLE001
            pass
    return ctx.ok(component_summary(comp))


def _list_components(args, ctx):
    try:
        actor = resolve_actor(args.get("actor"))
    except ValueError as exc:
        return ctx.err(str(exc))
    comps = list(actor.get_components_by_class(unreal.ActorComponent))
    return ctx.ok(
        {
            "actor": actor.get_actor_label(),
            "count": len(comps),
            "components": [component_summary(c) for c in comps],
        }
    )


def _get_component_properties(args, ctx):
    try:
        actor = resolve_actor(args.get("actor"))
    except ValueError as exc:
        return ctx.err(str(exc))
    name = args.get("component")
    if not name:
        return ctx.err("'component' (component name) is required")
    comp = _find_component(actor, name)
    if comp is None:
        return ctx.err("component not found on actor: %s" % name)
    info = component_summary(comp)
    properties = args.get("properties")
    if properties:
        values = {}
        for prop_name in properties:
            try:
                values[prop_name] = comp.get_editor_property(prop_name)
            except Exception as exc:  # noqa: BLE001
                values[prop_name] = "Error: %s" % exc
        info["properties"] = values
    return ctx.ok(info)


def _set_component_property(args, ctx):
    try:
        actor = resolve_actor(args.get("actor"))
    except ValueError as exc:
        return ctx.err(str(exc))
    comp_name = args.get("component")
    if not comp_name:
        return ctx.err("'component' (component name) is required")
    name = args.get("name")
    if not name:
        return ctx.err("'name' (property name) is required")
    if "value" not in args:
        return ctx.err("'value' is required")
    comp = _find_component(actor, comp_name)
    if comp is None:
        return ctx.err("component not found on actor: %s" % comp_name)
    try:
        comp.set_editor_property(name, args["value"])
    except Exception as exc:  # noqa: BLE001
        return ctx.err("could not set property '%s': %s" % (name, exc))
    return ctx.ok(component_summary(comp))


def _set_static_mesh(args, ctx):
    try:
        actor = resolve_actor(args.get("actor"))
    except ValueError as exc:
        return ctx.err(str(exc))
    mesh_path = args.get("mesh_path")
    if not mesh_path:
        return ctx.err("'mesh_path' is required")
    mesh = unreal.EditorAssetLibrary.load_asset(mesh_path)
    if mesh is None:
        return ctx.err("mesh asset not found: %s" % mesh_path)
    comp_name = args.get("component")
    if comp_name:
        comp = _find_component(actor, comp_name)
        if comp is None:
            return ctx.err("component not found on actor: %s" % comp_name)
    else:
        comp = actor.get_component_by_class(unreal.StaticMeshComponent)
        if comp is None:
            return ctx.err("actor has no StaticMeshComponent")
    comp.set_static_mesh(mesh)
    return ctx.ok(actor_summary(actor))


def _set_material(args, ctx):
    try:
        actor = resolve_actor(args.get("actor"))
    except ValueError as exc:
        return ctx.err(str(exc))
    material_path = args.get("material_path")
    if not material_path:
        return ctx.err("'material_path' is required")
    mat = unreal.EditorAssetLibrary.load_asset(material_path)
    if mat is None:
        return ctx.err("material asset not found: %s" % material_path)
    comp_name = args.get("component")
    if comp_name:
        comp = _find_component(actor, comp_name)
        if comp is None:
            return ctx.err("component not found on actor: %s" % comp_name)
    else:
        comp = None
        for candidate in actor.get_components_by_class(unreal.ActorComponent):
            if hasattr(candidate, "set_material"):
                comp = candidate
                break
        if comp is None:
            comp = actor.get_component_by_class(unreal.StaticMeshComponent)
        if comp is None:
            return ctx.err("actor has no component that accepts a material")
    if not hasattr(comp, "set_material"):
        return ctx.err("component does not support set_material")
    index = int(args.get("index", 0))
    comp.set_material(index, mat)
    return ctx.ok(actor_summary(actor))


def _set_physics_properties(args, ctx):
    try:
        actor = resolve_actor(args.get("actor"))
    except ValueError as exc:
        return ctx.err(str(exc))
    comp_name = args.get("component")
    if comp_name:
        comp = _find_component(actor, comp_name)
    else:
        comp = actor.get_component_by_class(unreal.PrimitiveComponent)
    if comp is None:
        return ctx.err("no PrimitiveComponent found on actor")
    try:
        if args.get("simulate_physics") is not None:
            comp.set_simulate_physics(bool(args["simulate_physics"]))
        if args.get("enable_gravity") is not None:
            comp.set_enable_gravity(bool(args["enable_gravity"]))
        if args.get("mass") is not None:
            comp.set_mass_override_in_kg(unreal.Name("None"), float(args["mass"]), True)
        if args.get("linear_damping") is not None:
            comp.set_linear_damping(float(args["linear_damping"]))
        if args.get("angular_damping") is not None:
            comp.set_angular_damping(float(args["angular_damping"]))
    except Exception as exc:  # noqa: BLE001
        return ctx.err("could not set physics property: %s" % exc)
    return ctx.ok(actor_summary(actor))


def _add_ism_instances(args, ctx):
    try:
        actor = resolve_actor(args.get("actor"))
    except ValueError as exc:
        return ctx.err(str(exc))
    transforms = args.get("transforms")
    if not isinstance(transforms, list) or not transforms:
        return ctx.err("'transforms' must be a non-empty list of {location,rotation,scale}")
    comp = actor.get_component_by_class(unreal.InstancedStaticMeshComponent)
    if comp is None:
        return ctx.err(
            "actor has no InstancedStaticMeshComponent; add one first via add_component"
        )
    added = 0
    try:
        with transaction("Funplay: add ISM instances"):
            for item in transforms:
                xform = unreal.Transform(
                    parse_vector(item.get("location")),
                    parse_rotator(item.get("rotation")),
                    parse_vector(item.get("scale"), (1.0, 1.0, 1.0)),
                )
                comp.add_instance(xform)
                added += 1
    except Exception as exc:  # noqa: BLE001
        return ctx.err("failed adding instances after %d: %s" % (added, exc))
    return ctx.ok({"added": added, "instance_count": comp.get_instance_count()})


def register(reg):
    _actor_ref = prop("string", "Actor label, object name, or full path.")
    reg.register(
        "add_component",
        "Add a component (by native class name or class path) to a level actor.",
        schema(
            {
                "actor": _actor_ref,
                "component_class": prop(
                    "string", "Component class name or path, e.g. 'PointLightComponent'."
                ),
                "name": prop("string", "Optional name for the new component."),
            },
            required=["actor", "component_class"],
        ),
        _add_component,
        profiles=("full",),
        group="components",
    )
    reg.register(
        "list_components",
        "List all components on a level actor.",
        schema({"actor": _actor_ref}, required=["actor"]),
        _list_components,
        profiles=("core", "full"),
        group="components",
    )
    reg.register(
        "get_component_properties",
        "Inspect a named component; optionally read specific editor properties.",
        schema(
            {
                "actor": _actor_ref,
                "component": prop("string", "Component name."),
                "properties": {
                    "type": "array",
                    "description": "Optional list of property names to read.",
                    "items": {"type": "string"},
                },
            },
            required=["actor", "component"],
        ),
        _get_component_properties,
        profiles=("core", "full"),
        group="components",
    )
    reg.register(
        "set_component_property",
        "Set an editor property on a named component of an actor.",
        schema(
            {
                "actor": _actor_ref,
                "component": prop("string", "Component name."),
                "name": prop("string", "Property name."),
                "value": {"description": "Property value (any JSON type)."},
            },
            required=["actor", "component", "name", "value"],
        ),
        _set_component_property,
        profiles=("full",),
        group="components",
    )
    reg.register(
        "set_static_mesh",
        "Set the mesh on an actor's StaticMeshComponent (first one, or a named component).",
        schema(
            {
                "actor": _actor_ref,
                "mesh_path": prop("string", "Content path to a StaticMesh asset."),
                "component": prop("string", "Optional component name to target."),
            },
            required=["actor", "mesh_path"],
        ),
        _set_static_mesh,
        profiles=("full",),
        group="components",
    )
    reg.register(
        "set_material",
        "Assign a material to a material slot on an actor's component.",
        schema(
            {
                "actor": _actor_ref,
                "material_path": prop("string", "Content path to a Material asset."),
                "index": prop("integer", "Material slot index (default 0)."),
                "component": prop("string", "Optional component name to target."),
            },
            required=["actor", "material_path"],
        ),
        _set_material,
        profiles=("full",),
        group="components",
    )
    reg.register(
        "set_physics_properties",
        "Configure physics on an actor's PrimitiveComponent: simulate_physics, "
        "enable_gravity, mass (kg), linear_damping, angular_damping.",
        schema(
            {
                "actor": _actor_ref,
                "simulate_physics": prop("boolean", "Enable rigid-body simulation."),
                "enable_gravity": prop("boolean", "Enable gravity."),
                "mass": prop("number", "Mass override in kilograms."),
                "linear_damping": prop("number", "Linear damping."),
                "angular_damping": prop("number", "Angular damping."),
                "component": prop("string", "Optional component name to target."),
            },
            required=["actor"],
        ),
        _set_physics_properties,
        profiles=("full",),
        group="components",
    )
    reg.register(
        "add_ism_instances",
        "Add instances to an actor's InstancedStaticMeshComponent (great for "
        "crowds/foliage/scatter). One undoable transaction.",
        schema(
            {
                "actor": _actor_ref,
                "transforms": {
                    "type": "array",
                    "description": "List of {location, rotation, scale} per instance.",
                    "items": {"type": "object"},
                },
            },
            required=["actor", "transforms"],
        ),
        _add_ism_instances,
        profiles=("full",),
        group="components",
    )
