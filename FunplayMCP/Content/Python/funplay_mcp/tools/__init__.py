"""Tool modules. Each submodule exposes ``register(registry)``."""

from . import (
    actors,
    assets,
    blueprints,
    components,
    data,
    editor_state,
    effects,
    execution,
    files,
    guidance,
    levels,
    materials,
    organization,
    play,
    procedural,
    reflection,
    screenshots,
    selection,
    umg,
    viewport,
)

_MODULES = (
    guidance,
    reflection,
    execution,
    actors,
    components,
    assets,
    blueprints,
    materials,
    levels,
    play,
    viewport,
    screenshots,
    selection,
    editor_state,
    files,
    procedural,
    organization,
    data,
    umg,
    effects,
)


def register_all(registry):
    for module in _MODULES:
        module.register(registry)
