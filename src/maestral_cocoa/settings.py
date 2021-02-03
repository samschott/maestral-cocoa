# -*- coding: utf-8 -*-

# system imports
import sys
import os
import os.path as osp
import asyncio
from pathlib import Path

# external imports
import toga

# local imports
from .utils import (
    request_authorization_from_user_and_run,
    create_task,
    call_async_maestral,
)
from .private.constants import ON, OFF
from .private.widgets import apply_round_clipping
from .settings_gui import SettingsGui
from .selective_sync import SelectiveSyncDialog
from .resources import FACEHOLDER_PATH
from .autostart import AutoStart


class SettingsWindow(SettingsGui):

    _update_interval_mapping = {
        "Daily": 60 * 60 * 24,
        "Weekly": 60 * 60 * 24 * 7,
        "Monthly": 60 * 60 * 24 * 30,
        "Never": 0,
    }

    _macos_cli_install_path = "/usr/local/bin/maestral"
    _cached_pic_stat = os.stat(FACEHOLDER_PATH)
    _cached_dbx_location = None

    def __init__(self, mdbx, app):
        super().__init__(app=app)

        self.mdbx = mdbx
        self.autostart = AutoStart(self.mdbx.config_name)

        self.btn_unlink.on_press = self.on_unlink_pressed
        self.btn_select_folders.on_press = self.on_folder_selection_pressed
        self.combobox_dbx_location.on_select = self.on_dbx_location_selected
        self.combobox_update_interval.on_select = self.on_update_interval_selected
        self.checkbox_autostart.on_toggle = self.on_autostart_clicked
        self.checkbox_notifications.on_toggle = self.on_notifications_clicked
        self.btn_cli_tool.on_press = self.on_cli_pressed

        self.default_dirname = f"Dropbox ({self.mdbx.config_name.capitalize()})"

        path_selection_message = (
            "Choose a new place for your Dropbox folder. A folder named "
            f'"{self.default_dirname}" will be created in the selected location.'
        )

        self.combobox_dbx_location.dialog_message = path_selection_message

        self._periodic_refresh_task = None
        self.refresh_gui()

    # ==== callback implementations ====================================================

    async def on_dbx_location_selected(self, widget):
        new_path = osp.join(widget.current_selection, self.default_dirname)

        try:
            await call_async_maestral(
                self.mdbx.config_name, "move_dropbox_directory", new_path
            )
        except OSError:
            await self.alert_sheet(
                title="Could not move folder",
                message=(
                    "Please make sure that you have permissions "
                    "to write to the selected location."
                ),
                button_labels=("Ok",),
            )
            self.mdbx.start_sync()

    def on_folder_selection_pressed(self, widget):
        SelectiveSyncDialog(self.mdbx, app=self.app).show_as_sheet(self)

    async def on_unlink_pressed(self, widget):
        choice = await self.alert_sheet(
            title="Unlink your Dropbox account?",
            message=(
                "You will still keep your Dropbox folder on this "
                "computer but your files will stop syncing."
            ),
            button_labels=("Unlink", "Cancel"),
        )

        if choice == 0:
            self._periodic_refresh_task.cancel()
            self.mdbx.unlink()
            await self.alert_sheet(
                title="Successfully unlinked",
                message="Maestral will now quit.",
                button_labels=("Ok",),
            )
            await self.app.exit(stop_daemon=True)

    async def on_update_interval_selected(self, widget):
        value = str(widget.value)
        self.mdbx.set_conf(
            "app", "update_notification_interval", self._update_interval_mapping[value]
        )

    async def on_autostart_clicked(self, widget):
        self.autostart.enabled = widget.state == ON

    async def on_notifications_clicked(self, widget):
        # 30 = SYNCISSUE, 15 = FILECHANGE
        self.mdbx.notification_level = 15 if widget.state == ON else 30

    async def on_cli_pressed(self, widget):

        if osp.islink(self._macos_cli_install_path):

            try:
                try:
                    os.remove(self._macos_cli_install_path)
                except PermissionError:
                    request_authorization_from_user_and_run(
                        ["/bin/rm", "-f", self._macos_cli_install_path]
                    )
            except FileNotFoundError:
                pass
            except Exception as e:
                await self.alert_sheet(
                    "Could not uninstall CLI", e.args[0], level="error"
                )

        else:
            maestral_cli = Path(sys.executable).parent / "maestral-cli"
            try:
                try:
                    os.symlink(maestral_cli, self._macos_cli_install_path)
                except PermissionError:
                    request_authorization_from_user_and_run(
                        [
                            "/bin/ln",
                            "-s",
                            str(maestral_cli),
                            self._macos_cli_install_path,
                        ]
                    )
            except Exception as e:
                await self.alert_sheet(
                    "Could not install CLI", e.args[0], level="error"
                )

        self._update_cli_tool_button()

    def _update_cli_tool_button(self):
        if osp.islink(self._macos_cli_install_path):
            self.btn_cli_tool.enabled = True
            self.btn_cli_tool.label = "Uninstall"
            self.label_cli_tool_info.text = (
                "CLI installed. See 'maestral --help' for available commands."
            )
        elif osp.exists(self._macos_cli_install_path):
            self.btn_cli_tool.enabled = False
            self.btn_cli_tool.label = "Install"
            self.label_cli_tool_info.text = "CLI already installed from Python package."
        else:
            self.btn_cli_tool.enabled = True
            self.btn_cli_tool.label = "Install"
            self.label_cli_tool_info.text = (
                "Install the 'maestral' command line tool to /usr/local/bin."
            )

    def set_profile_pic(self, path):
        path = path if osp.isfile(path) else FACEHOLDER_PATH
        new_stat = os.stat(path)
        if new_stat != self._cached_pic_stat:
            try:
                self.profile_pic_view.image = toga.Image(path)
            except OSError:
                self.profile_pic_view.image = self.faceholder
            apply_round_clipping(self.profile_pic_view)
            self._cached_pic_stat = new_stat

    # ==== populate gui with data ======================================================

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
        self.combobox_dbx_location.current_selection = parent_dir

        # populate app section
        self.checkbox_autostart.state = ON if self.autostart.enabled else OFF
        self.checkbox_notifications.state = (
            ON if self.mdbx.notification_level <= 15 else OFF
        )
        update_interval = self.mdbx.get_conf("app", "update_notification_interval")
        closest_key = min(
            self._update_interval_mapping,
            key=lambda x: abs(self._update_interval_mapping[x] - update_interval),
        )
        self.combobox_update_interval.value = closest_key
        self._update_cli_tool_button()

    def set_account_info_from_cache(self):

        acc_display_name = self.mdbx.get_state("account", "display_name")
        acc_mail = self.mdbx.get_state("account", "email")
        acc_type = self.mdbx.get_state("account", "type")
        acc_space_usage = self.mdbx.get_state("account", "usage")
        acc_space_usage_type = self.mdbx.get_state("account", "usage_type")

        if acc_space_usage_type == "team":
            acc_space_usage += " (Team)"

        if acc_type != "":
            acc_type_text = ", Dropbox {0}".format(acc_type.capitalize())
        else:
            acc_type_text = ""

        self.label_name.text = acc_display_name
        self.label_email.text = acc_mail + acc_type_text
        self.label_usage.text = acc_space_usage

    def on_close(self):
        if self._periodic_refresh_task:
            self._periodic_refresh_task.cancel()

    def show(self):
        self._periodic_refresh_task = create_task(self.periodic_refresh_gui())
        super().show()
