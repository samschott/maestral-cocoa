# -*- coding: utf-8 -*-

# system imports
import sys
import asyncio
import inspect
import time
import traceback
from functools import wraps
from concurrent.futures import ThreadPoolExecutor
import ctypes
import ctypes.util

# external imports
import toga
from toga.fonts import Font, SYSTEM, BOLD
from toga_cocoa.libs import *
from toga.handlers import long_running_task
from toga.platform import get_platform_factory
from rubicon.objc import ObjCClass
from maestral.daemon import MaestralProxy

# local imports
from .private.constants import (
    NSCompositeSourceOver,
    NSStackViewGravityBottom,
    NSUserInterfaceLayoutOrientationVertical,
    kAuthorizationFlagExtendRights,
    kAuthorizationFlagInteractionAllowed,
    kAuthorizationFlagDefaults,
    kAuthorizationFlagPreAuthorize,
    kAuthorizationRightExecute,
    kAuthorizationEmptyEnvironment,
    kAuthorizationEnvironmentPrompt,
    errAuthorizationToolExecuteFailure, errAuthorizationSuccess, errAuthorizationCanceled,
)
from .private.factory import attributed_str_from_html

sec = ctypes.cdll.LoadLibrary(ctypes.util.find_library('Security'))

NSAutoreleasePool = ObjCClass('NSAutoreleasePool')
NSVisualEffectView = ObjCClass('NSVisualEffectView')
NSAppearance = ObjCClass('NSAppearance')
NSStackView = ObjCClass('NSStackView')

alert_style_for_level_str = {
    'info': NSAlertStyle.Informational,
    'warning': NSAlertStyle.Warning,
    'error': NSAlertStyle.Critical
}

factory = get_platform_factory()


# ==== toga gui helpers ==================================================================

def apply_round_clipping(imageView: toga.ImageView):
    """Clips an image in a given toga.ImageView to a circular mask."""

    pool = NSAutoreleasePool.alloc().init()

    image = imageView._impl.native.image  # get native NSImage

    composedImage = NSImage.alloc().initWithSize(image.size)
    composedImage.lockFocus()

    ctx = NSGraphicsContext.currentContext
    ctx.saveGraphicsState()
    ctx.imageInterpolation = NSImageInterpolationHigh

    imageFrame = NSRect(NSPoint(0, 0), image.size)
    clipPath = NSBezierPath.bezierPathWithRoundedRect(
        imageFrame,
        xRadius=image.size.width / 2,
        yRadius=image.size.height / 2
    )
    clipPath.addClip()

    NSZeroRect = NSRect(NSPoint(0, 0), NSMakeSize(0, 0))
    image.drawInRect(
        imageFrame,
        fromRect=NSZeroRect,
        operation=NSCompositeSourceOver,
        fraction=1
    )
    composedImage.unlockFocus()
    ctx.restoreGraphicsState()

    imageView._impl.native.image = composedImage

    pool.drain()
    del pool


def clear_background(widget):
    """Removed all background from the given widget and its children."""
    widget._impl.native.backgroundColor = NSColor.clearColor
    widget._impl.native.drawsBackground = False
    for child in widget.children:
        clear_background(child)

    content = getattr(widget, 'content', None)

    if content is not None:
        clear_background(content)


# ==== custom dialogs ====================================================================

def save_file_sheet(window, suggested_filename, message='', file_types=None, callback=print):
    """Cocoa save file dialog implementation.

    We restrict the panel invocation to only choose files. We also allow
    creating directories but not selecting directories.

    Args:
        window: The window this dialog belongs to.
        suggested_filename: A default file name to use, such as 'Untitled.txt'.
        message: Informative message to display. Defaults to an empty string.
        file_types: A list of allowed file extensions.
        callback: Callable which takes a single selected file path as argument.
    """
    panel = NSSavePanel.alloc().init()
    panel.message = message

    if file_types:
        arr = NSArray.alloc().init()
        for x in file_types:
            arr = arr.arrayByAddingObject(x)
    else:
        arr = None

    panel.allowedFileTypes = arr
    panel.nameFieldStringValue = suggested_filename

    def completionHandler(r: int) -> None:
        path = panel.URL.path if r == NSFileHandlingPanelOKButton else None
        if callback:
            callback(path)

    panel.beginSheetModalForWindow(window._impl.native, completionHandler=completionHandler)


