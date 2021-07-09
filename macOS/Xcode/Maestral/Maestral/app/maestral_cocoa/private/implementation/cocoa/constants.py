# -*- coding: utf-8 -*-

# system imports
from enum import Enum

NSSquareStatusItemLength = -2
NSWindowBelow = -1
NSVisualEffectStateActive = 1
NSVisualEffectBlendingModeBehindWindow = 0
NSFullSizeContentViewWindowMask = 32768
NSLayoutFormatDirectionLeadingToTrailing = 0
NSCompositeSourceOver = 2

NSBezelStyleInline = 15
NSButtonTypeMomentaryPushIn = 7
NSFocusRingTypeNone = 1

NSStackViewGravityBottom = 3
NSUserInterfaceLayoutOrientationVertical = 1

NSWindowAnimationBehaviorDefault = 0
NSWindowAnimationBehaviorAlertPanel = 5


def NSControlState(boolean):
    return {False: 0, True: 1}[boolean]


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


NSVisualEffectMaterial = VisualEffectMaterial

NSUTF8StringEncoding = 4
NSImageLeading = 7

NSTextEncodingNameDocumentOption = "TextEncodingName"

NSImageNameFollowLinkFreestandingTemplate = "NSFollowLinkFreestandingTemplate"
NSImageNameInvalidDataFreestandingTemplate = "NSInvalidDataFreestandingTemplate"
NSImageNameRefreshFreestandingTemplate = "NSRefreshFreestandingTemplate"
NSImageNameRevealFreestandingTemplate = "NSRevealFreestandingTemplate"
NSImageNameStopProgressFreestandingTemplate = "NSStopProgressFreestandingTemplate"
