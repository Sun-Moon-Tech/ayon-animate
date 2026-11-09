from ayon_server.settings import (
    BaseSettingsModel,
    SettingsField,
    task_types_enum
)
from ayon_server.types import ColorRGB_hex

pip_position_enum = [
    {"value": "top_left", "label": "Top Left"},
    {"value": "top_right", "label": "Top Right"},
    {"value": "btm_left", "label": "Bottom Left"},
    {"value": "btm_right", "label": "Bottom Right"},
]

class RenderSourceProfile(BaseSettingsModel):
    _layout = "expanded"
    task_types: list[str] = SettingsField(
        default_factory=list,
        title="Task types",
        enum_resolver=task_types_enum
    )
    export_swf: bool = SettingsField(True, title="Export SWF")

class PictureInPictureSettings(BaseSettingsModel):
    """Settings for picture-in-picture (PiP) burnin when publishing Animate tasks."""
    pip_position : str = SettingsField(
        default_factory=list,
        title="PiP Position",
        description="Position of the PiP burnin on the screen.",
        enum_resolver=lambda: pip_position_enum,
    )

    pip_scale : float = SettingsField(
        1,
        title="PiP Scale",
        description="Target scale for the PiP burnin."
    )

    pip_offset : int = SettingsField(
        1,
        title="PiP Offset",
        description="Value for how much the PiP burnin will be offset from the corner, in pixels."
    )

class ExtractRenderSettings(BaseSettingsModel):
    """Render settings for the Publish tool in Animate."""

    swf_tasks: list[str] = SettingsField(
        default_factory=list,
        title="SWF tasks",
        description="List of tasks to render swfs on publish.",
        enum_resolver=task_types_enum
    )

    include_alpha_in_mov : bool = SettingsField(
        False,
        title="QuickTime alpha",
        description="Controls whether to include the alpha channel when exporting QuickTime movies through the publisher. NOTE: it's recommended to have this turned off if not using the QuickTime files, as this will cause mp4 exports to appear with a black background."
    )

    png_bg_colour : ColorRGB_hex = SettingsField(
        "#FFFFFF",
        title="PNG background colour",
        description="Background colour used for PNG sequences, replaces the background colour from the Animate scene."
    )

    task_render_profiles: list[RenderSourceProfile] = SettingsField(
        default_factory=list,
        title="Task profiles",
        description="Profiles for task-specific render settings."
    )

    picture_in_picture: PictureInPictureSettings = SettingsField(
        default_factory=PictureInPictureSettings,
        title="Picture-In-Picture (PiP) Settings"        
    ) 


class PublishPlugins(BaseSettingsModel):
    ExtractRender: ExtractRenderSettings = SettingsField(
        default_factory=ExtractRenderSettings,
        title="Extract Render Settings"
    )

DEFAULT_PUBLISH_SETTINGS = {
    "ExtractRender": {
        "swf_tasks": ["Animation"],
        "include_alpha_in_mov" : False,
        "png_bg_colour" : "#666666",
        "task_render_profiles": [
            {
                "task_types": ["Animation"],
                "export_swf": True
            }
        ],
        "picture_in_picture": {
            "pip_position" : "top_left",
            "pip_scale" : 0.25,
            "pip_offset" : 10
        }
    }
}