import pyblish.api
from ayon_core.pipeline import publish
from ayon_animate import api as animate


class ExtractDisableAccessibility(pyblish.api.ContextPlugin):
    """Turn off 'Make Movie Accessible' before saving/exporting.
    Avoids Animate's accessibility error popup during publish.
    """

    order = publish.Extractor.order - 0.495
    label = "Disable Document Accessibility"
    hosts = ["animate"]

    def process(self, context):
        result = animate.stub().eval(
            "(function(){try{var d=fl.getDocumentDOM();"
            "if(!d){return false;}d.silent=true;return true;}"
            "catch(e){return false;}})()"
        )
        if str(result).strip().lower() != "true":
            self.log.warning(
                "Could not disable accessibility on the active document"
            )
