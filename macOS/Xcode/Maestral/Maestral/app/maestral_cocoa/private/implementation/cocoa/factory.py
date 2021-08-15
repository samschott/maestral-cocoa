# -*- coding: utf-8 -*-

# system imports
import os.path as osp
import platform

# external imports
from travertino.size import at_least
from rubicon.objc import (
    NSMakeSize,
    NSZeroPoint,
    CGRectMake,
    ObjCClass,
    objc_method,
    SEL,
    at,
)
from toga.constants import LEFT, TRANSPARENT
from toga_cocoa.libs import (
    NSColor,
    NSString,
    NSTextView,
    NSTextAlignment,
    NSRecessedBezelStyle,
    NSViewMaxYMargin,
    NSMenuItem,
    NSMenu,
    NSApplication,
    NSObject,
    NSApplicationActivationPolicyAccessory,
    NSApplicationActivationPolicyRegular,
    NSImage,
    NSImageInterpolationHigh,
    NSGraphicsContext,
    NSRect,
    NSPoint,
    NSBezierPath,
    NSTextField,
    NSPopUpButton,
    NSOpenPanel,
    NSFileHandlingPanelOKButton,
    NSCompositingOperationCopy,
    NSURL,
)
from toga_cocoa.colors import native_color
from toga_cocoa.keys import cocoa_key
from toga_cocoa.app import App as TogaApp
from toga_cocoa.widgets.base import Widget
from toga_cocoa.widgets.switch import Switch as TogaSwitch
from toga_cocoa.widgets.button import Button as TogaButton
from toga_cocoa.window import Window as TogaWindow
from toga_cocoa.window import WindowDelegate as TogaWindowDeletage
from toga_cocoa.widgets.multilinetextinput import (
    MultilineTextInput as TogaMultilineTextInput,
)
from toga_cocoa.factory import ImageView
from toga_cocoa.factory import *  # noqa: F401,F406

# local imports
from . import dialogs
from .constants import (
    NSButtonTypeMomentaryPushIn,
    NSFocusRingTypeNone,
    NSControlState,
    NSSquareStatusItemLength,
    NSWindowAnimationBehaviorDefault,
    NSWindowAnimationBehaviorAlertPanel,
    NSUTF8StringEncoding,
    NSImageLeading,
    NSCompositeSourceOver,
    NSImageNameFollowLinkFreestandingTemplate,
    NSImageNameInvalidDataFreestandingTemplate,
    NSImageNameRefreshFreestandingTemplate,
    NSImageNameRevealFreestandingTemplate,
    NSImageNameStopProgressFreestandingTemplate,
)
from ...constants import (
    WORD_WRAP,
    CHARACTER_WRAP,
    CLIP,
    TRUNCATE_HEAD,
    TRUNCATE_MIDDLE,
    TRUNCATE_TAIL,
    ON,
    OFF,
    MIXED,
    ImageTemplate,
)


NSWorkspace = ObjCClass("NSWorkspace")
NSVisualEffectView = ObjCClass("NSVisualEffectView")
NSMutableAttributedString = ObjCClass("NSMutableAttributedString")
NSStatusBar = ObjCClass("NSStatusBar")
NSColorSpace = ObjCClass("NSColorSpace")

NSNormalWindowLevel = 0
NSModalPanelWindowLevel = 8


macos_version, *_ = platform.mac_ver()


# ==== icons ===========================================================================


class Icon:
    """Reimplements toga.Icon but provides the icon for the file / folder type
    instead of loading an icon from the file content."""

    _to_cocoa_template = {
        None: None,
        ImageTemplate.Refresh: NSImageNameRefreshFreestandingTemplate,
        ImageTemplate.FollowLink: NSImageNameFollowLinkFreestandingTemplate,
        ImageTemplate.Reveal: NSImageNameRevealFreestandingTemplate,
        ImageTemplate.InvalidData: NSImageNameInvalidDataFreestandingTemplate,
        ImageTemplate.StopProgress: NSImageNameStopProgressFreestandingTemplate,
    }

    def __init__(self, interface, path=None, for_path=None, template=None):
        self.interface = interface
        self.interface._impl = self
        self.path = str(path) if path else None
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
            cocoa_template = Icon._to_cocoa_template[self.template]
            self._native = NSImage.imageNamed(cocoa_template)
            return self._native


# ==== labels ==========================================================================


