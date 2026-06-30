from ayon_server.settings import BaseSettingsModel, SettingsField

class PublishPlugins(BaseSettingsModel):
    """Publish Plugins Settings."""
    swf_tasks: list[str] = SettingsField(
        default_factory=list,
        title="SWF Tasks"
    )

DEFAULT_PUBLISH_SETTINGS = {
    "swf_tasks": ["Animation"]
}
