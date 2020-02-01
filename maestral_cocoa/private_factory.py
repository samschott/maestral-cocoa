# -*- coding: utf-8 -*-
"""
@author: Sam Schott  (ss2151@cam.ac.uk)

(c) Sam Schott; This work is licensed under a Creative Commons
Attribution-NonCommercial-NoDerivs 2.0 UK: England & Wales License.

"""
from travertino.size import at_least

from toga.platform import get_platform_factory
from toga_cocoa.libs import *
from toga_cocoa.keys import toga_key, Key
from toga_cocoa.app import App as TogaApp
from toga_cocoa.widgets.base import Widget
from toga_cocoa.widgets.switch import Switch as TogaSwitch
from toga_cocoa.widgets.label import Label as TogaLabel
from toga_cocoa.widgets.button import Button as TogaButton
from toga_cocoa.widgets.selection import TogaPopupButton
from toga_cocoa.widgets.selection import Selection as TogaSelection
from toga_cocoa.widgets.multilinetextinput import MultilineTextInput as TogaMultilineTextInput
from toga_cocoa.factory import *

from .private_constants import (
    WORD_WRAP, CHARACTER_WRAP, CLIP, TRUNCATE_HEAD, TRUNCATE_MIDDLE, TRUNCATE_TAIL,
    NSButtonTypeMomentaryPushIn,NSFocusRingTypeNone, NSControlState,
    NSSquareStatusItemLength,
    ON, OFF, MIXED,
)

NSWorkspace = ObjCClass('NSWorkspace')
NSVisualEffectView = ObjCClass('NSVisualEffectView')
NSMutableAttributedString = ObjCClass('NSMutableAttributedString')
NSStatusBar = ObjCClass('NSStatusBar')
NSColorSpace = ObjCClass('NSColorSpace')

shared_workspace = NSWorkspace.sharedWorkspace

NSVisualEffectBlendingModeBehindWindow = 0
NSVisualEffectStateActive = 1
NSCompositeSourceOver = 2
NSUTF8StringEncoding = 4
NSImageLeading = 7

NSTextEncodingNameDocumentOption = 'TextEncodingName'
NSImageNameFollowLinkFreestandingTemplate = 'NSFollowLinkFreestandingTemplate'


# ==== icons =============================================================================

class IconForPath:
    """Reimplements toga.Icon but provides the icon for the file / folder type
    instead of loading an icon from the file content."""

    def __init__(self, interface, path):
        self.interface = interface
        self.interface._impl = self
        self.path = path

    @property
    def native(self):
        # always return a new pointer since an old one may be invalidated
        # icons are cached by AppKit anyways
        return shared_workspace.iconForFile(str(self.path))


# ==== labels ============================================================================

def _attributed_str_from_html(raw_html, font=None):
    """Converts html to a NSAttributed string using the system font family and color."""

    html_value = '<span style="font-family: \'{0}\'; font-size: {1}; color: {2}">{3}</span>'
    font_family = font.fontName if font else '-apple-system'
    font_size = font.pointSize if font else 13
    color = NSColor.labelColor.colorUsingColorSpace(NSColorSpace.deviceRGBColorSpace)
    color_str = f'rgb({color.redComponent*255},{color.blueComponent*255},{color.greenComponent*255})'
    html_value = html_value.format(font_family, font_size, color_str, raw_html)
    nsstring = NSString(at(html_value))
    data = nsstring.dataUsingEncoding(NSUTF8StringEncoding)
    attr_str = NSMutableAttributedString.alloc().initWithHTML(
        data,
        documentAttributes=None,
    )
    return attr_str


class Label(TogaLabel):
    """Reimplements toga_cocoa.Label with text wrapping."""

    _toga_to_cocoa_linebreakmode = {
        WORD_WRAP: 0,
        CHARACTER_WRAP: 1,
        CLIP: 2,
        TRUNCATE_HEAD: 3,
        TRUNCATE_TAIL: 4,
        TRUNCATE_MIDDLE: 5,
    }

    def create(self):
        super().create()
        self.native.brawsBackground = False

    def set_linebreak_mode(self, value):
        self.native.cell.lineBreakMode = self._toga_to_cocoa_linebreakmode[value]

    def rehint(self):
        if self.interface.linebreak_mode in (WORD_WRAP, CHARACTER_WRAP):
            availableLabelWidth = self.interface.style.width
            if availableLabelWidth:
                self.native.preferredMaxLayoutWidth = availableLabelWidth
        content_size = self.native.intrinsicContentSize()
        self.interface.intrinsic.width = at_least(content_size.width)
        self.interface.intrinsic.height = at_least(content_size.height)


