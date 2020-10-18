# -*- coding: utf-8 -*-
"""
@author: Sam Schott  (ss2151@cam.ac.uk)

(c) Sam Schott; This work is licensed under a Creative Commons
Attribution-NonCommercial-NoDerivs 2.0 UK: England & Wales License.

"""
import sys
import os.path as osp

try:
    from importlib.resources import files
except ImportError:
    from importlib_resources import files


def resource_path(name):
    folder = getattr(sys, "_MEIPASS", files("maestral_cocoa") / "resources")
    return osp.join(folder, name)


APP_ICON_PATH = resource_path("maestral.icns")
TRAY_ICON_PATH = resource_path("systray-{}.pdf")
FACEHOLDER_PATH = resource_path("faceholder.pdf")
