"""MCP prompts -- task templates that embed live editor context."""


class PromptProvider:
    def __init__(self, ctx, registry):
        self.ctx = ctx
        self.registry = registry

    def list_prompts(self):
        return [
            {
                "name": "level_review",
                "description": "Review the current level and suggest improvements.",
                "arguments": [],
            },
            {
                "name": "feature_plan",
                "description": "Plan how to build a gameplay feature in this project.",
                "arguments": [
                    {"name": "goal", "description": "What you want to build.", "required": True}
                ],
            },
            {
                "name": "debug_runtime",
                "description": "Help debug a runtime / Play-In-Editor issue from recent logs.",
                "arguments": [
                    {"name": "issue", "description": "The problem you are seeing.", "required": True}
                ],
            },
            {
                "name": "blueprint_actor",
                "description": "Design and scaffold a Blueprint actor.",
                "arguments": [
                    {"name": "goal", "description": "The actor to create.", "required": True}
                ],
            },
        ]

    def get_prompt(self, name, arguments):
        arguments = arguments or {}
        if name == "level_review":
            text = (
                "Review this Unreal level and suggest concrete, prioritized "
                "improvements. Use the funplay-unreal-mcp tools to make changes.\n\n"
                "## Level\n%s\n\n## Actors\n%s"
                % (self._call("get_level_info"), self._call("list_actors"))
            )
        elif name == "feature_plan":
            text = (
                "Plan how to build the following feature in this Unreal project, "
                "then implement it with the funplay-unreal-mcp tools.\n\n"
                "Goal: %s\n\n## Project\n%s"
                % (arguments.get("goal", "(unspecified)"), self._call("get_project_info"))
            )
        elif name == "debug_runtime":
            text = (
                "Help debug this Unreal runtime issue.\n\nIssue: %s\n\n"
                "## Play state\n%s\n\n## Recent log\n%s"
                % (
                    arguments.get("issue", "(unspecified)"),
                    self._call("get_play_state"),
                    self._call("get_output_log", {"max_lines": 120}),
                )
            )
        elif name == "blueprint_actor":
            text = (
                "Design and scaffold a Blueprint actor for: %s\n"
                "Use create_blueprint, add_blueprint_component, set_component_property "
                "and compile_blueprint.\n\n## Project\n%s"
                % (arguments.get("goal", "(unspecified)"), self._call("get_project_info"))
            )
        else:
            return {
                "description": "Unknown prompt.",
                "messages": [
                    {"role": "user", "content": {"type": "text", "text": "Unknown prompt: %s" % name}}
                ],
            }
        return {
            "description": name,
            "messages": [{"role": "user", "content": {"type": "text", "text": text}}],
        }

    def _call(self, tool, args=None):
        try:
            return self.registry.call_tool(tool, args or {})
        except Exception as exc:  # noqa: BLE001
            return "Error: %s" % exc
