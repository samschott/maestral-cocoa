# -*- coding: utf-8 -*-

# system imports
import os.path as osp

# external imports
from toga import SECTION_BREAK
from toga.constants import LEFT, TRANSPARENT
from toga.platform import get_platform_factory
from toga_cocoa.libs import (
    ObjCClass, NSColor, NSString, at, NSTextView, NSRecessedBezelStyle,
    NSTextAlignment, NSViewMaxYMargin, NSMenuItem, SEL, objc_method, NSKeyDown, NSMenu,
    NSApplication, send_super, NSObject, NSApplicationActivationPolicyAccessory, NSBundle,
    NSImage, NSImageInterpolationHigh, NSGraphicsContext, NSRect, NSPoint, NSBezierPath,
    NSTextField
)
from toga_cocoa.colors import native_color
from toga_cocoa.keys import toga_key, Key
from toga_cocoa.app import App as TogaApp
from toga_cocoa.widgets.base import Widget
from toga_cocoa.widgets.switch import Switch as TogaSwitch, at_least
from toga_cocoa.widgets.button import Button as TogaButton
from toga_cocoa.widgets.selection import Selection as TogaSelection
from toga_cocoa.widgets.scrollcontainer import ScrollContainer as TogaScrollContainer
from toga_cocoa.window import Window as TogaWindow
from toga_cocoa.widgets.multilinetextinput import MultilineTextInput as TogaMultilineTextInput
from toga_cocoa.factory import *  # noqa: F401,F406
from rubicon.objc import NSMakeSize, NSMakeRect

# local imports
from . import dialogs
from .constants import (
    NSButtonTypeMomentaryPushIn, NSFocusRingTypeNone, NSControlState,
    NSSquareStatusItemLength, NSWindowAnimationBehaviorDefault,
    NSWindowAnimationBehaviorAlertPanel, NSUTF8StringEncoding, NSImageLeading,
    NSVisualEffectStateActive, NSVisualEffectBlendingModeBehindWindow,
    NSCompositeSourceOver, NSImageNameFollowLinkFreestandingTemplate,
    NSImageNameInvalidDataFreestandingTemplate, NSImageNameRefreshFreestandingTemplate,
    NSImageNameRevealFreestandingTemplate, NSImageNameStopProgressFreestandingTemplate
)
from ...constants import (
    WORD_WRAP, CHARACTER_WRAP, CLIP, TRUNCATE_HEAD, TRUNCATE_MIDDLE, TRUNCATE_TAIL,
    ON, OFF, MIXED, ImageTemplate
)


NSWorkspace = ObjCClass('NSWorkspace')
NSVisualEffectView = ObjCClass('NSVisualEffectView')
NSMutableAttributedString = ObjCClass('NSMutableAttributedString')
NSStatusBar = ObjCClass('NSStatusBar')
NSColorSpace = ObjCClass('NSColorSpace')
NSAutoreleasePool = ObjCClass('NSAutoreleasePool')


# ==== icons =============================================================================

class Icon:
    """Reimplements toga.Icon but provides the icon for the file / folder type
    instead of loading an icon from the file content."""

    _to_cocoa_template = {
        None: None,
        ImageTemplate.Refresh: NSImageNameRefreshFreestandingTemplate,
        ImageTemplate.FollowLink: NSImageNameFollowLinkFreestandingTemplate,
        ImageTemplate.Reveal: NSImageNameRevealFreestandingTemplate,
        ImageTemplate.InvalidData: NSImageNameInvalidDataFreestandingTemplate,
        ImageTemplate.StopProgress: NSImageNameStopProgressFreestandingTemplate
    }

    def __init__(self, interface, path=None, for_path=None, template=None):
        self.interface = interface
        self.interface._impl = self
        self.path = path
        self.for_path = for_path
        self.template = template

        self._native = None

    @property
    def native(self):

        if self._native:
            return self._native

        if self.path:
            self._native = NSImage.alloc().initWithContentsOfFile(self.path)
            return self._native

        elif self.for_path:
            # always return a new pointer since an old one may be invalidated
            # icons are cached by AppKit anyways
            path = str(self.for_path)
            if osp.exists(path):
                return NSWorkspace.sharedWorkspace.iconForFile(path)
            else:
                _, extension = osp.splitext(path)
                return NSWorkspace.sharedWorkspace.iconForFileType(extension)

        elif self.template:
            cocoa_template = self._to_cocoa_template[self.template]
            self._native = NSImage.imageNamed(cocoa_template)
            return self._native


