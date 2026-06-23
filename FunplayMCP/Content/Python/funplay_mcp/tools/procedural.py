"""Procedural building tools: assemble StaticMeshActors from engine basic shapes.

Each tool spawns a batch of StaticMeshActors (walls, floors, stairs, scatters)
wrapped in a single undo transaction. The total number of blocks per call is
capped to keep the editor responsive."""

import random

import unreal

from .common import (
    VEC3,
    actor_subsystem,
    load_basic_shape,
    parse_vector,
    prop,
    schema,
    transaction,
)

# Hard cap on actors spawned per call (keeps the editor responsive).
MAX_BLOCKS = 2000


def _place_block(mesh, location, scale, folder):
    """Spawn one StaticMeshActor and return it (or None on failure)."""
    actor = actor_subsystem().spawn_actor_from_class(
        unreal.StaticMeshActor, location, unreal.Rotator()
    )
    if actor is None:
        return None
    actor.static_mesh_component.set_static_mesh(mesh)
    actor.set_actor_scale3d(scale)
    if folder:
        try:
            actor.set_folder_path(folder)
        except Exception:  # noqa: BLE001  -- folder paths are best-effort
            pass
    return actor


def _build_wall(args, ctx):
    try:
        length = int(args.get("length"))
    except (TypeError, ValueError):
        return ctx.err("'length' (int blocks) is required")
    if length <= 0:
        return ctx.err("'length' must be a positive integer")
    height = int(args.get("height", 1))
    if height <= 0:
        return ctx.err("'height' must be a positive integer")
    axis = (args.get("axis") or "x").lower()
    if axis not in ("x", "y"):
        return ctx.err("'axis' must be 'x' or 'y'")
    block_size = float(args.get("block_size", 100.0))
    folder = args.get("folder")
    try:
        mesh = load_basic_shape(args.get("mesh", "cube"))
        start = parse_vector(args.get("location"))
    except ValueError as exc:
        return ctx.err(str(exc))

    requested = length * height
    capped = min(requested, MAX_BLOCKS)
    labels = []
    with transaction("Funplay: build_wall"):
        for h in range(height):
            for i in range(length):
                if len(labels) >= capped:
                    break
                dx = block_size * i if axis == "x" else 0.0
                dy = block_size * i if axis == "y" else 0.0
                loc = unreal.Vector(start.x + dx, start.y + dy, start.z + block_size * h)
                actor = _place_block(mesh, loc, unreal.Vector(1.0, 1.0, 1.0), folder)
                if actor is not None:
                    labels.append(actor.get_actor_label())
            if len(labels) >= capped:
                break
    return ctx.ok(
        {"count": len(labels), "actors": labels, "truncated": requested > capped}
    )


def _build_floor(args, ctx):
    try:
        rows = int(args.get("rows"))
        cols = int(args.get("cols"))
    except (TypeError, ValueError):
        return ctx.err("'rows' and 'cols' (ints) are required")
    if rows <= 0 or cols <= 0:
        return ctx.err("'rows' and 'cols' must be positive integers")
    block_size = float(args.get("block_size", 100.0))
    folder = args.get("folder")
    try:
        mesh = load_basic_shape(args.get("mesh", "cube"))
        start = parse_vector(args.get("location"))
    except ValueError as exc:
        return ctx.err(str(exc))

    requested = rows * cols
    capped = min(requested, MAX_BLOCKS)
    labels = []
    with transaction("Funplay: build_floor"):
        for r in range(rows):
            for c in range(cols):
                if len(labels) >= capped:
                    break
                loc = unreal.Vector(
                    start.x + block_size * r, start.y + block_size * c, start.z
                )
                actor = _place_block(mesh, loc, unreal.Vector(1.0, 1.0, 1.0), folder)
                if actor is not None:
                    labels.append(actor.get_actor_label())
            if len(labels) >= capped:
                break
    return ctx.ok(
        {"count": len(labels), "actors": labels, "truncated": requested > capped}
    )


def _build_stairs(args, ctx):
    try:
        steps = int(args.get("steps"))
    except (TypeError, ValueError):
        return ctx.err("'steps' (int) is required")
    if steps <= 0:
        return ctx.err("'steps' must be a positive integer")
    run = float(args.get("run", 100.0))
    rise = float(args.get("rise", 50.0))
    width = float(args.get("width", 100.0))
    folder = args.get("folder")
    try:
        mesh = load_basic_shape(args.get("mesh", "cube"))
        start = parse_vector(args.get("location"))
    except ValueError as exc:
        return ctx.err(str(exc))

    capped = min(steps, MAX_BLOCKS)
    # Basic cube is 100uu; scale to the requested run/width/rise footprint.
    scale = unreal.Vector(run / 100.0, width / 100.0, rise / 100.0)
    labels = []
    with transaction("Funplay: build_stairs"):
        for i in range(capped):
            loc = unreal.Vector(
                start.x + run * i, start.y, start.z + rise * i
            )
            actor = _place_block(mesh, loc, scale, folder)
            if actor is not None:
                labels.append(actor.get_actor_label())
    return ctx.ok(
        {"count": len(labels), "actors": labels, "truncated": steps > capped}
    )


