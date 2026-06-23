"""Tool registry: name/description/inputSchema/handler + core/full profiles.

The registry owns the ``ToolContext`` and decides whether a handler runs on the
game thread. Tool handlers return a single string (see context.py)."""


class ToolRegistry:
    def __init__(self, ctx):
        self.ctx = ctx
        self._tools = {}
        self._order = []

    def register(
        self,
        name,
        description,
        input_schema,
        handler,
        profiles=("full",),
        game_thread=True,
        group="other",
        timeout=60.0,
    ):
        if name in self._tools:
            raise ValueError("duplicate tool name: %s" % name)
        self._tools[name] = {
            "definition": {
                "name": name,
                "description": description,
                "inputSchema": input_schema or {"type": "object", "properties": {}},
            },
            "handler": handler,
            "profiles": tuple(profiles),
            "game_thread": bool(game_thread),
            "group": group,
            "timeout": float(timeout),
        }
        self._order.append(name)

    def get(self, name):
        return self._tools.get(name)

    def has(self, name):
        return name in self._tools

    def names(self):
        return list(self._order)

    def is_allowed(self, name, profile):
        tool = self._tools.get(name)
        if not tool:
            return False
        if self.ctx.settings.is_tool_disabled(name):
            return False
        if profile == "full":
            return True
        return "core" in tool["profiles"]

    def list_tools(self, profile=None):
        profile = profile or self.ctx.settings.tool_profile
        return [
            self._tools[name]["definition"]
            for name in self._order
            if self.is_allowed(name, profile)
        ]

    def call_tool(self, name, args):
        tool = self._tools.get(name)
        if not tool:
            return self.ctx.err("Unknown tool: %s" % name)
        profile = self.ctx.settings.tool_profile
        if not self.is_allowed(name, profile):
            return self.ctx.err(
                "Tool '%s' is not available in the '%s' profile." % (name, profile)
            )
        handler = tool["handler"]
        if not isinstance(args, dict):
            args = {}
        if tool["game_thread"]:
            return self.ctx.run_on_game_thread(
                handler, args, self.ctx, timeout=tool["timeout"]
            )
        return handler(args, self.ctx)

    def catalog(self, profile=None):
        profile = profile or self.ctx.settings.tool_profile
        items = []
        for name in self._order:
            tool = self._tools[name]
            items.append(
                {
                    "name": name,
                    "group": tool["group"],
                    "profiles": list(tool["profiles"]),
                    "exposed": self.is_allowed(name, profile),
                    "disabled": self.ctx.settings.is_tool_disabled(name),
                    "description": tool["definition"]["description"],
                }
            )
        return items

    def exposure_summary(self, profile=None):
        profile = profile or self.ctx.settings.tool_profile
        return {
            "profile": profile,
            "core_count": sum(
                1 for n in self._order if "core" in self._tools[n]["profiles"]
            ),
            "total_count": len(self._order),
            "exposed_count": sum(
                1 for n in self._order if self.is_allowed(n, profile)
            ),
        }