# ==== labels ============================================================================

def attributed_str_from_html(raw_html, font=None, color=None):
    """Converts html to a NSAttributed string using the system font family and color."""

    html_value = """
    <span style="font-family: '{0}'; font-size: {1}; color: {2}">
    {3}
    </span>
    """
    font_family = font.fontName if font else 'system-ui'
    font_size = font.pointSize if font else 13
    color = color or NSColor.labelColor
    c = color.colorUsingColorSpace(NSColorSpace.deviceRGBColorSpace)
    c_str = f'rgb({c.redComponent * 255},{c.blueComponent * 255},{c.greenComponent * 255})'
    html_value = html_value.format(font_family, font_size, c_str, raw_html)
    nsstring = NSString(at(html_value))
    data = nsstring.dataUsingEncoding(NSUTF8StringEncoding)
    attr_str = NSMutableAttributedString.alloc().initWithHTML(
        data,
        documentAttributes=None,
    )
    return attr_str


class Label(Widget):
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
        self.native = NSTextField.labelWithString('')
        self.native.impl = self
        self.native.interface = self.interface

        # Add the layout constraints
        self.add_constraints()

    def set_alignment(self, value):
        self.native.alignment = NSTextAlignment(value)

    def set_color(self, value):
        if value:
            self.native.textColor = native_color(value)

    def set_font(self, font):
        if font:
            self.native.font = font.bind(self.interface.factory).native

    def set_text(self, value):
        self.native.stringValue = value

    def set_linebreak_mode(self, value):
        self.native.cell.lineBreakMode = self._toga_to_cocoa_linebreakmode[value]

    def set_background_color(self, color):
        if color in (None, TRANSPARENT):
            self.native.backgroundColor = NSColor.clearColor
            self.native.drawsBackground = False
        else:
            self.native.backgroundColor = native_color(color)
            self.native.drawsBackground = True

    def rehint(self):

        if self.interface.style.width:
            self.native.preferredMaxLayoutWidth = self.interface.style.width

        content_size = self.native.intrinsicContentSize()

        if self.interface.style.width:
            self.interface.intrinsic.width = at_least(content_size.width)
            self.interface.intrinsic.height = at_least(content_size.height)
        else:
            self.interface.intrinsic.width = at_least(0)
            self.interface.intrinsic.height = at_least(content_size.height)


class RichLabel(Widget):
    """A multiline text view with html support. Rehint is only a hack for now.
    Using the layout manager of NSTextView does not work well since it generally returns
    a too small height for a given width."""

    def create(self):
        self._color = None
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
        attr_str = attributed_str_from_html(value, color=self._color)
        self.native.textStorage.setAttributedString(attr_str)
        self.rehint()

    def set_font(self, font):
        native_font = font.bind(self.interface.factory).native
        attr_str = attributed_str_from_html(self.interface.html, color=self._color,
                                            font=native_font)
        self.native.textStorage.setAttributedString(attr_str)
        self.rehint()

    def set_color(self, value):
        if value:
            self._color = native_color(value)

        # update html
        self.set_html(self.interface.html)

    def rehint(self):
        # force layout and get layout rect
        self.native.layoutManager.glyphRangeForTextContainer(self.native.textContainer)
        rect = self.native.layoutManager.usedRectForTextContainer(self.native.textContainer)

        self.interface.intrinsic.width = at_least(rect.size.width)
        self.interface.intrinsic.height = rect.size.height


class RichMultilineTextInput(TogaMultilineTextInput):
    """A scrollable text view with html support."""

    def set_html(self, value):
        attr_str = attributed_str_from_html(value, font=self.text.font)
        self.text.textStorage.setAttributedString(attr_str)


# ==== buttons ===========================================================================

