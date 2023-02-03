# -*- coding: utf-8 -*-

# system imports
import os
import time
import asyncio
from abc import ABC, abstractmethod
from typing import Any

# external imports
from maestral.daemon import MaestralProxy, stop_maestral_daemon_process
from maestral.exceptions import UpdateCheckError

# local imports
from .utils import call_async_maestral
from .dialogs import UpdateDialog, ProgressDialog
from .private.widgets import SystemTrayApp


class AutoUpdaterBackend(ABC):
    def __init__(self, mdbx: MaestralProxy):
        self.mdbx = mdbx
        self.started = False

    def start_updater(self) -> None:
        self._start_updater()
        self.started = True

    @abstractmethod
    def _start_updater(self) -> None:
        ...

    @abstractmethod
    def set_update_check_interval(self, value: int) -> None:
        ...

    @abstractmethod
    async def check_for_updates(self) -> None:
        ...

    @abstractmethod
    async def check_for_updates_in_background(self) -> None:
        ...


class AutoUpdaterSparkle(AutoUpdaterBackend):
    """
    A Sparkle backend for macOS App bundles distributed outside of an app store. Updates
    the bundle in-place and restarts it. Sparkle uses an "appcast" (RSS feed) to be
    notified of available updates. The URL for the feed must be provided in the
    Info.plist of the app bundle in the ``SUFeedURL`` key. The Sparkle framework must
    be bundled together with the app in the ``Contents/Frameworks`` folder.

    See https://sparkle-project.org/documentation/ for more information.
    """

    def __init__(self, mdbx: MaestralProxy) -> None:
        super().__init__(mdbx)

        # Note: Any macOS specific imports are kept local. We could eventually split
        # off platform-specific implementations to separate modules instead.

        from rubicon.objc import ObjCClass, NSObject, objc_method, objc_property
        from rubicon.objc.runtime import objc_id
        from ctypes import c_int, c_bool, CDLL

        class SparkleDelegate(NSObject):
            supportsGentleScheduledUpdateReminders = objc_property(c_bool)

            @objc_method
            def updater_willInstallUpdate_(
                self, updater: objc_id, item: objc_id
            ) -> None:
                stop_maestral_daemon_process(self.config_name)

            @objc_method
            def updater_didFinishUpdateCycleForUpdateCheck_error_(
                self, updater: objc_id, check: c_int, error: objc_id
            ) -> None:
                if not error:
                    self.mdbx.set_state("app", "update_notification_last", time.time())

        NSBundle = ObjCClass("NSBundle")

        path = f"{NSBundle.mainBundle.privateFrameworksPath}/Sparkle.framework/Sparkle"

        if not os.path.exists(path):
            raise FileNotFoundError("Could not load Sparkle framework")

        CDLL(path)

        SPUStandardUpdaterController = ObjCClass("SPUStandardUpdaterController")

        self.delegate = SparkleDelegate.alloc().init()
        self.delegate.supportsGentleScheduledUpdateReminders = True
        self.delegate.config_name = self.mdbx.config_name
        self.delegate.mdbx = self.mdbx

        self.spu_controller = (
            SPUStandardUpdaterController.alloc().initWithUpdaterDelegate(
                self.delegate, userDriverDelegate=None
            )
        )

        update_interval = self.mdbx.get_conf("app", "update_notification_interval")
        self.set_update_check_interval(update_interval)

    def set_update_check_interval(self, value: float) -> None:
        if value > 0:
            self.spu_controller.updater.updateCheckInterval = value

        self.spu_controller.updater.automaticallyChecksForUpdates = value != 0

        if self.started:
            # reset countdown / timer to next update check to reflect new interval
            self.spu_controller.updater.resetUpdateCycle()

    def _start_updater(self) -> None:
        self.spu_controller.updater.startUpdater(None)

    async def check_for_updates(self) -> None:
        self.spu_controller.checkForUpdates(None)

    async def check_for_updates_in_background(self) -> None:
        self.spu_controller.updater.checkForUpdatesInBackground()


class AutoUpdaterFallback(AutoUpdaterBackend):
    """
    A manual implementation that uses the daemon's update checker. This can only notify
    us of available updates but cannot install updates by itself. Use this when
    management is handled by an external package manager (app store, pip, homebrew,
    etc).

    Under the hood, the daemon uses the GitHub releases API to check for new versions.
    We manage the GUI for presenting release notes, etc, ourselves.
    """

    def __init__(self, mdbx: MaestralProxy, app: SystemTrayApp) -> None:
        super().__init__(mdbx)
        self.app = app
        self.config_name = self.mdbx.config_name

    def _start_updater(self) -> None:
        self.app.add_background_task(self._periodic_check_for_updates)

    def set_update_check_interval(self, value: int) -> None:
        pass

    async def check_for_updates(self) -> None:
        progress = ProgressDialog("Checking for Updates", app=self.app)
        progress.raise_()

        try:
            res = await call_async_maestral(self.config_name, "check_for_updates")
        except UpdateCheckError as e:
            if not progress.visible:
                return  # aborted by user

            progress.close()
            return await self.app.alert_async(
                title=e.title, message=e.message, level="error"
            )

        if not progress.visible:
            return  # aborted by user

        progress.close()

        if res.update_available:
            self._show_update_dialog(res.latest_release, res.release_notes)
        elif not res.update_available:
            await self.app.alert_async(
                title="You’re up-to-date!",
                message=f"Maestral v{res.latest_release} is the newest version available.",
            )

    def _show_update_dialog(self, latest_release: str, release_notes: str) -> None:
        self.update_dialog = UpdateDialog(
            version=latest_release,
            release_notes=release_notes,
            app=self.app,
        )
        self.update_dialog.raise_()

    async def check_for_updates_in_background(self) -> None:
        last_update_check = self.mdbx.get_state("app", "update_notification_last")
        interval = self.mdbx.get_conf("app", "update_notification_interval")

        if (
            interval == 0 or time.time() - last_update_check < interval
        ):  # checks disabled
            return

        res = await call_async_maestral(self.config_name, "check_for_updates")

        if res.update_available:
            self.mdbx.set_state("app", "update_notification_last", time.time())
            self._show_update_dialog(res.latest_release, res.release_notes)

    async def _periodic_check_for_updates(self, sender: Any = None) -> None:
        while True:
            await asyncio.sleep(30 * 60)
            await self.check_for_updates_in_background()


class AutoUpdater:
    _backend: AutoUpdaterBackend

    def __init__(self, mdbx: MaestralProxy, app: SystemTrayApp) -> None:
        self.mdbx = mdbx
        self.app = app

        try:
            self._backend = AutoUpdaterSparkle(self.mdbx)
        except (ImportError, ValueError, OSError):
            self._backend = AutoUpdaterFallback(self.mdbx, self.app)

    def start_updater(self) -> None:
        self._backend.start_updater()

    async def check_for_updates(self, sender=None) -> None:
        await self._backend.check_for_updates()

    async def check_for_updates_in_background(self) -> None:
        await self._backend.check_for_updates_in_background()

    @property
    def last_update_check(self) -> float:
        return self.mdbx.get_state("app", "update_notification_last")

    @property
    def update_check_interval(self) -> int:
        return self.mdbx.get_conf("app", "update_notification_interval")

    @update_check_interval.setter
    def update_check_interval(self, value: int) -> None:
        self.mdbx.set_conf("app", "update_notification_interval", value)
        self._backend.set_update_check_interval(value)
