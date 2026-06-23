"""Tool execution context + JSON rendering of ``unreal`` types.

Every tool handler has the signature ``handler(args: dict, ctx: ToolContext) -> str``
and returns a single string per the Funplay-family contract:
  * plain text            -> a text content block
  * a JSON object/array   -> text block + structuredContent
  * "Error: <message>"    -> marks the call as an error
  * "data:image/png;base64,..." -> an image content block
Handlers tagged ``game_thread=True`` (the default) are always invoked on the
game thread, so they may call ``unreal.*`` directly."""

import json

import unreal


def object_ref(obj):
    """A compact JSON-safe reference to a UObject."""
    ref = {}
    try:
        ref["name"] = obj.get_name()
    except Exception:  # noqa: BLE001
        ref["name"] = None
    try:
        ref["class"] = obj.get_class().get_name()
    except Exception:  # noqa: BLE001
        ref["class"] = type(obj).__name__
    try:
        ref["path"] = obj.get_path_name()
    except Exception:  # noqa: BLE001
        ref["path"] = None
    if hasattr(obj, "get_actor_label"):
        try:
            ref["label"] = obj.get_actor_label()
        except Exception:  # noqa: BLE001
            pass
    return ref


def json_safe(value):
    """Recursively convert a value (including ``unreal`` structs) to JSON-safe data."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [json_safe(v) for v in value]

    name = type(value).__name__
    if name == "Vector":
        return {"x": value.x, "y": value.y, "z": value.z}
    if name in ("Vector2D", "IntPoint"):
        return {"x": value.x, "y": value.y}
    if name == "Rotator":
        return {"pitch": value.pitch, "yaw": value.yaw, "roll": value.roll}
    if name == "Quat":
        return {"x": value.x, "y": value.y, "z": value.z, "w": value.w}
    if name in ("LinearColor", "Color"):
        return {"r": value.r, "g": value.g, "b": value.b, "a": value.a}
    if name == "Transform":
        rotation = value.rotation
        if hasattr(rotation, "rotator"):
            rotation = rotation.rotator()
        return {
            "location": json_safe(value.translation),
            "rotation": json_safe(rotation),
            "scale": json_safe(value.scale3d),
        }
    if name in ("Name", "Text"):
        return str(value)

    try:
        if isinstance(value, (unreal.Array, unreal.Set, unreal.FixedArray)):
            return [json_safe(v) for v in value]
        if isinstance(value, unreal.Map):
            return {str(k): json_safe(v) for k, v in value.items()}
    except Exception:  # noqa: BLE001
        pass

    try:
        if isinstance(value, unreal.Object):
            return object_ref(value)
    except Exception:  # noqa: BLE001
        pass

    try:
        return str(value)
    except Exception:  # noqa: BLE001
        return repr(value)


def to_json(value):
    return json.dumps(json_safe(value), indent=2, ensure_ascii=False)


class ToolContext:
    def __init__(self, settings):
        self.unreal = unreal
        self.settings = settings

    def run_on_game_thread(self, fn, *args, **kwargs):
        from . import gamethread

        return gamethread.run_on_game_thread(fn, *args, **kwargs)

    def log(self, message):
        unreal.log("[FunplayMCP] %s" % message)

    def debug(self, message):
        if self.settings.debug_logging_enabled:
            unreal.log("[FunplayMCP] %s" % message)

    # -- result helpers ----------------------------------------------------
    @staticmethod
    def ok(value):
        return to_json(value)

    @staticmethod
    def text(message):
        return str(message)

    @staticmethod
    def err(message):
        return "Error: " + str(message)

    @staticmethod
    def tool_error(code, message, data=None):
        payload = {"success": False, "code": code, "error": str(message)}
        if data is not None:
            payload["data"] = json_safe(data)
        return to_json(payload)
