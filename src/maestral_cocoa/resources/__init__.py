# -*- coding: utf-8 -*-

# system imports
import os.path as osp

try:
    from importlib.resources import files
except ImportError:
    from importlib_resources import files


def resource_path(name):
    return osp.join(files("maestral_cocoa"), "resources", name)


APP_ICON_PATH = resource_path("maestral.icns")
TRAY_ICON_PATH = resource_path("systray-{}.pdf")
FACEHOLDER_PATH = resource_path("faceholder.pdf")
