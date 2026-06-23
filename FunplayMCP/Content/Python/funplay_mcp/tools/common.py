"""Shared helpers for tool handlers.

All functions here are called from tool handlers, which run on the game thread,
so they may use ``unreal.*`` freely. JSON rendering lives in ``..context``."""

import os

import unreal

from ..context import json_safe, object_ref, to_json  # noqa: F401  (re-exported)


# -- JSON schema builders --------------------------------------------------
def schema(properties=None, required=None):
    out = {"type": "object", "properties": properties or {}}
    if required:
        out["required"] = list(required)
    return out


def prop(type_name, description, **extra):
    out = {"type": type_name, "description": description}
    out.update(extra)
    return out


# Convenience property snippets reused across modules.
VEC3 = {
    "type": "array",
    "description": "An [x, y, z] vector (also accepts {x, y, z}).",
    "items": {"type": "number"},
}
ROT3 = {
    "type": "array",
    "description": "A [pitch, yaw, roll] rotation in degrees (also accepts {pitch, yaw, roll}).",
    "items": {"type": "number"},
}


# -- editor subsystems -----------------------------------------------------
def actor_subsystem():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def asset_subsystem():
    return unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)


def level_subsystem():
    return unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def unreal_editor_subsystem():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)


def asset_tools():
    return unreal.AssetToolsHelpers.get_asset_tools()


def editor_world():
    try:
        world = unreal_editor_subsystem().get_editor_world()
        if world is not None:
            return world
    except Exception:  # noqa: BLE001
        pass
    return unreal.EditorLevelLibrary.get_editor_world()


# -- class / value resolution ---------------------------------------------
def resolve_class(name):
    """Resolve a class from a native name (``PointLight``) or asset path
    (``/Game/Blueprints/BP_Foo`` or ``/Script/Engine.StaticMeshActor``)."""
    if not name:
        raise ValueError("class name/path is required")
    if hasattr(unreal, name):
        return getattr(unreal, name)
    if name.startswith("/"):
        asset_path = name[:-2] if name.endswith("_C") else name
        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        if isinstance(asset, unreal.Blueprint):
            return asset.generated_class()
        loaded = unreal.load_object(None, name)
        if loaded is not None:
            return loaded
    raise ValueError("could not resolve class: %s" % name)


def parse_vector(value, default=(0.0, 0.0, 0.0)):
    if value is None:
        return unreal.Vector(*default)
    if isinstance(value, dict):
        return unreal.Vector(
            float(value.get("x", 0.0)),
            float(value.get("y", 0.0)),
            float(value.get("z", 0.0)),
        )
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        return unreal.Vector(float(value[0]), float(value[1]), float(value[2]))
    raise ValueError("expected an [x, y, z] vector, got: %r" % (value,))


def parse_rotator(value, default=(0.0, 0.0, 0.0)):
    """``default``/list order is (pitch, yaw, roll), degrees."""
    if value is None:
        p, y, r = default
        return unreal.Rotator(roll=r, pitch=p, yaw=y)
    if isinstance(value, dict):
        return unreal.Rotator(
            roll=float(value.get("roll", 0.0)),
            pitch=float(value.get("pitch", 0.0)),
            yaw=float(value.get("yaw", 0.0)),
        )
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        return unreal.Rotator(
            roll=float(value[2]), pitch=float(value[0]), yaw=float(value[1])
        )
    raise ValueError("expected a [pitch, yaw, roll] rotation, got: %r" % (value,))


# -- actors ----------------------------------------------------------------
def all_level_actors():
    return [a for a in actor_subsystem().get_all_level_actors() if a is not None]


def resolve_actor(ref):
    """Find a level actor by label, object name, or full path."""
    if not ref:
        raise ValueError("actor reference is required")
    for actor in all_level_actors():
        if (
            actor.get_actor_label() == ref
            or actor.get_name() == ref
            or actor.get_path_name() == ref
        ):
            return actor
    raise ValueError("actor not found: %s" % ref)


def actor_summary(actor):
    return {
        "label": actor.get_actor_label(),
        "name": actor.get_name(),
        "class": actor.get_class().get_name(),
        "path": actor.get_path_name(),
        "location": json_safe(actor.get_actor_location()),
        "rotation": json_safe(actor.get_actor_rotation()),
        "scale": json_safe(actor.get_actor_scale3d()),
    }


def component_summary(component):
    info = {
        "name": component.get_name(),
        "class": component.get_class().get_name(),
        "path": component.get_path_name(),
    }
    return info


# -- paths -----------------------------------------------------------------
def project_dir():
    return os.path.abspath(
        unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
    )


def safe_project_path(relative):
    """Resolve a path that must stay inside the project directory."""
    if not relative:
        raise ValueError("path is required")
    base = project_dir()
    candidate = os.path.abspath(os.path.join(base, relative))
    if candidate != base and not candidate.startswith(base + os.sep):
        raise ValueError("path escapes the project directory: %s" % relative)
    return candidate


def normalize_content_path(path):
    """Normalize a /Game-style content path."""
    if not path:
        raise ValueError("content path is required")
    path = path.replace("\\", "/")
    if not path.startswith("/"):
        path = "/Game/" + path
    return path.rstrip("/") or "/Game"
