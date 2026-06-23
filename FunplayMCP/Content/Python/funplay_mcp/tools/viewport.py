"""Viewport tools: drive the level-editor camera.

Wraps ``UnrealEditorSubsystem.set_/get_level_viewport_camera_info`` so an
assistant can deterministically aim the perspective viewport before grabbing a
screenshot -- the "aim then screenshot" loop. ``focus_viewport`` frames one or
more actors (or a raw point) from a fixed orientation."""

import unreal

from ..context import json_safe
from .common import (
    ROT3,
    VEC3,
    parse_rotator,
    parse_vector,
    prop,
    resolve_actor,
    schema,
    unreal_editor_subsystem,
)


def _set_viewport_camera(args, ctx):
    if args.get("location") is None:
        return ctx.err("'location' is required")
    ues = unreal_editor_subsystem()
    if not hasattr(ues, "set_level_viewport_camera_info"):
        return ctx.err("editor viewport not available")
    try:
        location = parse_vector(args.get("location"))
        rotation = parse_rotator(args.get("rotation"))
    except ValueError as exc:
        return ctx.err(str(exc))
    try:
        ues.set_level_viewport_camera_info(location, rotation)
    except Exception as exc:  # noqa: BLE001
        return ctx.err(str(exc))
    return ctx.ok({"location": json_safe(location), "rotation": json_safe(rotation)})


def _get_viewport_camera(args, ctx):
    ues = unreal_editor_subsystem()
    if not hasattr(ues, "get_level_viewport_camera_info"):
        return ctx.err("editor viewport not available")
    try:
        info = ues.get_level_viewport_camera_info()
    except Exception as exc:  # noqa: BLE001
        return ctx.err(str(exc))
    # Method returns a (Vector, Rotator) tuple on some builds, a struct on others.
    try:
        loc, rot = info
    except (TypeError, ValueError):
        loc = getattr(info, "location", None)
        rot = getattr(info, "rotation", None)
    return ctx.ok({"location": json_safe(loc), "rotation": json_safe(rot)})


def _focus_center(args, ctx):
    """Return (center Vector, source label) or (None, error string)."""
    if args.get("actor") is not None or args.get("actors") is not None:
        refs = args.get("actors")
        if refs is None:
            refs = [args.get("actor")]
        elif not isinstance(refs, (list, tuple)):
            refs = [refs]
        actors = []
        for ref in refs:
            try:
                actors.append(resolve_actor(ref))
            except ValueError:
                continue
        if not actors:
            return None, "no matching actors found"
        sx = sy = sz = 0.0
        for actor in actors:
            loc = actor.get_actor_location()
            # Prefer the bounds origin when available; falls back to location.
            try:
                origin, _extent = actor.get_actor_bounds(False)
                loc = origin
            except Exception:  # noqa: BLE001
                pass
            sx += loc.x
            sy += loc.y
            sz += loc.z
        n = float(len(actors))
        return unreal.Vector(sx / n, sy / n, sz / n), None
    if args.get("location") is not None:
        try:
            return parse_vector(args.get("location")), None
        except ValueError as exc:
            return None, str(exc)
    return None, "provide one of: actor, actors, location"


def _focus_viewport(args, ctx):
    ues = unreal_editor_subsystem()
    if not hasattr(ues, "set_level_viewport_camera_info"):
        return ctx.err("editor viewport not available")
    center, problem = _focus_center(args, ctx)
    if center is None:
        return ctx.err(problem)
    try:
        distance = float(args.get("distance", 1000.0))
    except (TypeError, ValueError):
        return ctx.err("'distance' must be a number")
    try:
        rotation = parse_rotator(args.get("orientation"), (-30.0, -45.0, 0.0))
    except ValueError as exc:
        return ctx.err(str(exc))
    try:
        forward = unreal.MathLibrary.get_forward_vector(rotation)
        camera_location = unreal.Vector(
            center.x - forward.x * distance,
            center.y - forward.y * distance,
            center.z - forward.z * distance,
        )
        ues.set_level_viewport_camera_info(camera_location, rotation)
    except Exception as exc:  # noqa: BLE001
        return ctx.err(str(exc))
    return ctx.ok(
        {
            "center": json_safe(center),
            "camera_location": json_safe(camera_location),
            "rotation": json_safe(rotation),
        }
    )


def register(reg):
    reg.register(
        "set_viewport_camera",
        "Move the level-editor perspective camera to a location (and optional "
        "rotation). Pair with take_screenshot to aim, then capture.",
        schema(
            {"location": VEC3, "rotation": ROT3},
            required=["location"],
        ),
        _set_viewport_camera,
        profiles=("core", "full"),
        group="viewport",
    )
    reg.register(
        "get_viewport_camera",
        "Read the level-editor perspective camera's current location and rotation.",
        schema({}),
        _get_viewport_camera,
        profiles=("core", "full"),
        group="viewport",
    )
    reg.register(
        "focus_viewport",
        "Aim the viewport camera at one actor, a set of actors (averaged), or a "
        "raw point -- offset back by 'distance' along a fixed orientation. The "
        "deterministic 'aim then screenshot' helper.",
        schema(
            {
                "actor": prop("string", "Single actor label, name, or path to frame."),
                "actors": {
                    "type": "array",
                    "description": "List of actor refs to frame (averaged center).",
                    "items": {"type": "string"},
                },
                "location": VEC3,
                "distance": prop("number", "Camera pull-back distance (default 1000)."),
                "orientation": ROT3,
            }
        ),
        _focus_viewport,
        profiles=("core", "full"),
        group="viewport",
    )
