# -*- coding: utf-8 -*-
from .nodes import FacialCustomization

NODE_CLASS_MAPPINGS = {
    "FacialCustomization": FacialCustomization,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "FacialCustomization": "Facial Customization",
}

WEB_DIRECTORY = "./js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