def attributed_str_from_html(raw_html, font=None, color=None):
    """Converts html to a NSAttributed string using the system font family and color."""

    html_value = """
    <span style="font-family: '{0}'; font-size: {1}; color: {2}">
    {3}
    </span>
    """
    font_family = font.fontName if font else "system-ui"
    font_size = font.pointSize if font else 13
    color = color or NSColor.labelColor
    c = color.colorUsingColorSpace(NSColorSpace.deviceRGBColorSpace)
    c_str = (
        f"rgb({c.redComponent * 255},{c.blueComponent * 255},{c.greenComponent * 255})"
    )
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
        self.native = NSTextField.labelWithString("")
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
        self.native.cell.lineBreakMode = Label._toga_to_cocoa_linebreakmode[value]

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
    """A multiline text view with html support."""

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
        attr_str = attributed_str_from_html(
            self.interface.html, color=self._color, font=native_font
        )
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
        rect = self.native.layoutManager.usedRectForTextContainer(
            self.native.textContainer
        )

        self.interface.intrinsic.width = at_least(rect.size.width)
        self.interface.intrinsic.height = rect.size.height


# ==== text input ======================================================================


class RichMultilineTextInput(TogaMultilineTextInput):
    """A scrollable text view with html support."""

    def set_html(self, value):
        attr_str = attributed_str_from_html(value, font=self.text.font)
        self.text.textStorage.setAttributedString(attr_str)


# ==== buttons =========================================================================


class FreestandingIconButton(TogaButton):
    """A styled button with an icon."""

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
        self.native.title = " {}".format(self.interface.label)

    def set_icon(self, icon_iface):
        icon = icon_iface.bind(self.interface.factory)
        if self.interface.style.height > 0:
            icon_size = self.interface.style.height
        else:
            icon_size = 16
        self.native.image = resize_image_to(icon.native, icon_size)
        self.native.image.template = True


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


class FileChooserTarget(NSObject):
    @objc_method
    def onSelect_(self, obj) -> None:
        if self.impl.native.indexOfSelectedItem == 2:

            self.impl.native.selectItemAtIndex(0)

            panel = NSOpenPanel.alloc().init()
            panel.title = self.interface.dialog_title
            panel.message = self.interface.dialog_message
            panel.canChooseFiles = self.interface.select_files
            panel.canChooseDirectories = self.interface.select_folders
            panel.canCreateDirectories = True
            panel.resolvesAliases = True
            panel.allowsMultipleSelection = False
            panel.directoryURL = NSURL.fileURLWithPath(
                osp.dirname(self.interface.current_selection)
            )
            panel.prompt = "Select"

            def completion_handler(r: int) -> None:

                if r == NSFileHandlingPanelOKButton:
                    self.impl.set_current_selection(str(panel.URL.path))

                    if self.interface.on_select:
                        self.interface.on_select(self.interface)

            panel.beginSheetModalForWindow(
                self.interface.window._impl.native, completionHandler=completion_handler
            )


class FileSelectionButton(Widget):
    def create(self):
        self.native = NSPopUpButton.alloc().init()
        self.target = FileChooserTarget.alloc().init()
        self.target.interface = self.interface
        self.target.impl = self
        self.native.target = self.target
        self.native.action = SEL("onSelect:")

        self._current_selection = ""
        self.native.addItemWithTitle("")
        self.native.menu.addItem(NSMenuItem.separatorItem())
        self.native.addItemWithTitle("Choose...")

        self.add_constraints()

    def get_current_selection(self):
        return self._current_selection

    def set_current_selection(self, path):

        if not osp.exists(path) and not self.interface.select_files:
            # use generic folder icon
            image = NSWorkspace.sharedWorkspace.iconForFile("/usr")
        else:
            # use actual icon for file / folder, falls back to generic file icon
            image = NSWorkspace.sharedWorkspace.iconForFile(path)

        item = self.native.itemAtIndex(0)
        item.title = path if self.interface.show_full_path else osp.basename(path)
        item.image = resize_image_to(image, 16)
        self._current_selection = path

    def set_on_select(self, handler):
        pass

    def set_select_files(self, value):
        pass

    def set_select_folders(self, value):
        pass

    def set_dialog_title(self, value):
        pass

    def set_show_full_path(self, value):
        item = self.native.itemAtIndex(0)
        path = self.interface.current_selection
        item.title = path if value else osp.basename(path)

    def set_dialog_message(self, value):
        pass

    def rehint(self):
        content_size = self.native.intrinsicContentSize()
        self.interface.intrinsic.height = content_size.height + 1
        self.interface.intrinsic.width = at_least(
            max(self.interface.MIN_WIDTH, content_size.width)
        )


