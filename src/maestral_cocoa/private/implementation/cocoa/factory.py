# -*- coding: utf-8 -*-

# system imports
import os.path as osp
import platform

# external imports
import toga_cocoa.factory

toga_cocoa.factory.__path__ = ""

from travertino.size import at_least
from travertino.constants import NONE
from rubicon.objc import (
    NSMakeSize,
    NSZeroPoint,
    NSDictionary,
    CGRectMake,
    ObjCClass,
    objc_method,
    objc_property,
    SEL,
)
from rubicon.objc.runtime import objc_id
from toga.fonts import Font as InterfaceFont
from toga.constants import LEFT
from toga_cocoa.libs import (
    NSLinkAttributeName,
    NSFontAttributeName,
    NSAttributedString,
    NSTextView,
    NSTextAlignment,
    NSBezelStyle,
    NSViewMaxYMargin,
    NSMenuItem,
    NSMenu,
    NSApplication,
    NSObject,
    NSImage,
    NSImageInterpolationHigh,
    NSGraphicsContext,
    NSRect,
    NSPoint,
    NSBezierPath,
    NSTextField,
    NSPopUpButton,
    NSOpenPanel,
    NSModalResponseOK,
    NSCompositingOperationCopy,
    NSApplicationActivationPolicyRegular,
    NSURL,
    NSButton,
    NSSwitchButton,
    NSRadioButton,
    NSBundle,
)
from toga_cocoa.colors import native_color
from toga_cocoa.keys import cocoa_key
from toga_cocoa.app import App as TogaApp
from toga_cocoa.widgets.base import Widget
from toga_cocoa.widgets.button import Button as TogaButton
from toga_cocoa.window import Window as TogaWindow
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
NSFileManager = ObjCClass("NSFileManager")
NSVisualEffectView = ObjCClass("NSVisualEffectView")
NSStatusBar = ObjCClass("NSStatusBar")
NSColorSpace = ObjCClass("NSColorSpace")

NSNormalWindowLevel = 0
NSModalPanelWindowLevel = 8


macos_version, *_ = platform.mac_ver()


# ==== icons ===========================================================================


class Icon:
    """Reimplements toga.Icon with support for

    1. Platform template images.
    2. Providing the icon for the file / folder type instead of loading an icon from
       the file content.
    """

    _to_cocoa_template = {
        None: None,
        ImageTemplate.Refresh: NSImageNameRefreshFreestandingTemplate,
        ImageTemplate.FollowLink: NSImageNameFollowLinkFreestandingTemplate,
        ImageTemplate.Reveal: NSImageNameRevealFreestandingTemplate,
        ImageTemplate.InvalidData: NSImageNameInvalidDataFreestandingTemplate,
        ImageTemplate.StopProgress: NSImageNameStopProgressFreestandingTemplate,
    }

    SIZES = None
    EXTENSIONS = [".icns", ".png", ".pdf"]

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

        elif self.for_path:
            # always return a new pointer since an old one may be invalidated
            # icons are cached by AppKit anyways
            path = str(self.for_path)
            if osp.exists(path):
                self._native = NSWorkspace.sharedWorkspace.iconForFile(path)
            else:
                _, extension = osp.splitext(path)
                self._native = NSWorkspace.sharedWorkspace.iconForFileType(extension)

        elif self.template:
            cocoa_template = Icon._to_cocoa_template[self.template]
            self._native = NSImage.imageNamed(cocoa_template)

        return self._native


# ==== labels ==========================================================================


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
        self.native = NSTextField.alloc().init()

        self.native.drawsBackground = False
        self.native.editable = False
        self.native.bezeled = False

        # Add the layout constraints
        self.add_constraints()

    def set_alignment(self, value):
        self.native.alignment = NSTextAlignment(value)

    def set_color(self, value):
        if value:
            self.native.textColor = native_color(value)

    def set_font(self, font):
        if font:
            self.native.font = font._impl.native

    def set_text(self, value):
        self.native.stringValue = value

    def set_linebreak_mode(self, value):
        self.native.cell.lineBreakMode = Label._toga_to_cocoa_linebreakmode[value]

    def rehint(self):
        if self.interface.style.width != NONE:
            self.native.preferredMaxLayoutWidth = float(self.interface.style.width)

        content_size = self.native.intrinsicContentSize()

        if self.interface.style.width != NONE:
            self.interface.intrinsic.width = at_least(content_size.width)
            self.interface.intrinsic.height = at_least(content_size.height)
        else:
            self.interface.intrinsic.width = at_least(0)
            self.interface.intrinsic.height = at_least(content_size.height)


