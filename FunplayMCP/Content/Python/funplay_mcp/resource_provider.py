"""MCP resources -- read-only views over the editor, backed by registry tools."""

from .context import to_json


class ResourceProvider:
    def __init__(self, ctx, registry):
        self.ctx = ctx
        self.registry = registry
        self.server = None  # set by the plugin after construction

    def list_resources(self):
        return [
            _res("unreal://project/context", "Project Context",
                 "Overview of the project, server, and available tools.", "text/markdown"),
            _res("unreal://project/info", "Project Info",
                 "Project name, directory, engine version."),
            _res("unreal://level/current", "Current Level",
                 "Summary of the active level."),
            _res("unreal://actors/list", "Level Actors",
                 "All actors in the current level."),
            _res("unreal://selection/current", "Selection",
                 "Currently selected actors."),
            _res("unreal://tools/catalog", "Tool Catalog",
                 "Every registered tool and its profile/exposure."),
            _res("unreal://logs/recent", "Recent Output Log",
                 "Tail of the editor output log."),
            _res("unreal://interaction/history", "Interaction History",
                 "Recent MCP tool calls handled this session."),
        ]

    def list_resource_templates(self):
        return [
            {
                "uriTemplate": "unreal://actor/{ref}",
                "name": "Actor",
                "description": "Inspect an actor by label, name, or path.",
                "mimeType": "application/json",
            },
            {
                "uriTemplate": "unreal://asset/{path}",
                "name": "Asset",
                "description": "Inspect an asset by content path.",
                "mimeType": "application/json",
            },
        ]

    def read_resource(self, uri):
        text, mime = self._read(uri)
        return {"contents": [{"uri": uri, "mimeType": mime, "text": text}]}

    # -- internals ---------------------------------------------------------
    def _call(self, tool, args=None):
        try:
            return self.registry.call_tool(tool, args or {})
        except Exception as exc:  # noqa: BLE001
            return "Error: %s" % exc

    def _read(self, uri):
        if uri == "unreal://project/context":
            return self._project_context(), "text/markdown"
        if uri == "unreal://project/info":
            return self._call("get_project_info"), "application/json"
        if uri == "unreal://level/current":
            return self._call("get_level_info"), "application/json"
        if uri == "unreal://actors/list":
            return self._call("list_actors"), "application/json"
        if uri == "unreal://selection/current":
            return self._call("get_selection"), "application/json"
        if uri == "unreal://tools/catalog":
            return self._call("get_tool_catalog"), "application/json"
        if uri == "unreal://logs/recent":
            return self._call("get_output_log", {"max_lines": 200}), "application/json"
        if uri == "unreal://interaction/history":
            history = self.server.interaction_log() if self.server else []
            return to_json(history), "application/json"
        if uri.startswith("unreal://actor/"):
            ref = uri[len("unreal://actor/"):]
            return self._call("get_actor_info", {"actor": ref}), "application/json"
        if uri.startswith("unreal://asset/"):
            path = uri[len("unreal://asset/"):]
            return self._call("get_asset_info", {"asset_path": path}), "application/json"
        return "Error: Unknown resource: %s" % uri, "text/plain"

    def _project_context(self):
        summary = self.registry.exposure_summary()
        lines = [
            "# Funplay MCP -- Unreal Project Context",
            "",
            "## Project",
            "```json",
            self._call("get_project_info"),
            "```",
            "",
            "## Current Level",
            "```json",
            self._call("get_level_info"),
            "```",
            "",
            "## Tools",
            "- Profile: `%s`" % summary["profile"],
            "- Exposed: %d of %d registered (%d core)"
            % (summary["exposed_count"], summary["total_count"], summary["core_count"]),
            "",
            "Call `get_tool_catalog` to list everything, or `execute_python` for "
            "anything no dedicated tool covers.",
        ]
        return "\n".join(lines)


def _res(uri, name, description, mime="application/json"):
    return {"uri": uri, "name": name, "description": description, "mimeType": mime}