# ==== menus and status bar ============================================================


class TogaMenuItem(NSMenuItem):
    @objc_method
    def onPress_(self, obj) -> None:
        if self.interface.action:
            self.interface.action(self.interface)


class MenuItem:
    def __init__(self, interface):
        self.interface = interface
        self.native = TogaMenuItem.alloc().init()
        self.native.interface = self.interface
        self.native.impl = self
        self.native.target = self.native
        self.native.action = SEL("onPress:")

    def set_enabled(self, enabled):
        self.native.enabled = enabled

    def set_icon(self, icon):
        if icon:
            icon = icon.bind(self.interface.factory)
            nsimage = resize_image_to(icon.native, 16)
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

    def set_shortcut(self, shortcut):
        if shortcut:
            key, modifier = cocoa_key(shortcut)

            self.native.keyEquivalent = key
            if modifier:
                self.native.keyEquivalentModifierMask = modifier


class MenuItemSeparator:
    def __init__(self, interface):
        self.interface = interface
        self.native = NSMenuItem.separatorItem()
        self.native.retain()


class TogaMenu(NSMenu):
    @objc_method
    def menuWillOpen_(self, obj) -> None:
        self.impl._visible = True
        if self.interface.on_open:
            self.interface.on_open(self.interface)

    @objc_method
    def menuDidClose_(self, obj) -> None:
        self.impl._visible = False
        if self.interface.on_close:
            self.interface.on_close(self.interface)


class Menu:
    def __init__(self, interface):
        self.interface = interface
        self._visible = False

        self.native = TogaMenu.alloc().init()
        self.native.autoenablesItems = False

        self.native.impl = self
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


# ==== StatusBarItem ===================================================================


class StatusBarItem:
    MARGIN = 2

    def __init__(self, interface):
        self.interface = interface
        self.native = NSStatusBar.systemStatusBar.statusItemWithLength(
            NSSquareStatusItemLength
        )
        self.size = NSStatusBar.systemStatusBar.thickness

    def set_icon(self, icon):
        icon = icon.bind(self.interface.factory)
        nsimage = resize_image_to(icon.native, self.size - 2 * self.MARGIN)
        nsimage.template = True
        self.native.button.image = nsimage

    def set_menu(self, menu_impl):
        self.native.menu = menu_impl.native


# ==== Application =====================================================================


class SystemTrayAppDelegate(NSObject):
    @objc_method
    def applicationWillTerminate_(self, sender):
        if self.interface.app.on_exit:
            self.interface.app.on_exit(self.interface.app)

    @objc_method
    def selectMenuItem_(self, sender) -> None:
        cmd = self.interface._impl._menu_items[sender]
        if cmd.action:
            cmd.action(None)


class SystemTrayApp(TogaApp):

    _MAIN_WINDOW_CLASS = None

    def _create_app_commands(self):
        # Hack: we use _create_app_commands here to inject our own modifications
        # into the superclass create command *before* the actual GUI is loaded.

        self.delegate = SystemTrayAppDelegate.alloc().init()
        self.delegate.impl = self
        self.delegate.interface = self.interface
        self.delegate.native = self.native
        self.native.delegate = self.delegate
        self.native.activationPolicy = NSApplicationActivationPolicyAccessory

    def select_file(self):
        pass

    def open_document(self, path):
        pass

    async def alert_async(
        self,
        title,
        message,
        details,
        details_title,
        button_labels,
        checkbox_text,
        level,
        icon,
    ):

        return await dialogs.alert_async(
            title,
            message,
            details,
            details_title,
            button_labels,
            checkbox_text,
            level,
            icon,
        )

    def alert(
        self,
        title,
        message,
        details,
        details_title,
        button_labels,
        checkbox_text,
        level,
        icon,
    ):

        return dialogs.alert(
            title,
            message,
            details,
            details_title,
            button_labels,
            checkbox_text,
            level,
            icon,
        )


class WindowDeletage(TogaWindowDeletage):
    @objc_method
    def windowWillClose_(self, notification) -> None:

        if not self.interface.is_dialog:

            # hide dock icon when last window is about to close
            app = NSApplication.sharedApplication

            visible_windows = [
                w
                for w in app.windows
                if w.isVisible and w.objc_class.name != "NSStatusBarWindow"
            ]

            if len(visible_windows) <= 1:
                app.activationPolicy = NSApplicationActivationPolicyAccessory