def open_file_sheet(window, message='', file_types=None, multiselect=False, callback=print):
    """Cocoa open file dialog implementation.
    We restrict the panel invocation to only choose files. We also allow
    creating directories but not selecting directories.
    Args:
        window: The window this dialog belongs to.
        message: Informative message to display. Defaults to an empty string.
        file_types: A list of allowed file extensions.
        multiselect: Flag to allow multiple file selection.
        callback: Callable which takes a list of selected file paths as argument.
    """

    if file_types:
        arr = NSArray.alloc().init()
        for x in file_types:
            arr = arr.arrayByAddingObject(x)
    else:
        arr = None

    # Initialize and configure the panel.
    panel = NSOpenPanel.alloc().init()
    panel.message = message
    panel.allowedFileTypes = arr
    panel.allowsMultipleSelection = multiselect
    panel.canChooseDirectories = False
    panel.canCreateDirectories = True
    panel.canChooseFiles = True

    def completionHandler(r: int) -> None:

        if r == NSFileHandlingPanelOKButton:
            if multiselect:
                paths = [str(url.path) for url in panel.URLs]
            else:
                paths = [str(panel.URL.path)]
        else:
            paths = []

        if callback:
            callback(paths)

    panel.beginSheetModalForWindow(window._impl.native, completionHandler=completionHandler)


def select_folder_sheet(window, message='', multiselect=False, callback=print):
    """Cocoa select folder dialog implementation.

    Args:
        window: Window dialog belongs to.
        message: Informative message to display. Defaults to an empty string.
        multiselect: Flag to allow multiple file selection.
        callback: Callable which takes a list of selected file paths as argument.
    """
    panel = NSOpenPanel.alloc().init()
    panel.message = message
    panel.canChooseFiles = False
    panel.canChooseDirectories = True
    panel.canCreateDirectories = True
    panel.resolvesAliases = True
    panel.allowsMultipleSelection = multiselect

    def completionHandler(r: int) -> None:

        if r == NSFileHandlingPanelOKButton:
            if multiselect:
                paths = [str(url.path) for url in panel.URLs]
            else:
                paths = [str(panel.URL.path)]
        else:
            paths = []

        if callback:
            callback(paths)

    panel.beginSheetModalForWindow(window._impl.native, completionHandler=completionHandler)


def _construct_alert(title, message, details=None, details_title='Traceback',
                     button_names=('Ok',), checkbox_text=None, level='info', icon=None):
    alert = NSAlert.alloc().init()
    alert.alertStyle = alert_style_for_level_str[level]
    alert.messageText = title
    alert.informativeText = message
    alert.icon = icon

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
        attr_str = attributed_str_from_html(details)
        trace.textStorage.setAttributedString(attr_str)

        scroll.documentView = trace

        title = NSTextField.labelWithString(details_title)
        title.font = Font(SYSTEM, 12, weight=BOLD)._impl.native

        stack = NSStackView.alloc().initWithFrame(NSMakeRect(0, 0, 500, 265))
        stack.orientation = NSUserInterfaceLayoutOrientationVertical
        stack.alignment = NSLayoutAttributeLeading
        stack.addView(title, inGravity=NSStackViewGravityBottom)
        stack.addView(scroll, inGravity=NSStackViewGravityBottom)

        alert.accessoryView = stack

    if checkbox_text:
        alert.showsSuppressionButton = True
        alert.suppressionButton.title = checkbox_text

    for name in button_names:
        alert.addButtonWithTitle(name)

    return alert


def alert_sheet(window, title, message, details=None, details_title='Traceback',
                callback=print, button_labels=('Ok',), checkbox_text=None, level='info',
                icon=None):
    """
    Shows an alert sheet attached to `window`. If `details` are given, they will be shown
    in a scroll view. If `checkbox_text` is given, an additional checkbox is shown.
    The callback must be a callable which takes the index of the button pressed
    (right == 0) as input.
    """
    icon = icon.bind(factory).native if icon else None
    alert = _construct_alert(title, message, details, details_title, button_labels,
                             checkbox_text, level, icon)

    def completionHandler(r: int) -> None:
        callback(r - NSAlertFirstButtonReturn)

    alert.beginSheetModalForWindow(window._impl.native, completionHandler=completionHandler)


def alert(title, message, details=None, details_title='Traceback', button_names=('Ok',),
          checkbox_text=None, level='info', icon=None):
    """
    Shows an alert. If `details` are given, they will be shown in a scroll view. If
    `checkbox_text` is given, an addition checkbox is shown. Returns the index of the
    button pressed (right == 0) and, if a checkbox was shown, its checked state as bool
    (checked == True).
    """
    icon = icon.bind(factory).native if icon else None
    alert = _construct_alert(title, message, details, details_title, button_names,
                             checkbox_text, level, icon)

    NSApplication.sharedApplication.activateIgnoringOtherApps(True)
    result = alert.runModal()

    if checkbox_text:
        return result - NSAlertFirstButtonReturn, alert.suppressionButton.state == NSOnState
    else:
        return result - NSAlertFirstButtonReturn


