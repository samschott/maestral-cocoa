# -*- coding: utf-8 -*-

# system imports
import sys
import os
import os.path as osp
import asyncio

# external imports
import toga
from maestral.utils.autostart import AutoStart

# local imports
from .utils import request_authorization_from_user_and_run, call_async_maestral, apply_round_clipping
from .private.constants import ON, OFF
from .private.widgets import IconForPath
from .settings_gui import SettingsGui
from .selective_sync import SelectiveSyncDialog
from .dialogs import Dialog
from .resources import FACEHOLDER_PATH


class SettingsWindow(SettingsGui):

    _update_interval_mapping = {
        'Daily': 60 * 60 * 24,
        'Weekly': 60 * 60 * 24 * 7,
        'Monthly': 60 * 60 * 24 * 30,
        'Never': 0
    }

    _macos_cli_tool_path = '/usr/local/bin/maestral'
    _cached_pic_stat = os.stat(FACEHOLDER_PATH)
    _cached_dbx_location = None

    def __init__(self, mdbx, app):
        super().__init__(app=app)

        self.mdbx = mdbx
        self.autostart = AutoStart(self.mdbx.config_name, gui=True)

        self.btn_unlink.on_press = self.on_unlink_pressed
        self.btn_select_folders.on_press = self.on_folder_selection_pressed
        self.combobox_dbx_location.on_select = self._on_button_location_pressed
        self.combobox_update_interval.on_select = self.on_update_interval_selected
        self.checkbox_autostart.on_toggle = self.on_autostart_clicked
        self.checkbox_notifications.on_toggle = self.on_notifications_clicked
        self.checkbox_analytics.on_toggle = self.on_analytics_clicked
        self.btn_cli_tool.on_press = self.on_cli_pressed

        self._periodic_refresh_task = asyncio.Task(self.periodic_refresh_gui())
        self.refresh_gui()

    # ==== callback implementations ======================================================

    async def on_dbx_location_selected(self, path):
        new_path = osp.join(path, self.mdbx.get_conf('main', 'default_dir_name'))
        try:
            self.mdbx.move_dropbox_directory(new_path)
        except OSError:
            await self.alert_sheet(
                title='Could not move folder',
                message=('Please make sure that you have permissions '
                         'to write to the selected location.'),
                button_labels=('Ok',),
            )
            self.mdbx.resume_sync()

    def on_folder_selection_pressed(self, widget):
        SelectiveSyncDialog(self.mdbx, app=self.app).show_as_sheet(self)

    def on_unlink_pressed(self, widget):
        self.unlink_dialog = Dialog(
            title='Unlink your Dropbox account?',
            message=('You will still keep your Dropbox folder on this '
                     'computer but your files will stop syncing.'),
            button_labels=('Unlink', 'Cancel'),
            default='Cancel',
            callback=self.on_unlink_decided,
            icon=self.app.icon
        )
        self.unlink_dialog.show_as_sheet(self)

    async def on_unlink_decided(self, btn_name):
        if btn_name == 'Unlink':
            self._periodic_refresh_task.cancel()
            self.unlink_dialog.dialog_buttons.enabled = False
            self.unlink_dialog.spinner.start()
            await call_async_maestral(self.mdbx.config_name, 'unlink')
            self.unlink_dialog.spinner.stop()
            self.unlink_dialog.close()
            await self.alert_sheet(
                title='Successfully unlinked',
                message='Maestral will now quit.',
                button_labels=('Ok',),
            )
            await self.app.exit(stop_daemon=True)
        else:
            self.unlink_dialog.close()

    async def on_update_interval_selected(self, widget):
        value = str(widget.value)
        self.mdbx.set_conf('app', 'update_notification_interval',
                           self._update_interval_mapping[value])

    async def on_autostart_clicked(self, widget):
        self.autostart.enabled = widget.state == ON

    async def on_notifications_clicked(self, widget):
        # 30 = SYNCISSUE, 15 = FILECHANGE
        self.mdbx.notification_level = 15 if widget.state == ON else 30

    async def on_analytics_clicked(self, widget):
        self.mdbx.analytics = widget.state == ON

    async def on_cli_pressed(self, widget):

        if osp.islink(self._macos_cli_tool_path):
            try:
                os.remove(self._macos_cli_tool_path)
            except PermissionError:
                request_authorization_from_user_and_run(['/bin/rm', '-f', self._macos_cli_tool_path])
        else:
            maestral_cli = os.path.join(getattr(sys, '_MEIPASS', ''), 'maestral_cli')
            try:
                os.symlink(maestral_cli, self._macos_cli_tool_path)
            except PermissionError:
                request_authorization_from_user_and_run(['/bin/ln', '-s', maestral_cli, self._macos_cli_tool_path])

        self._udpdate_cli_tool_button()

    def _udpdate_cli_tool_button(self):
        if osp.islink(self._macos_cli_tool_path):
            self.btn_cli_tool.enabled = True
            self.btn_cli_tool.label = 'Uninstall'
            self.label_cli_tool_info.text = (
                "CLI installed. See 'maestral --help' for available commands."
            )
        elif osp.exists(self._macos_cli_tool_path):
            self.btn_cli_tool.enabled = False
            self.btn_cli_tool.label = 'Install'
            self.label_cli_tool_info.text = (
                'CLI already installed from Python package.'
            )
        else:
            self.btn_cli_tool.enabled = True
            self.btn_cli_tool.label = 'Install'
            self.label_cli_tool_info.text = (
                "Install the 'maestral' command line tool to /usr/local/bin."
            )

    async def _on_button_location_pressed(self, widget):

        if widget.value == self.COMBOBOX_CHOOSE:
            message = ('Choose a new place for your Dropbox folder. A folder named '
                       f'"Dropbox ({self.mdbx.config_name.title()})" will be '
                       'created in the selected location.')
            paths = await self.select_folder_sheet(message=message)

            if len(paths) > 0:
                path = paths[0]

                self._update_combobox_location(path)
                await self.on_dbx_location_selected(path)
            else:
                self.combobox_dbx_location.value = self.combobox_dbx_location.items[0]

    def _update_combobox_location(self, path):
        if path != self._cached_dbx_location:
            self._cached_dbx_location = path
            icon = IconForPath(path)
            short_path = osp.basename(path)
            self.combobox_dbx_location.items = [
                (icon, short_path), toga.SECTION_BREAK, self.COMBOBOX_CHOOSE
            ]

    def set_profile_pic(self, path):
        path = path if osp.isfile(path) else FACEHOLDER_PATH
        new_stat = os.stat(path)
        if new_stat != self._cached_pic_stat:
            try:
                self.profile_pic_view.image = toga.Image(path)
            except OSError:
                self.profile_pic_view.image = self.faceholder
            self.profile_pic_view._impl.native.imageAlignment = 3
            apply_round_clipping(self.profile_pic_view)

            self._cached_pic_stat = new_stat

    # ==== populate gui with data ========================================================

    async def periodic_refresh_gui(self, interval=2):

        while True:
            self.refresh_gui()
            await asyncio.sleep(interval)

    def refresh_gui(self):

        # populate account info
        self.set_profile_pic(self.mdbx.account_profile_pic_path)
        self.set_account_info_from_cache()

        # populate sync section
        parent_dir = osp.split(self.mdbx.dropbox_path)[0]
        self._update_combobox_location(parent_dir)

        # populate app section
        self.checkbox_autostart.state = ON if self.autostart.enabled else OFF
        self.checkbox_notifications.state = ON if self.mdbx.notification_level <= 15 else OFF
        self.checkbox_analytics.state = ON if self.mdbx.analytics else OFF
        update_interval = self.mdbx.get_conf('app', 'update_notification_interval')
        closest_key = min(
            self._update_interval_mapping,
            key=lambda x: abs(self._update_interval_mapping[x] - update_interval)
        )
        self.combobox_update_interval.value = closest_key
        self._udpdate_cli_tool_button()

    def set_account_info_from_cache(self):

        acc_display_name = self.mdbx.get_state('account', 'display_name')
        acc_mail = self.mdbx.get_state('account', 'email')
        acc_type = self.mdbx.get_state('account', 'type')
        acc_space_usage = self.mdbx.get_state('account', 'usage')
        acc_space_usage_type = self.mdbx.get_state('account', 'usage_type')

        if acc_space_usage_type == 'team':
            acc_space_usage += ' (Team)'

        if acc_type != '':
            acc_type_text = ', Dropbox {0}'.format(acc_type.capitalize())
        else:
            acc_type_text = ''

        self.label_name.text = acc_display_name
        self.label_email.text = acc_mail + acc_type_text
        self.label_usage.text = acc_space_usage

    def on_close(self):
        self._periodic_refresh_task.cancel()

    def show(self):
        asyncio.ensure_future(self._periodic_refresh_task)
        super().show()
