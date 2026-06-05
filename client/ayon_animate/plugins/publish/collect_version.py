"""
Requires:
    context -> version

Provides:
    instance -> version - incremented latest published workfile version

"""
import pyblish.api


class CollectVersion(pyblish.api.InstancePlugin):
    """Collect version for publishable instances.

    Used to synchronize version from workfile to all publishable instances:
        - image (manually created or color coded)
        - review
        - workfile

    Dev comment:
    Explicit collector created to control this from single place and not from
    3 different.

    Workfile set here explicitly as version might to be forced from latest + 1
    because of Webpublisher.
    (This plugin must run after CollectPublishedVersion!)
    """
    # QUESTION can we move the logic to the 'CollectPublishedVersion'?
    order = pyblish.api.CollectorOrder - 0.35

    label = "Collect Version"

    hosts = ["animate"]
    families = ["image", "review", "workfile"]
    settings_category = "animate"
    targets = ["automated"]    
    
    def process(self, instance):
        # if not instance.data.get("version"):
        #     raise ValueError("Version is not set on instance. This plugin requires version to be set before. Instance Data: {}".format(instance.data))
        workfile_version = instance.context.data["version"]
        self.log.debug(f"Applying version {workfile_version}")
        instance.data["version"] = workfile_version
