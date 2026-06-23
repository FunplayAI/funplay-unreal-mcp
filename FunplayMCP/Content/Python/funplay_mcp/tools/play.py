"""Play tools: request Play-In-Editor / Simulate / stop, and query play state.

These editor requests are async -- honored on a later tick, not immediately."""

import unreal

from .common import level_subsystem, schema


def _play_in_editor(args, ctx):
    level_subsystem().editor_request_begin_play()
    return ctx.text("Requested Play-In-Editor.")


def _stop_play_in_editor(args, ctx):
    level_subsystem().editor_request_end_play()
    return ctx.text("Requested stop of Play-In-Editor.")


def _simulate_in_editor(args, ctx):
    level_subsystem().editor_play_simulate()
    return ctx.text("Requested Simulate-In-Editor.")


def _get_play_state(args, ctx):
    return ctx.ok({"is_in_play": bool(level_subsystem().is_in_play_in_editor())})


def register(reg):
    reg.register(
        "play_in_editor",
        "Request Play-In-Editor (PIE). Async -- honored on a later editor tick.",
        schema({}),
        _play_in_editor,
        profiles=("full",),
        group="play",
    )
    reg.register(
        "stop_play_in_editor",
        "Request to stop the current Play-In-Editor / Simulate session. Async.",
        schema({}),
        _stop_play_in_editor,
        profiles=("full",),
        group="play",
    )
    reg.register(
        "simulate_in_editor",
        "Request Simulate-In-Editor. Async -- honored on a later editor tick.",
        schema({}),
        _simulate_in_editor,
        profiles=("full",),
        group="play",
    )
    reg.register(
        "get_play_state",
        "Report whether the editor is currently in a Play/Simulate session.",
        schema({}),
        _get_play_state,
        profiles=("core", "full"),
        group="play",
    )
