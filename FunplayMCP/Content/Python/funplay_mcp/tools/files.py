"""File tools: read / write / list / exists, scoped to the project directory."""

import os

import unreal

from .common import prop, safe_project_path, schema


def _read_file(args, ctx):
    path = args.get("path")
    try:
        resolve = safe_project_path(path)
    except ValueError as exc:
        return ctx.err(str(exc))
    if not os.path.isfile(resolve):
        return ctx.err("not a file: %s" % path)
    max_chars = int(args.get("max_chars", 100000))
    with open(resolve, "r", encoding="utf-8", errors="replace") as handle:
        text = handle.read()
    truncated = len(text) > max_chars
    if truncated:
        text = text[:max_chars]
    return ctx.ok({"path": path, "content": text, "truncated": truncated})


def _write_file(args, ctx):
    path = args.get("path")
    try:
        resolve = safe_project_path(path)
    except ValueError as exc:
        return ctx.err(str(exc))
    content = args.get("content")
    if content is None:
        return ctx.err("'content' is required")
    content = str(content)
    if args.get("create_dirs", True):
        parent = os.path.dirname(resolve)
        if parent:
            os.makedirs(parent, exist_ok=True)
    with open(resolve, "w", encoding="utf-8") as handle:
        handle.write(content)
    return ctx.text("Wrote %d bytes to %s" % (len(content.encode("utf-8")), path))


def _list_directory(args, ctx):
    path = args.get("path") or "."
    try:
        resolve = safe_project_path(path)
    except ValueError as exc:
        return ctx.err(str(exc))
    if not os.path.isdir(resolve):
        return ctx.err("not a directory: %s" % path)
    entries = []
    for name in sorted(os.listdir(resolve)):
        full = os.path.join(resolve, name)
        is_dir = os.path.isdir(full)
        try:
            size = 0 if is_dir else os.path.getsize(full)
        except OSError:
            size = 0
        entries.append({"name": name, "is_dir": is_dir, "size": size})
    return ctx.ok({"path": path, "entries": entries})


def _file_exists(args, ctx):
    path = args.get("path")
    try:
        resolve = safe_project_path(path)
    except ValueError as exc:
        return ctx.err(str(exc))
    return ctx.ok(
        {
            "path": path,
            "exists": os.path.exists(resolve),
            "is_dir": os.path.isdir(resolve),
        }
    )


def register(reg):
    reg.register(
        "read_file",
        "Read a UTF-8 text file relative to the project directory (truncated to "
        "max_chars).",
        schema(
            {
                "path": prop("string", "Path relative to the project directory."),
                "max_chars": prop(
                    "integer", "Maximum characters to return (default 100000)."
                ),
            },
            required=["path"],
        ),
        _read_file,
        profiles=("core", "full"),
        group="files",
    )
    reg.register(
        "write_file",
        "Write a UTF-8 text file relative to the project directory (creates parent "
        "dirs by default).",
        schema(
            {
                "path": prop("string", "Path relative to the project directory."),
                "content": prop("string", "Text content to write."),
                "create_dirs": prop(
                    "boolean", "Create parent directories if missing (default true)."
                ),
            },
            required=["path", "content"],
        ),
        _write_file,
        profiles=("full",),
        group="files",
    )
    reg.register(
        "list_directory",
        "List entries (name, is_dir, size) in a directory relative to the project.",
        schema(
            {"path": prop("string", "Directory relative to the project (default '.').")}
        ),
        _list_directory,
        profiles=("core", "full"),
        group="files",
    )
    reg.register(
        "file_exists",
        "Check whether a path (relative to the project) exists and if it is a directory.",
        schema(
            {"path": prop("string", "Path relative to the project directory.")},
            required=["path"],
        ),
        _file_exists,
        profiles=("core", "full"),
        group="files",
    )
