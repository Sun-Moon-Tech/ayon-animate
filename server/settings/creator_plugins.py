
from ayon_server.settings import (
    BaseSettingsModel,
    SettingsField,
    task_types_enum
)

class CreateRenderPluginModel(BaseSettingsModel):
    enabled: bool = SettingsField(True, title="Enabled")
    active_on_create: bool = SettingsField(True, title="Active by default")
    mark_for_review: bool = SettingsField(False, title="Review by default")
    include_reference_pip: bool = SettingsField(False, title="Include reference PiP by default")
    reference_pip_tasks: list[str] = SettingsField(
        default_factory=list,
        title="Include reference PiP",
        description="List of tasks that will include a PiP burnin by default. Can also be toggled in publisher settings.",
        enum_resolver=task_types_enum
    )
    default_variants: list[str] = SettingsField(
        default_factory=list,
        title="Default Variants"
    )

class AnimateCreatorPlugins(BaseSettingsModel):
    RenderCreator: CreateRenderPluginModel = SettingsField(
        title="Create Render",
        default_factory=CreateRenderPluginModel,
    )

DEFAULT_CREATE_SETTINGS = {
    "RenderCreator": {
        "enabled": True,
        "active_on_create": True,
        "mark_for_review": False,
        "include_reference_pip" : False,
        "reference_pip_tasks": [
            "Blocking"
        ],
        "default_variants": [
            "Main"
        ]
    }
}