def _scatter_actors(args, ctx):
    try:
        count = int(args.get("count"))
    except (TypeError, ValueError):
        return ctx.err("'count' (int) is required")
    if count <= 0:
        return ctx.err("'count' must be a positive integer")
    radius = float(args.get("radius", 1000.0))
    seed = int(args.get("seed", 0))
    folder = args.get("folder")
    asset_path = args.get("asset_path")
    try:
        center = parse_vector(args.get("center"))
    except ValueError as exc:
        return ctx.err(str(exc))

    # Optional asset overrides the basic-shape mesh.
    asset = None
    mesh = None
    if asset_path:
        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        if asset is None:
            return ctx.err("asset not found: %s" % asset_path)
    else:
        try:
            mesh = load_basic_shape(args.get("mesh", "cube"))
        except ValueError as exc:
            return ctx.err(str(exc))

    rng = random.Random(seed)
    capped = min(count, MAX_BLOCKS)
    labels = []
    with transaction("Funplay: scatter_actors"):
        for _ in range(capped):
            dx = rng.uniform(-radius, radius)
            dy = rng.uniform(-radius, radius)
            loc = unreal.Vector(center.x + dx, center.y + dy, center.z)
            if asset is not None:
                actor = actor_subsystem().spawn_actor_from_object(
                    asset, loc, unreal.Rotator()
                )
                if actor is not None and folder:
                    try:
                        actor.set_folder_path(folder)
                    except Exception:  # noqa: BLE001
                        pass
            else:
                actor = _place_block(mesh, loc, unreal.Vector(1.0, 1.0, 1.0), folder)
            if actor is not None:
                labels.append(actor.get_actor_label())
    return ctx.ok(
        {"count": len(labels), "actors": labels, "truncated": count > capped}
    )


def register(reg):
    _mesh = prop("string", "Basic shape: cube/sphere/cylinder/cone/plane (default cube).")
    _folder = prop("string", "Optional World Outliner folder path for spawned actors.")
    reg.register(
        "build_wall",
        "Build a wall of StaticMeshActors: length*height blocks along an axis, "
        "stacked up Z by block_size. Capped at %d blocks total (result reports "
        "truncation)." % MAX_BLOCKS,
        schema(
            {
                "length": prop("integer", "Number of blocks along the axis."),
                "height": prop("integer", "Number of blocks stacked up Z (default 1)."),
                "location": VEC3,
                "block_size": prop("number", "Block edge size in uu (default 100.0)."),
                "mesh": _mesh,
                "axis": prop("string", "Run axis: 'x' or 'y' (default 'x')."),
                "folder": _folder,
            },
            required=["length"],
        ),
        _build_wall,
        profiles=("full",),
        group="procedural",
    )
    reg.register(
        "build_floor",
        "Build a rows x cols grid of StaticMeshActors on the XY plane. Capped at "
        "%d blocks total (result reports truncation)." % MAX_BLOCKS,
        schema(
            {
                "rows": prop("integer", "Number of blocks along X."),
                "cols": prop("integer", "Number of blocks along Y."),
                "location": VEC3,
                "block_size": prop("number", "Block edge size in uu (default 100.0)."),
                "mesh": _mesh,
                "folder": _folder,
            },
            required=["rows", "cols"],
        ),
        _build_floor,
        profiles=("full",),
        group="procedural",
    )
    reg.register(
        "build_stairs",
        "Build a staircase of StaticMeshActors: each step offset by (run, 0, rise). "
        "Steps are scaled to run/width/rise. Capped at %d steps (result reports "
        "truncation)." % MAX_BLOCKS,
        schema(
            {
                "steps": prop("integer", "Number of steps."),
                "location": VEC3,
                "run": prop("number", "Horizontal advance per step in uu (default 100.0)."),
                "rise": prop("number", "Vertical advance per step in uu (default 50.0)."),
                "width": prop("number", "Step width in uu (default 100.0)."),
                "mesh": _mesh,
                "folder": _folder,
            },
            required=["steps"],
        ),
        _build_stairs,
        profiles=("full",),
        group="procedural",
    )
    reg.register(
        "scatter_actors",
        "Scatter actors at random XY positions within radius of a center. Spawns "
        "from asset_path if given, else basic-shape blocks. Deterministic via seed. "
        "Capped at %d actors (result reports truncation)." % MAX_BLOCKS,
        schema(
            {
                "count": prop("integer", "Number of actors to scatter."),
                "center": VEC3,
                "radius": prop("number", "Max XY offset from center in uu (default 1000.0)."),
                "asset_path": prop("string", "Optional content path to spawn instead of a mesh block."),
                "mesh": _mesh,
                "seed": prop("integer", "RNG seed for reproducible layout (default 0)."),
                "folder": _folder,
            },
            required=["count"],
        ),
        _scatter_actors,
        profiles=("full",),
        group="procedural",
    )
