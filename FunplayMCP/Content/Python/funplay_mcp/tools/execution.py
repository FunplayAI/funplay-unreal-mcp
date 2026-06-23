"""execute_python -- the centerpiece -- and run_console_command."""

import contextlib
import io
import traceback

import unreal

from ..context import json_safe
from .common import all_level_actors, editor_world, prop, schema

# Conceptual denylist: block filesystem/process escape by default. The point of
# execute_python is Unreal automation, so unreal.* calls are NOT blocked (except
# obvious destructive deletes). Override per-call with safety_checks=false.
_SAFETY_DENYLIST = [
    "subprocess",
    "os.system",
    "os.popen",
    "os.remove",
    "os.unlink",
    "os.rmdir",
    "os.removedirs",
    "os.rename",
    "os.replace",
    "os.exec",
    "os.kill",
    "os.fork",
    "shutil.rmtree",
    "shutil.move",
    "shutil.copy",
    "sys.exit",
    "socket.",
    "ftplib",
    "urlretrieve",
    "delete_asset",
    "delete_directory",
    "delete_loaded_asset",
]


def _safety_matches(code):
    lowered = code.lower()
    return [needle for needle in _SAFETY_DENYLIST if needle in lowered]


def _snapshot():
    try:
        labels = set(a.get_actor_label() for a in all_level_actors())
    except Exception:  # noqa: BLE001
        labels = set()
    return {"count": len(labels), "labels": labels}


def _diff(before, after):
    return {
        "actors_created": sorted(after["labels"] - before["labels"]),
        "actors_removed": sorted(before["labels"] - after["labels"]),
        "actor_count_delta": after["count"] - before["count"],
    }


def _execute_python(args, ctx):
    code = args.get("code")
    if not isinstance(code, str) or not code.strip():
        return ctx.err("'code' (a Python snippet) is required")

    safety = args.get("safety_checks")
    if safety is None:
        safety = ctx.settings.execute_python_safety_checks_enabled
    if safety:
        matches = _safety_matches(code)
        if matches:
            return ctx.tool_error(
                "EXECUTE_PYTHON_SAFETY_BLOCKED",
                "Snippet blocked by safety checks. Pass safety_checks=false to override.",
                {"matches": matches},
            )

    include_metadata = args.get("include_metadata", True)
    before = _snapshot() if include_metadata else None

    logs = []
    namespace = {
        "unreal": unreal,
        "__name__": "__funplay_exec__",
        "log": lambda *a: logs.append(" ".join(str(x) for x in a)),
    }
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            exec(compile(code, "<funplay_execute_python>", "exec"), namespace)  # noqa: S102
    except BaseException as exc:  # noqa: BLE001
        return ctx.tool_error(
            "EXECUTE_PYTHON_ERROR",
            str(exc),
            {"traceback": traceback.format_exc(), "stdout": out.getvalue()},
        )

    payload = {"success": True, "stdout": out.getvalue(), "logs": logs}
    if "result" in namespace:
        payload["result"] = json_safe(namespace["result"])
    if include_metadata and before is not None:
        payload["changes"] = _diff(before, _snapshot())
    return ctx.ok(payload)


def _run_console_command(args, ctx):
    command = args.get("command")
    if not command:
        return ctx.err("'command' is required")
    unreal.SystemLibrary.execute_console_command(editor_world(), command)
    return ctx.text("Executed console command: %s" % command)


def register(reg):
    reg.register(
        "execute_python",
        "Execute an arbitrary Python snippet inside the Unreal Editor (the "
        "embedded 'unreal' module is available as `unreal`; assign to a variable "
        "named `result` to return data, call log(...) for log lines). Returns "
        "stdout, logs, result and a diff of created/removed actors. The most "
        "powerful tool -- use it when no dedicated tool fits.",
        schema(
            {
                "code": prop("string", "The Python source to execute."),
                "safety_checks": prop(
                    "boolean",
                    "Override the filesystem/process safety denylist for this call.",
                ),
                "include_metadata": prop(
                    "boolean",
                    "Include the before/after actor diff (default true).",
                ),
            },
            required=["code"],
        ),
        _execute_python,
        profiles=("core", "full"),
        group="execution",
        timeout=120.0,
    )
    reg.register(
        "run_console_command",
        "Run an Unreal console command (e.g. 'stat fps', 'r.ScreenPercentage 50').",
        schema(
            {"command": prop("string", "The console command to run.")},
            required=["command"],
        ),
        _run_console_command,
        profiles=("full",),
        group="execution",
    )
