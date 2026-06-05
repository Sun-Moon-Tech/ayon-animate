import re

from ayon_core.lib import BoolDef
from ayon_core.pipeline import (
    Creator,
    CreatedInstance,
    CreatorError
)
from ayon_core.lib import prepare_template_data
from ayon_core.pipeline.create import PRODUCT_NAME_ALLOWED_SYMBOLS
from ayon_animate import api
from ayon_animate.api.pipeline import cache_and_get_instances
from ayon_animate.lib import FLAutoCreator, clean_product_name
import os

# Class is probably going to take a lot of work to switch from image to animate's png seq.
# Likely workflow will be: export image seq and swf from Animate. Swf will be autocreated as one instance, png seq will be used as an inbetween step via ffmpeg
# in order to publish either mp4s or pngs depending on the created instance. Animate doesn't have a way to export mp4s directly, so ffmpeg is the only option. 

class RenderCreator(Creator):
    """Creates image instance for publishing.

    Result of 'image' instance is image of all visible layers, or image(s) of
    selected layers.
    """
    identifier = "render"
    label = "Render"
    product_base_type = "render"
    product_type = product_base_type
    description = "Render creator"
    settings_category = "animate"

    # Settings
    default_variants = ""
    mark_for_review = True
    active_on_create = True
    
    def create(self, product_name_from_ui, data, pre_create_data):
        stub = api.stub()  # only after Animate is up
        self.host_trace("Creating render instance")

        product_type = data.get("productType")
        self.host_trace(f"Product type from data: {product_type}")

        if not product_type:
            product_type = self.product_base_type
            self.host_trace(f"Product type not found in data, using default: {product_type}")

        product_name = clean_product_name(product_name_from_ui)
        data_update = {
            "productName": product_name,
        }
        data.update(data_update)
        
        mark_for_review = (pre_create_data.get("mark_for_review") or
                            self.mark_for_review)
        self.host_trace(f"Mark for review: {mark_for_review}")
        creator_attributes = {"mark_for_review": mark_for_review}
        data.update({"creator_attributes": creator_attributes})

        if not self.active_on_create:
            data["active"] = False

        new_instance = CreatedInstance(
            product_base_type=self.product_base_type,
            product_type=product_type,
            product_name=product_name,
            data=data,
            creator=self,
        )
        self.host_trace(f"Created instance with id {new_instance.get('instance_id')}")
        self.host_trace(f"Instance data: {new_instance.data_to_store()}")

        stub.imprint(new_instance.get("instance_id"),
                        new_instance.data_to_store())
        self._add_instance_to_context(new_instance)
        self.host_trace("Instance imprinted and added to context")


    def host_trace(self, message):
        return api.stub().host_trace(message)
 
    def collect_instances(self):
        for instance_data in cache_and_get_instances(self):
            # legacy instances have family=='image'
            creator_id = (instance_data.get("creator_identifier") or
                          instance_data.get("family"))

            if creator_id == self.identifier:
                instance_data = self._handle_legacy(instance_data)
                instance = CreatedInstance.from_existing(
                    instance_data, self
                )
                self._add_instance_to_context(instance)

    def update_instances(self, update_list):
        self.log.debug("update_list:: {}".format(update_list))
        for created_inst, _changes in update_list:
            if created_inst.get("layer"):
                # not storing PSItem layer to metadata
                created_inst.pop("layer")
            api.stub().imprint(created_inst.get("instance_id"),
                               created_inst.data_to_store())

    def remove_instances(self, instances):
        for instance in instances:
            self.host.remove_instance(instance)
            self._remove_instance_from_context(instance)

    def get_pre_create_attr_defs(self):
        output = [
            BoolDef("use_selection", default=False,
                    label="Create only for selected"),
            BoolDef("create_multiple",
                    default=False,
                    label="Create separate instance for each selected"),
            BoolDef("use_layer_name",
                    default=False,
                    label="Use layer name in product"),
            BoolDef(
                "mark_for_review",
                label="Create separate review",
                default=False
            )
        ]
        return output

    def get_instance_attr_defs(self):
        return [
            BoolDef(
                "mark_for_review",
                label="Review"
            )
        ]

    def get_detail_description(self):
        return """Creator for Render instances

        Main publishable item in Animate will be of `Render` product.
        Result of this item (instance) is picture that could be loaded and
        used in another DCCs (for example as single layer in composition in
        AfterEffects, reference in Maya etc).

        There are couple of options what to publish:
        - separate render per selected layer (or group of layers)
        - one render for all selected layers
        - all visible layers (groups) flattened into single render

        In most cases you would like to keep `Create only for selected`
        toggled on and select what you would like to publish.
        Toggling this option off will allow you to create instance for all
        visible layers without a need to select them explicitly.

        Use 'Create separate instance for each selected' to create separate
        renders per selected layer (group of layers).

        'Use layer name in product' will explicitly add layer name into
        product name. Position of this name is configurable in
        `project_settings/global/tools/creator/product_name_profiles`.
        If layer placeholder ({layer}) is not used in `product_name_profiles`
        but layer name should be used (set explicitly in UI or implicitly if
        multiple renders should be created), it is added in capitalized form
        as a suffix to product name.

        Each render could have its separate review created if necessary via
        `Create separate review` toggle.
        But more use case is to use separate `review` instance to create review
        from all published items.
        """

    def _handle_legacy(self, instance_data):
        """Converts old instances to new format."""
        if not instance_data.get("members"):
            instance_data["members"] = [instance_data.get("uuid")]

        if instance_data.get("uuid"):
            # uuid not needed, replaced with unique instance_id
            api.stub().remove_instance(instance_data.get("uuid"))
            instance_data.pop("uuid")

        if not instance_data.get("task"):
            instance_data["task"] = self.create_context.get_current_task_name()

        if not instance_data.get("variant"):
            instance_data["variant"] = ""

        return instance_data

    def _clean_highlights(self, stub, item):
        return (
            item
            .replace(stub.PUBLISH_ICON, "")
            .replace(stub.LOADED_ICON, "")
        )

    def get_dynamic_data(
        self,
        project_name,
        folder_entity,
        task_entity,
        variant,
        host_name,
        instance=None,
        project_entity=None,
        product_type=None,
    ):
        if instance is not None:
            layer_name = instance.get("layer_name")
            if layer_name:
                return {"layer": layer_name}
        return {"layer": "{layer}"}
