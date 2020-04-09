import os.path as osp
import asyncio

from maestral.utils.notify import FILECHANGE, SYNCISSUE
from maestral.utils.autostart import AutoStart

from .utils import async_call, run_maestral_async, alert_sheet
from .private.constants import ON, OFF
from .settings_gui import SettingsGui
from .selective_sync import ExcludedFoldersDialog
from .dialogs import Dialog


class SettingsWindow(SettingsGui):

    _update_interval_mapping = {
        'Daily': 60 * 60 * 24,
        'Weekly': 60 * 60 * 24 * 7,
        'Monthly': 60 * 60 * 24 * 30,
        'Never': 0
    }

    def __init__(self, mdbx, app):
        super().__init__(app=app)

        self.mdbx = mdbx
        self.refresh = True
        self.autostart = AutoStart(self.mdbx.config_name, gui=True)

        self.refresh_gui()
        self.periodic_refresh_gui()

    # ==== callbacks to implement ========================================================

    @async_call
    async def on_dbx_location_selected(self, path):
        new_path = osp.join(path, self.mdbx.get_conf('main', 'default_dir_name'))
        try:
            self.mdbx.move_dropbox_directory(new_path)
        except OSError:
            alert_sheet(
                window=self,
                title='Could not move folder',
                message=('Please make sure that you have permissions '
                         'to write to the selected location.'),
                button_labels=('Ok',),
                icon=self.app.icon,
            )
            self.mdbx.resume_sync()

    def on_folder_selection_pressed(self, widget):
        ExcludedFoldersDialog(self.mdbx, app=self.app).show_as_sheet(self)

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

    @async_call
    async def on_unlink_decided(self, btn_name):
        if btn_name == 'Unlink':
            self.refresh = False
            self.unlink_dialog.dialog_buttons.enabled = False
            self.unlink_dialog.spinner.start()
            await run_maestral_async(self.mdbx.config_name, 'unlink')
            self.unlink_dialog.spinner.stop()
            self.unlink_dialog.close()
            alert_sheet(
                window=self,
                title='Successfully unlinked',
                message='Maestral will now quit.',
                button_labels=('Ok',),
                callback=lambda s: self.app.exit(stop_daemon=True),
                icon=self.app.icon
            )
        else:
            self.unlink_dialog.close()

    def on_update_interval_selected(self, widget):
        value = str(widget.value)
        self.mdbx.set_conf('app', 'update_notification_interval',
                           self._update_interval_mapping[value])

    def on_autostart_clicked(self, widget):
        self.autostart.enabled = widget.state == ON

    def on_notifications_clicked(self, widget):
        self.mdbx.notification_level = FILECHANGE if widget.state == ON else SYNCISSUE

    def on_analytics_clicked(self, widget):
        self.mdbx.analytics = widget.state == ON

    # ==== populate gui with data ========================================================

    @async_call
    async def periodic_refresh_gui(self, interval=2):

        while self.refresh:
            if self.visible:
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
        self.checkbox_notifications.state = ON if self.mdbx.notification_level == FILECHANGE else OFF
        self.checkbox_analytics.state = ON if self.mdbx.analytics else OFF
        update_interval = self.mdbx.get_conf('app', 'update_notification_interval')
        closest_key = min(
            self._update_interval_mapping,
            key=lambda x: abs(self._update_interval_mapping[x] - update_interval)
        )
        self.combobox_update_interval.value = closest_key

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
        self.refresh = False
