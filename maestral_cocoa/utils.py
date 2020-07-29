# -*- coding: utf-8 -*-

# system imports
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from ctypes import (
    cdll, util, c_char_p, c_void_p, byref, pointer, Structure, c_uint32, POINTER
)

# external imports
import toga
from toga_cocoa.libs import (
    NSImage, NSImageInterpolationHigh, NSGraphicsContext, NSRect, NSPoint, NSBezierPath
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

def apply_round_clipping(image_view: toga.ImageView):
    """Clips an image in a given toga.ImageView to a circular mask."""

    pool = NSAutoreleasePool.alloc().init()

    image = image_view._impl.native.image  # get native NSImage

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

    image_view._impl.native.image = composed_image

    pool.drain()
    del pool


# ==== async calls =======================================================================

thread_pool_executor = ThreadPoolExecutor(10)


def call_async_threaded(func, *args):
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(thread_pool_executor, func, *args)


def call_async_threaded_maestral(config_name, func_name, *args):

    def func(*inner_args):
        with MaestralProxy(config_name) as m:
            m_func = m.__getattr__(func_name)
            return m_func(*inner_args)

    loop = asyncio.get_event_loop()
    return loop.run_in_executor(thread_pool_executor, func, *args)


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
