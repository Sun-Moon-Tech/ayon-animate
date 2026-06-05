from pathlib import Path

from ayon_core.pipeline import publish
from ayon_core.pipeline.colorspace import get_remapped_colorspace_from_native
from ayon_core.pipeline.publish import get_instance_staging_dir
from ayon_animate import api as animate


class ExtractLayers(
    publish.Extractor,
    publish.ColormanagedPyblishPluginMixin
):
    """Export layers within the instance layerset to a PSD file.
    
    Layersets can be merged to reduce the number of layers in the output file.
    """

    label = "Extract Layers"
    order = publish.Extractor.order  # Must be after ExtractImage
    hosts = ["photoshop"]
    families = ["image"]
    merge_layersets = False

    def process(self, instance):
        fla_stub = animate.stub()
        native_colorspace = fla_stub.get_color_profile_name()
        self.log.info(f"Document colorspace profile: {native_colorspace}")
        host_name = instance.context.data["hostName"]
        project_settings = instance.context.data["project_settings"]
        host_imageio_settings = project_settings["animate"]["imageio"]
        ayon_colorspace = get_remapped_colorspace_from_native(
            native_colorspace,
            host_name,
            host_imageio_settings,
        )
        self.log.debug(f"ayon_colorspace: {ayon_colorspace}")
        # Duplicate the document to the staging directory
        filepath = Path(
            get_instance_staging_dir(instance),
            fla_stub.get_active_document_name()
        )
        self.log.info(f"Duplicating document to staging directory: {filepath}")
        with fla_stub.duplicate_document(
            filepath
        ):
            # Delete all layers except the instance layerset
            layer = instance.data.get("layer")
            fla_stub.delete_all_layers(
                exclude_layers=[layer],
                exclude_recursive=True
            )

            # Merge all layersets within the instance set
            if self.merge_layersets:
                self.log.info("Merging all layersets within instance set...")
                fla_stub.merge_all_layersets(
                    parent_set=layer.id
                )

            # Dissolve instance layerset
            self.log.info("Dissolving instance layerset...")
            fla_stub.dissolve_layerset(layer.id)

        instance.data["stagingDir"] = filepath.parent
        representations = instance.data.setdefault("representations", [])
        representation = {
            "name": "psd",
            "ext": "psd",
            "files": filepath.name,
            "stagingDir": filepath.parent,
        }
        # inject colorspace data
        self.set_representation_colorspace(
            representation, instance.context,
            colorspace=ayon_colorspace
        )
        self.log.debug(f"Representation: {representation}")
        representations.append(representation)