class FreestandingIconButton(TogaButton):
    """A styled button to follow a link (file or url)"""

    def create(self):
        super().create()
        self.native.showsBorderOnlyWhileMouseInside = True
        self.native.bordered = False
        self.native.buttonType = NSButtonTypeMomentaryPushIn
        self.native.bezelStyle = NSRecessedBezelStyle
        self.native.imagePosition = NSImageLeading
        self.native.alignment = NSTextAlignment(LEFT)
        self.native.focusRingType = NSFocusRingTypeNone

    def set_label(self, label):
        self.native.title = ' {}'.format(self.interface.label)

    def set_icon(self, icon_iface):
        factory = get_platform_factory()
        icon = icon_iface.bind(factory)
        self.native.image = icon.native.resizeTo(11)


class Switch(TogaSwitch):
    """Reimplements toga_cocoa.Switch but allows *programmatic* setting of
    an intermediate state."""

    _to_cocoa = {OFF: 0, MIXED: -1, ON: 1}
    _to_toga = {0: OFF, -1: MIXED, 1: ON}

    def create(self):
        super().create()
        self.native.allowsMixedState = True
        self.native.autoresizingMask = NSViewMaxYMargin | NSViewMaxYMargin

    def set_state(self, value):
        self.native.state = self._to_cocoa[value]

    def get_state(self):
        return self._to_toga[self.native.state]

    def set_font(self, font):
        if font:
            self.native.font = font.bind(self.interface.factory).native

    def rehint(self):
        content_size = self.native.intrinsicContentSize()
        self.interface.intrinsic.height = 20
        self.interface.intrinsic.width = at_least(content_size.width)


class Selection(TogaSelection):
    """Reimplements toga_cocoa.Selection to allow section breaks."""

    def add_item(self, item):
        if isinstance(item, tuple):
            icon_iface, label = item
        else:
            icon_iface = None
            label = item

        if label == SECTION_BREAK:
            self.native.menu.addItem(NSMenuItem.separatorItem())

        else:
            self.native.addItemWithTitle(label)

            if icon_iface:
                factory = get_platform_factory()
                icon = icon_iface.bind(factory)
                icon = icon.native.resizeTo(16)
                self.native.lastItem.image = icon

    def select_item(self, item):
        if isinstance(item, tuple):
            item = item[1]
        self.native.selectItemWithTitle(item)

    def rehint(self):
        content_size = self.native.intrinsicContentSize()
        # increase height by 1 px for better icon alignment
        self.interface.intrinsic.height = content_size.height + 1
        self.interface.intrinsic.width = at_least(max(self.interface.MIN_WIDTH, content_size.width))


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


class ScrollContainer(TogaScrollContainer):

    def set_bounds(self, x, y, width, height):
        super().set_bounds(x, y, width, height)
        if not self.interface.horizontal:
            self.interface.content._impl.native.frame = NSMakeRect(
                0, 0,
                width, self.interface.content.layout.height
            )
        elif not self.interface.vertical:
            self.interface.content._impl.native.frame = NSMakeRect(
                0, 0,
                self.interface.content.layout.width, height
            )
        else:
            self.interface.content._impl.native.frame = NSMakeRect(
                0, 0,
                self.interface.content.layout.width, self.interface.content.layout.height
            )


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
        if self.interface.on_open:
            self.interface.on_open(self.interface)

    @objc_method
    def menuDidClose_(self, obj) -> None:
        self._impl._visible = False
        if self.interface.on_close:
            self.interface.on_close(self.interface)


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

    def insert_item(self, index, item_impl):
        self.native.insertItem(item_impl.native, atIndex=index)

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
        nsimage = icon.native.resizeTo(self.size - 2 * self.MARGIN)
        nsimage.template = True
        self.native.button.image = icon.native

    def set_menu(self, menu_impl):
        self.native.menu = menu_impl.native

# ==== Application =======================================================================


class CocoaSystemTrayApp(NSApplication):

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
            else:
                send_super(__class__, self, 'sendEvent:', event)
        else:
            send_super(__class__, self, 'sendEvent:', event)


class SystemTrayAppDelegate(NSObject):
    @objc_method
    def applicationWillTerminate_(self, sender):
        if self.interface.app.on_exit:
            self.interface.app.on_exit(self.interface.app)

    @objc_method
    def applicationDidFinishLaunching_(self, notification):
        self.native.activateIgnoringOtherApps(True)