class RichLabel(Widget):
    """A multiline text view with html support. Rehint is only a hack for now.
    Using the layout manager of NSTextView does not work well since it generally returns
    a too small height for a given width."""

    def create(self):
        self.native = NSTextView.alloc().init()
        self.native.impl = self
        self.native.interface = self.interface

        self.native.drawsBackground = False
        self.native.editable = False
        self.native.selectable = True
        self.native.textContainer.lineFragmentPadding = 0

        self.native.bezeled = False

        # Add the layout constraints
        self.add_constraints()

    def set_html(self, value):
        attr_str = _attributed_str_from_html(value, self.native.font)
        self.native.textStorage.setAttributedString(attr_str)
        self.rehint()

    def set_font(self, value):
        if value:
            self.native.font = value._impl.native

    def rehint(self):
        self.interface.intrinsic.width = at_least(self.interface.MIN_WIDTH)
        self.interface.intrinsic.height = at_least(self.interface.MIN_HEIGHT)


class RichMultilineTextInput(TogaMultilineTextInput):
    """A scrollable text view with html support."""

    def set_html(self, value):
        attr_str = _attributed_str_from_html(value, self.text.font)
        self.text.textStorage.setAttributedString(attr_str)


# ==== buttons ===========================================================================

class FollowLinkButton(TogaButton):
    """A styled button to follow a link (file or url)"""

    def create(self):
        super().create()
        self.native.showsBorderOnlyWhileMouseInside = True
        self.native.bordered = False
        self.native.buttonType = NSButtonTypeMomentaryPushIn
        self.native.bezelStyle = NSRecessedBezelStyle
        self.native.image = NSImage.imageNamed(NSImageNameFollowLinkFreestandingTemplate).resizeTo(11)
        self.native.imagePosition = NSImageLeading
        self.native.alignment = NSTextAlignment(LEFT)
        self.native.focusRingType = NSFocusRingTypeNone

    def set_label(self, label):
        self.native.title = ' {}'.format(self.interface.label)


class Switch(TogaSwitch):
    """Reimplements toga_cocoa.Switch but allows *programmatic* setting of
    an intermediate state."""

    _to_cocoa = {OFF: 0, MIXED: -1, ON: 1}
    _to_toga = {0: OFF, -1: MIXED, 1: ON}

    def __init__(self, interface):
        super().__init__(interface)
        self.native.allowsMixedState = True
        self.native.autoresizingMask = NSViewMaxYMargin | NSViewMaxYMargin

    def set_state(self, value):
        self.native.state = self._to_cocoa[value]

    def get_state(self):
        return self._to_toga[self.native.state]

    def set_font(self, value):
        if value:
            self.native.font = value._impl.native

    def rehint(self):
        content_size = self.native.intrinsicContentSize()
        self.interface.intrinsic.height = content_size.height
        self.interface.intrinsic.width = at_least(content_size.width)


class Selection(TogaSelection):
    def create(self):
        self.native = TogaPopupButton.alloc().init()
        self.native.interface = self.interface

        self.native.translatesAutoresizingMaskIntoConstraints = False

        self.native.target = self.native
        self.native.action = SEL('onSelect:')

        self.add_constraints()


# ==== layout widgets ====================================================================

class VibrantBox(Widget):
    """A box with macOS vibrancy."""

    def create(self):
        self.native = NSVisualEffectView.new()
        self.native.state = NSVisualEffectStateActive
        self.native.blendingMode = NSVisualEffectBlendingModeBehindWindow
        self.native.material = self.interface.material
        self.native.wantsLayer = True

        # Add the layout constraints
        self.add_constraints()

    def set_material(self, material):
        self.native.material = material

    def rehint(self):
        content_size = self.native.intrinsicContentSize()
        self.interface.intrinsic.width = at_least(content_size.width)
        self.interface.intrinsic.height = at_least(content_size.height)


