"""UE API reflection -- search and describe the embedded `unreal` module.

The embedded module is fully self-describing (class/method docstrings, an
"Editor Properties" list in each class docstring, iterable enums), so these tools
let an assistant discover the real API instead of guessing it -- the single
highest-leverage capability the leading Unreal MCP servers all ship."""

import re

import unreal

from ..context import json_safe, object_ref
from .common import prop, resolve_actor, resolve_class, schema

_index = None
_PROP_RE = re.compile(r"-\s*``([A-Za-z0-9_]+)``")


def _index_names():
    global _index
    if _index is None:
        _index = sorted(n for n in dir(unreal) if not n.startswith("_"))
    return _index


def _kind_of(obj):
    try:
        if isinstance(obj, type) and issubclass(obj, unreal.EnumBase):
            return "enum"
    except Exception:  # noqa: BLE001
        pass
    if isinstance(obj, type):
        return "class"
    if callable(obj):
        return "function"
    return "other"


def _prop_names(klass):
    names = []
    for base in getattr(klass, "__mro__", [klass]):
        for name in _PROP_RE.findall(base.__doc__ or ""):
            if name not in names:
                names.append(name)
    return names


def _search_api(args, ctx):
    query = (args.get("query") or "").strip().lower()
    if not query:
        return ctx.err("'query' is required")
    kind = (args.get("kind") or "any").lower()
    limit = int(args.get("limit", 50))
    out = []
    for name in _index_names():
        if query not in name.lower():
            continue
        k = _kind_of(getattr(unreal, name, None))
        if kind != "any" and k != kind:
            continue
        out.append({"name": name, "kind": k})
        if len(out) >= limit:
            break
    return ctx.ok(
        {"query": args.get("query"), "kind": kind, "count": len(out), "results": out}
    )


def _describe_class(args, ctx):
    name = args.get("name")
    if not name:
        return ctx.err("'name' (an unreal class name, e.g. 'StaticMeshComponent') is required")
    cls = getattr(unreal, name, None)
    if cls is None or not isinstance(cls, type):
        return ctx.err("not a class in the unreal module: %s" % name)
    doc = cls.__doc__ or ""
    max_doc = int(args.get("max_doc_chars", 4000))
    methods = sorted(
        m for m in dir(cls)
        if not m.startswith("_") and callable(getattr(cls, m, None))
    )
    return ctx.ok(
        {
            "name": name,
            "bases": [b.__name__ for b in getattr(cls, "__bases__", ())],
            "doc": doc[:max_doc],
            "doc_truncated": len(doc) > max_doc,
            "editor_properties": _prop_names(cls),
            "methods": methods,
        }
    )


def _list_enum_values(args, ctx):
    name = args.get("name")
    if not name:
        return ctx.err("'name' (an unreal enum name) is required")
    cls = getattr(unreal, name, None)
    if cls is None:
        return ctx.err("not found in the unreal module: %s" % name)
    values = []
    try:
        for member in cls:
            values.append({"name": member.name, "value": int(member.value)})
    except Exception:  # noqa: BLE001
        values = [{"name": n} for n in dir(cls) if n.isupper()]
    if not values:
        return ctx.err("%s does not look like an enum" % name)
    return ctx.ok({"name": name, "count": len(values), "values": values})


def _resolve_inspect_target(args):
    if args.get("asset_path"):
        obj = unreal.EditorAssetLibrary.load_asset(args["asset_path"])
        if obj is None:
            raise ValueError("asset not found: %s" % args["asset_path"])
        return obj
    if args.get("actor"):
        return resolve_actor(args["actor"])
    if args.get("class_default"):
        cls = resolve_class(args["class_default"])
        getter = getattr(unreal, "get_default_object", None)
        return getter(cls) if getter else cls.get_default_object()
    raise ValueError("provide one of: actor, asset_path, class_default")


def _inspect_object(args, ctx):
    try:
        obj = _resolve_inspect_target(args)
    except ValueError as exc:
        return ctx.err(str(exc))
    limit = int(args.get("max_properties", 80))
    names = _prop_names(type(obj))
    props = {}
    for name in names[:limit]:
        try:
            props[name] = json_safe(obj.get_editor_property(name))
        except Exception:  # noqa: BLE001
            props[name] = "<unreadable>"
    return ctx.ok(
        {
            "object": object_ref(obj),
            "property_count": len(props),
            "truncated": len(names) > limit,
            "properties": props,
        }
    )


def register(reg):
    reg.register(
        "search_api",
        "Search the embedded Unreal Python API by substring -- find class, "
        "function, or enum names. Use this before guessing an API.",
        schema(
            {
                "query": prop("string", "Substring to search for."),
                "kind": prop("string", "Filter: 'class', 'function', 'enum', or 'any'."),
                "limit": prop("integer", "Max results (default 50)."),
            },
            required=["query"],
        ),
        _search_api,
        profiles=("core", "full"),
        game_thread=False,
        group="reflection",
    )
    reg.register(
        "describe_class",
        "Describe an unreal class: bases, docstring, editor properties, and methods.",
        schema(
            {
                "name": prop("string", "Class name, e.g. 'StaticMeshComponent'."),
                "max_doc_chars": prop("integer", "Cap the docstring length (default 4000)."),
            },
            required=["name"],
        ),
        _describe_class,
        profiles=("core", "full"),
        game_thread=False,
        group="reflection",
    )
    reg.register(
        "list_enum_values",
        "List the members (name + value) of an unreal enum.",
        schema({"name": prop("string", "Enum name, e.g. 'EAttachmentRule'.")},
               required=["name"]),
        _list_enum_values,
        profiles=("full",),
        game_thread=False,
        group="reflection",
    )
    reg.register(
        "inspect_object",
        "Dump the editor-exposed properties of any actor, asset, or class CDO via "
        "reflection. Provide one of: actor, asset_path, class_default.",
        schema(
            {
                "actor": prop("string", "Actor label/name/path to inspect."),
                "asset_path": prop("string", "Content path of an asset to inspect."),
                "class_default": prop("string", "Class name to inspect its CDO."),
                "max_properties": prop("integer", "Cap properties read (default 80)."),
            }
        ),
        _inspect_object,
        profiles=("full",),
        group="reflection",
    )