class SystemTrayApp(TogaApp):

    _MAIN_WINDOW_CLASS = None

    def create(self):
        self.native = CocoaSystemTrayApp.sharedApplication
        self.native.activationPolicy = NSApplicationActivationPolicyAccessory

        factory = get_platform_factory()
        self.interface.icon.bind(factory)
        self.native.applicationIconImage = self.interface.icon._impl.native

        self.resource_path = osp.dirname(osp.dirname(NSBundle.mainBundle.bundlePath))

        self.appDelegate = SystemTrayAppDelegate.alloc().init()
        self.appDelegate.impl = self
        self.appDelegate.interface = self.interface
        self.appDelegate.native = self.native
        self.native.delegate = self.appDelegate

        # Call user code to populate the main window
        self.interface.startup()

        # Create the lookup table of menu items,
        # then force the creation of the menus.
        self._menu_items = {}
        self.create_menus()

    def select_file(self):
        pass

    def open_document(self, path):
        pass

    def alert(self, title, message, details, details_title, button_labels, checkbox_text,
              level, icon):

        return dialogs.alert(title, message, details, details_title, button_labels,
                             checkbox_text, level, icon)


class Window(TogaWindow):

    def is_visible(self):
        return bool(self.native.isVisible)

    def center(self):
        self.native.center()

    def force_to_front(self):
        self.native.makeKeyAndOrderFront(None)
        self.native.orderFrontRegardless()
        if self.interface.app:
            self.interface.app._impl.native.activateIgnoringOtherApps(True)

    def show_as_sheet(self, window):
        window._impl.native.beginSheet(self.native, completionHandler=None)

    def hide(self):
        self.native.orderOut(None)

    def close(self):

        if self.native.sheetParent:
            # end sheet session before closing
            self.native.sheetParent.endSheet(self.native)

        self.native.close()

    def set_release_on_close(self, value):
        self.native.releasedWhenClosed = value

    def set_dialog(self, value):

        animation = NSWindowAnimationBehaviorAlertPanel if value else NSWindowAnimationBehaviorDefault
        self.native.animationBehavior = animation
        self.native.level = 3

    def start_modal(self):
        self.show()
        return self.interface.app._impl.native.runModalForWindow(self.native)

    def stop_modal(self, res=0):
        if self.interface.app._impl.native.modalWindow == self.native:
            self.interface.app._impl.native.stopModalWithCode(res)

    # dialogs

    async def save_file_sheet(self, title, message, suggested_filename, file_types):
        return await dialogs.save_file_sheet(self.interface, suggested_filename, title,
                                             message, file_types)

    async def open_file_sheet(self, title, message, initial_directory, file_types,
                              multiselect):
        return await dialogs.open_file_sheet(self.interface, title, message, file_types,
                                             multiselect)

    async def select_folder_sheet(self, title, message, initial_directory, multiselect):
        return await dialogs.select_folder_sheet(self.interface, title, message,
                                                 multiselect)

    async def alert_sheet(self, title, message, details, details_title, button_labels,
                          checkbox_text, level, icon):
        return await dialogs.alert_sheet(self.interface, title, message, details,
                                         details_title, button_labels, checkbox_text,
                                         level, icon)


# ==== helpers ===========================================================================

def apply_round_clipping(image_view_impl: ImageView):
    """Clips an image in a given toga_cocoa.ImageView to a circular mask."""

    pool = NSAutoreleasePool.alloc().init()

    image = image_view_impl.native.image  # get native NSImage

    composed_image = NSImage.alloc().initWithSize(image.size)
    composed_image.lockFocus()

    ctx = NSGraphicsContext.currentContext
    ctx.saveGraphicsState()
    ctx.imageInterpolation = NSImageInterpolationHigh

    image_frame = NSRect(NSPoint(0, 0), image.size)
    clip_path = NSBezierPath.bezierPathWithRoundedRect(
        image_frame,
        xRadius=image.size.width / 2,
        yRadius=image.size.height / 2
    )
    clip_path.addClip()

    zero_rect = NSRect(NSPoint(0, 0), NSMakeSize(0, 0))
    image.drawInRect(
        image_frame,
        fromRect=zero_rect,
        operation=NSCompositeSourceOver,
        fraction=1
    )
    composed_image.unlockFocus()
    ctx.restoreGraphicsState()

    image_view_impl.native.image = composed_image

    pool.drain()
    del pool
