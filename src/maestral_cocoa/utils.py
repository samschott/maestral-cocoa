# -*- coding: utf-8 -*-

# system imports
import os
import asyncio
import shlex
from concurrent.futures import ThreadPoolExecutor
from typing import (
    Union,
    Awaitable,
    TypeVar,
    AsyncGenerator,
    List,
    Any,
    Callable,
)

# external imports
from rubicon.objc import ObjCClass
from maestral.daemon import MaestralProxy


_T = TypeVar("_T")


NSAppleScript = ObjCClass("NSAppleScript")


# ==== async calls =====================================================================

thread_pool_executor = ThreadPoolExecutor(10)


def create_task(coro: Awaitable[_T]) -> Union[asyncio.Task[_T], asyncio.Future[_T]]:

    loop = asyncio.get_event_loop()

    try:
        return loop.create_task(coro)
    except AttributeError:
        return asyncio.ensure_future(coro, loop=loop)


def call_async(func: Callable, *args) -> Awaitable:
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(thread_pool_executor, func, *args)


def call_async_maestral(config_name: str, func_name: str, *args) -> Awaitable:
    def func(*inner_args):
        with MaestralProxy(config_name) as m:
            m_func = m.__getattr__(func_name)
            return m_func(*inner_args)

    loop = asyncio.get_event_loop()
    return loop.run_in_executor(thread_pool_executor, func, *args)


def generate_async_maestral(config_name: str, func_name: str, *args) -> AsyncGenerator:
    loop = asyncio.get_event_loop()
    queue: "asyncio.Queue[Any]" = asyncio.Queue(1)
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


def request_authorization_from_user_and_run(exe: List[str]) -> None:
    # shlex.join requires Python 3.8 and later.

    cmd = shlex.join(exe)

    source = f'do shell script "{cmd}" with administrator privileges'

    script = NSAppleScript.alloc().initWithSource(source)
    res = script.executeAndReturnError(None)

    if res is None:
        raise RuntimeError(f"Could not run privileged command {cmd!r}")


def is_empty(dirname: Union[str, bytes, os.PathLike]) -> bool:
    """Checks if a directory is empty."""

    exceptions = {".DS_Store"}
    n_exceptions = len(exceptions)

    children: List[os.DirEntry] = []

    try:
        with os.scandir(dirname) as sd_iter:
            while len(children) <= n_exceptions:
                children.append(next(sd_iter))
    except StopIteration:
        pass

    return all(child.name in exceptions for child in children)