class LinkLabel(Widget):
    """A label with a hyperlink."""

    def create(self):
        self.native = NSTextView.alloc().init()

        self.native.drawsBackground = False
        self.native.editable = False
        self.native.selectable = True
        self.native.textContainer.lineFragmentPadding = 2.0

        self.native.bezeled = False

        # Add the layout constraints
        self.add_constraints()

    def _update(self):
        style = self.interface.style
        font = InterfaceFont(style.font_family, style.font_size)

        attributes = NSDictionary.dictionaryWithObjects(
            [self.interface.url, font._impl.native],
            forKeys=[NSLinkAttributeName, NSFontAttributeName],
        )
        self.attr_string = NSAttributedString.alloc().initWithString(
            self.interface.text, attributes=attributes
        )
        self.native.textStorage.setAttributedString(self.attr_string)
        self.rehint()

    def set_text(self, value):
        self._update()

    def set_url(self, value):
        self._update()

    def set_font(self, value):
        self._update()

    def rehint(self):
        # force layout and get layout rect
        self.native.layoutManager.glyphRangeForTextContainer(self.native.textContainer)
        rect = self.native.layoutManager.usedRectForTextContainer(
            self.native.textContainer
        )

        self.interface.intrinsic.width = at_least(rect.size.width)
        self.interface.intrinsic.height = rect.size.height


# ==== buttons =========================================================================


class FreestandingIconButton(TogaButton):
    """A styled button with an icon."""

    def create(self):
        super().create()
        self.native.showsBorderOnlyWhileMouseInside = True
        self.native.bordered = False
        self.native.buttonType = NSButtonTypeMomentaryPushIn
        self.native.bezelStyle = NSBezelStyle.Recessed
        self.native.imagePosition = NSImageLeading
        self.native.alignment = NSTextAlignment(LEFT)
        self.native.focusRingType = NSFocusRingTypeNone

    def set_text(self, text):
        self.native.title = " {}".format(self.interface.text)

    def set_icon(self, icon):
        if self.interface.style.height != NONE:
            icon_size = self.interface.style.height
        else:
            icon_size = 16
        self.native.image = resize_image_to(icon._impl.native, icon_size)
        self.native.image.template = True


class SwitchTarget(NSObject):
    interface = objc_property(object, weak=True)
    impl = objc_property(object, weak=True)

    @objc_method
    def onPress_(self, obj: objc_id) -> None:
        if self.interface.on_change:
            self.interface.on_change(self.interface)

        self.impl.native.allowsMixedState = False


class Switch(Widget):
    """Similar to toga_cocoa.Switch but allows *programmatic* setting of
    an intermediate state."""

    _to_cocoa = {OFF: 0, MIXED: -1, ON: 1}
    _to_toga = {0: OFF, -1: MIXED, 1: ON}

    def create(self):
        self.native = NSButton.alloc().init()
        self.native.setButtonType(NSSwitchButton)
        self.native.autoresizingMask = NSViewMaxYMargin | NSViewMaxYMargin

        self.target = SwitchTarget.alloc().init()
        self.target.interface = self.interface
        self.target.impl = self

        self.native.target = self.target
        self.native.action = SEL("onPress:")

        # Add the layout constraints
        self.add_constraints()

    def set_text(self, text):
        self.native.title = text

    def get_text(self):
        return str(self.native.title)

    def set_state(self, value):
        self.native.allowsMixedState = value == MIXED
        self.native.state = self._to_cocoa[value]

    def set_value(self, value):
        self.native.state = int(value)

    def get_value(self):
        return bool(self.native.state)

    def get_state(self):
        return self._to_toga[self.native.state]

    def set_font(self, font):
        if font:
            self.native.font = font._impl.native

    def rehint(self):
        content_size = self.native.intrinsicContentSize()
        self.interface.intrinsic.height = 20
        self.interface.intrinsic.width = at_least(content_size.width)

    def set_on_change(self, handler):
        pass


