from ayon_core.lib import BoolDef, EnumDef, TextDef
from ayon_core.pipeline import (
    Creator,
    CreatedInstance,
    CreatorError
)
from ayon_core.pipeline.create import PRODUCT_NAME_ALLOWED_SYMBOLS
from ayon_animate import api
from ayon_animate.api.pipeline import cache_and_get_instances
from ayon_animate.lib import FLAutoCreator, clean_product_name
import os

# Class is probably going to take a lot of work to switch from image to animate's png seq.
# Likely workflow will be: export image seq and swf from Animate. Swf will be autocreated as one instance, png seq will be used as an inbetween step via ffmpeg
# in order to publish either mp4s or pngs depending on the created instance. Animate doesn't have a way to export mp4s directly, so ffmpeg is the only option. 

FRAME_RANGE_ENUM = [
    {"value": "all", "label": "entire sequence"},
    {"value": "selected", "label": "selection in timeline"},
    {"value": "range", "label": "frame range"},
]

class PNGSequenceCreator(Creator):
    """Renders the current scene as a PNG sequence.
    """
    identifier = "png_sequence"
    label = "PNG sequence"
    product_base_type = "render"
    product_type = product_base_type
    description = """Creates a PNG sequence of the timeline, and uploads the PNGs and a compiled video.
NOTE: This render type does not support audio."""
    settings_category = "animate"

    # Settings
    default_variants = ""
    mark_for_review = True
    active_on_create = True
    pngs_on_create = False

    timeline_length = 0

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
            "productName": product_name
        }
        data.update(data_update)
        
        mark_for_review = (pre_create_data.get("mark_for_review") or
                            self.mark_for_review)
        self.host_trace(f"Mark for review: {mark_for_review}")
        include_pngs = (pre_create_data.get("include_pngs") or False)
        self.host_trace(f"Include PNGs in publish: {include_pngs}")

        # start_frame = (pre_create_data.get("start_frame") or 0)
        # end_frame = (pre_create_data.get("end_frame") or self.get_timeline_length())
        frame_range_type = (pre_create_data.get("frame_range_type") or "all")
        match frame_range_type:
            case "all":
                frame_range = f"1-{self.timeline_length}"
            case "range":
                frame_range = pre_create_data.get("frame_range",f"1-{self.timeline_length}")
            case "selected" : 
                raw_frames = stub.get_selected_frames()
                frame_range = self._frame_range_to_text(raw_frames)
        self.host_trace(f"Frame range: {frame_range}")
            
        creator_attributes = {
            "mark_for_review": mark_for_review,
            "include_pngs" : include_pngs,
            "frame_range" : frame_range,
            }
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
        self.timeline_length = api.stub().get_timeline_length()
        output = [
            BoolDef(
                "mark_for_review",
                label="Mark for review",
                default=self.mark_for_review
            ),
            BoolDef(
                "include_pngs",
                label="Include PNGs in publish",
                default=self.pngs_on_create
            ),
            EnumDef(
                "frame_range_type",
                label="Export frames from",
                items=FRAME_RANGE_ENUM,
            ),
            TextDef(
                "frame_range",
                label="Frame range",
                default=f"1-{self.timeline_length}",
            )
        ]
        return output

    def get_instance_attr_defs(self):
        return [
            BoolDef(
                "mark_for_review",
                label="Mark for review"
            ),
            BoolDef(
                "include_pngs",
                label="Include PNGs in publish",
                default=False
            ),
            TextDef(
                "frame_range",
                label="Frame range",
                default="0",
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

        if not instance_data["creator_attributes"].get("frame_range"):
            start_frame = instance_data["creator_attributes"].get("start_frame",1)
            end_frame = instance_data["creator_attributes"].get("end_frame",self.timeline_length)
            frame_range = [i for i in range(start_frame,end_frame+1)]
            instance_data["creator_attributes"]["frame_range"] = self._frame_range_to_text(frame_range)

        for var_name in ["start_frame","end_frame","render_source"]:
            if instance_data.get(var_name):
                instance_data.pop(var_name)
            if instance_data["creator_attributes"].get(var_name):
                instance_data["creator_attributes"].pop(var_name)

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


    def _frame_range_to_text(self,frame_range):
        frame_list = []
        if frame_range == None:
            raise CreatorError("""
Could not convert frame range as frame range is empty.

If you have 'selection in timeline' selected, make sure the frames are highlighted before trying to
create the PNG sequence product.
            """)
        # check if single frame is present
        if len(frame_range) == 1:
            return str(frame_range[0])
        # iterate to get frame range as clean text
        current_range_start = frame_range[0]
        current_range_end = frame_range[0]
        for frame in frame_range:
            # handle start of list
            if frame == frame_range[0]:
                continue

            # calculate if the range needs to go in the list
            if (frame > current_range_end+1):
                if current_range_start == current_range_end:
                    frame_list.append(current_range_start)
                elif current_range_end == current_range_start+1:
                    frame_list.append(current_range_start)
                    frame_list.append(current_range_end)
                else:
                    frame_list.append(f"{current_range_start}-{current_range_end}")
                # restart range
                current_range_start = frame
            # always set range end to current frame
            current_range_end = frame

            # end of list
            if frame == frame_range[-1]:
                if current_range_start == current_range_end:
                    frame_list.append(current_range_start)
                else:
                    frame_list.append(f"{current_range_start}-{current_range_end}")
        return ",".join(str(f) for f in frame_list)