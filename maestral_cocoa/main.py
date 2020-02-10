# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 31 16:23:13 2018

@author: samschott
"""
# system imports
import sys
import os
import os.path as osp
import asyncio
import logging
import platform
import time
from subprocess import Popen
from datetime import datetime, timedelta

# external packages
import click
import markdown2
import toga
from toga.style.pack import Pack, FONT_SIZE_CHOICES

# maestral modules
from maestral.config.main import MaestralConfig
from maestral.utils import pending_link, pending_dropbox_folder
from maestral.constants import (
    IDLE, SYNCING, PAUSED, STOPPED, DISCONNECTED, SYNC_ERROR, ERROR,
)
from maestral.daemon import (
    start_maestral_daemon_process,
    start_maestral_daemon_thread,
    stop_maestral_daemon_process,
    get_maestral_pid,
    get_maestral_proxy,
    Start,
)
from maestral import __author__, __url__
from maestral import __version__ as __daemon_version__

# local imports
from maestral_cocoa import __version__ as __gui_version__
from maestral_cocoa.utils import async_call, run_maestral_async, alert
from maestral_cocoa.private.widgets import MenuItem, MenuItemSeparator, Menu, StatusBarItem, SystemTrayApp
from maestral_cocoa.autostart import AutoStart
from maestral_cocoa.settings import SettingsWindow
from maestral_cocoa.syncissues import SyncIssuesWindow
from maestral_cocoa.rebuildindex import RebuildIndexDialog
from maestral_cocoa.dbx_location_dialog import DbxLocationDialog
from maestral_cocoa.dialogs import Dialog, UpdateDialog, ProgressDialog, RelinkDialog
from maestral_cocoa.resources import APP_ICON_PATH, TRAY_ICON_PATH


Pack.validated_property('font_size', choices=FONT_SIZE_CHOICES, initial=13)
logger = logging.getLogger(__name__)

IS_MACOS_BUNDLE = getattr(sys, 'frozen', False)


# TODO:
#  - fix memory leak

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

        self.mdbx = None
        self._started = False
        self._conf = MaestralConfig(self.config_name)  # use only for reading, before daemon is attached!

        self._n_sync_errors = None

        self.settings_window = None
        self.sync_issues_window = None
        self.rebuild_dialog = None

        self.item_status = None
        self.item_email = None
        self.item_usage = None
        self.item_sync_issues = None
        self.item_pause = None
        self.menu_recent_files = None

        self.autostart = AutoStart()

        self.menu = Menu()
        self._cached_status = DISCONNECTED
        self._cached_recent_files = []
        self.tray = StatusBarItem(self.icon_mapping.get(DISCONNECTED), menu=self.menu)

        self.setup_ui_unlinked()
        self.load_maestral()
        self.periodic_check_for_updates()

    def set_icon(self, status):
        if status != self._cached_status:
            self.tray.icon = self.icon_mapping.get(status, self.icon_mapping[SYNCING])
            self._cached_status = status

    @async_call
    async def periodic_refresh_gui(self, interval=0.5):

        while True:
            if self.mdbx:
                self.update_status()
                self.update_recent_files()
                self.update_snoozed()
                self.update_error()

    @async_call
    async def periodic_check_for_updates(self, interval=30*60):
        while self.periodic_updates:
            await asyncio.sleep(interval)
            await self.auto_check_for_updates()

    def load_maestral(self):

        if pending_link(self.config_name):
            from .setup import SetupDialog
            logger.info('Setting up Maestral...')
            res = SetupDialog(self.config_name, app=self).runModal()

            if res == 0:
                logger.info('Setup complete.')
                self._started = True
                self.mdbx = get_maestral_proxy(self.config_name)
                self.mdbx.run()
            else:
                logger.info('Setup aborted by user.')
                self.exit(stop_daemon=True)
        elif pending_dropbox_folder(self.config_name):
            self.set_icon(ERROR)
            self.mdbx = self._get_or_start_maestral_daemon(run=False)
            self.setup_ui_linked()
            self.periodic_refresh_gui()
            res = DbxLocationDialog(self.mdbx, app=self).runModal()
            if res != 0:
                self.exit(stop_daemon=True)
        else:
            self.mdbx = self._get_or_start_maestral_daemon()
            self.setup_ui_linked()
            self.periodic_refresh_gui()

    def _get_or_start_maestral_daemon(self, run=True):

        pid = get_maestral_pid(self.config_name)
        if pid:
            self._started = False
        else:
            if IS_MACOS_BUNDLE:
                res = start_maestral_daemon_thread(self.config_name, run=run)
            else:
                res = start_maestral_daemon_process(self.config_name, run=run)

            if res == Start.Failed:
                title = 'Could not start Maestral'
                message = ('Could not start or connect to sync daemon. Please try again '
                           'and contact the developer if this issue persists.')
                alert(title, message, level='error', icon=self.icon)
                self.exit()
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

        item_login = MenuItem('Start on login', checkable=True, action=lambda s: self.autostart.toggle())
        item_login.checked = self.autostart.enabled
        item_help = MenuItem('Help Center', action=self.on_help_clicked)

        s2 = MenuItemSeparator()

        item_quit = MenuItem('Quit Maestral', action=lambda s: self.exit())

        self.menu.add(item_folder, item_website, s0, item_status, s1, item_login, item_help, s2, item_quit)

    def setup_ui_linked(self):

        if not self.mdbx:
            return

        self.settings_window = SettingsWindow(self.mdbx, app=self)

        # ------------- populate context menu -------------------

        self.menu.clear()

        item_folder = MenuItem('Open Dropbox Folder', action=lambda s: click.launch(self.mdbx.dropbox_path))
        item_website = MenuItem('Launch Dropbox Website', action=self.on_website_clicked)

        s0 = MenuItemSeparator()

        self.item_email = MenuItem(self.mdbx.get_conf('account', 'email'))
        self.item_usage = MenuItem(self.mdbx.get_conf('account', 'usage'))

        s1 = MenuItemSeparator()

        self.item_status = MenuItem(IDLE)
        self.item_pause = MenuItem(self.PAUSE_TEXT if self.mdbx.syncing else self.RESUME_TEXT, action=self.on_start_stop_clicked)
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
            item_folder,
            item_website,
            s0,
            self.item_email,
            self.item_usage,
            s1,
            self.item_status,
            self.item_pause,
            self.item_recent_files,
            s2,
            self.item_snooze,
            self.item_sync_issues,
            item_rebuild,
            s3,
            item_settings,
            self.item_updates,
            item_help,
            s4,
            item_quit,
        )

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
        self.settings_window.refresh = True
        self.settings_window.raise_()

    def on_sync_issues_clicked(self, widget):
        SyncIssuesWindow(self.mdbx, app=self).raise_()

    def on_rebuild_clicked(self, widget):
        RebuildIndexDialog(self.mdbx, app=self).raise_()

    # ==== other callbacks  ==============================================================

    @async_call
    async def auto_check_for_updates(self):

        last_update_check = self.mdbx.get_conf('app', 'update_notification_last')
        interval = self.mdbx.get_conf('app', 'update_notification_interval')

        if interval == 0 or time.time() - last_update_check < interval:  # checks disabled
            return

        res = await run_maestral_async(self.config_name, 'check_for_updates')
        if res['update_available']:
            self.mdbx.set_conf('app', 'update_notification_last', time.time())
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

        html_notes = markdown2.markdown(release_notes)
        html_notes = html_notes.replace('<h4>', '<br/> <h4>')
        UpdateDialog(
            version=latest_release,
            release_notes=html_notes,
            icon=self.icon
        ).raise_()

    # ==== periodic updates ==============================================================

    def update_status(self):
        """Change icon according to status."""

        n_sync_errors = len(self.mdbx.sync_errors)
        status = self.mdbx.status
        is_paused = self.mdbx.paused
        is_stopped = self.mdbx.stopped

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
            self.item_usage.label = self.mdbx.get_conf('account', 'usage')
            self.item_email.label = self.mdbx.get_conf('account', 'email')

            self.item_status.label = status

    def update_recent_files(self):
        """Update menu with list of recently changed files."""

        if self.menu.visible:
            recent_files = self.mdbx.get_conf('internal', 'recent_changes')

            if recent_files != self._cached_recent_files:

                self.menu_recent_files.clear()

                for dbx_path in reversed(recent_files):
                    fname = osp.basename(dbx_path)
                    local_path = self.mdbx.to_local_path(dbx_path)
                    menu_item = MenuItem(
                        fname,
                        action=lambda w: click.launch(w.local_path, locate=True)
                    )
                    menu_item.local_path = local_path
                    self.menu_recent_files.add(menu_item)

                self._cached_recent_files = recent_files

    def update_snoozed(self):
        minutes = self.mdbx.notification_snooze

        if minutes > 0:
            eta = datetime.now() + timedelta(minutes=minutes)

            self.item_snooze.label = 'Notifications snoozed until %s' % eta.strftime('%H:%M')
            self.menu_snooze.insert(0, self.separator_snooze)
            self.menu_snooze.insert(0, self.item_resume_notifications)
        else:
            self.item_snooze.label = 'Snooze Notifications'
            self.menu_snooze.remove(self.item_resume_notifications)
            self.menu_snooze.remove(self.separator_snooze)

    def update_error(self):
        errs = self.mdbx.maestral_errors

        if not errs:
            return

        self.mdbx.clear_maestral_errors()

        self.set_icon(ERROR)
        self.item_pause.label = self.RESUME_TEXT
        self.item_pause.enabled = False
        self.item_status.label = self.mdbx.status

        self.mdbx.stop_sync()

        err = errs[-1]

        if err['type'] in ('RevFileError', 'BadInputError', 'CursorResetError', 'InotifyError'):
            alert(err['title'], err['message'], level='error', icon=self.icon)
        elif err['type'] == 'DropboxDeletedError':
            self._exec_dbx_location_dialog()
        elif err['type'] == 'DropboxAuthError':
            self._exec_relink_dialog(RelinkDialog.REVOKED)
        elif err['type'] == 'TokenExpiredError':
            self._exec_relink_dialog(RelinkDialog.EXPIRED)
        else:
            self._exec_error_dialog(err)

    def _exec_dbx_location_dialog(self):
        DbxLocationDialog(self.mdbx, app=self).raise_()

    def _exec_relink_dialog(self, reason):
        RelinkDialog(self.mdbx, reason, app=self).raise_()

    def _exec_error_dialog(self, err):

        title = 'An unexpected error occurred'

        analytics = self.mdbx.get_conf('app', 'analytics')

        if analytics:
            message = ('A report has been sent to the developers. '
                       'Please restart Maestral to continue syncing.')

            alert(title, message, details=err['traceback'], level='error', icon=self.icon)

        else:
            message = ('You can send a report to the developers or open an issue on '
                       'GitHub. Please restart Maestral to continue syncing.')
            btn_no, auto_share_checkbox = alert(
                title, message,
                details=err['traceback'],
                button_names=('Send to Developers', 'Don\'t send'),
                checkbox_text='Always send error reports',
                icon=self.icon,
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
                                'gui': toga.__version__,
                                'desktop': 'Cocoa',
                            },
                        'error': err,
                    }
                )

            if auto_share_checkbox:
                self.mdbx.set_conf('app', 'analytics', True)

    def exit(self, *args, stop_daemon=False):
        """Quits Maestral.

        :param bool stop_daemon: If ``True``, the sync daemon will be stopped when
            quitting the GUI, if ``False``, it will be kept alive. If ``None``, the
            daemon will only be stopped if it was started by the GUI.
        """
        logger.info('Quitting...')

        # stop sync daemon if we started it
        if not IS_MACOS_BUNDLE and (self._started or stop_daemon):
            self.mdbx = None
            stop_maestral_daemon_process(self.config_name)

        super().exit()

    def restart(self, *args):
        """Restarts the Maestral GUI and sync daemon."""

        logger.info('Restarting...')

        # schedule restart after current process has quit
        pid = os.getpid()  # get ID of current process
        Popen("lsof -p {0} +r 1 &>/dev/null; maestral gui --config-name='{1}'".format(pid, self.config_name), shell=True)

        # quit Maestral
        self.exit(stop_daemon=True)


def run(config_name='maestral') -> MaestralGui:

    MaestralGui.config_name = config_name

    app = MaestralGui(
        formal_name='Maestral',
        app_id='com.samschott.maestral',
        app_name='maestral_cocoa',
        icon=APP_ICON_PATH,
        author=__author__,
        version=__gui_version__,
        home_page=__url__
    )

    return app.main_loop()


def run_from_console():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', help='config name', default='maestral')
    args = parser.parse_args()

    run(args.c)


if __name__ == '__main__':
    run()
