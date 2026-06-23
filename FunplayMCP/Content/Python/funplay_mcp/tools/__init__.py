"""Tool modules. Each submodule exposes ``register(registry)``."""

from . import (
    actors,
    assets,
    blueprints,
    components,
    editor_state,
    execution,
    files,
    guidance,
    levels,
    materials,
    play,
    screenshots,
    selection,
)

_MODULES = (
    guidance,
    execution,
    actors,
    components,
    assets,
    blueprints,
    materials,
    levels,
    play,
    screenshots,
    selection,
    editor_state,
    files,
)


def register_all(registry):
    for module in _MODULES:
        module.register(registry)
