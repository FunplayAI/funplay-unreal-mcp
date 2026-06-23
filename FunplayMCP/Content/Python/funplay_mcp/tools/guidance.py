"""Discovery / help tools."""

from .common import prop, schema


def _get_tool_catalog(args, ctx):
    group = args.get("group")
    items = ctx.registry.catalog()
    if group:
        items = [i for i in items if i["group"] == group]
    return ctx.ok(
        {
            "profile": ctx.settings.tool_profile,
            "summary": ctx.registry.exposure_summary(),
            "tools": items,
        }
    )


def register(reg):
    reg.register(
        "get_tool_catalog",
        "List every registered tool with its category, profiles (core/full), and "
        "whether it is currently exposed. Useful for discovering capabilities.",
        schema(
            {
                "group": prop(
                    "string",
                    "Optional category filter (e.g. 'actors', 'assets', 'levels').",
                )
            }
        ),
        _get_tool_catalog,
        profiles=("core", "full"),
        game_thread=False,
        group="guidance",
    )