# ==== async calls =======================================================================

default_executor = ThreadPoolExecutor(10)


async def func_with_cleanup(func, *args, **kwargs):
    try:
        await func(*args, **kwargs)
    except Exception as e:
        print('Error in async handler:', e, file=sys.stderr)
        traceback.print_exc()


def async_call(func):
    """Wrap a function so it can be invoked.

    If the function is a bound method, or function, it will be invoked as is.
    If the function is a generator, it will be invoked asynchronously, with
        the yield values from the generator representing the duration
        to sleep between iterations.
    If the function is a coroutine, it will be installed on the asynchronous
        event loop.

    Returns a wrapped function that will invoke the function. The wrapper
    function is annotated with the original function on the `_raw` attribute.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        if asyncio.iscoroutinefunction(func):
            asyncio.ensure_future(
                func_with_cleanup(func, *args, **kwargs)
            )
        else:
            result = func(*args, **kwargs)
            if inspect.isgenerator(result):
                asyncio.ensure_future(
                    long_running_task(result, cleanup=None)
                )
            else:
                try:
                    return result
                except Exception as e:
                    print('Error in handler:', e, file=sys.stderr)
                    traceback.print_exc()

    return wrapper


def run_async(func, *args):
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(default_executor, func, *args)


def run_maestral_async(config_name, func_name, *args):

    def func(*inner_args):
        with MaestralProxy(config_name) as m:
            m_func = m.__getattr__(func_name)
            return m_func(*inner_args)

    loop = asyncio.get_event_loop()
    return loop.run_in_executor(default_executor, func, *args)


# ==== system calls ======================================================================

class AuthorizationItem(Structure):
    _fields_ = [
        ('name', c_char_p),
        ('valueLength', c_uint32),
        ('value', c_char_p),
        ('flags', c_uint32)
    ]


class AuthorizationItemSet(Structure):
    _fields_ = [
        ('count', c_uint32),
        ('items', POINTER(AuthorizationItem))
    ]


AuthorizationRights = AuthorizationItemSet
AuthorizationEnvironment = AuthorizationItemSet
AuthorizationFlags = c_uint32
AuthorizationRef = c_void_p


def _osx_sudo_start():
    auth = ctypes.c_void_p()
    r_auth = ctypes.byref(auth)

    flags = kAuthorizationFlagInteractionAllowed | kAuthorizationFlagExtendRights | kAuthorizationFlagPreAuthorize
    sec.AuthorizationCreate(None, None, flags, r_auth)

    return auth


def _osx_sudo_cmd(auth, exe, auth_text=None):

    cmd = exe[0].encode()
    argv = [e.encode() for e in exe[1:]]
    if auth_text:
        auth_text = auth_text.encode()

    item = AuthorizationItem(name=kAuthorizationRightExecute, valueLength=len(cmd), value=cmd, flags=0)
    rights = AuthorizationRights(count=1, items=pointer(item))

    if not auth_text:
        env_p = kAuthorizationEmptyEnvironment
    else:
        prompt_item = AuthorizationItem(name=kAuthorizationEnvironmentPrompt, valueLength=len(auth_text),
                                        value=auth_text, flags=0)
        environment = AuthorizationEnvironment(count=1, items=pointer(prompt_item))
        env_p = pointer(environment)

    flags = kAuthorizationFlagInteractionAllowed | kAuthorizationFlagExtendRights | kAuthorizationFlagPreAuthorize
    sec.AuthorizationCopyRights(auth, byref(rights), env_p, flags, None)
    argv = (c_char_p * (len(argv) + 1))(*(argv + [None]))
    # channel = POINTER(FILE)()
    i = 0
    while True:
        io = ctypes.c_void_p()
        r_io = ctypes.byref(io)

        err = sec.AuthorizationExecuteWithPrivileges(auth, cmd, kAuthorizationFlagDefaults, argv, r_io)

        if err == errAuthorizationSuccess:
            break
        elif err == errAuthorizationToolExecuteFailure:
            if i != 5:
                time.sleep(1)
                i += 1
                continue
            raise RuntimeError('Execution failed')
        elif err == errAuthorizationCanceled:
            raise PermissionError('Authorization canceled')


def _osx_sudo_end(auth):
    sec.AuthorizationFree(auth, kAuthorizationFlagDefaults)


def request_authorization_from_user_and_run(exe, auth_text=None):
    auth = _osx_sudo_start()
    try:
        _osx_sudo_cmd(auth, exe, auth_text)
    finally:
        _osx_sudo_end(auth)