class FileChooserTarget(NSObject):
    interface = objc_property(object, weak=True)
    impl = objc_property(object, weak=True)

    @objc_method
    def onSelect_(self, obj: objc_id) -> None:
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
                if r == NSModalResponseOK:
                    self.impl.set_current_selection(str(panel.URL.path))

                    if self.interface.on_change:
                        self.interface.on_change(self.interface)

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

    def _display_path(self, path):
        file_manager = NSFileManager.defaultManager

        display_components = file_manager.componentsToDisplayForPath(path)

        if display_components:
            path_display = "/".join([str(p) for p in display_components])
        else:
            path_display = path

        return path_display

    def set_current_selection(self, path):
        if not osp.exists(path) and not self.interface.select_files:
            # use generic folder icon
            image = NSWorkspace.sharedWorkspace.iconForFile("/usr")
        else:
            # use actual icon for file / folder, falls back to generic file icon
            image = NSWorkspace.sharedWorkspace.iconForFile(path)

        item = self.native.itemAtIndex(0)

        path_display = self._display_path(path)

        if self.interface.show_full_path:
            title = path_display
        else:
            title = osp.basename(path_display)

        item.title = title
        item.image = resize_image_to(image, 16)
        self._current_selection = path

    def set_on_change(self, handler):
        pass

    def set_select_files(self, value):
        pass

    def set_select_folders(self, value):
        pass

    def set_dialog_title(self, value):
        pass

    def set_show_full_path(self, value):
        item = self.native.itemAtIndex(0)
        display_path = self._display_path(self._current_selection)
        item.title = display_path if value else osp.basename(display_path)

    def set_dialog_message(self, value):
        pass

    def rehint(self):
        content_size = self.native.intrinsicContentSize()
        self.interface.intrinsic.height = content_size.height + 1
        self.interface.intrinsic.width = at_least(
            max(self.interface.MIN_WIDTH, content_size.width)
        )


class RadioButtonTarget(NSObject):
    interface = objc_property(object, weak=True)
    impl = objc_property(object, weak=True)

    @objc_method
    def onPressA_(self, obj: objc_id) -> None:
        if self.interface.on_change:
            self.interface.on_change(self.interface)

    @objc_method
    def onPressB_(self, obj: objc_id) -> None:
        if self.interface.on_change:
            self.interface.on_change(self.interface)


class RadioButton(Switch):
    """Similar to toga_cocoa.Switch but allows *programmatic* setting of
    an intermediate state."""

    def create(self):
        self.native = NSButton.alloc().init()
        self.native.setButtonType(NSRadioButton)
        self.native.autoresizingMask = NSViewMaxYMargin | NSViewMaxYMargin

        self.target = RadioButtonTarget.alloc().init()
        self.target.interface = self.interface
        self.target.impl = self

        self.native.target = self.target

        # Add the layout constraints
        self.add_constraints()

    def set_group(self, group):
        self.native.action = SEL(f"onPress{group.name}:")


# ==== menus and status bar ============================================================


class TogaMenuItem(NSMenuItem):
    interface = objc_property(object, weak=True)
    impl = objc_property(object, weak=True)

    @objc_method
    def onPress_(self, obj: objc_id) -> None:
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
            nsimage = resize_image_to(icon._impl.native, 16)
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
    interface = objc_property(object, weak=True)
    impl = objc_property(object, weak=True)

    @objc_method
    def menuWillOpen_(self, obj: objc_id) -> None:
        self.impl._visible = True
        if self.interface.on_open:
            self.interface.on_open(self.interface)

    @objc_method
    def menuDidClose_(self, obj: objc_id) -> None:
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
        nsimage = resize_image_to(icon._impl.native, self.size - 2 * self.MARGIN)
        nsimage.template = True
        self.native.button.image = nsimage

    def set_menu(self, menu_impl):
        self.native.menu = menu_impl.native


# ==== Application =====================================================================


class SystemTrayAppDelegate(NSObject):
    interface = objc_property(object, weak=True)
    impl = objc_property(object, weak=True)

    @objc_method
    def applicationWillTerminate_(self, sender: objc_id) -> None:
        if self.interface.app.on_exit:
            self.interface.app.on_exit(self.interface.app)

    @objc_method
    def selectMenuItem_(self, sender: objc_id) -> None:
        cmd = self.impl._menu_items[sender]
        if cmd.action:
            cmd.action(None)


class SystemTrayApp(TogaApp):
    _MAIN_WINDOW_CLASS = None

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


class Window(TogaWindow):
    def center(self):
        self.native.center()

    def force_to_front(self):
        self.native.makeKeyAndOrderFront(None)

    def show_as_sheet(self, window):
        window._impl.native.beginSheet(self.native, completionHandler=None)

    def close(self):
        if self.native.sheetParent:
            self.native.sheetParent.endSheet(self.native)
        else:
            self.native.close()

    def set_dialog(self, value):
        if value:
            self.native.animationBehavior = NSWindowAnimationBehaviorAlertPanel
            self.native.level = NSModalPanelWindowLevel
        else:
            self.native.animationBehavior = NSWindowAnimationBehaviorDefault
            self.native.level = NSNormalWindowLevel


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
