from ayon_server.settings import BaseSettingsModel, SettingsField

class ExtractRenderSettings(BaseSettingsModel):
    """Animate Render Settings."""

    swf_tasks: list[str] = SettingsField(
        default_factory=list,
        title="Swf Tasks",
        description="List of tasks to render swfs on publish."
    )

class PublishPlugins(BaseSettingsModel):
    ExtractRender: ExtractRenderSettings = SettingsField(
        default_factory=ExtractRenderSettings,
        title="Extract Render Settings"
    )
DEFAULT_PUBLISH_SETTINGS = {
    "ExtractRender": {
        "swf_tasks": ["Animation"]
}
}