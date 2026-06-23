"""Asset tools: list / find / inspect / duplicate / rename / delete / save / import."""

import unreal

from .common import (
    asset_subsystem,
    asset_tools,
    normalize_content_path,
    object_ref,
    prop,
    schema,
)


def _list_assets(args, ctx):
    path = args.get("path", "/Game")
    recursive = args.get("recursive", True)
    try:
        norm = normalize_content_path(path)
    except ValueError as exc:
        return ctx.err(str(exc))
    try:
        paths = asset_subsystem().list_assets(norm, bool(recursive), False)
    except Exception as exc:  # noqa: BLE001
        return ctx.err(str(exc))
    assets = list(paths)
    return ctx.ok({"path": norm, "count": len(assets), "assets": assets})


def _find_assets(args, ctx):
    query = (args.get("query") or "").lower()
    class_filter = (args.get("class_name") or "").lower()
    path = args.get("path", "/Game")
    try:
        norm = normalize_content_path(path)
    except ValueError as exc:
        return ctx.err(str(exc))
    try:
        paths = asset_subsystem().list_assets(norm, True, False)
    except Exception as exc:  # noqa: BLE001
        return ctx.err(str(exc))
    out = []
    truncated = False
    for p in paths:
        if query and query not in p.lower():
            continue
        cls = ""
        try:
            data = asset_subsystem().find_asset_data(p)
            if data is not None and data.is_valid():
                cls = str(data.asset_class_path.asset_name)
        except Exception:  # noqa: BLE001
            cls = ""
        if class_filter and class_filter not in cls.lower():
            continue
        if len(out) >= 500:
            truncated = True
            break
        out.append({"path": p, "class": cls})
    result = {"count": len(out), "assets": out}
    if truncated:
        result["truncated"] = True
        result["note"] = "results capped at 500"
    return ctx.ok(result)


def _get_asset_info(args, ctx):
    asset_path = args.get("asset_path")
    if not asset_path:
        return ctx.err("'asset_path' is required")
    try:
        data = asset_subsystem().find_asset_data(asset_path)
    except Exception as exc:  # noqa: BLE001
        return ctx.err(str(exc))
    if data is None or not data.is_valid():
        return ctx.err("asset not found: %s" % asset_path)
    info = {
        "package_name": str(data.package_name),
        "asset_name": str(data.asset_name),
    }
    try:
        info["class"] = str(data.asset_class_path.asset_name)
    except Exception:  # noqa: BLE001
        try:
            info["class"] = data.get_class().get_name()
        except Exception:  # noqa: BLE001
            info["class"] = None
    try:
        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        if asset is not None:
            info["object"] = object_ref(asset)
    except Exception:  # noqa: BLE001
        pass
    return ctx.ok(info)


def _duplicate_asset(args, ctx):
    source_path = args.get("source_path")
    dest_path = args.get("dest_path")
    if not source_path:
        return ctx.err("'source_path' is required")
    if not dest_path:
        return ctx.err("'dest_path' is required")
    try:
        asset_subsystem().duplicate_asset(source_path, dest_path)
    except Exception as exc:  # noqa: BLE001
        return ctx.err(str(exc))
    return ctx.text("Duplicated %s -> %s" % (source_path, dest_path))


def _rename_asset(args, ctx):
    source_path = args.get("source_path")
    dest_path = args.get("dest_path")
    if not source_path:
        return ctx.err("'source_path' is required")
    if not dest_path:
        return ctx.err("'dest_path' is required")
    try:
        asset_subsystem().rename_asset(source_path, dest_path)
    except Exception as exc:  # noqa: BLE001
        return ctx.err(str(exc))
    return ctx.text("Renamed %s -> %s" % (source_path, dest_path))


def _delete_asset(args, ctx):
    asset_path = args.get("asset_path")
    if not asset_path:
        return ctx.err("'asset_path' is required")
    try:
        asset_subsystem().delete_asset(asset_path)
    except Exception as exc:  # noqa: BLE001
        return ctx.err(str(exc))
    return ctx.text("Deleted asset: %s" % asset_path)


def _save_asset(args, ctx):
    asset_path = args.get("asset_path")
    if not asset_path:
        return ctx.err("'asset_path' is required")
    try:
        asset_subsystem().save_asset(asset_path, False)
    except Exception as exc:  # noqa: BLE001
        return ctx.err(str(exc))
    return ctx.text("Saved asset: %s" % asset_path)


def _import_asset(args, ctx):
    filename = args.get("filename")
    destination_path = args.get("destination_path")
    if not filename:
        return ctx.err("'filename' is required")
    if not destination_path:
        return ctx.err("'destination_path' is required")
    try:
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", filename)
        task.set_editor_property("destination_path", destination_path)
        task.set_editor_property("automated", True)
        task.set_editor_property("save", True)
        task.set_editor_property("replace_existing", True)
        asset_tools().import_asset_tasks([task])
        imported = list(task.get_editor_property("imported_object_paths"))
    except Exception as exc:  # noqa: BLE001
        return ctx.err(str(exc))
    return ctx.ok({"imported": imported})


