
from ayon_server.settings import (
    BaseSettingsModel,
    SettingsField,
    task_types_enum
)

class CreateRenderPluginModel(BaseSettingsModel):
    enabled: bool = SettingsField(True, title="Enabled")
    active_on_create: bool = SettingsField(True, title="Active by default")
    mark_for_review: bool = SettingsField(False, title="Review by default")
    include_reference_pip: bool = SettingsField(
        False,
        title="Reference PiP by default",
        description="Whether to enable reference picture-in-picture by default.",
    )
    tasks_to_include_pip: list[str] = SettingsField(
        default_factory=list,
        title="Tasks to include PiP",
        description="List of tasks that will include a reference picture-in-picture burnin by default, if not enabled globally by <i>Reference PiP by default</i>.",
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
        "mark_for_review": True,
        "include_reference_pip" : False,
        "tasks_to_include_pip": [
            "Blocking"
        ],
        "default_variants": [
            "Main"
        ]
    }
}