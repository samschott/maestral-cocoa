# -*- coding: utf-8 -*-

# system imports
import asyncio
from concurrent.futures import Future

# external imports
from toga.fonts import Font, SYSTEM, BOLD
from toga_cocoa.libs import (
    NSArray,
    NSSavePanel,
    NSFileHandlingPanelOKButton,
    NSOpenPanel,
    NSAlert,
    NSMakeRect,
    NSScrollView,
    NSBezelBorder,
    NSTextView,
    NSTextField,
    NSLayoutAttributeLeading,
    NSAlertFirstButtonReturn,
    NSApplication,
    NSOnState,
    NSAlertStyle,
    NSObject,
)
from rubicon.objc import ObjCClass, objc_method

# local imports
from . import factory
from .constants import (
    NSStackViewGravityBottom,
    NSUserInterfaceLayoutOrientationVertical,
    NSWindowAnimationBehaviorAlertPanel,
)


alert_style_for_level_str = {
    "info": NSAlertStyle.Informational,
    "warning": NSAlertStyle.Warning,
    "error": NSAlertStyle.Critical,
}

NSAppearance = ObjCClass("NSAppearance")
NSStackView = ObjCClass("NSStackView")


async def save_file_sheet(
    window, suggested_filename, title="", message="", file_types=None
):
    """Cocoa save file dialog implementation.

    We restrict the panel invocation to only choose files. We also allow
    creating directories but not selecting directories.

    Args:
        window: The window this dialog belongs to.
        suggested_filename: A default file name to use, such as 'Untitled.txt'.
        title: A dialog title. Defaults to an empty string.
        message: Informative message to display. Defaults to an empty string.
        file_types: A list of allowed file extensions.

    Returns:
        The file name.
    """
    panel = NSSavePanel.alloc().init()
    panel.title = title
    panel.message = message

    if file_types:
        arr = NSArray.alloc().init()
        for x in file_types:
            arr = arr.arrayByAddingObject(x)
    else:
        arr = None

    panel.allowedFileTypes = arr
    panel.nameFieldStringValue = suggested_filename

    future = Future()

    def completion_handler(r: int) -> None:
        path = panel.URL.path if r == NSFileHandlingPanelOKButton else None
        future.set_result(path)

    panel.beginSheetModalForWindow(
        window._impl.native, completionHandler=completion_handler
    )

    return await asyncio.wrap_future(future)


async def open_file_sheet(
    window, title="", message="", file_types=None, multiselect=False
):
    """Cocoa open file dialog implementation.
    We restrict the panel invocation to only choose files. We also allow
    creating directories but not selecting directories.
    Args:
        window: The window this dialog belongs to.
        title: A dialog title. Defaults to an empty string.
        message: Informative message to display. Defaults to an empty string.
        file_types: A list of allowed file extensions.
        multiselect: Flag to allow multiple file selection.
     Returns:
         A list of selected file paths.
    """

    if file_types:
        arr = NSArray.alloc().init()
        for x in file_types:
            arr = arr.arrayByAddingObject(x)
    else:
        arr = None

    # Initialize and configure the panel.
    panel = NSOpenPanel.alloc().init()
    panel.message = title
    panel.message = message
    panel.allowedFileTypes = arr
    panel.allowsMultipleSelection = multiselect
    panel.canChooseDirectories = False
    panel.canCreateDirectories = True
    panel.canChooseFiles = True

    future = Future()

    def completion_handler(r: int) -> None:

        if r == NSFileHandlingPanelOKButton:
            if multiselect:
                paths = [str(url.path) for url in panel.URLs]
            else:
                paths = [str(panel.URL.path)]
        else:
            paths = []

        future.set_result(paths)

    panel.beginSheetModalForWindow(
        window._impl.native, completionHandler=completion_handler
    )

    return await asyncio.wrap_future(future)


async def select_folder_sheet(window, title="", message="", multiselect=False):
    """Cocoa select folder dialog implementation.

    Args:
        window: Window dialog belongs to.
        title: A dialog title. Defaults to an empty string.
        message: Informative message to display. Defaults to an empty string.
        multiselect: Flag to allow multiple file selection.
    Returns:
         A list of selected folder paths.
    """
    panel = NSOpenPanel.alloc().init()
    panel.title = title
    panel.message = message
    panel.canChooseFiles = False
    panel.canChooseDirectories = True
    panel.canCreateDirectories = True
    panel.resolvesAliases = True
    panel.allowsMultipleSelection = multiselect
    panel.prompt = "Select"

    future = Future()

    def completion_handler(r: int) -> None:

        if r == NSFileHandlingPanelOKButton:
            if multiselect:
                paths = [str(url.path) for url in panel.URLs]
            else:
                paths = [str(panel.URL.path)]
        else:
            paths = []

        future.set_result(paths)

    panel.beginSheetModalForWindow(
        window._impl.native, completionHandler=completion_handler
    )

    return await asyncio.wrap_future(future)


