from ayon_server.settings import BaseSettingsModel, SettingsField
from .workfile_builder import WorkfileBuilderPlugin


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

DEFAULT_ANIMATE_SETTING = {
    "auto_install_extension": True,
    "workfile_builder": {
        "create_first_version": True,
        "custom_templates": []
    }
}
