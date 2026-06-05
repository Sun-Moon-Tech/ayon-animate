# -*- coding: utf-8 -*-
"""Close PS after publish. For Webpublishing only."""
import pyblish.api

from ayon_animate import api as animate


class CloseFLA(pyblish.api.ContextPlugin):
    """Close FLA after publish. For Webpublishing only.
    """

    order = pyblish.api.IntegratorOrder + 14
    label = "Close FLA"
    optional = True
    active = True

    hosts = ["animate"]
    targets = ["automated"]

    def process(self, context):
        self.log.info("CloseFLA")

        stub = animate.stub()
        self.log.info("Shutting down FLA")
        stub.save()
        stub.close()
        self.log.info("FLA closed")
