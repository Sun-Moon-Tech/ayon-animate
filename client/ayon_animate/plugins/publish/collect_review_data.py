"""
Requires:
    - (ayon-core) CollectContextEntities
    context -> frameStart
    context -> frameEnd
    context -> fps

Provides:
    instance     -> family ("review")
"""

import pyblish.api


class CollectReviewData(pyblish.api.InstancePlugin):
    """Adds data needed for review."""

    label = "Collect Review data"
    hosts = ["animate"]

    order = pyblish.api.CollectorOrder - 0.4

    settings_category = "animate"
    families = ["review"]

    def process(self, instance):
        context = instance.context
        if not context.data.get("frameStart"):
            frame_start = 0
        else:
            frame_start = context.data["frameStart"]
        if not context.data.get("frameEnd"):
            frame_end = 1
        else:
            frame_end = context.data["frameEnd"]
        if not context.data.get("fps"):
            fps = 25
        else:
            fps = context.data["fps"]

        instance.data["frameStart"] = frame_start
        instance.data["frameEnd"] = frame_end
        instance.data["fps"] = fps
