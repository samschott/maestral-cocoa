# -*- coding: utf-8 -*-
# system imports
import os
import os.path as osp
import asyncio
import platform
import time
from subprocess import Popen
from datetime import datetime, timedelta

# external imports
import click
import toga
from toga.style.pack import Pack, FONT_SIZE_CHOICES
from maestral.utils.autostart import AutoStart
from maestral.constants import (
    IDLE, SYNCING, PAUSED, STOPPED, DISCONNECTED, SYNC_ERROR, ERROR,
    APP_NAME, BUNDLE_ID
)
from maestral.daemon import (
    start_maestral_daemon_process,
    stop_maestral_daemon_process,
    get_maestral_proxy,
    Start,
    Pyro5
)
from maestral import __author__, __url__
from maestral import __version__ as __daemon_version__

# local imports
from maestral_cocoa import __version__ as __gui_version__
from maestral_cocoa.utils import async_call, run_async, run_maestral_async
from maestral_cocoa.private.widgets import (
    MenuItem, MenuItemSeparator, Menu, StatusBarItem, SystemTrayApp
)
from maestral_cocoa.setup import SetupDialog
from maestral_cocoa.settings import SettingsWindow
from maestral_cocoa.syncissues import SyncIssuesWindow
from maestral_cocoa.dbx_location_dialog import DbxLocationDialog
from maestral_cocoa.dialogs import Dialog, UpdateDialog, ProgressDialog, RelinkDialog
from maestral_cocoa.resources import APP_ICON_PATH, TRAY_ICON_PATH


Pack.validated_property('font_size', choices=FONT_SIZE_CHOICES, initial=13)