def _construct_alert(
    title,
    message,
    details=None,
    details_title="Traceback",
    button_labels=("Ok",),
    checkbox_text=None,
    level="info",
    icon=None,
):
    a = NSAlert.alloc().init()
    a.alertStyle = alert_style_for_level_str[level]
    a.messageText = title
    a.informativeText = message
    a.icon = icon

    if details:
        scroll = NSScrollView.alloc().initWithFrame(NSMakeRect(0, 0, 500, 250))
        scroll.hasVerticalScroller = True
        scroll.hasHorizontalScroller = False
        scroll.autohidesScrollers = False
        scroll.borderType = NSBezelBorder

        trace = NSTextView.alloc().init()
        trace.editable = False
        trace.verticallyResizable = True
        trace.horizontallyResizable = True
        attr_str = factory.attributed_str_from_html(details)
        trace.textStorage.setAttributedString(attr_str)

        scroll.documentView = trace

        title = NSTextField.labelWithString(details_title)
        title.font = Font(SYSTEM, 12, weight=BOLD).bind(factory).native

        stack = NSStackView.alloc().initWithFrame(NSMakeRect(0, 0, 500, 265))
        stack.orientation = NSUserInterfaceLayoutOrientationVertical
        stack.alignment = NSLayoutAttributeLeading
        stack.addView(title, inGravity=NSStackViewGravityBottom)
        stack.addView(scroll, inGravity=NSStackViewGravityBottom)

        a.accessoryView = stack

    if checkbox_text:
        a.showsSuppressionButton = True
        a.suppressionButton.title = checkbox_text

    for name in button_labels:
        a.addButtonWithTitle(name)

    return a


async def alert_sheet(
    window,
    title,
    message,
    details=None,
    details_title="Traceback",
    button_labels=("Ok",),
    checkbox_text=None,
    level="info",
    icon=None,
):
    """
    Shows an alert sheet attached to `window`. If `details` are given, they will be
    shown in a scroll view. If `checkbox_text` is given, an additional checkbox is
    shown. Returns the index of the button pressed (right == 0).
    """
    icon = icon.bind(factory).native if icon else None
    a = _construct_alert(
        title,
        message,
        details,
        details_title,
        button_labels,
        checkbox_text,
        level,
        icon,
    )

    future = Future()

    def completion_handler(r: int) -> None:
        future.set_result(r - NSAlertFirstButtonReturn)

    a.beginSheetModalForWindow(
        window._impl.native, completionHandler=completion_handler
    )

    return await asyncio.wrap_future(future)


def alert(
    title,
    message,
    details=None,
    details_title="Traceback",
    button_labels=("Ok",),
    checkbox_text=None,
    level="info",
    icon=None,
):
    """
    Shows an alert. If `details` are given, they will be shown in a scroll view. If
    `checkbox_text` is given, an addition checkbox is shown. Returns the label of the
    button pressed and, if a checkbox was shown, its checked state as bool
    (checked == True).
    """
    icon = icon.bind(factory).native if icon else None
    a = _construct_alert(
        title,
        message,
        details,
        details_title,
        button_labels,
        checkbox_text,
        level,
        icon,
    )

    NSApplication.sharedApplication.activateIgnoringOtherApps(True)
    result = a.runModal()

    button_index = result - NSAlertFirstButtonReturn

    if a.showsSuppressionButton:
        return button_index, a.suppressionButton.state == NSOnState
    else:
        return button_index


class AlertButtonTarget(NSObject):
    @objc_method
    def buttonPressed_(self, button):
        self.alert.window.close()
        button_index = self.button_labels.index(button.title)

        if self.alert.showsSuppressionButton:
            res = (button_index, self.alert.suppressionButton.state == NSOnState)
        else:
            res = button_index

        self.future.set_result(res)


async def alert_async(
    title,
    message,
    details=None,
    details_title="Traceback",
    button_labels=("Ok",),
    checkbox_text=None,
    level="info",
    icon=None,
):
    """
    Shows an alert. If `details` are given, they will be shown in a scroll view. If
    `checkbox_text` is given, an addition checkbox is shown. Returns the index of the
    button pressed and, if a checkbox was shown, its checked state as bool.
    """
    icon = icon.bind(factory).native if icon else None
    a = _construct_alert(
        title,
        message,
        details,
        details_title,
        button_labels,
        checkbox_text,
        level,
        icon,
    )

    NSApplication.sharedApplication.activateIgnoringOtherApps(True)

    future = Future()

    target = AlertButtonTarget.alloc().init()
    target.alert = a
    target.button_labels = button_labels
    target.future = future

    for button in a.buttons:
        button.target = target

    a.layout()
    a.window.animationBehavior = NSWindowAnimationBehaviorAlertPanel
    a.window.center()
    a.window.makeKeyAndOrderFront(None)

    return await asyncio.wrap_future(future)
