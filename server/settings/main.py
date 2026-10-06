from ayon_server.settings import BaseSettingsModel, SettingsField
from .creator_plugins import AnimateCreatorPlugins, DEFAULT_CREATE_SETTINGS
from .publish_plugins import PublishPlugins, DEFAULT_PUBLISH_SETTINGS
from .workfile_builder import WorkfileBuilderPlugin

class AnimateSettings(BaseSettingsModel):
    """Animate Project Settings."""

    auto_install_extension: bool = SettingsField(
        False,
        title="Install AYON Extension",
        description="Triggers pre-launch hook which installs extension."
    )

    create: AnimateCreatorPlugins = SettingsField(
        default_factory=AnimateCreatorPlugins,
        title="Creator plugins"
    )

    publish: PublishPlugins = SettingsField(
        default_factory=PublishPlugins,
        title="Publish plugins"
    )

    workfile_builder: WorkfileBuilderPlugin = SettingsField(
        default_factory=WorkfileBuilderPlugin,
        title="Workfile Builder"
    )

DEFAULT_ANIMATE_SETTING = {
    "auto_install_extension": True,
    "create": DEFAULT_CREATE_SETTINGS,
    "publish": DEFAULT_PUBLISH_SETTINGS,
    "workfile_builder": {
        "create_first_version": True,
        "custom_templates": []
    }
}