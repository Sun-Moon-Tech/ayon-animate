from typing import Any

from ayon_server.addons import BaseServerAddon

from .settings import (
    DEFAULT_ANIMATE_SETTING,
    AnimateSettings,
)


class Animate(BaseServerAddon):
    settings_model = AnimateSettings

    async def get_default_settings(self):
        settings_model_cls = self.get_settings_model()
        return settings_model_cls(**DEFAULT_ANIMATE_SETTING)