class Window(TogaWindow):
    def create(self):
        super().create()
        self.delegate = WindowDeletage.alloc().init()
        self.delegate.interface = self.interface
        self.delegate.impl = self
        self.native.delegate = self.delegate
        self.app = NSApplication.sharedApplication

    def cocoa_windowShouldClose(self):
        if self.interface.on_close:
            should_close = self.interface.on_close(self)
        else:
            should_close = True

        return should_close

    def is_visible(self):
        return bool(self.native.isVisible)

    def center(self):
        self.native.center()

    def force_to_front(self):
        self.app.activateIgnoringOtherApps(True)
        self.native.makeKeyAndOrderFront(None)

    def show_as_sheet(self, window):
        window._impl.native.beginSheet(self.native, completionHandler=None)

    def show(self):
        if not self.interface.is_dialog:
            self.app.activationPolicy = NSApplicationActivationPolicyRegular
        super().show()

    def close(self):

        if self.native.sheetParent:
            # End sheet session.
            self.native.sheetParent.endSheet(self.native)
        elif self.interface.closeable:
            # Mimic the press of the close button.
            self.native.performClose(self.native)
        else:
            # Window has no close button -> performClose does not work.
            # Get close confirmation and close if ok.
            if self.cocoa_windowShouldClose():
                self.native.close()

    def set_release_on_close(self, value):
        self.native.releasedWhenClosed = value

    def set_dialog(self, value):

        if value:
            self.native.animationBehavior = NSWindowAnimationBehaviorAlertPanel
            self.native.level = NSModalPanelWindowLevel
        else:
            self.native.animationBehavior = NSWindowAnimationBehaviorDefault
            self.native.level = NSNormalWindowLevel

    # dialogs

    async def save_file_sheet(self, title, message, suggested_filename, file_types):
        return await dialogs.save_file_sheet(
            self.interface, suggested_filename, title, message, file_types
        )

    async def open_file_sheet(
        self, title, message, initial_directory, file_types, multiselect
    ):
        return await dialogs.open_file_sheet(
            self.interface, title, message, file_types, multiselect
        )

    async def select_folder_sheet(self, title, message, initial_directory, multiselect):
        return await dialogs.select_folder_sheet(
            self.interface, title, message, multiselect
        )

    async def alert_sheet(
        self,
        title,
        message,
        details,
        details_title,
        button_labels,
        checkbox_text,
        level,
        icon,
    ):
        return await dialogs.alert_sheet(
            self.interface,
            title,
            message,
            details,
            details_title,
            button_labels,
            checkbox_text,
            level,
            icon,
        )


# ==== helpers =========================================================================


def apply_round_clipping(image_view_impl: ImageView) -> None:
    """Clips an image in a given toga_cocoa.ImageView to a circular mask."""

    image = image_view_impl.native.image  # get native NSImage

    composed_image = NSImage.alloc().initWithSize(image.size)
    composed_image.lockFocus()

    ctx = NSGraphicsContext.currentContext
    ctx.saveGraphicsState()
    ctx.imageInterpolation = NSImageInterpolationHigh

    image_frame = NSRect(NSPoint(0, 0), image.size)
    clip_path = NSBezierPath.bezierPathWithRoundedRect(
        image_frame, xRadius=image.size.width / 2, yRadius=image.size.height / 2
    )
    clip_path.addClip()

    zero_rect = NSRect(NSPoint(0, 0), NSMakeSize(0, 0))
    image.drawInRect(
        image_frame, fromRect=zero_rect, operation=NSCompositeSourceOver, fraction=1
    )
    composed_image.unlockFocus()
    ctx.restoreGraphicsState()

    image_view_impl.native.image = composed_image


def resize_image_to(image: NSImage, height: int) -> NSImage:

    new_size = NSMakeSize(height, height)
    new_image = NSImage.alloc().initWithSize(new_size)
    new_image.lockFocus()
    image.size = new_size

    ctx = NSGraphicsContext.currentContext
    ctx.saveGraphicsState()
    ctx.imageInterpolation = NSImageInterpolationHigh

    image.drawAtPoint(
        NSZeroPoint,
        fromRect=CGRectMake(0, 0, new_size.width, new_size.height),
        operation=NSCompositingOperationCopy,
        fraction=1.0,
    )

    new_image.unlockFocus()
    ctx.restoreGraphicsState()

    return new_image
