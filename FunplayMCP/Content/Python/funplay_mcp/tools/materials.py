"""Material tools: create materials / instances, set parameters, inspect."""

import unreal

from .common import (
    asset_tools,
    normalize_content_path,
    object_ref,
    prop,
    schema,
)


def _create_material(args, ctx):
    name = args.get("name")
    if not name:
        return ctx.err("'name' is required")
    path = args.get("path") or "/Game/Materials"
    try:
        content_path = normalize_content_path(path)
    except ValueError as exc:
        return ctx.err(str(exc))
    try:
        m = asset_tools().create_asset(
            name, content_path, unreal.Material, unreal.MaterialFactoryNew()
        )
        if m is None:
            return ctx.err("failed to create material: %s/%s" % (content_path, name))
        base_color = args.get("base_color")
        if base_color is not None:
            expr = unreal.MaterialEditingLibrary.create_material_expression(
                m, unreal.MaterialExpressionVectorParameter, -350, 0
            )
            expr.set_editor_property("parameter_name", "BaseColor")
            expr.set_editor_property(
                "default_value",
                unreal.LinearColor(
                    base_color[0], base_color[1], base_color[2], 1.0
                ),
            )
            unreal.MaterialEditingLibrary.connect_material_property(
                expr, "", unreal.MaterialProperty.MP_BASE_COLOR
            )
            unreal.MaterialEditingLibrary.recompile_material(m)
        unreal.EditorAssetLibrary.save_loaded_asset(m)
    except Exception as exc:  # noqa: BLE001
        return ctx.err(str(exc))
    return ctx.ok(object_ref(m))


def _create_material_instance(args, ctx):
    name = args.get("name")
    if not name:
        return ctx.err("'name' is required")
    parent_path = args.get("parent_path")
    if not parent_path:
        return ctx.err("'parent_path' is required")
    path = args.get("path") or "/Game/Materials"
    try:
        content_path = normalize_content_path(path)
    except ValueError as exc:
        return ctx.err(str(exc))
    try:
        mic = asset_tools().create_asset(
            name,
            content_path,
            unreal.MaterialInstanceConstant,
            unreal.MaterialInstanceConstantFactoryNew(),
        )
        if mic is None:
            return ctx.err(
                "failed to create material instance: %s/%s" % (content_path, name)
            )
        parent = unreal.EditorAssetLibrary.load_asset(parent_path)
        if parent is None:
            return ctx.err("parent material not found: %s" % parent_path)
        unreal.MaterialEditingLibrary.set_material_instance_parent(mic, parent)
        unreal.EditorAssetLibrary.save_loaded_asset(mic)
    except Exception as exc:  # noqa: BLE001
        return ctx.err(str(exc))
    return ctx.ok(object_ref(mic))


def _set_material_instance_parameter(args, ctx):
    instance_path = args.get("instance_path")
    if not instance_path:
        return ctx.err("'instance_path' is required")
    name = args.get("name")
    if not name:
        return ctx.err("'name' (parameter name) is required")
    param_type = (args.get("type") or "").lower()
    if "value" not in args:
        return ctx.err("'value' is required")
    value = args.get("value")
    try:
        mic = unreal.EditorAssetLibrary.load_asset(instance_path)
        if mic is None:
            return ctx.err("material instance not found: %s" % instance_path)
        if param_type == "scalar":
            unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(
                mic, name, float(value)
            )
        elif param_type == "vector":
            unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(
                mic,
                name,
                unreal.LinearColor(
                    value[0],
                    value[1],
                    value[2],
                    value[3] if len(value) > 3 else 1.0,
                ),
            )
        elif param_type == "texture":
            tex = unreal.EditorAssetLibrary.load_asset(value)
            if tex is None:
                return ctx.err("texture not found: %s" % value)
            unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(
                mic, name, tex
            )
        else:
            return ctx.err(
                "'type' must be one of 'scalar', 'vector', 'texture'"
            )
        unreal.EditorAssetLibrary.save_loaded_asset(mic)
    except Exception as exc:  # noqa: BLE001
        return ctx.err(str(exc))
    return ctx.text(
        "Set %s parameter '%s' on %s" % (param_type, name, instance_path)
    )


def _get_material_info(args, ctx):
    material_path = args.get("material_path")
    if not material_path:
        return ctx.err("'material_path' is required")
    try:
        asset = unreal.EditorAssetLibrary.load_asset(material_path)
        if asset is None:
            return ctx.err("material not found: %s" % material_path)
        info = {"path": material_path, "class": asset.get_class().get_name()}
        if isinstance(asset, unreal.MaterialInstanceConstant):
            try:
                info["parent"] = object_ref(asset.get_editor_property("parent"))
            except Exception:  # noqa: BLE001
                info["parent"] = None
    except Exception as exc:  # noqa: BLE001
        return ctx.err(str(exc))
    return ctx.ok(info)


def register(reg):
    reg.register(
        "create_material",
        "Create a new Material asset, optionally wiring a BaseColor "
        "vector parameter from an [r, g, b] color (0..1).",
        schema(
            {
                "name": prop("string", "Asset name for the new material."),
                "path": prop(
                    "string", "Content folder (default /Game/Materials)."
                ),
                "base_color": {
                    "type": "array",
                    "description": "Optional [r, g, b] base color, each 0..1.",
                    "items": {"type": "number"},
                },
            },
            required=["name"],
        ),
        _create_material,
        profiles=("full",),
        group="materials",
    )
    reg.register(
        "create_material_instance",
        "Create a Material Instance Constant parented to an existing material.",
        schema(
            {
                "name": prop("string", "Asset name for the new instance."),
                "path": prop(
                    "string", "Content folder (default /Game/Materials)."
                ),
                "parent_path": prop(
                    "string", "Content path of the parent material."
                ),
            },
            required=["name", "parent_path"],
        ),
        _create_material_instance,
        profiles=("full",),
        group="materials",
    )
    reg.register(
        "set_material_instance_parameter",
        "Set a scalar, vector, or texture parameter on a material instance.",
        schema(
            {
                "instance_path": prop(
                    "string", "Content path of the material instance."
                ),
                "name": prop("string", "Parameter name."),
                "type": prop(
                    "string", "Parameter type: 'scalar', 'vector', or 'texture'."
                ),
                "value": {
                    "description": "Scalar number, [r,g,b(,a)] for vector, "
                    "or a texture content path."
                },
            },
            required=["instance_path", "name", "type", "value"],
        ),
        _set_material_instance_parameter,
        profiles=("full",),
        group="materials",
    )
    reg.register(
        "get_material_info",
        "Inspect a material or material instance: class and (for instances) parent.",
        schema(
            {"material_path": prop("string", "Content path of the material asset.")},
            required=["material_path"],
        ),
        _get_material_info,
        profiles=("core", "full"),
        group="materials",
    )
