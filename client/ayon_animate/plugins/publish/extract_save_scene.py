from ayon_core.pipeline import publish
from ayon_animate import api as animate


class ExtractSaveScene(publish.Extractor):
    """Save scene before extraction."""

    order = publish.Extractor.order - 0.49
    label = "Extract Save Scene"
    hosts = ["animate"]
    families = ["workfile"]

    def process(self, instance):
        animate.stub().save()
