import os

from ayon_core.pipeline import publish
from ayon_animate import api as animate


class ExtractSourcesReview(
    publish.Extractor,
    publish.ColormanagedPyblishPluginMixin
):
    """
        Produce a flattened or sequence image files from all 'image' instances.

        These files are then used by global `ExtractReview` and
        `ExtractThumbnail` to create reviews with globally controllable
        configuration.

        If no 'image' instance is created, it produces flattened image from
        all visible layers.

        It can also create separate reviews per `image` instance if necessary.
        (toggle on an instance in Publisher UI).

        'review' family could be used in other steps as a reference, as it
        contains flattened image by default. (Eg. artist could load this
        review as a single item and see full image. In most cases 'image'
        product type is separated by layers to better usage in animation
        or comp.)
    """

    label = "Extract Sources for Review"
    hosts = ["animate"]
    families = ["review"]
    settings_category = "animate"
    order = publish.Extractor.order - 0.28

    # Extract Options
    # make_image_sequence = None

    def process(self, instance):
        staging_dir = self.staging_dir(instance)
        self.log.info("Outputting image to {}".format(staging_dir))

        stub = animate.stub()
        host_name = instance.context.data["hostName"]
        project_settings = instance.context.data["project_settings"]
    
        self.output_seq_filename = os.path.splitext(
            stub.get_active_document_name())[0] + ".mp4"

        additional_repre = {
            "name": "mp4",
            "ext": "mp4",
            "frameStart": instance.data["frameStart"],
            "frameEnd": instance.data["frameEnd"],
            "fps": instance.data["fps"],
            "stagingDir": staging_dir,
            "tags": ["review"],
        }
        product_base_type = instance.data.get("productBaseType")
        if not product_base_type:
            product_base_type = instance.data["productType"]
        if product_base_type == "render":
            self._attach_review_tag(instance)

            additional_repre["output_name"] = "mp4"
            additional_repre["files"] = self.output_seq_filename

        instance.data["stagingDir"] = staging_dir

        self.log.info(f"Extracted {instance} to {staging_dir}")

    def _attach_review_tag(self, instance):
        """Searches for repre for which mp4 review should be created.

        "mp4" representation is preferred.

        """
        mp4_source_repre = None
        for repre in instance.data["representations"]:
            if repre["name"] == "mp4":
                mp4_source_repre = repre
                repre["tags"].append("review")
                break

        if not mp4_source_repre:
            repre = instance.data["representations"][0]
            repre["tags"].append("review")