def _create_folder(args, ctx):
    path = args.get("path")
    if not path:
        return ctx.err("'path' is required")
    try:
        norm = normalize_content_path(path)
    except ValueError as exc:
        return ctx.err(str(exc))
    try:
        unreal.EditorAssetLibrary.make_directory(norm)
    except Exception as exc:  # noqa: BLE001
        return ctx.err(str(exc))
    return ctx.text("Created folder: %s" % norm)


def _asset_exists(args, ctx):
    asset_path = args.get("asset_path")
    if not asset_path:
        return ctx.err("'asset_path' is required")
    try:
        exists = bool(asset_subsystem().does_asset_exist(asset_path))
    except Exception as exc:  # noqa: BLE001
        return ctx.err(str(exc))
    return ctx.ok({"exists": exists, "path": asset_path})


def _get_asset_references(args, ctx):
    asset_path = args.get("asset_path")
    if not asset_path:
        return ctx.err("'asset_path' is required")
    package = asset_path.split(".")[0]
    try:
        registry = unreal.AssetRegistryHelpers.get_asset_registry()
        options = unreal.AssetRegistryDependencyOptions()
        deps = registry.get_dependencies(package, options) or []
        refs = registry.get_referencers(package, options) or []
    except Exception as exc:  # noqa: BLE001
        return ctx.err(str(exc))
    return ctx.ok(
        {
            "package": package,
            "dependencies": [str(d) for d in deps],
            "referencers": [str(r) for r in refs],
        }
    )


def register(reg):
    reg.register(
        "list_assets",
        "List asset object paths under a content path (e.g. /Game), optionally recursive.",
        schema(
            {
                "path": prop("string", "Content path to list (default /Game)."),
                "recursive": prop("boolean", "Recurse into subfolders (default true)."),
            }
        ),
        _list_assets,
        profiles=("core", "full"),
        group="assets",
    )
    reg.register(
        "find_assets",
        "Find assets by path substring and/or class-name substring under a content path. "
        "Results are capped at 500.",
        schema(
            {
                "query": prop("string", "Path substring filter."),
                "class_name": prop("string", "Asset class-name substring filter."),
                "path": prop("string", "Content path to search (default /Game)."),
            }
        ),
        _find_assets,
        profiles=("core", "full"),
        group="assets",
    )
    reg.register(
        "get_asset_info",
        "Inspect an asset: package name, asset name, class, and an object reference.",
        schema(
            {"asset_path": prop("string", "Content path of the asset.")},
            required=["asset_path"],
        ),
        _get_asset_info,
        profiles=("core", "full"),
        group="assets",
    )
    reg.register(
        "duplicate_asset",
        "Duplicate an asset to a new content path.",
        schema(
            {
                "source_path": prop("string", "Source asset content path."),
                "dest_path": prop("string", "Destination asset content path."),
            },
            required=["source_path", "dest_path"],
        ),
        _duplicate_asset,
        profiles=("full",),
        group="assets",
    )
    reg.register(
        "rename_asset",
        "Rename (move) an asset to a new content path.",
        schema(
            {
                "source_path": prop("string", "Source asset content path."),
                "dest_path": prop("string", "Destination asset content path."),
            },
            required=["source_path", "dest_path"],
        ),
        _rename_asset,
        profiles=("full",),
        group="assets",
    )
    reg.register(
        "delete_asset",
        "Delete an asset by content path.",
        schema(
            {"asset_path": prop("string", "Content path of the asset to delete.")},
            required=["asset_path"],
        ),
        _delete_asset,
        profiles=("full",),
        group="assets",
    )
    reg.register(
        "save_asset",
        "Save a (possibly dirty) asset to disk by content path.",
        schema(
            {"asset_path": prop("string", "Content path of the asset to save.")},
            required=["asset_path"],
        ),
        _save_asset,
        profiles=("full",),
        group="assets",
    )
    reg.register(
        "import_asset",
        "Import a file from disk into the content browser (FBX, textures, etc.).",
        schema(
            {
                "filename": prop("string", "Absolute disk path of the source file."),
                "destination_path": prop(
                    "string", "Destination content folder, e.g. /Game/Imported."
                ),
            },
            required=["filename", "destination_path"],
        ),
        _import_asset,
        profiles=("full",),
        group="assets",
    )
    reg.register(
        "create_folder",
        "Create a content-browser folder (directory).",
        schema(
            {"path": prop("string", "Content path of the folder to create.")},
            required=["path"],
        ),
        _create_folder,
        profiles=("full",),
        group="assets",
    )
    reg.register(
        "asset_exists",
        "Check whether an asset exists at a content path.",
        schema(
            {"asset_path": prop("string", "Content path to check.")},
            required=["asset_path"],
        ),
        _asset_exists,
        profiles=("core", "full"),
        group="assets",
    )
    reg.register(
        "get_asset_references",
        "Get an asset's dependencies (what it uses) and referencers (what uses it) "
        "from the asset registry -- check before renaming or deleting.",
        schema(
            {"asset_path": prop("string", "Content path of the asset.")},
            required=["asset_path"],
        ),
        _get_asset_references,
        profiles=("core", "full"),
        group="assets",
    )
