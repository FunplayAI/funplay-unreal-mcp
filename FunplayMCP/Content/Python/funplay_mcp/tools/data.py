"""DataTable tools: create / read / write rows / export CSV.

DataTable APIs (DataTableFactory, DataTableFunctionLibrary) vary across UE
5.3-5.8, so every fiddly call is probed with getattr/hasattr and falls back to a
clear ctx.err instead of crashing."""

import unreal

from .common import (
    asset_tools,
    normalize_content_path,
    object_ref,
    prop,
    schema,
)


def _create_data_table(args, ctx):
    name = args.get("name")
    if not name:
        return ctx.err("'name' is required")
    row_struct = args.get("row_struct")
    if not row_struct:
        return ctx.err("'row_struct' (path to a UScriptStruct) is required")
    path = args.get("path") or "/Game/Data"
    # Resolve the row struct (e.g. /Game/Structs/MyRow or a /Script path).
    try:
        struct = unreal.load_object(None, row_struct)
    except Exception as exc:  # noqa: BLE001
        return ctx.err(str(exc))
    if struct is None:
        return ctx.err("could not load row struct: %s" % row_struct)
    factory_cls = getattr(unreal, "DataTableFactory", None)
    if factory_cls is None:
        return ctx.err("DataTableFactory not available on this engine version")
    try:
        factory = factory_cls()
        # Property name differs by version ('struct' vs 'row_struct').
        set_ok = False
        for key in ("struct", "row_struct"):
            try:
                factory.set_editor_property(key, struct)
                set_ok = True
                break
            except Exception:  # noqa: BLE001
                continue
        if not set_ok:
            return ctx.err("could not set row struct on DataTableFactory")
        dt = asset_tools().create_asset(
            name, normalize_content_path(path), unreal.DataTable, factory
        )
    except Exception as exc:  # noqa: BLE001
        return ctx.err(str(exc))
    if dt is None:
        return ctx.err("failed to create DataTable: %s" % name)
    try:
        unreal.EditorAssetLibrary.save_loaded_asset(dt)
    except Exception as exc:  # noqa: BLE001
        return ctx.err(str(exc))
    return ctx.ok(object_ref(dt))


def _load_data_table(args, ctx):
    """Load a DataTable asset; returns (dt, None) or (None, error_string)."""
    table_path = args.get("data_table_path")
    if not table_path:
        return None, "'data_table_path' is required"
    dt = unreal.EditorAssetLibrary.load_asset(table_path)
    if dt is None:
        return None, "DataTable not found: %s" % table_path
    return dt, None


def _get_data_table(args, ctx):
    dt, err = _load_data_table(args, ctx)
    if err:
        return ctx.err(err)
    lib = getattr(unreal, "DataTableFunctionLibrary", None)
    if lib is None:
        return ctx.err("DataTableFunctionLibrary not available on this engine version")
    fn = getattr(lib, "get_data_table_as_json", None)
    if fn is not None:
        try:
            return ctx.ok({"json": fn(dt)})
        except Exception as exc:  # noqa: BLE001
            return ctx.err(str(exc))
    # Fall back to row names only.
    names_fn = getattr(lib, "get_data_table_row_names", None)
    if names_fn is None:
        return ctx.err("no DataTable read API available on this engine version")
    try:
        names = [str(n) for n in names_fn(dt)]
    except Exception as exc:  # noqa: BLE001
        return ctx.err(str(exc))
    return ctx.ok({"row_names": names})


def _set_data_table_rows(args, ctx):
    dt, err = _load_data_table(args, ctx)
    if err:
        return ctx.err(err)
    json_str = args.get("json")
    if not json_str:
        return ctx.err("'json' (a JSON string of rows) is required")
    lib = getattr(unreal, "DataTableFunctionLibrary", None)
    if lib is None:
        return ctx.err("DataTableFunctionLibrary not available on this engine version")
    fn = getattr(lib, "fill_data_table_from_json_string", None)
    if fn is None:
        return ctx.err("fill_data_table_from_json_string not available on this engine version")
    try:
        fn(dt, json_str)
        unreal.EditorAssetLibrary.save_loaded_asset(dt)
    except Exception as exc:  # noqa: BLE001
        return ctx.err(str(exc))
    return ctx.text("Filled DataTable rows from JSON: %s" % args.get("data_table_path"))


def _export_data_table_csv(args, ctx):
    dt, err = _load_data_table(args, ctx)
    if err:
        return ctx.err(err)
    lib = getattr(unreal, "DataTableFunctionLibrary", None)
    if lib is None:
        return ctx.err("DataTableFunctionLibrary not available on this engine version")
    fn = getattr(lib, "get_data_table_as_csv", None)
    if fn is None:
        return ctx.err("CSV export not available on this engine version")
    try:
        return ctx.ok({"csv": fn(dt)})
    except Exception as exc:  # noqa: BLE001
        return ctx.err(str(exc))


def register(reg):
    reg.register(
        "create_data_table",
        "Create a DataTable asset backed by a row UScriptStruct. 'row_struct' is a "
        "path to a struct (e.g. /Game/Structs/MyRow or a /Script path).",
        schema(
            {
                "name": prop("string", "Asset name for the new DataTable."),
                "path": prop("string", "Content folder (default '/Game/Data')."),
                "row_struct": prop("string", "Path to the row UScriptStruct."),
            },
            required=["name", "row_struct"],
        ),
        _create_data_table,
        profiles=("full",),
        group="data",
    )
    reg.register(
        "get_data_table",
        "Read a DataTable: returns its rows as a JSON string, or row names if the "
        "JSON export API is unavailable.",
        schema(
            {"data_table_path": prop("string", "Content path of the DataTable.")},
            required=["data_table_path"],
        ),
        _get_data_table,
        profiles=("full",),
        group="data",
    )
    reg.register(
        "set_data_table_rows",
        "Replace a DataTable's rows from a JSON string (fill_data_table_from_json_string).",
        schema(
            {
                "data_table_path": prop("string", "Content path of the DataTable."),
                "json": prop("string", "JSON string of rows to fill."),
            },
            required=["data_table_path", "json"],
        ),
        _set_data_table_rows,
        profiles=("full",),
        group="data",
    )
    reg.register(
        "export_data_table_csv",
        "Export a DataTable's rows as a CSV string.",
        schema(
            {"data_table_path": prop("string", "Content path of the DataTable.")},
            required=["data_table_path"],
        ),
        _export_data_table_csv,
        profiles=("full",),
        group="data",
    )
