# -*- coding: utf-8 -*-

# system imports
import asyncio
from concurrent.futures import Future

# external imports
from toga.fonts import Font, SYSTEM, BOLD
from toga_cocoa.libs import (
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
from toga_cocoa.dialogs import *  # noqa: F401,F406
from rubicon.objc import ObjCClass, objc_method

# local imports
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

NSStackView = ObjCClass("NSStackView")


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
        trace.insetText(details)

        scroll.documentView = trace

        title = NSTextField.labelWithString(details_title)
        title.font = Font(SYSTEM, 12, weight=BOLD)._impl.native

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
    native = _construct_alert(
        title,
        message,
        details,
        details_title,
        button_labels,
        checkbox_text,
        level,
        icon._impl.native if icon else None,
    )

    NSApplication.sharedApplication.activateIgnoringOtherApps(True)
    result = native.runModal()

    button_index = result - NSAlertFirstButtonReturn

    if native.showsSuppressionButton:
        return button_index, native.suppressionButton.state == NSOnState
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
    native = _construct_alert(
        title,
        message,
        details,
        details_title,
        button_labels,
        checkbox_text,
        level,
        icon._impl.native if icon else None,
    )

    NSApplication.sharedApplication.activateIgnoringOtherApps(True)

    future = Future()

    target = AlertButtonTarget.alloc().init()
    target.alert = native
    target.button_labels = button_labels
    target.future = future

    for button in native.buttons:
        button.target = target

    native.layout()
    native.window.animationBehavior = NSWindowAnimationBehaviorAlertPanel
    native.window.center()
    native.window.makeKeyAndOrderFront(None)

    return await asyncio.wrap_future(future)
