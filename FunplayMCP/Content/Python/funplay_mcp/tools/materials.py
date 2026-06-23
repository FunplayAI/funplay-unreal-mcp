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


def _resolve_expression_class(name):
    if not name:
        raise ValueError("'expression_class' is required")
    for candidate in (name, "MaterialExpression" + name):
        cls = getattr(unreal, candidate, None)
        if cls is not None:
            return cls
    raise ValueError("unknown material expression class: %s" % name)


def _material_property_enum(name):
    key = "MP_" + str(name).upper().replace("MP_", "")
    enum = getattr(unreal.MaterialProperty, key, None)
    if enum is None:
        raise ValueError("unknown material property: %s" % name)
    return enum


def _add_material_expression(args, ctx):
    material_path = args.get("material_path")
    if not material_path:
        return ctx.err("'material_path' is required")
    try:
        material = unreal.EditorAssetLibrary.load_asset(material_path)
        if material is None:
            return ctx.err("material not found: %s" % material_path)
        cls = _resolve_expression_class(args.get("expression_class"))
        expr = unreal.MaterialEditingLibrary.create_material_expression(
            material, cls, int(args.get("node_x", 0)), int(args.get("node_y", 0))
        )
        if expr is None:
            return ctx.err("failed to create expression")
        for key, value in (args.get("properties") or {}).items():
            try:
                expr.set_editor_property(key, value)
            except Exception:  # noqa: BLE001
                pass
        if args.get("connect_to_property"):
            unreal.MaterialEditingLibrary.connect_material_property(
                expr,
                args.get("output", ""),
                _material_property_enum(args["connect_to_property"]),
            )
        if args.get("recompile"):
            unreal.MaterialEditingLibrary.recompile_material(material)
        unreal.EditorAssetLibrary.save_loaded_asset(material)
    except Exception as exc:  # noqa: BLE001
        return ctx.err(str(exc))
    return ctx.ok({"expression": expr.get_name(), "path": expr.get_path_name()})


def _connect_material_expressions(args, ctx):
    try:
        from_expr = unreal.load_object(None, args.get("from_path"))
        to_expr = unreal.load_object(None, args.get("to_path"))
        if from_expr is None or to_expr is None:
            return ctx.err("could not resolve from_path/to_path expression objects")
        unreal.MaterialEditingLibrary.connect_material_expressions(
            from_expr, args.get("from_output", ""), to_expr, args.get("to_input", "")
        )
        material = unreal.EditorAssetLibrary.load_asset(args.get("material_path"))
        if material is not None:
            unreal.EditorAssetLibrary.save_loaded_asset(material)
    except Exception as exc:  # noqa: BLE001
        return ctx.err(str(exc))
    return ctx.text("Connected material expressions.")


def _connect_material_property(args, ctx):
    try:
        expr = unreal.load_object(None, args.get("from_path"))
        if expr is None:
            return ctx.err("could not resolve from_path expression object")
        unreal.MaterialEditingLibrary.connect_material_property(
            expr, args.get("output", ""), _material_property_enum(args.get("property"))
        )
        material = unreal.EditorAssetLibrary.load_asset(args.get("material_path"))
        if material is not None:
            unreal.EditorAssetLibrary.save_loaded_asset(material)
    except Exception as exc:  # noqa: BLE001
        return ctx.err(str(exc))
    return ctx.text("Connected expression to material property.")


def _recompile_material(args, ctx):
    material_path = args.get("material_path")
    if not material_path:
        return ctx.err("'material_path' is required")
    try:
        material = unreal.EditorAssetLibrary.load_asset(material_path)
        if material is None:
            return ctx.err("material not found: %s" % material_path)
        unreal.MaterialEditingLibrary.recompile_material(material)
        unreal.EditorAssetLibrary.save_loaded_asset(material)
    except Exception as exc:  # noqa: BLE001
        return ctx.err(str(exc))
    return ctx.text("Recompiled material: %s" % material_path)


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
    reg.register(
        "add_material_expression",
        "Add a node (expression) to a Material's graph; optionally set its properties "
        "and wire its output to a material property (e.g. 'base_color'). Returns the "
        "expression's durable object path for later connect calls.",
        schema(
            {
                "material_path": prop("string", "Content path of the material."),
                "expression_class": prop(
                    "string", "Expression class, e.g. 'Constant3Vector', 'TextureSample', 'Multiply'."
                ),
                "node_x": prop("integer", "Graph X position (default 0)."),
                "node_y": prop("integer", "Graph Y position (default 0)."),
                "properties": {"type": "object", "description": "Editor properties to set on the node."},
                "connect_to_property": prop(
                    "string", "Optional material property to wire output into, e.g. 'base_color', 'metallic'."
                ),
                "output": prop("string", "Output pin name (default empty = first)."),
                "recompile": prop("boolean", "Recompile after adding (default false)."),
            },
            required=["material_path", "expression_class"],
        ),
        _add_material_expression,
        profiles=("full",),
        group="materials",
    )
    reg.register(
        "connect_material_expressions",
        "Wire one material expression's output pin to another's input pin (use the "
        "object paths returned by add_material_expression).",
        schema(
            {
                "material_path": prop("string", "Content path of the material."),
                "from_path": prop("string", "Source expression object path."),
                "from_output": prop("string", "Source output pin name (default first)."),
                "to_path": prop("string", "Target expression object path."),
                "to_input": prop("string", "Target input pin name (default first)."),
            },
            required=["from_path", "to_path"],
        ),
        _connect_material_expressions,
        profiles=("full",),
        group="materials",
    )
    reg.register(
        "connect_material_property",
        "Wire a material expression's output to a material output property "
        "(e.g. 'base_color', 'roughness', 'emissive_color').",
        schema(
            {
                "material_path": prop("string", "Content path of the material."),
                "from_path": prop("string", "Source expression object path."),
                "output": prop("string", "Source output pin name (default first)."),
                "property": prop("string", "Material property, e.g. 'base_color'."),
            },
            required=["from_path", "property"],
        ),
        _connect_material_property,
        profiles=("full",),
        group="materials",
    )
    reg.register(
        "recompile_material",
        "Recompile and save a Material after graph edits.",
        schema(
            {"material_path": prop("string", "Content path of the material.")},
            required=["material_path"],
        ),
        _recompile_material,
        profiles=("full",),
        group="materials",
    )
