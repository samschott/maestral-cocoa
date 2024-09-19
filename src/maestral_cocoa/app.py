from __future__ import annotations

# system imports
import os
import sys
import gc
from traceback import format_exception
from subprocess import Popen
from datetime import datetime, timedelta
from typing import Type, TypeVar

# external imports
import click
import toga
from maestral.constants import (
    IDLE,
    SYNCING,
    PAUSED,
    CONNECTING,
    CONNECTED,
    SYNC_ERROR,
    ERROR,
    APP_NAME,
    BUNDLE_ID,
)
from maestral.daemon import (
    start_maestral_daemon_process,
    stop_maestral_daemon_process,
    MaestralProxy,
    Start,
    CommunicationError,
)
from maestral.exceptions import (
    NoDropboxDirError,
    NotLinkedError,
    TokenRevokedError,
    TokenExpiredError,
    KeyringAccessError,
    MaestralApiError,
)
from mypy.dmypy.client import action

# local imports
from . import __version__ as __gui_version__
from . import __author__, __url__
from .utils import call_async, call_async_maestral
from .setup import SetupDialog
from .settings import SettingsWindow
from .syncissues import SyncIssuesWindow
from .activity import ActivityWindow
from .dbx_location_dialog import DbxLocationDialog
from .dialogs import RelinkDialog
from .resources import APP_ICON_PATH, resource_path
from .autostart import AutoStart
from .updater import AutoUpdater


MaestralWindow = TypeVar(
    "MaestralWindow", SettingsWindow, SyncIssuesWindow, ActivityWindow
)


def _build_snooze_command(snooze_time: float, maestral_proxy:  MaestralProxy, **kwargs) -> toga.Command:

    def snooze(interface, *args, **kwargs) -> None:
        maestral_proxy.notification_snooze = snooze_time

    return toga.Command(action=snooze, **kwargs)


