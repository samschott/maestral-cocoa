# -*- coding: utf-8 -*-
"""
@author: Sam Schott  (ss2151@cam.ac.uk)

(c) Sam Schott; This work is licensed under a Creative Commons
Attribution-NonCommercial-NoDerivs 2.0 UK: England & Wales License.

"""
import sys
import os.path as osp
import pkg_resources


def resource_path(name):
    folder = getattr(
        sys, "_MEIPASS", pkg_resources.resource_filename("maestral_cocoa", "resources")
    )
    return osp.join(folder, name)


extension = "pdf" if sys.platform == "darwin" else "svg"

APP_ICON_PATH = resource_path("maestral.icns")
TRAY_ICON_PATH = resource_path("systray-{}")
FACEHOLDER_PATH = resource_path(f"faceholder.{extension}")
