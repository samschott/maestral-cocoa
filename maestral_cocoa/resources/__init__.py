# -*- coding: utf-8 -*-
"""
@author: Sam Schott  (ss2151@cam.ac.uk)

(c) Sam Schott; This work is licensed under a Creative Commons
Attribution-NonCommercial-NoDerivs 2.0 UK: England & Wales License.

"""

import pkg_resources


def resource_path(name):
    return pkg_resources.resource_filename('maestral_cocoa', f'resources/{name}')


APP_ICON_PATH = resource_path('maestral.icns')
TRAY_ICON_PATH = resource_path('systray-{}.pdf')
FACEHOLDER_PATH = resource_path('faceholder.pdf')