class MaestralGui(toga.App):
    """A native GUI for the Maestral daemon."""

    PAUSE_TEXT = "Pause Syncing"
    RESUME_TEXT = "Resume Syncing"
    START_TEXT = "Start Syncing"

    def __init__(self, config_name: str = "maestral") -> None:
        self.config_name = config_name
        super().__init__(
            formal_name=APP_NAME,
            app_id=BUNDLE_ID,
            app_name="maestral_cocoa",
            icon=APP_ICON_PATH,
            author=__author__,
            version=__gui_version__,
            home_page=__url__,
        )

    def startup(self) -> None:
        self.icon_mapping = {
            IDLE: toga.Icon(resource_path("systray-idle.pdf")),
            CONNECTED: toga.Icon(resource_path("systray-idle.pdf")),
            SYNCING: toga.Icon(resource_path("systray-syncing.pdf")),
            PAUSED: toga.Icon(resource_path("systray-paused.pdf")),
            CONNECTING: toga.Icon(resource_path("systray-disconnected.pdf")),
            SYNC_ERROR: toga.Icon(resource_path("systray-info.pdf")),
            ERROR: toga.Icon(resource_path("systray-error.pdf")),
        }

        self.main_window = None

        self._daemon_started = False
        self._cached_status = CONNECTING
        self._linked_ui = False

        self.mdbx = self.get_or_start_maestral_daemon()

        self.autostart = AutoStart(self.config_name)
        self.updater = AutoUpdater(self.mdbx, self)

        self.status_icon = toga.MenuStatusIcon(icon=self.icon_mapping[CONNECTING])
        self.status_icons.add(self.status_icon)

        # Check if we are linked. Run setup if required.
        try:
            pending_link = self.mdbx.pending_link
        except KeyringAccessError:
            self.add_background_task(self.update_error)
            return

        pending_folder = self.mdbx.pending_dropbox_folder

        if pending_link or pending_folder:
            setup_dialog = SetupDialog(mdbx=self.mdbx)
            setup_dialog.show()
            setup_dialog.on_success = self.on_setup_completed
            setup_dialog.on_failure = self.exit_and_stop_daemon

            if not pending_link:
                # Skip link page programmatically.
                setup_dialog.goto_page(2)

        else:
            self.add_background_task(self.on_setup_completed)

    def set_icon(self, status: str) -> None:
        if status != self._cached_status:
            self.status_icon.icon = self.icon_mapping.get(
                status, self.icon_mapping[SYNCING]
            )
            self._cached_status = status

    async def on_menu_open(self, interface, *args, **kwargs) -> None:
        await self.update_snoozed(self)
        await self.update_status(self)

    async def on_setup_completed(self, interface, *args, **kwargs) -> None:
        self.mdbx.start_sync()
        self.updater.start_updater()
        self._linked_ui = True
        self.set_up_commands()
        await self.periodic_refresh_gui(self)

    def get_or_start_maestral_daemon(self) -> MaestralProxy:
        res = start_maestral_daemon_process(self.config_name)

        if res == Start.Failed:
            title = "Could not start Maestral"
            message = (
                "Could not start or connect to sync daemon. Please try again "
                "and contact the developer if this issue persists."
            )
            self.alert(title, message, level="error")
            stop_maestral_daemon_process(self.config_name)
            # super().exit() fails on toga-cocoa because the event loop has not yet been
            # started. Call sys.exit() instead.
            sys.exit(0)
        elif res == Start.AlreadyRunning:
            self._daemon_started = False
        elif res == Start.Ok:
            self._daemon_started = True

        return MaestralProxy(self.config_name)

    def on_open_clicked(self, interface, *args, **kwargs):
        click.launch(self.mdbx.dropbox_path)

    def set_up_commands(self) -> None:
        self.item_folder = toga.Command(
            text="Open Dropbox Folder",
            group=self.status_icon,
            action=self.on_open_clicked,
            section=0,
            order=0,
        )
        self.item_website = toga.Command(
            text="Launch Dropbox Website",
            action=self.on_website_clicked,
            group=self.status_icon,
            section=0,
            order=1,
        )

        self.item_email = toga.Command(
            text=self.mdbx.get_state("account", "email"),
            group=self.status_icon,
            action=None,
            section=1,
            order=0,
        )
        self.item_usage = toga.Command(
            text=self.mdbx.get_state("account", "usage"),
            group=self.status_icon,
            action=None,
            section=1,
            order=1,
        )

        self.item_status = toga.Command(
            text="Setting up...",
            group=self.status_icon,
            action=None,
            section=2,
            order=0,
        )
        self.item_pause = toga.Command(
            text=self.RESUME_TEXT if self.mdbx.paused else self.PAUSE_TEXT,
            action=self.on_start_stop_clicked,
            group=self.status_icon,
            section=2,
            order=1,
        )
        self.item_activity = toga.Command(
            text="Show Recent Changes...",
            action=self.on_activity_clicked,
            group=self.status_icon,
            section=2,
            order=2,
        )
        self.item_sync_issues = toga.Command(
            text="Show Sync Issues...",
            group=self.status_icon,
            action=None,
            section=2,
            order=3,
        )

        self.group_snooze = toga.Group(
            text="Snooze Notifications",
            parent=self.status_icon,
            section=3,
        )
        self.item_snooze30 = _build_snooze_command(
            text="For the next 30 minutes",
            snooze_time=30,
            maestral_proxy=self.mdbx,
            group=self.group_snooze,
            section=0,
            order=0,
        )
        self.item_snooze60 = _build_snooze_command(
            text="For the next hour",
            snooze_time=60,
            maestral_proxy=self.mdbx,
            group=self.group_snooze,
            section=0,
            order=1,
        )
        self.item_snooze480 = _build_snooze_command(
            text="For the next 8 hours",
            snooze_time=480,
            maestral_proxy=self.mdbx,
            group=self.group_snooze,
            section=0,
            order=2,
        )
        self.item_resume_notifications = _build_snooze_command(
            text="Turn on notifications",
            snooze_time=0,
            maestral_proxy=self.mdbx,
            group=self.group_snooze,
            section=0,
            order=3,
        )
        self.item_rebuild = toga.Command(
            text="Rebuild Index...",
            action=self.on_rebuild_clicked,
            group=self.status_icon,
            section=3,
            order=1,
        )

        self.item_settings = toga.Command(
            text="Preferences...",
            action=self.on_settings_clicked,
            group=self.status_icon,
            section=4,
            order=0,
        )
        self.item_updates = toga.Command(
            text="Check for Updates...",
            action=self.updater.check_for_updates,
            group=self.status_icon,
            section=4,
            order=1,
        )
        self.item_help = toga.Command(
            text="Help Center",
            action=self.on_help_clicked,
            group=self.status_icon,
            section=4,
            order=2,
        )

        self.status_icons.commands.add(
            self.item_folder,
            self.item_website,
            self.item_email,
            self.item_usage,
            self.item_status,
            self.item_pause,
            self.item_activity,
            self.item_sync_issues,
            self.item_snooze30,
            self.item_snooze60,
            self.item_snooze480,
            self.item_rebuild,
            self.item_settings,
            self.item_updates,
            self.item_help,
        )

        # --------------- switch to idle icon -------------------
        self.set_icon(IDLE)

    # ==== callbacks menu items ========================================================

    @staticmethod
    def on_website_clicked(interface, *args, **kwargs) -> None:
        """Open the Dropbox website."""
        click.launch("https://www.dropbox.com/")

    @staticmethod
    def on_help_clicked(interface, *args, **kwargs) -> None:
        """Open the Dropbox help website."""
        click.launch(f"{__url__}/docs")

    def on_start_stop_clicked(self, interface, *args, **kwargs) -> None:
        """Pause / resume syncing on menu item clicked."""
        try:
            if self.item_pause.text == self.PAUSE_TEXT:
                self.mdbx.stop_sync()
                self.item_pause.text = self.RESUME_TEXT
            elif self.item_pause.text == self.RESUME_TEXT:
                self.mdbx.start_sync()
                self.item_pause.text = self.PAUSE_TEXT
            elif self.item_pause.text == self.START_TEXT:
                self.mdbx.start_sync()
                self.item_pause.text = self.PAUSE_TEXT
        except NoDropboxDirError:
            self.add_background_task(self._exec_dbx_location_dialog)
        except NotLinkedError:
            self.add_background_task(self.restart)

    def _get_or_create_window(self, clazz: Type[MaestralWindow]) -> MaestralWindow:
        for window in self.windows:
            if isinstance(window, clazz):
                return window

        return clazz(mdbx=self.mdbx)

    def on_settings_clicked(self, interface, *args, **kwargs) -> None:
        self._get_or_create_window(SettingsWindow).show()

    def on_sync_issues_clicked(self, interface, *args, **kwargs) -> None:
        self._get_or_create_window(SyncIssuesWindow).show()

    def on_activity_clicked(self, interface, *args, **kwargs) -> None:
        self._get_or_create_window(ActivityWindow).show()

    def on_rebuild_clicked(self, interface, *args, **kwargs) -> None:
        choice = self.alert(
            title="Rebuilt Maestral's sync index?",
            message=(
                "Rebuilding the index may take several minutes, depending on the size "
                "of your Dropbox. Any changes to local files will be synced once "
                "rebuilding has completed."
            ),
            button_labels=("Rebuild", "Cancel"),
            icon=self.icon,
        )

        if choice == 0:
            self.mdbx.rebuild_index()

    # ==== periodic refresh of gui =====================================================

    async def periodic_refresh_gui(self, interface, *args, **kwargs) -> None:
        while True:
            try:
                await self.update_status(self)
                await self.update_error(self)
                await call_async_maestral(self.config_name, "status_change_longpoll")
                gc.collect()
            except CommunicationError:
                super().exit()

    async def update_status(self, interface, *args, **kwargs) -> None:
        """Change icon according to status."""
        n_sync_errors = len(self.mdbx.sync_errors)
        has_sync_issues = n_sync_errors > 0
        status = self.mdbx.status
        is_paused = self.mdbx.paused

        # update icon
        if has_sync_issues and status == IDLE:
            new_icon = SYNC_ERROR
        else:
            new_icon = status

        self.set_icon(new_icon)

        # update action texts
        if has_sync_issues:
            self.item_sync_issues.action = self.on_sync_issues_clicked
            self.item_sync_issues.text = f"Show Sync Issues ({n_sync_errors})..."
        else:
            self.item_sync_issues.action = None
            self.item_sync_issues.text = f"No Sync Issues"

        self.item_pause.text = self.RESUME_TEXT if is_paused else self.PAUSE_TEXT
        self.item_usage.text = self.mdbx.get_state("account", "usage")
        self.item_email.text = self.mdbx.get_state("account", "email")

        self.item_status.text = status

    async def update_snoozed(self, interface, *args, **kwargs) -> None:
        minutes = self.mdbx.notification_snooze

        if minutes > 0:
            eta = datetime.now() + timedelta(minutes=minutes)

            self.item_snooze.text = "Notifications snoozed until {}".format(
                eta.strftime("%H:%M")
            )
            self.menu_snooze.insert(0, self.item_snooze_separator)
            self.menu_snooze.insert(0, self.item_resume_notifications)
        else:
            self.item_snooze.text = "Snooze Notifications"
            self.menu_snooze.remove(self.item_resume_notifications)
            self.menu_snooze.remove(self.item_snooze_separator)

    async def update_error(self, interface, *args, **kwargs) -> None:
        errs = self.mdbx.fatal_errors

        if not errs:
            return

        self.mdbx.clear_fatal_errors()

        self.set_icon(ERROR)

        if self._linked_ui:
            self.item_pause.text = self.RESUME_TEXT
            self.item_status.text = self.mdbx.status

        err = errs[-1]

        if isinstance(err, NoDropboxDirError):
            await self._exec_dbx_location_dialog(self)
        elif isinstance(err, TokenRevokedError):
            await self._exec_relink_dialog(RelinkDialog.REVOKED)
        elif isinstance(err, TokenExpiredError):
            await self._exec_relink_dialog(RelinkDialog.EXPIRED)
        elif isinstance(err, MaestralApiError):
            filename = err.dbx_path or err.local_path
            if filename:
                message = f"Path: {filename}\n" + err.message
            else:
                message = err.message
            await self.alert_async(err.title, message, level="error")
        else:
            # We don't know this error yet. Show a full stacktrace dialog.
            await self._exec_error_dialog(err)

    async def _exec_dbx_location_dialog(self, interface, *args, **kwargs) -> None:

        def start_sync_callback(a, *aa, **kwa):
            self.mdbx.start_sync()

        location_dialog = DbxLocationDialog(mdbx=self.mdbx)
        location_dialog.show()
        location_dialog.on_success = start_sync_callback
        location_dialog.on_failure = self.exit_and_stop_daemon

    async def _exec_relink_dialog(self, reason: int) -> None:
        RelinkDialog(self.mdbx, reason).show()

    async def _exec_error_dialog(self, err: Exception) -> None:
        title = "An unexpected error occurred"
        message = (
            "You can report this issue together with the traceback below on GitHub. "
            "Please restart Maestral to continue syncing."
        )

        details: str | None

        if err.__traceback__:
            details = "".join(format_exception(err.__class__, err, err.__traceback__))
        else:
            details = None

        await self.alert_async(
            title,
            message,
            details=details,
            button_labels=("Close",),
            level="error",
        )

    # ==== quit functions ==============================================================

    async def exit_and_stop_daemon(self, interface, *args, **kwargs) -> None:
        """Stops the sync daemon and quits Maestral."""
        await call_async(stop_maestral_daemon_process, self.config_name)
        super().exit()

    def exit(self, interface, *args, **kwargs) -> None:
        """Quits Maestral. Stops the sync daemon only if we started it ourselves."""
        # Note: Keep this method synchrounous for compatibility with the parent class.

        async def async_exit(interface, *args, **kwargs) -> None:
            if self._daemon_started:
                stop_maestral_daemon_process(self.config_name)
            super(MaestralGui, self).exit()

        self.add_background_task(async_exit)

    async def restart(self, interface, *args, **kwargs) -> None:
        """Restarts the Maestral GUI and sync daemon."""
        # Schedule restart after current process has quit
        pid = os.getpid()  # get ID of current process
        Popen(
            f"lsof -p {pid} +r 1 &>/dev/null; "
            f"maestral gui --config-name='{self.config_name}'",
            shell=True,
        )

        # Quit Maestral.
        await self.exit_and_stop_daemon(self)


def run(config_name: str = "maestral") -> None:
    app = MaestralGui(config_name)
    return app.main_loop()
