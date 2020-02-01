# -*- coding: utf-8 -*-
"""
@author: Sam Schott  (ss2151@cam.ac.uk)

(c) Sam Schott; This work is licensed under a Creative Commons
Attribution-NonCommercial-NoDerivs 2.0 UK: England & Wales License.

"""
import sys
import os.path as osp

_root = getattr(sys, '_MEIPASS', osp.dirname(osp.abspath(__file__)))

APP_ICON_PATH = osp.join(_root, 'maestral.icns')
TRAY_ICON_PATH = osp.join(_root, 'systray-{}.pdf')
FACEHOLDER_PATH = osp.join(_root, 'faceholder.pdf')
