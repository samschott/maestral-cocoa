# -*- coding: utf-8 -*-

try:
    from importlib.resources import path
except ImportError:
    from importlib_resources import path  # type: ignore


def resource_path(name: str) -> str:
    """Returns the resource path as a string. Extracts the resource if necessary."""
    return str(path("maestral_cocoa.resources", name).__enter__())


APP_ICON_PATH = resource_path("maestral.icns")
FACEHOLDER_PATH = resource_path("faceholder.pdf")
