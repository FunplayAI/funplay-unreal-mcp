"""Niagara effects tools: spawn a NiagaraSystem actor and set its parameters.

Niagara ships as an optional plugin, so every handler probes ``unreal`` for the
relevant types before doing anything and bails cleanly if it's disabled."""

import unreal

from .common import (
    ROT3,
    VEC3,
    actor_subsystem,
    actor_summary,
    parse_rotator,
    parse_vector,
    prop,
    resolve_actor,
    schema,
    transaction,
)


def _niagara_available():
    """True only when the Niagara plugin's core types are exposed."""
    return hasattr(unreal, "NiagaraActor") and hasattr(unreal, "NiagaraSystem")


def _niagara_component(actor):
    """Best-effort fetch of the actor's NiagaraComponent."""
    try:
        comp = actor.get_editor_property("niagara_component")
        if comp is not None:
            return comp
    except Exception:  # noqa: BLE001
        pass
    return getattr(actor, "niagara_component", None)


def _spawn_niagara_system(args, ctx):
    if not _niagara_available():
        return ctx.err("Niagara not available; enable the Niagara plugin and restart")
    system_path = args.get("system_path")
    if not system_path:
        return ctx.err("'system_path' is required")
    system = unreal.EditorAssetLibrary.load_asset(system_path)
    if system is None:
        return ctx.err("NiagaraSystem not found: %s" % system_path)
    location = parse_vector(args.get("location"))
    rotation = parse_rotator(args.get("rotation"))
    with transaction("Funplay: Spawn Niagara System"):
        actor = actor_subsystem().spawn_actor_from_class(
            unreal.NiagaraActor, location, rotation
        )
        if actor is None:
            return ctx.err("failed to spawn NiagaraActor")
        comp = _niagara_component(actor)
        if comp is None:
            return ctx.err("spawned NiagaraActor has no niagara_component")
        # set_asset is the modern API; older versions use the editor property.
        try:
            if hasattr(comp, "set_asset"):
                comp.set_asset(system)
            else:
                comp.set_editor_property("asset", system)
        except Exception as exc:  # noqa: BLE001
            return ctx.err("could not assign NiagaraSystem: %s" % exc)
        if args.get("label"):
            actor.set_actor_label(args["label"])
    return ctx.ok(actor_summary(actor))


def _set_niagara_parameter(args, ctx):
    if not _niagara_available():
        return ctx.err("Niagara not available; enable the Niagara plugin and restart")
    try:
        actor = resolve_actor(args.get("actor"))
    except ValueError as exc:
        return ctx.err(str(exc))
    name = args.get("name")
    if not name:
        return ctx.err("'name' (parameter name) is required")
    if "value" not in args:
        return ctx.err("'value' is required")
    ptype = (args.get("type") or "").lower()
    if ptype not in ("float", "vector", "color", "bool"):
        return ctx.err("'type' must be one of: float, vector, color, bool")
    comp = _niagara_component(actor)
    if comp is None:
        return ctx.err("actor has no niagara_component: %s" % actor.get_actor_label())
    value = args["value"]
    var = unreal.Name(name)
    try:
        if ptype == "float":
            fval = float(value)
            if hasattr(comp, "set_variable_float"):
                comp.set_variable_float(var, fval)
            elif hasattr(comp, "set_float_parameter"):
                comp.set_float_parameter(var, fval)
            else:
                return ctx.err("no float parameter setter on NiagaraComponent")
        elif ptype == "vector":
            comp.set_variable_vec3(var, parse_vector(value))
        elif ptype == "color":
            if not isinstance(value, (list, tuple)) or len(value) < 3:
                return ctx.err("color value must be [r, g, b] or [r, g, b, a]")
            color = unreal.LinearColor(
                float(value[0]),
                float(value[1]),
                float(value[2]),
                float(value[3]) if len(value) > 3 else 1.0,
            )
            comp.set_variable_linear_color(var, color)
        else:  # bool
            comp.set_variable_bool(var, bool(value))
    except Exception as exc:  # noqa: BLE001
        return ctx.err("could not set parameter '%s': %s" % (name, exc))
    return ctx.text("Set %s parameter '%s' on %s" % (ptype, name, actor.get_actor_label()))


def register(reg):
    reg.register(
        "spawn_niagara_system",
        "Spawn a NiagaraActor that plays a NiagaraSystem asset at an optional "
        "location/rotation. Requires the Niagara plugin.",
        schema(
            {
                "system_path": prop("string", "Content path of a NiagaraSystem asset."),
                "location": VEC3,
                "rotation": ROT3,
                "label": prop("string", "Optional editor label for the new actor."),
            },
            required=["system_path"],
        ),
        _spawn_niagara_system,
        profiles=("full",),
        group="effects",
    )
    reg.register(
        "set_niagara_parameter",
        "Set a user parameter on a NiagaraActor's component "
        "(float / vector / color / bool). Requires the Niagara plugin.",
        schema(
            {
                "actor": prop("string", "NiagaraActor label, object name, or full path."),
                "name": prop("string", "Niagara user parameter name."),
                "type": prop("string", "Value type: 'float', 'vector', 'color', or 'bool'."),
                "value": {"description": "The parameter value (type depends on 'type')."},
            },
            required=["actor", "name", "type", "value"],
        ),
        _set_niagara_parameter,
        profiles=("full",),
        group="effects",
    )