class MaestralGui(SystemTrayApp):
    """A Qt GUI for the Maestral daemon."""

    PAUSE_TEXT = 'Pause Syncing'
    RESUME_TEXT = 'Resume Syncing'
    START_TEXT = 'Start Syncing'

    icon_mapping = {
        IDLE: toga.Icon(TRAY_ICON_PATH.format('idle')),
        SYNCING: toga.Icon(TRAY_ICON_PATH.format('syncing')),
        PAUSED: toga.Icon(TRAY_ICON_PATH.format('paused')),
        STOPPED: toga.Icon(TRAY_ICON_PATH.format('error')),
        DISCONNECTED: toga.Icon(TRAY_ICON_PATH.format('disconnected')),
        SYNC_ERROR: toga.Icon(TRAY_ICON_PATH.format('info')),
        ERROR: toga.Icon(TRAY_ICON_PATH.format('error')),
    }

    config_name = 'maestral'

    def startup(self):

        self._started = False
        self.mdbx = None

        self.setup_dialog = None
        self.settings_window = None
        self.sync_issues_window = None
        self.rebuild_dialog = None

        self.item_status = None
        self.item_email = None
        self.item_usage = None
        self.item_sync_issues = None
        self.item_pause = None
        self.menu_recent_files = None

        self.periodic_updates = True
        self.refresh_interval = 2

        self.autostart = AutoStart(self.config_name, gui=True)

        self.menu = Menu()
        self._cached_status = DISCONNECTED
        self._cached_recent_changes = []
        self.tray = StatusBarItem(self.icon_mapping.get(DISCONNECTED), menu=self.menu)

        self.setup_ui_unlinked()
        self.load_maestral()

    def set_icon(self, status):
        if status != self._cached_status:
            self.tray.icon = self.icon_mapping.get(status, self.icon_mapping[SYNCING])
            self._cached_status = status

    @async_call
    async def periodic_refresh_gui(self):

        while self.periodic_updates:
            try:
                self.update_status()
                self.update_error()
            except Pyro5.errors.CommunicationError:
                super().exit()

            await asyncio.sleep(self.refresh_interval)

    def on_menu_open(self, sender):
        self.update_recent_files()
        self.update_snoozed()
        self.refresh_interval = 0.5
        self.update_status()

    def on_menu_close(self, sender):
        self.refresh_interval = 2

    @async_call
    async def periodic_check_for_updates(self, interval=30 * 60):
        while self.periodic_updates:
            await asyncio.sleep(interval)
            await self.auto_check_for_updates()

    @async_call
    async def load_maestral(self):

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
            self.periodic_refresh_gui()
            self.periodic_check_for_updates()

    def _on_setup_completed(self):

        if self.setup_dialog.exit_status == self.setup_dialog.ACCEPTED:
            self.mdbx.start_sync()

            self.setup_ui_linked()
            self.periodic_refresh_gui()
            self.periodic_check_for_updates()
        else:
            self.exit(stop_daemon=True)

    def get_or_start_maestral_daemon(self):

        res = start_maestral_daemon_process(self.config_name)

        if res == Start.Failed:
            title = 'Could not start Maestral'
            message = ('Could not start or connect to sync daemon. Please try again '
                       'and contact the developer if this issue persists.')
            self.alert(title, message, level='error')
            self.exit(stop_daemon=True)
        elif res == Start.AlreadyRunning:
            self._started = False
        elif res == Start.Ok:
            self._started = True

        return get_maestral_proxy(self.config_name)

    def setup_ui_unlinked(self):

        self.menu.clear()

        # ------------- populate context menu -------------------
        item_folder = MenuItem('Open Dropbox Folder')
        item_website = MenuItem('Launch Dropbox Website', action=self.on_website_clicked)

        s0 = MenuItemSeparator()

        item_status = MenuItem('Setting up...')

        s1 = MenuItemSeparator()

        item_login = MenuItem('Start on login', checkable=True,
                              action=lambda s: self.autostart.toggle())
        item_login.checked = self.autostart.enabled
        item_help = MenuItem('Help Center', action=self.on_help_clicked)

        s2 = MenuItemSeparator()

        item_quit = MenuItem('Quit Maestral', action=lambda s: self.exit())

        self.menu.add(
            item_folder, item_website, s0,
            item_status, s1,
            item_login, item_help, s2,
            item_quit
        )

    def setup_ui_linked(self):

        if not self.mdbx:
            return

        self.settings_window = SettingsWindow(self.mdbx, app=self)

        # ------------- populate context menu -------------------

        self.menu.clear()

        item_folder = MenuItem('Open Dropbox Folder', action=lambda s: click.launch(self.mdbx.dropbox_path))
        item_website = MenuItem('Launch Dropbox Website', action=self.on_website_clicked)

        s0 = MenuItemSeparator()

        self.item_email = MenuItem(self.mdbx.get_state('account', 'email'))
        self.item_usage = MenuItem(self.mdbx.get_state('account', 'usage'))

        s1 = MenuItemSeparator()

        self.item_status = MenuItem(IDLE)
        initial_text = self.RESUME_TEXT if self.mdbx.paused else self.PAUSE_TEXT
        self.item_pause = MenuItem(initial_text, action=self.on_start_stop_clicked)
        self.menu_recent_files = Menu()
        self.item_recent_files = MenuItem('Recently Changed Files', submenu=self.menu_recent_files)

        s2 = MenuItemSeparator()

        self.item_snooze = MenuItem('Snooze Notifications')

        def snooze_for(minutes):
            self.mdbx.notification_snooze = minutes

        self.item_snooze30 = MenuItem('For the next 30 minutes', action=lambda s: snooze_for(30))
        self.item_snooze60 = MenuItem('For the next hour', action=lambda s: snooze_for(60))
        self.item_snooze480 = MenuItem('For the next 8 hours', action=lambda s: snooze_for(480))

        self.menu_snooze = Menu(items=[self.item_snooze30, self.item_snooze60, self.item_snooze480])
        self.item_snooze.submenu = self.menu_snooze

        self.item_resume_notifications = MenuItem('Turn on notifications', action=lambda s: snooze_for(0))
        self.separator_snooze = MenuItemSeparator()

        self.item_sync_issues = MenuItem('Show Sync Issues...', action=self.on_sync_issues_clicked)
        item_rebuild = MenuItem('Rebuild index...', action=self.on_rebuild_clicked)

        s3 = MenuItemSeparator()

        item_settings = MenuItem('Preferences...', action=self.on_settings_clicked)
        self.item_updates = MenuItem('Check for Updates...', action=self.on_check_for_updates_clicked)
        item_help = MenuItem('Help Center', action=self.on_help_clicked)

        s4 = MenuItemSeparator()

        if self._started:
            item_quit = MenuItem('Quit Maestral', action=self.exit)
        else:
            item_quit = MenuItem('Quit Maestral GUI', action=self.exit)

        self.menu.add(
            item_folder, item_website, s0,
            self.item_email, self.item_usage, s1,
            self.item_status, self.item_pause, self.item_recent_files, s2,
            self.item_snooze, self.item_sync_issues,
            item_rebuild, s3,
            item_settings, self.item_updates, item_help, s4,
            item_quit,
        )

        self.menu.on_open = self.on_menu_open
        self.menu.on_close = self.on_menu_close

        # --------------- switch to idle icon -------------------
        self.set_icon(IDLE)

    # ==== callbacks menu items ==========================================================

    @staticmethod
    def on_website_clicked(widget):
        """Open the Dropbox website."""
        click.launch('https://www.dropbox.com/')

    @staticmethod
    def on_help_clicked(widget):
        """Open the Dropbox help website."""
        click.launch('https://dropbox.com/help')

    def on_start_stop_clicked(self, widget):
        """Pause / resume syncing on menu item clicked."""
        if self.item_pause.label == self.PAUSE_TEXT:
            self.mdbx.pause_sync()
            self.item_pause.label = self.RESUME_TEXT
        elif self.item_pause.label == self.RESUME_TEXT:
            self.mdbx.resume_sync()
            self.item_pause.label = self.PAUSE_TEXT
        elif self.item_pause.label == self.START_TEXT:
            self.mdbx.start_sync()
            self.item_pause.label = self.PAUSE_TEXT

    def on_settings_clicked(self, widget):
        self.settings_window.raise_()

    def on_sync_issues_clicked(self, widget):
        SyncIssuesWindow(self.mdbx, app=self).raise_()

    def on_rebuild_clicked(self, widget):
        self.rebuild_dialog = Dialog(
            title='Rebuilt Maestral\'s sync index?',
            message=(
                'Rebuilding the index may take several minutes, depending on the size of '
                'your Dropbox. Any changes to local files will be synced once rebuilding '
                'has completed. If you quit Maestral during the process, rebuilding will '
                'be resumed on the next launch.'
            ),
            button_labels=('Rebuild', 'Cancel'),
            icon=self.icon,
            callback=self.on_rebuild_decided,
        )

        self.rebuild_dialog.raise_()

    def on_rebuild_decided(self, btn_name):

        if btn_name == 'Rebuild':
            self.mdbx.rebuild_index()

        self.rebuild_dialog.close()

    # ==== other callbacks  ==============================================================

    async def auto_check_for_updates(self):

        last_update_check = self.mdbx.get_state('app', 'update_notification_last')
        interval = self.mdbx.get_conf('app', 'update_notification_interval')

        if interval == 0 or time.time() - last_update_check < interval:  # checks disabled
            return

        res = await run_maestral_async(self.config_name, 'check_for_updates')
        if res['update_available']:
            self.mdbx.set_state('app', 'update_notification_last', time.time())
            self.show_update_dialog(res['latest_release'], res['release_notes'])

    async def on_check_for_updates_clicked(self, widget):

        progress = ProgressDialog('Checking for Updates', app=self)
        progress.raise_()

        res = await run_maestral_async(self.config_name, 'check_for_updates')

        if not progress.visible:
            return  # aborted by user
        else:
            progress.close()

        if res['error']:
            Dialog('Could not check for updates', res['error'], icon=self.icon).raise_()
        elif res['update_available']:
            self.show_update_dialog(res['latest_release'], res['release_notes'])
        elif not res['update_available']:
            message = 'Maestral v{} is the newest version available.'.format(res['latest_release'])
            Dialog('You’re up-to-date!', message, icon=self.icon).raise_()

    def show_update_dialog(self, latest_release, release_notes):

        UpdateDialog(
            version=latest_release,
            release_notes=release_notes,
            icon=self.icon
        ).raise_()

    # ==== periodic updates ==============================================================

    def update_status(self):
        """Change icon according to status."""

        n_sync_errors = len(self.mdbx.sync_errors)
        status = self.mdbx.status
        is_paused = self.mdbx.paused
        is_stopped = not self.mdbx.running

        # update icon
        if is_paused:
            new_icon = PAUSED
        elif is_stopped:
            new_icon = ERROR
        elif n_sync_errors > 0 and status == IDLE:
            new_icon = SYNC_ERROR
        else:
            new_icon = status

        self.set_icon(new_icon)

        # update action texts
        if self.menu.visible:
            if n_sync_errors > 0:
                self.item_sync_issues.label = f'Show Sync Issues ({n_sync_errors})...'
            else:
                self.item_sync_issues.label = 'Show Sync Issues...'

            self.item_pause.label = self.RESUME_TEXT if is_paused else self.PAUSE_TEXT
            self.item_usage.label = self.mdbx.get_state('account', 'usage')
            self.item_email.label = self.mdbx.get_state('account', 'email')

            self.item_status.label = status

    def update_recent_files(self):
        """Update menu with list of recently changed files."""

        if self.menu.visible:

            recent_changes = self.mdbx.get_state('sync', 'recent_changes')

            if recent_changes != self._cached_recent_changes:

                self.menu_recent_files.clear()

                for entry in recent_changes:
                    dbx_path = entry.get('path_display')
                    fname = osp.basename(dbx_path)
                    local_path = self.mdbx.to_local_path(dbx_path)
                    menu_item = MenuItem(
                        fname,
                        action=lambda w: click.launch(w.local_path, locate=True)
                    )
                    menu_item.local_path = local_path
                    self.menu_recent_files.add(menu_item)

                self._cached_recent_changes = recent_changes

    def update_snoozed(self):
        minutes = self.mdbx.notification_snooze

        if minutes > 0:
            eta = datetime.now() + timedelta(minutes=minutes)

            self.item_snooze.label = 'Notifications snoozed until {}'.format(eta.strftime('%H:%M'))
            self.menu_snooze.insert(0, self.separator_snooze)
            self.menu_snooze.insert(0, self.item_resume_notifications)
        else:
            self.item_snooze.label = 'Snooze Notifications'
            self.menu_snooze.remove(self.item_resume_notifications)
            self.menu_snooze.remove(self.separator_snooze)

    def update_error(self):
        errs = self.mdbx.fatal_errors

        if not errs:
            return

        self.mdbx.clear_fatal_errors()

        self.set_icon(ERROR)
        self.item_pause.label = self.RESUME_TEXT
        self.item_pause.enabled = False
        self.item_status.label = self.mdbx.status

        self.mdbx.stop_sync()

        err = errs[-1]

        if err['type'] == 'NoDropboxDirError':
            self._exec_dbx_location_dialog()
        elif err['type'] == 'TokenRevokedError':
            self._exec_relink_dialog(RelinkDialog.REVOKED)
        elif err['type'] == 'TokenExpiredError':
            self._exec_relink_dialog(RelinkDialog.EXPIRED)
        elif 'MaestralApiError' in err['inherits'] or 'SyncError' in err['inherits']:
            self.alert(err['title'], err['message'], level='error')
        else:
            self._exec_error_dialog(err)

    def _exec_dbx_location_dialog(self):
        self.setup_dialog = DbxLocationDialog(self)
        self.setup_dialog.raise_()
        self.setup_dialog.on_close = self._on_setup_completed

    def _exec_relink_dialog(self, reason):
        RelinkDialog(self, reason).raise_()

    def _exec_error_dialog(self, err):

        title = 'An unexpected error occurred'

        if self.mdbx.analytics:
            message = ('A report has been sent to the developers. '
                       'Please restart Maestral to continue syncing.')

            html_traceback = err['traceback'].replace('\n', '<br />')
            self.alert(title, message, details=html_traceback, level='error')

        else:
            message = ('You can send a report to the developers or open an issue on '
                       'GitHub. Please restart Maestral to continue syncing.')
            btn_no, auto_share_checkbox = self.alert(
                title, message,
                details=err['traceback'],
                button_names=('Send to Developers', 'Don\'t send'),
                checkbox_text='Always send error reports',
            )

            if btn_no == 0:
                import bugsnag
                bugsnag.configure(
                    api_key='081c05e2bf9730d5f55bc35dea15c833',
                    app_version=__daemon_version__,
                    auto_notify=False,
                    auto_capture_sessions=False,
                )
                bugsnag.notify(
                    RuntimeError(err['type']),
                    meta_data={
                        'system':
                            {
                                'platform': platform.platform(),
                                'python': platform.python_version(),
                                'gui': f'toga {toga.__version__}',
                                'desktop': 'Cocoa',
                            },
                        'original exception': err,
                    }
                )

            self.mdbx.analytics = self.mdbx.analytics or auto_share_checkbox

    @async_call
    async def exit(self, *args, stop_daemon=False):
        """Quits Maestral.

        :param bool stop_daemon: If ``True``, the sync daemon will be stopped when
            quitting the GUI, if ``False``, it will be kept alive. If ``None``, the
            daemon will only be stopped if it was started by the GUI.
        """
        self.periodic_updates = False

        # stop sync daemon if we started it or ``stop_daemon`` is ``True``
        if stop_daemon or self._started:
            await run_async(stop_maestral_daemon_process, self.config_name)

        super().exit()

    def restart(self, *args):
        """Restarts the Maestral GUI and sync daemon."""

        # schedule restart after current process has quit
        pid = os.getpid()  # get ID of current process
        Popen(f"lsof -p {pid} +r 1 &>/dev/null; "
              f"maestral gui --config-name='{self.config_name}'",
              shell=True)

        # quit Maestral
        self.exit(stop_daemon=True)


def run(config_name='maestral'):

    MaestralGui.config_name = config_name

    app = MaestralGui(
        formal_name=APP_NAME,
        app_id=BUNDLE_ID,
        app_name='maestral_cocoa',
        icon=APP_ICON_PATH,
        author=__author__,
        version=__gui_version__,
        home_page=__url__
    )

    return app.main_loop()
