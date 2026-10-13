import re

from ayon_core.pipeline import get_representation_path
from ayon_animate import api as animate

class AssetLoader(animate.AnimateLoader):
    """Load assets

    Loads asset from another file as an instanced symbol
    """

    product_base_types = {"workfile"}