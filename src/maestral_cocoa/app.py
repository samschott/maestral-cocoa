# -*- coding: utf-8 -*-
# system imports
import os
import asyncio
import time
from subprocess import Popen
from datetime import datetime, timedelta

# external imports
import click
from toga.style.pack import Pack, FONT_SIZE_CHOICES
from maestral.constants import (
    IDLE,
    SYNCING,
    STOPPED,
    CONNECTING,
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
    TokenRevokedError,
    TokenExpiredError,
    MaestralApiError,
    SyncError,
)

# local imports
from . import __version__ as __gui_version__
from . import __author__, __url__
from .utils import (
    call_async,
    call_async_maestral,
    create_task,
)
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
from .dialogs import UpdateDialog, ProgressDialog, RelinkDialog
from .resources import APP_ICON_PATH, TRAY_ICON_PATH
from .autostart import AutoStart


# increase default font size from 12 to 13 points
Pack.validated_property("font_size", choices=FONT_SIZE_CHOICES, initial=13)


def name(cls):
    return cls.__name__


class MenuItemSnooze(MenuItem):
    def __init__(self, label, snooze_time, mdbx):
        super().__init__(label, action=self.snooze)
        self.mdbx = mdbx
        self.snooze_time = snooze_time

    def snooze(self, widget):
        self.mdbx.notification_snooze = self.snooze_time


