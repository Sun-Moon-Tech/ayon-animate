"""Public API

Anything that isn't defined here is INTERNAL and unreliable for external use.

"""

from .launch_logic import stub

from .pipeline import (
    AnimateHost,
    ls,
    containerise
)
from .plugin import (
    AnimateLoader,
    get_unique_layer_name
)


from .lib import (
    maintained_selection,
    isolated_layers_visibility,
)

__all__ = [
    # launch_logic
    "stub",

    # pipeline
    "AnimateHost",
    "ls",
    "containerise",

    # Plugin
    "AnimateLoader",
    "get_unique_layer_name",

    # lib
    "maintained_selection",
    "isolated_layers_visibility",
]
