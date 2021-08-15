# -*- coding: utf-8 -*-

# system imports
import os
from subprocess import Popen
from datetime import datetime, timedelta
from typing import Any

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
from maestral.errors import (
    NoDropboxDirError,
    NotLinkedError,
    TokenRevokedError,
    TokenExpiredError,
    KeyringAccessError,
    MaestralApiError,
    SyncError,
)

# local imports
from . import __version__ as __gui_version__
from . import __author__, __url__
from .utils import call_async, call_async_maestral
from .private.widgets import (
    MenuItem,
    MenuItemSeparator,
    Menu,
    StatusBarItem,
    SystemTrayApp,
    Icon,
)
from .setup import SetupDialog
from .settings import SettingsWindow
from .syncissues import SyncIssuesWindow
from .activity import ActivityWindow
from .dbx_location_dialog import DbxLocationDialog
from .dialogs import RelinkDialog
from .resources import APP_ICON_PATH, resource_path
from .autostart import AutoStart
from .updater import AutoUpdater


def name(cls):
    return cls.__name__


class MenuItemSnooze(MenuItem):
    def __init__(self, label: str, snooze_time: float, mdbx: MaestralProxy) -> None:
        super().__init__(label, action=self.snooze)
        self.mdbx = mdbx
        self.snooze_time = snooze_time

    def snooze(self, widget: Any) -> None:
        self.mdbx.notification_snooze = self.snooze_time


