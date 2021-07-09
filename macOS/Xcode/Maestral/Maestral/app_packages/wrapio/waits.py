import abc
import asyncio
import threading


__all__ = ()


class Wait(abc.ABC):

    __slots__ = ()

    @abc.abstractmethod
    def _make_event(self):

        raise NotImplementedError()

    @abc.abstractmethod
    def _make(self, event):

        raise NotImplementedError()

    def __call__(self, manage, event = None):

        if not event:
            event = self._make_event()

        self._make(manage, event)

        return event


class Asyncio(Wait):

    __slots__ = ()

    def _make_event(self):

        return asyncio.Event()

    def _make(self, manage, event):

        coroutine = event.wait()
        loop = asyncio.get_event_loop()
        task = loop.create_task(coroutine)

        callback = lambda task: manage()
        task.add_done_callback(callback)


class Threading(Wait):

    __slots__ = ()

    def _make_event(self):

        return threading.Event()

    def _make(self, manage, event):

        def callback():
            event.wait()
            manage()

        thread = threading_.Thread(target = callback)
        thread.start()
