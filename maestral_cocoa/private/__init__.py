# -*- coding: utf-8 -*-

# system imports
import gc

# external imports
from rubicon.objc.eventloop import CFTimerHandle, CFRunLoopTimerCallBack


# patch async event callback to plug memory leak

def _cf_timer_callback(self, callback, args):
    # Create a CF-compatible callback for a timer event
    def cf_timer_callback(cftimer, extra):
        callback(*args)
        self._loop._timers.discard(self)
        gc.collect()

    return CFRunLoopTimerCallBack(cf_timer_callback)


CFTimerHandle._cf_timer_callback = _cf_timer_callback
