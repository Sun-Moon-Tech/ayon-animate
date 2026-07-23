from ayon_server.settings import (
    BaseSettingsModel,
    SettingsField,
    task_types_enum
)



class RenderSourceProfile(BaseSettingsModel):
    _layout = "expanded"
    task_types: list[str] = SettingsField(
        default_factory=list,
        title="Task types",
        enum_resolver=task_types_enum
    )
    export_swf: bool = SettingsField(True, title="Export SWF")
    render_source: str = SettingsField(
        "",
        title="Render source",
        description="Render source for the given task type(s). Expects a value from: movie, h264, png_sequence"
    )

class ExtractRenderSettings(BaseSettingsModel):
    """Render settings for the Publish tool in Animate."""

    swf_tasks: list[str] = SettingsField(
        default_factory=list,
        title="SWF tasks",
        description="List of tasks to render swfs on publish.",
        enum_resolver=task_types_enum
    )

    render_source: str = SettingsField(
        "",
        title="Default render source",
        description="Default render source if not specified for the given task. Expects a value from: movie, h264, png_sequence"
    )

    include_alpha_in_mov : bool = SettingsField(
        False,
        title="Export QuickTime with alpha channel",
        description="Controls whether to include the alpha channel when exporting QuickTime movies through the publisher. NOTE: it's recommended to have this turned off if not using the QuickTime files, as this will cause mp4 exports to appear with a black background."
    )


    task_render_profiles: list[RenderSourceProfile] = SettingsField(
        default_factory=list,
        title="Task profiles",
        description="Profiles for task-specific render settings."
    ) 


class PublishPlugins(BaseSettingsModel):
    ExtractRender: ExtractRenderSettings = SettingsField(
        default_factory=ExtractRenderSettings,
        title="Extract Render Settings"
    )

DEFAULT_PUBLISH_SETTINGS = {
    "ExtractRender": {
        "swf_tasks": ["Animation"],
        "render_source" : "h264",
        "include_alpha_in_mov" : False,
        "task_render_profiles" : [
            {
                "task_types":["Animation"],
                "export_swf":True,
                "render_source":"h264"
            },
        ]
    }
}