class MaestralGui(SystemTrayApp):
    """A native GUI for the Maestral daemon."""

    PAUSE_TEXT = "Pause Syncing"
    RESUME_TEXT = "Resume Syncing"
    START_TEXT = "Start Syncing"

    icon_mapping = {
        IDLE: Icon(resource_path("systray-idle.pdf")),
        CONNECTED: Icon(resource_path("systray-idle.pdf")),
        SYNCING: Icon(resource_path("systray-syncing.pdf")),
        PAUSED: Icon(resource_path("systray-paused.pdf")),
        CONNECTING: Icon(resource_path("systray-disconnected.pdf")),
        SYNC_ERROR: Icon(resource_path("systray-info.pdf")),
        ERROR: Icon(resource_path("systray-error.pdf")),
    }

    def __init__(self, config_name: str = "maestral") -> None:
        self.config_name = config_name
        super().__init__(
            formal_name=APP_NAME,
            app_id=BUNDLE_ID,
            app_name="maestral_cocoa",
            icon=Icon(APP_ICON_PATH),
            author=__author__,
            version=__gui_version__,
            home_page=__url__,
        )

    def startup(self) -> None:

        self._started = False
        self._cached_status = CONNECTING

        self.mdbx = self.get_or_start_maestral_daemon()

        self.autostart = AutoStart(self.config_name)
        self.updater = AutoUpdater(self.mdbx, self)

        self.menu = Menu()
        self.tray = StatusBarItem(icon=self.icon_mapping[CONNECTING], menu=self.menu)

        self.setup_ui_unlinked()

        # Check if we are linked. Run setup if required.

        try:
            pending_link = self.mdbx.pending_link
        except KeyringAccessError:
            self.add_background_task(self.update_error)
            return

        pending_folder = self.mdbx.pending_dropbox_folder

        if pending_link or pending_folder:
            self.setup_dialog = SetupDialog(mdbx=self.mdbx, app=self)
            self.setup_dialog.raise_()
            self.setup_dialog.on_success = self.on_setup_completed
            self.setup_dialog.on_failure = self.exit_and_stop_daemon

            if not pending_link:
                # Skip link page programmatically.
                self.setup_dialog.goto_page(2)

        else:
            self.add_background_task(self.on_setup_completed)

    def set_icon(self, status: str) -> None:
        if status != self._cached_status:
            self.tray.icon = self.icon_mapping.get(status, self.icon_mapping[SYNCING])
            self._cached_status = status

    async def on_menu_open(self, sender: Any = None) -> None:
        await self.update_snoozed()
        await self.update_status()

    async def on_setup_completed(self, sender: Any = None) -> None:
        self.mdbx.start_sync()
        self.setup_ui_linked()
        self.updater.start_updater()
        await self.periodic_refresh_gui()

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
            super().exit()
        elif res == Start.AlreadyRunning:
            self._started = False
        elif res == Start.Ok:
            self._started = True

        return MaestralProxy(self.config_name)

    def setup_ui_unlinked(self) -> None:

        self.menu.clear()

        # ------------- populate context menu -------------------
        self.item_folder = MenuItem("Open Dropbox Folder")
        self.item_website = MenuItem(
            "Launch Dropbox Website", action=self.on_website_clicked
        )

        self.item_status = MenuItem("Setting up...")

        self.item_login = MenuItem(
            "Start on login", checkable=True, action=lambda s: self.autostart.toggle()
        )
        self.item_login.checked = self.autostart.enabled
        self.item_help = MenuItem("Help Center", action=self.on_help_clicked)

        self.item_quit = MenuItem(
            "Quit Maestral", action=self.exit, shortcut=toga.Key.MOD_1 + "q"
        )

        self.menu.add(
            self.item_folder,
            self.item_website,
            MenuItemSeparator(),
            self.item_status,
            MenuItemSeparator(),
            self.item_login,
            self.item_help,
            MenuItemSeparator(),
            self.item_quit,
        )

    def setup_ui_linked(self) -> None:

        self.settings_window = SettingsWindow(mdbx=self.mdbx, app=self)
        self.activity_window = ActivityWindow(mdbx=self.mdbx, app=self)
        self.sync_issues_window = SyncIssuesWindow(mdbx=self.mdbx, app=self)

        # ------------- update context menu -------------------

        # remove unneeded items
        self.menu.remove(self.item_login)

        # update existing menu items
        self.item_folder.action = lambda s: click.launch(self.mdbx.dropbox_path)
        self.item_status.label = IDLE

        # add new menu items
        self.item_email = MenuItem(self.mdbx.get_state("account", "email"))
        self.item_usage = MenuItem(self.mdbx.get_state("account", "usage"))
        self.item_pause = MenuItem(
            self.RESUME_TEXT if self.mdbx.paused else self.PAUSE_TEXT,
            action=self.on_start_stop_clicked,
        )
        self.item_activity = MenuItem(
            "Show Recent Changes...", action=self.on_activity_clicked
        )

        self.item_snooze30 = MenuItemSnooze("For the next 30 minutes", 30, self.mdbx)
        self.item_snooze60 = MenuItemSnooze("For the next hour", 60, self.mdbx)
        self.item_snooze480 = MenuItemSnooze("For the next 8 hours", 480, self.mdbx)
        self.item_resume_notifications = MenuItemSnooze(
            "Turn on notifications", 0, self.mdbx
        )
        self.item_snooze_separator = MenuItemSeparator()

        self.menu_snooze = Menu(
            items=[self.item_snooze30, self.item_snooze60, self.item_snooze480]
        )
        self.item_snooze = MenuItem("Snooze Notifications", submenu=self.menu_snooze)

        self.item_sync_issues = MenuItem(
            "Show Sync Issues...", action=self.on_sync_issues_clicked
        )
        self.item_rebuild = MenuItem("Rebuild index...", action=self.on_rebuild_clicked)

        self.item_settings = MenuItem("Preferences...", action=self.on_settings_clicked)
        self.item_updates = MenuItem(
            "Check for Updates...", action=self.updater.check_for_updates
        )

        if self._started:
            self.item_quit.label = "Quit Maestral"
        else:
            self.item_quit.label = "Quit Maestral GUI"

        self.menu.insert(2, MenuItemSeparator())
        self.menu.insert(3, self.item_email)
        self.menu.insert(4, self.item_usage)
        self.menu.insert(7, self.item_pause)
        self.menu.insert(8, self.item_activity)
        self.menu.insert(10, self.item_snooze)
        self.menu.insert(11, self.item_sync_issues)
        self.menu.insert(12, self.item_rebuild)
        self.menu.insert(13, MenuItemSeparator())
        self.menu.insert(14, self.item_settings)
        self.menu.insert(15, self.item_updates)

        self.menu.on_open = self.on_menu_open

        # --------------- switch to idle icon -------------------
        self.set_icon(IDLE)

    # ==== callbacks menu items ========================================================

    @staticmethod
    def on_website_clicked(widget: Any) -> None:
        """Open the Dropbox website."""
        click.launch("https://www.dropbox.com/")

    @staticmethod
    def on_help_clicked(widget: Any) -> None:
        """Open the Dropbox help website."""
        click.launch(f"{__url__}/docs")

    def on_start_stop_clicked(self, widget: Any) -> None:
        """Pause / resume syncing on menu item clicked."""

        try:
            if self.item_pause.label == self.PAUSE_TEXT:
                self.mdbx.stop_sync()
                self.item_pause.label = self.RESUME_TEXT
            elif self.item_pause.label == self.RESUME_TEXT:
                self.mdbx.start_sync()
                self.item_pause.label = self.PAUSE_TEXT
            elif self.item_pause.label == self.START_TEXT:
                self.mdbx.start_sync()
                self.item_pause.label = self.PAUSE_TEXT
        except NoDropboxDirError:
            self.add_background_task(self._exec_dbx_location_dialog)
        except NotLinkedError:
            self.add_background_task(self.restart)

    def on_settings_clicked(self, widget: Any) -> None:
        self.settings_window.raise_()

    def on_sync_issues_clicked(self, widget: Any) -> None:
        self.sync_issues_window.raise_()

    def on_activity_clicked(self, widget: Any) -> None:
        self.activity_window.raise_()

    def on_rebuild_clicked(self, widget: Any) -> None:
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

    async def periodic_refresh_gui(self, sender: Any = None) -> None:

        while True:
            try:
                await self.update_status()
                await self.update_error()
                await call_async_maestral(self.config_name, "status_change_longpoll")
            except CommunicationError:
                super().exit()

    async def update_status(self, sender: Any = None) -> None:
        """Change icon according to status."""

        n_sync_errors = len(self.mdbx.sync_errors)
        status = self.mdbx.status
        is_paused = self.mdbx.paused

        # update icon
        if n_sync_errors > 0 and status == IDLE:
            new_icon = SYNC_ERROR
        else:
            new_icon = status

        self.set_icon(new_icon)

        # update action texts
        if self.menu.visible:
            if n_sync_errors > 0:
                self.item_sync_issues.label = f"Show Sync Issues ({n_sync_errors})..."
            else:
                self.item_sync_issues.label = "Show Sync Issues..."

            self.item_pause.label = self.RESUME_TEXT if is_paused else self.PAUSE_TEXT
            self.item_usage.label = self.mdbx.get_state("account", "usage")
            self.item_email.label = self.mdbx.get_state("account", "email")

            self.item_status.label = status

    async def update_snoozed(self, sender: Any = None) -> None:

        minutes = self.mdbx.notification_snooze

        if minutes > 0:
            eta = datetime.now() + timedelta(minutes=minutes)

            self.item_snooze.label = "Notifications snoozed until {}".format(
                eta.strftime("%H:%M")
            )
            self.menu_snooze.insert(0, self.item_snooze_separator)
            self.menu_snooze.insert(0, self.item_resume_notifications)
        else:
            self.item_snooze.label = "Snooze Notifications"
            self.menu_snooze.remove(self.item_resume_notifications)
            self.menu_snooze.remove(self.item_snooze_separator)

    async def update_error(self, sender: Any = None) -> None:
        errs = self.mdbx.fatal_errors

        if not errs:
            return

        self.mdbx.clear_fatal_errors()

        self.set_icon(ERROR)

        if self.item_pause:
            self.item_pause.label = self.RESUME_TEXT
        if self.item_status:
            self.item_status.label = self.mdbx.status

        err = errs[-1]

        if err["type"] == name(NoDropboxDirError):
            await self._exec_dbx_location_dialog()
        elif err["type"] == name(TokenRevokedError):
            await self._exec_relink_dialog(RelinkDialog.REVOKED)
        elif err["type"] == name(TokenExpiredError):
            await self._exec_relink_dialog(RelinkDialog.EXPIRED)
        elif (
            name(SyncError) in err["inherits"]
            or name(MaestralApiError) in err["inherits"]
        ):
            filename = err["dbx_path"] or err["local_path"]
            if filename:
                message = f"Path: {filename}\n" + err["message"]
            else:
                message = err["message"]
            await self.alert_async(err["title"], message, level="error")
        else:
            # We don't know this error yet. Show a full stacktrace dialog.
            await self._exec_error_dialog(err)

    async def _exec_dbx_location_dialog(self, sender: Any = None) -> None:
        self.location_dialog = DbxLocationDialog(mdbx=self.mdbx, app=self)
        self.location_dialog.raise_()
        self.location_dialog.on_success = lambda s: self.mdbx.start_sync()
        self.location_dialog.on_failure = self.exit_and_stop_daemon

    async def _exec_relink_dialog(self, reason: int) -> None:
        self.rld = RelinkDialog(self.mdbx, self, reason).raise_()

    async def _exec_error_dialog(self, err: dict) -> None:

        title = "An unexpected error occurred"
        message = (
            "You can report this issue together with the traceback below on GitHub. "
            "Please restart Maestral to continue syncing."
        )
        details = err["traceback"].replace("\n", "<br />")

        await self.alert_async(
            title,
            message,
            details=details,
            button_labels=("Close",),
            level="error",
        )

    # ==== quit functions ==============================================================

    async def exit_and_stop_daemon(self, sender: Any = None) -> None:
        """Stops the sync daemon and quits Maestral."""
        await call_async(stop_maestral_daemon_process, self.config_name)
        super().exit()

    async def exit(self, sender: Any = None) -> None:
        """Quits Maestral. Stops the sync daemon only if we started it ourselves."""

        if self._started:
            await call_async(stop_maestral_daemon_process, self.config_name)

        super().exit()

    async def restart(self, sender: Any = None) -> None:
        """Restarts the Maestral GUI and sync daemon."""

        # Schedule restart after current process has quit
        pid = os.getpid()  # get ID of current process
        Popen(
            f"lsof -p {pid} +r 1 &>/dev/null; "
            f"maestral gui --config-name='{self.config_name}'",
            shell=True,
        )

        # Quit Maestral.
        await self.exit_and_stop_daemon()


def run(config_name: str = "maestral") -> None:
    app = MaestralGui(config_name)
    return app.main_loop()