class MaestralGui(SystemTrayApp):
    """A native GUI for the Maestral daemon."""

    PAUSE_TEXT = "Pause Syncing"
    RESUME_TEXT = "Resume Syncing"
    START_TEXT = "Start Syncing"

    icon_mapping = {
        IDLE: Icon(TRAY_ICON_PATH.format("idle")),
        SYNCING: Icon(TRAY_ICON_PATH.format("syncing")),
        STOPPED: Icon(TRAY_ICON_PATH.format("paused")),
        CONNECTING: Icon(TRAY_ICON_PATH.format("disconnected")),
        SYNC_ERROR: Icon(TRAY_ICON_PATH.format("info")),
        ERROR: Icon(TRAY_ICON_PATH.format("error")),
    }

    def __init__(self, config_name="maestral"):
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

    def startup(self):

        self._started = False
        self.mdbx = None

        self.setup_dialog = None
        self.settings_window = None
        self.sync_issues_window = None
        self.activity_window = None

        self.item_status = None
        self.item_email = None
        self.item_usage = None
        self.item_sync_issues = None
        self.item_pause = None

        self.autostart = AutoStart(self.config_name)

        self.menu = Menu()
        self._cached_status = CONNECTING
        self._cached_history = []
        self.tray = StatusBarItem(
            icon=self.icon_mapping.get(CONNECTING), menu=self.menu
        )

        self.setup_ui_unlinked()
        self.load_maestral()

    def set_icon(self, status):
        if status != self._cached_status:
            self.tray.icon = self.icon_mapping.get(status, self.icon_mapping[SYNCING])
            self._cached_status = status

    async def periodic_refresh_gui(self):

        while True:
            try:
                self.update_status()
                await self.update_error()

                await call_async_maestral(self.config_name, "status_change_longpoll")

            except CommunicationError:
                super().exit()

    async def periodic_check_for_updates(self, interval=30 * 60):
        while True:
            await asyncio.sleep(interval)
            await self.auto_check_for_updates()

    def on_menu_open(self, sender):
        self.update_snoozed()
        self.update_status()

    def load_maestral(self):

        self.mdbx = self.get_or_start_maestral_daemon()

        if self.mdbx.pending_link:
            self.setup_dialog = SetupDialog(self)
            self.setup_dialog.raise_()
            self.setup_dialog.on_close = self._on_setup_completed

        elif self.mdbx.pending_dropbox_folder:
            self.set_icon(ERROR)
            self.setup_dialog = DbxLocationDialog(self)
            self.setup_dialog.raise_()
            self.setup_dialog.on_close = self._on_setup_completed

        else:
            self.mdbx.start_sync()
            self.setup_ui_linked()

            create_task(self.periodic_refresh_gui())
            create_task(self.periodic_check_for_updates())

    def _on_setup_completed(self):

        if self.setup_dialog.exit_status == self.setup_dialog.ACCEPTED:
            self.mdbx.start_sync()

            self.setup_ui_linked()
            create_task(self.periodic_refresh_gui())
            create_task(self.periodic_check_for_updates())
        else:
            create_task(self.exit(stop_daemon=True))

    def get_or_start_maestral_daemon(self):

        res = start_maestral_daemon_process(self.config_name)

        if res == Start.Failed:
            title = "Could not start Maestral"
            message = (
                "Could not start or connect to sync daemon. Please try again "
                "and contact the developer if this issue persists."
            )
            self.alert(title, message, level="error")
            create_task(self.exit(stop_daemon=True))
        elif res == Start.AlreadyRunning:
            self._started = False
        elif res == Start.Ok:
            self._started = True

        return MaestralProxy(self.config_name)

    def setup_ui_unlinked(self):

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

        self.item_quit = MenuItem("Quit Maestral", action=self.exit)

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

    def setup_ui_linked(self):

        if not self.mdbx:
            return

        self.settings_window = SettingsWindow(self.mdbx, app=self)
        self.activity_window = ActivityWindow(self.mdbx, app=self)
        self.sync_issues_window = SyncIssuesWindow(self.mdbx, app=self)

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
            "Check for Updates...", action=self.on_check_for_updates_clicked
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
    def on_website_clicked(widget):
        """Open the Dropbox website."""
        click.launch("https://www.dropbox.com/")

    @staticmethod
    def on_help_clicked(widget):
        """Open the Dropbox help website."""
        click.launch("https://dropbox.com/help")

    def on_start_stop_clicked(self, widget):
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
            self._exec_dbx_location_dialog()

    def on_settings_clicked(self, widget):
        self.settings_window.raise_()

    def on_sync_issues_clicked(self, widget):
        self.sync_issues_window.raise_()

    def on_activity_clicked(self, widget):
        self.activity_window.raise_()

    def on_rebuild_clicked(self, widget):
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

    # ==== other callbacks  ============================================================

    async def auto_check_for_updates(self):

        last_update_check = self.mdbx.get_state("app", "update_notification_last")
        interval = self.mdbx.get_conf("app", "update_notification_interval")

        if (
            interval == 0 or time.time() - last_update_check < interval
        ):  # checks disabled
            return

        res = await call_async_maestral(self.config_name, "check_for_updates")
        if res["update_available"]:
            self.mdbx.set_state("app", "update_notification_last", time.time())
            self.show_update_dialog(res["latest_release"], res["release_notes"])

    async def on_check_for_updates_clicked(self, widget):

        progress = ProgressDialog("Checking for Updates", app=self)
        progress.raise_()

        res = await call_async_maestral(self.config_name, "check_for_updates")

        if not progress.visible:
            return  # aborted by user
        else:
            progress.close()

        if res["error"]:
            await self.alert_async(
                title="Could not check for updates", message=res["error"], level="error"
            )
        elif res["update_available"]:
            self.show_update_dialog(res["latest_release"], res["release_notes"])
        elif not res["update_available"]:
            message = "Maestral v{} is the newest version available.".format(
                res["latest_release"]
            )
            await self.alert_async(title="You’re up-to-date!", message=message)

    def show_update_dialog(self, latest_release, release_notes):

        self.update_dialog = UpdateDialog(
            version=latest_release,
            release_notes=release_notes,
            icon=self.icon,
        )
        self.update_dialog.raise_()

    # ==== periodic updates ============================================================

    def update_status(self):
        """Change icon according to status."""

        n_sync_errors = len(self.mdbx.sync_errors)
        status = self.mdbx.status
        is_paused = self.mdbx.paused

        # update icon
        if is_paused:
            new_icon = STOPPED
        elif n_sync_errors > 0 and status == IDLE:
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

    def update_snoozed(self):

        minutes = self.mdbx.notification_snooze

        if minutes > 0:
            eta = datetime.now() + timedelta(minutes=minutes)

            self.item_snooze.label = "Notifications snoozed until {}".format(
                eta.strftime("%H:%M")
            )
            self.menu_snooze.insert(0, MenuItemSeparator())
            self.menu_snooze.insert(0, self.item_resume_notifications)
        else:
            self.item_snooze.label = "Snooze Notifications"
            self.menu_snooze.remove(self.item_resume_notifications)
            self.menu_snooze.remove(MenuItemSeparator())

    async def update_error(self):
        errs = self.mdbx.fatal_errors

        if not errs:
            return

        self.mdbx.clear_fatal_errors()

        self.set_icon(ERROR)
        self.item_pause.label = self.RESUME_TEXT
        self.item_pause.enabled = False
        self.item_status.label = self.mdbx.status

        err = errs[-1]

        if err["type"] == name(NoDropboxDirError):
            self._exec_dbx_location_dialog()
        elif err["type"] == name(TokenRevokedError):
            self._exec_relink_dialog(RelinkDialog.REVOKED)
        elif err["type"] == name(TokenExpiredError):
            self._exec_relink_dialog(RelinkDialog.EXPIRED)
        elif (
            name(MaestralApiError) in err["inherits"]
            or name(SyncError) in err["inherits"]
        ):
            await self.alert_async(err["title"], err["message"], level="error")
        else:
            await self._exec_error_dialog(err)

    def _exec_dbx_location_dialog(self):
        self.setup_dialog = DbxLocationDialog(self)
        self.setup_dialog.raise_()
        self.setup_dialog.on_close = self._on_setup_completed

    def _exec_relink_dialog(self, reason):
        RelinkDialog(self, reason).raise_()

    async def _exec_error_dialog(self, err):

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

    async def exit(self, *args, stop_daemon=False):
        """Quits Maestral.

        :param bool stop_daemon: If ``True``, the sync daemon will be stopped when
            quitting the GUI, if ``False``, it will be kept alive. If ``None``, the
            daemon will only be stopped if it was started by the GUI.
        """

        # stop sync daemon if we started it or ``stop_daemon`` is ``True``
        if stop_daemon or self._started:
            await call_async(stop_maestral_daemon_process, self.config_name)

        super().exit()

    def restart(self, *args):
        """Restarts the Maestral GUI and sync daemon."""

        # schedule restart after current process has quit
        pid = os.getpid()  # get ID of current process
        Popen(
            f"lsof -p {pid} +r 1 &>/dev/null; "
            f"maestral gui --config-name='{self.config_name}'",
            shell=True,
        )

        # quit Maestral
        create_task(self.exit(stop_daemon=True))


def run(config_name="maestral"):
    app = MaestralGui(config_name)
    return app.main_loop()
