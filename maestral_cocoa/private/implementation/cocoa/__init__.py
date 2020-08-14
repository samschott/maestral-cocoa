# -*- coding: utf-8 -*-
from rubicon.objc import eventloop
from rubicon.objc import objc_const


# Patch default mode for asyncio events in Cocoa event loop:
# we want to use kCFRunLoopDefaultMode instead of kCFRunLoopCommonModes
# so that asyncio events don't get processed while a modal dialog is shown.
# This prevents possible exceptions when showing a modal dialog from an
# asyncio coroutine. See https://github.com/beeware/toga/issues/1006
eventloop.kCFRunLoopCommonModes = objc_const(eventloop.libcf, 'kCFRunLoopDefaultMode')
