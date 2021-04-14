# -*- coding: utf-8 -*-

# system imports
import os
import asyncio
import shlex
from concurrent.futures import ThreadPoolExecutor

# external imports
from rubicon.objc import ObjCClass
from maestral.daemon import MaestralProxy


NSAppleScript = ObjCClass("NSAppleScript")


# ==== async calls =====================================================================

thread_pool_executor = ThreadPoolExecutor(10)


def create_task(coro):

    loop = asyncio.get_event_loop()

    try:
        return loop.create_task(coro)
    except AttributeError:
        return asyncio.ensure_future(coro, loop=loop)


def call_async(func, *args):
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(thread_pool_executor, func, *args)


def call_async_maestral(config_name, func_name, *args):
    def func(*inner_args):
        with MaestralProxy(config_name) as m:
            m_func = m.__getattr__(func_name)
            return m_func(*inner_args)

    loop = asyncio.get_event_loop()
    return loop.run_in_executor(thread_pool_executor, func, *args)


def generate_async_maestral(config_name, func_name, *args):
    loop = asyncio.get_event_loop()
    queue = asyncio.Queue(1)
    exception = None
    _END = object()

    def func(*inner_args):
        nonlocal exception
        with MaestralProxy(config_name) as m:
            m_func = m.__getattr__(func_name)
            generator = m_func(*inner_args)

            try:
                for res in generator:
                    asyncio.run_coroutine_threadsafe(queue.put(res), loop).result()
            except Exception as e:
                exception = e
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(_END), loop).result()

    async def yield_results():

        while True:
            next_item = await queue.get()
            if next_item is _END:
                break
            yield next_item
        if exception is not None:
            # the iterator has raised, propagate the exception
            raise exception

    thread_pool_executor.submit(func, *args)

    return yield_results()


# ==== system calls ====================================================================


def request_authorization_from_user_and_run(exe):
    # shlex.join requires Python 3.8 and later.

    source = f'do shell script "{shlex.join(exe)}" with administrator privileges'

    script = NSAppleScript.alloc().initWithSource(source)
    res = script.executeAndReturnError(None)

    if res is None:
        raise RuntimeError("Could install CLI")


def is_empty(dirname):
    """Checks if a directory is empty."""

    try:
        with os.scandir(dirname) as sciter:
            next(sciter)
    except StopIteration:
        return True

    return False
