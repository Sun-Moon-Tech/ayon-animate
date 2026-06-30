from ayon_server.settings import BaseSettingsModel, SettingsField
from .workfile_builder import WorkfileBuilderPlugin
from .publish_plugins import PublishPlugins, DEFAULT_PUBLISH_SETTINGS


class AnimateSettings(BaseSettingsModel):
    """Animate Project Settings."""

    auto_install_extension: bool = SettingsField(
        False,
        title="Install AYON Extension",
        description="Triggers pre-launch hook which installs extension."
    )

    workfile_builder: WorkfileBuilderPlugin = SettingsField(
        default_factory=WorkfileBuilderPlugin,
        title="Workfile Builder"
    )

    publish: PublishPlugins = SettingsField(
        default_factory=PublishPlugins,
        title="Publish Plugins Settings"
    )

DEFAULT_ANIMATE_SETTING = {
    "auto_install_extension": True,
    "workfile_builder": {
        "create_first_version": True,
        "custom_templates": []
    },
    "publish": DEFAULT_PUBLISH_SETTINGS
}