# ==== menus and status bar ==============================================================

class TogaMenuItem(NSMenuItem):
    @objc_method
    def onPress_(self, obj) -> None:
        if self.interface.action:
            self.interface.action(self.interface)


class MenuItem:
    def __init__(self, interface):
        self.interface = interface
        self.native = TogaMenuItem.alloc().init()

        self.native._impl = self
        self.native.interface = self.interface
        self.native.target = self.native
        self.native.action = SEL('onPress:')

    def set_enabled(self, enabled):
        self.native.enabled = enabled

    def set_icon(self, icon):
        if icon:
            factory = get_platform_factory()
            icon = icon.bind(factory)
            nsimage = icon.native.resizeTo(16)
            self.native.image = nsimage
        else:
            self.native.image = None

    def set_label(self, label):
        self.native.title = label

    def set_submenu(self, menu_impl):
        if menu_impl:
            self.native.submenu = menu_impl.native
            self.native.enabled = True
        else:
            self.native.submenu = None

    def set_action(self, action):
        pass

    def set_checked(self, yes):
        self.native.state = NSControlState(yes)


class MenuItemSeparator:
    def __init__(self, interface):
        self.interface = interface
        self.native = NSMenuItem.separatorItem()
        self.native.autoenablesItems = False


class TogaMenu(NSMenu):

    @objc_method
    def menuWillOpen_(self, obj) -> None:
        self._impl._visible = True

    @objc_method
    def menuDidClose_(self, obj) -> None:
        self._impl._visible = False


class Menu:

    def __init__(self, interface):
        self.interface = interface
        self._visible = False

        self.native = TogaMenu.alloc().init()
        self.native.autoenablesItems = False

        self.native._impl = self
        self.native.interface = self.interface
        self.native.delegate = self.native

    def add_item(self, item_impl):
        self.native.addItem(item_impl.native)

    def remove_item(self, item_impl):
        self.native.removeItem(item_impl.native)

    @property
    def visible(self):
        return self._visible


# ==== StatusBarItem =====================================================================

class StatusBarItem:
    MARGIN = 2

    def __init__(self, interface):
        self.interface = interface
        self.native = NSStatusBar.systemStatusBar.statusItemWithLength(NSSquareStatusItemLength)
        self.size = NSStatusBar.systemStatusBar.thickness

    def set_icon(self, icon):
        factory = get_platform_factory()
        icon = icon.bind(factory)
        nsimage = icon.native.resizeTo(self.size - 2*self.MARGIN)
        nsimage.template = True
        self.native.button.image = icon.native

    def set_menu(self, menu_impl):
        self.native.menu = menu_impl.native

# ==== Application =======================================================================


class KeyBoardApp(NSApplication):
    @objc_method
    def sendEvent_(self, event) -> None:
        if event.type == NSKeyDown:
            toga_event = toga_key(event)
            if toga_event == {'key': Key.X, 'modifiers': {Key.MOD_1}}:
                self.sendAction_to_from_(SEL('cut:'), None, self)
            elif toga_event == {'key': Key.C, 'modifiers': {Key.MOD_1}}:
                self.sendAction_to_from_(SEL('copy:'), None, self)
            elif toga_event == {'key': Key.V, 'modifiers': {Key.MOD_1}}:
                self.sendAction_to_from_(SEL('paste:'), None, self)
            elif toga_event == {'key': Key.Z, 'modifiers': {Key.MOD_1}}:
                self.sendAction_to_from_(SEL('undo:'), None, self)
            elif toga_event == {'key': Key.Z, 'modifiers': {Key.SHIFT, Key.MOD_1}}:
                self.sendAction_to_from_(SEL('redo:'), None, self)
            elif toga_event == {'key': Key.A, 'modifiers': {Key.MOD_1}}:
                self.sendAction_to_from_(SEL('selectAll:'), None, self)

        send_super(__class__, self, 'sendEvent:', event)


class SystemTrayApp(TogaApp):

    _MAIN_WINDOW_CLASS = None

    def create(self):
        self.native = KeyBoardApp.sharedApplication
        super().create()

    def select_file(self):
        pass
