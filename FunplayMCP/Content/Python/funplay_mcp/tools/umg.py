"""UMG tools: create Widget Blueprints and populate their widget tree.

Scope is deliberately narrow -- widget *creation*, simple *hierarchy*, and
*property* edits only. Complex slot layout (anchors/offsets) and event/binding
graphs are NOT supported here; use the Unreal editor for those. WidgetTree
access varies across UE 5.3-5.8, so every tree call is guarded."""

import unreal

from ..context import object_ref
from .common import (
    asset_tools,
    normalize_content_path,
    prop,
    resolve_class,
    schema,
    transaction,
)


def _load_wbp(path):
    """Load a WidgetBlueprint asset; raise ValueError on miss/wrong type."""
    if not path:
        raise ValueError("'widget_blueprint_path' is required")
    wbp = unreal.EditorAssetLibrary.load_asset(path)
    if wbp is None:
        raise ValueError("widget blueprint not found: %s" % path)
    if not isinstance(wbp, unreal.WidgetBlueprint):
        raise ValueError("asset is not a WidgetBlueprint: %s" % path)
    return wbp


def _widget_tree(wbp):
    """Fetch the WidgetTree off a WidgetBlueprint, tolerant of API drift."""
    tree = None
    try:
        tree = wbp.get_editor_property("widget_tree")
    except Exception:  # noqa: BLE001
        tree = None
    if tree is None:
        tree = getattr(wbp, "widget_tree", None)
    if tree is None:
        raise ValueError("could not access the widget tree on this blueprint")
    return tree


def _tree_root(tree):
    """Return the tree's root widget (or None), defensively."""
    try:
        return tree.get_editor_property("root_widget")
    except Exception:  # noqa: BLE001
        return getattr(tree, "root_widget", None)


def _compile(wbp):
    """Best-effort blueprint compile; swallow failures so edits still apply."""
    lib = getattr(unreal, "BlueprintEditorLibrary", None)
    if lib is None:
        return
    try:
        lib.compile_blueprint(wbp)
    except Exception:  # noqa: BLE001
        pass


def _create_widget_blueprint(args, ctx):
    name = args.get("name")
    if not name:
        return ctx.err("'name' is required")
    try:
        path = normalize_content_path(args.get("path") or "/Game/UI")
    except ValueError as exc:
        return ctx.err(str(exc))
    factory = getattr(unreal, "WidgetBlueprintFactory", None)
    if factory is None:
        return ctx.err("WidgetBlueprintFactory not available; enable plugin UMG and restart")
    try:
        f = factory()
        wbp = asset_tools().create_asset(name, path, unreal.WidgetBlueprint, f)
    except Exception as exc:  # noqa: BLE001
        return ctx.err(str(exc))
    if wbp is None:
        return ctx.err("failed to create widget blueprint: %s/%s" % (path, name))
    try:
        unreal.EditorAssetLibrary.save_loaded_asset(wbp)
    except Exception:  # noqa: BLE001
        pass
    return ctx.ok(object_ref(wbp))


def _add_widget(args, ctx):
    try:
        wbp = _load_wbp(args.get("widget_blueprint_path"))
        tree = _widget_tree(wbp)
    except ValueError as exc:
        return ctx.err(str(exc))
    widget_class = args.get("widget_class")
    try:
        cls = resolve_class(widget_class)
    except ValueError as exc:
        return ctx.err(str(exc))
    try:
        with transaction("Funplay: Add Widget"):
            w = tree.construct_widget(cls)
            if w is None:
                return ctx.err("construct_widget returned nothing for %s" % widget_class)
            if args.get("name"):
                try:
                    w.rename(args["name"])
                except Exception:  # noqa: BLE001
                    pass  # rename is best-effort; name collisions are non-fatal
            root = _tree_root(tree)
            if root is None:
                tree.set_editor_property("root_widget", w)
            else:
                # Only panel widgets accept children; ignore if root is a leaf.
                try:
                    root.add_child(w)
                except Exception:  # noqa: BLE001
                    pass
    except Exception as exc:  # noqa: BLE001
        return ctx.err(str(exc))
    _compile(wbp)
    return ctx.ok({"widget": w.get_name(), "class": widget_class})


def _find_widget(tree, widget_name):
    """Locate a widget by name in the tree; fall back to the root."""
    try:
        for w in tree.get_all_widgets():
            if w is not None and w.get_name() == widget_name:
                return w
    except Exception:  # noqa: BLE001
        pass
    return _tree_root(tree)


def _set_widget_property(args, ctx):
    try:
        wbp = _load_wbp(args.get("widget_blueprint_path"))
        tree = _widget_tree(wbp)
    except ValueError as exc:
        return ctx.err(str(exc))
    widget_name = args.get("widget_name")
    if not widget_name:
        return ctx.err("'widget_name' is required")
    name = args.get("name")
    if not name:
        return ctx.err("'name' (property name) is required")
    if "value" not in args:
        return ctx.err("'value' is required")
    target = _find_widget(tree, widget_name)
    if target is None:
        return ctx.err("widget not found: %s" % widget_name)
    try:
        with transaction("Funplay: Set Widget Property"):
            target.set_editor_property(name, args["value"])
    except Exception as exc:  # noqa: BLE001
        return ctx.err("could not set property '%s': %s" % (name, exc))
    _compile(wbp)
    return ctx.text("Set %s.%s on %s" % (target.get_name(), name, widget_name))


def register(reg):
    reg.register(
        "create_widget_blueprint",
        "Create a new UMG Widget Blueprint asset (saved to disk).",
        schema(
            {
                "name": prop("string", "Asset name for the new Widget Blueprint."),
                "path": prop("string", "Content folder (default '/Game/UI')."),
            },
            required=["name"],
        ),
        _create_widget_blueprint,
        profiles=("full",),
        group="umg",
    )
    reg.register(
        "add_widget",
        "Add a widget (e.g. 'TextBlock', 'Button', 'VerticalBox', 'CanvasPanel') "
        "to a Widget Blueprint. Sets it as the root if the tree is empty, else "
        "adds it as a child of the root panel. Creation + hierarchy only -- "
        "slot layout and event binding are not supported.",
        schema(
            {
                "widget_blueprint_path": prop("string", "Content path of the Widget Blueprint."),
                "widget_class": prop("string", "Widget class name, e.g. 'TextBlock'."),
                "name": prop("string", "Optional name for the new widget."),
            },
            required=["widget_blueprint_path", "widget_class"],
        ),
        _add_widget,
        profiles=("full",),
        group="umg",
    )
    reg.register(
        "set_widget_property",
        "Set an editor property on a widget inside a Widget Blueprint, located by "
        "its name (falls back to the root widget).",
        schema(
            {
                "widget_blueprint_path": prop("string", "Content path of the Widget Blueprint."),
                "widget_name": prop("string", "Name of the widget to modify."),
                "name": prop("string", "Property name to set."),
                "value": {"description": "Property value (any JSON type)."},
            },
            required=["widget_blueprint_path", "widget_name", "name", "value"],
        ),
        _set_widget_property,
        profiles=("full",),
        group="umg",
    )
