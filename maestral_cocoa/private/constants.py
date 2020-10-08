# -*- coding: utf-8 -*-

# system imports
from enum import Enum


OFF = 0
MIXED = 1
ON = 2

CLIP = 0
TRUNCATE_HEAD = 1
TRUNCATE_MIDDLE = 2
TRUNCATE_TAIL = 3

WORD_WRAP = 10
CHARACTER_WRAP = 11


class VisualEffectMaterial(Enum):
    Titlebar = 3  # The material for a window’s titlebar
    Menu = 5  # The material for menus.
    Popover = 6  # The material for the background of popover windows
    Sidebar = 7  # The material for the background of window sidebars
    HeaderView = 10  # The material for in-line header or footer views
    Sheet = 11  # The material for the background of sheet windows
    WindowBackground = 12  # The material for the background of opaque windows
    HUDWindow = 13  # The material for the background of heads-up display (HUD) windows
    FullScreenUI = (
        15  # The material for the background of a full-screen modal interface
    )
    ToolTip = 17  # The material for the background of a tool tip
    ContentBackground = 18  # The material for the background of opaque content
    UnderWindowBackground = 21  # The material for under a window's background
    UnderPageBackground = 22  # The material for the area behind the pages of a document


class ImageTemplate(Enum):
    FollowLink = 0
    InvalidData = 1
    Refresh = 2
    Reveal = 3
    StopProgress = 4
