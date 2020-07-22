# -*- coding: utf-8 -*-

# system imports
import sys
import asyncio
import inspect
import time
import traceback
from functools import wraps
from concurrent.futures import ThreadPoolExecutor
from ctypes import (
    cdll, util, c_char_p, c_void_p, byref, pointer, Structure, c_uint32, POINTER
)

# external imports
import toga
from toga.handlers import long_running_task
from toga_cocoa.libs import (
    NSAlertStyle, NSImage, NSImageInterpolationHigh, NSGraphicsContext, NSRect, NSPoint,
    NSBezierPath
)
from rubicon.objc import (
    ObjCClass, NSMakeSize
)
from maestral.daemon import MaestralProxy

from .private.implementation.cocoa.constants import (
    NSCompositeSourceOver,
    kAuthorizationFlagExtendRights,
    kAuthorizationFlagInteractionAllowed,
    kAuthorizationFlagDefaults,
    kAuthorizationFlagPreAuthorize,
    kAuthorizationRightExecute,
    kAuthorizationEmptyEnvironment,
    kAuthorizationEnvironmentPrompt,
    errAuthorizationToolExecuteFailure,
    errAuthorizationSuccess,
    errAuthorizationCanceled,
)


sec = cdll.LoadLibrary(util.find_library('Security'))

NSAutoreleasePool = ObjCClass('NSAutoreleasePool')
NSVisualEffectView = ObjCClass('NSVisualEffectView')


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
    auth = c_void_p()
    r_auth = byref(auth)

    flags = (kAuthorizationFlagInteractionAllowed
             | kAuthorizationFlagExtendRights
             | kAuthorizationFlagPreAuthorize)
    sec.AuthorizationCreate(None, None, flags, r_auth)

    return auth


def _osx_sudo_cmd(auth, exe, auth_text=None):

    cmd = exe[0].encode()
    argv = [e.encode() for e in exe[1:]]
    if auth_text:
        auth_text = auth_text.encode()

    item = AuthorizationItem(name=kAuthorizationRightExecute, valueLength=len(cmd),
                             value=cmd, flags=0)
    rights = AuthorizationRights(count=1, items=pointer(item))

    if not auth_text:
        env_p = kAuthorizationEmptyEnvironment
    else:
        prompt_item = AuthorizationItem(name=kAuthorizationEnvironmentPrompt,
                                        valueLength=len(auth_text),
                                        value=auth_text, flags=0)
        environment = AuthorizationEnvironment(count=1, items=pointer(prompt_item))
        env_p = pointer(environment)

    flags = (kAuthorizationFlagInteractionAllowed
             | kAuthorizationFlagExtendRights
             | kAuthorizationFlagPreAuthorize)
    sec.AuthorizationCopyRights(auth, byref(rights), env_p, flags, None)
    argv = (c_char_p * (len(argv) + 1))(*(argv + [None]))

    i = 0
    while True:
        io = c_void_p()
        r_io = byref(io)

        err = sec.AuthorizationExecuteWithPrivileges(auth, cmd,
                                                     kAuthorizationFlagDefaults,
                                                     argv, r_io)

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
