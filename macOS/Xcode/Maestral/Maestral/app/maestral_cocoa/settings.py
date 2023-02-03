# -*- coding: utf-8 -*-

from __future__ import annotations

# system imports
import sys
import os
import os.path as osp
import asyncio
from pathlib import Path
from typing import Any, TYPE_CHECKING

# external imports
import toga
from maestral.utils.path import delete
from maestral.daemon import MaestralProxy
from maestral.exceptions import MaestralApiError, NotLinkedError

# local imports
from .utils import (
    request_authorization_from_user_and_run,
    call_async_maestral,
    is_empty,
)
from .private.constants import ON, OFF
from .private.widgets import FileSelectionButton, Switch, apply_round_clipping
from .settings_gui import SettingsGui
from .selective_sync import SelectiveSyncDialog
from .bandwidth import BandwidthDialog
from .resources import FACEHOLDER_PATH
from .autostart import AutoStart
from .constants import FROZEN

if TYPE_CHECKING:
    from .app import MaestralGui


class SettingsWindow(SettingsGui):
    _update_interval_mapping = {
        "Daily": 60 * 60 * 24,
        "Weekly": 60 * 60 * 24 * 7,
        "Monthly": 60 * 60 * 24 * 30,
        "Never": 0,
    }

    _macos_cli_install_path = Path("/usr/local/bin/maestral")
    _cached_pic_stat = os.stat(FACEHOLDER_PATH)
    _cached_dbx_location = None

    def __init__(self, mdbx: MaestralProxy, app: MaestralGui) -> None:
        super().__init__(app=app)

        self._refresh = False
        self._refresh_interval = 2
        self._refresh_interval_profile_pic = 60 * 45

        self.on_close = self.on_close_pressed

        self.mdbx = mdbx
        self.autostart = AutoStart(self.mdbx.config_name)

        self.btn_unlink.on_press = self.on_unlink_pressed
        self.btn_select_folders.on_press = self.on_folder_selection_pressed
        self.btn_bandwidth.on_press = self.on_bandwidth_pressed
        self.combobox_dbx_location.on_select = self.on_dbx_location_selected

        self.combobox_update_interval.on_select = self.on_update_interval_selected
        self.checkbox_autostart.on_change = self.on_autostart_clicked
        self.checkbox_notifications.on_change = self.on_notifications_clicked

        if FROZEN:
            self.btn_cli_tool.on_press = self.on_cli_pressed

        path_selection_message = (
            "Choose a new local Dropbox folder. If the new folder is not empty, you "
            "can either delete its content or merge it with your Dropbox."
        )

        self.combobox_dbx_location.dialog_message = path_selection_message
        self.refresh_gui()
        self.app.add_background_task(self.refresh_profile_pic)

    # ==== callback implementations ====================================================

    async def on_dbx_location_selected(self, widget: FileSelectionButton) -> None:
        new_path = widget.current_selection

        if new_path == self.mdbx.dropbox_path:
            return

        try:
            # The folder will always exist (cannot choose a non-existing folder).
            # Ask if we can delete it / its contents if it isn't empty.
            if not is_empty(new_path):
                return await self.error_dialog(
                    title="Folder is not empty",
                    message=(
                        f'The folder "{osp.basename(new_path)}" is not empty. '
                        "Please select an empty folder."
                    ),
                )

            delete(new_path, raise_error=True)

            await call_async_maestral(
                self.mdbx.config_name, "move_dropbox_directory", new_path
            )
        except Exception as exc:
            await self.error_dialog(
                title="Could not move folder",
                message=str(exc.args[0]),
            )
            self.mdbx.start_sync()

    def on_folder_selection_pressed(self, widget: Any) -> None:
        SelectiveSyncDialog(mdbx=self.mdbx, app=self.app).show_as_sheet(self)

    def on_bandwidth_pressed(self, widget: Any) -> None:
        BandwidthDialog(mdbx=self.mdbx, app=self.app).show_as_sheet(self)

    async def on_unlink_pressed(self, widget: Any) -> None:
        should_unlink = await self.confirm_dialog(
            title="Unlink your Dropbox account?",
            message=(
                "You will still keep your Dropbox folder on this "
                "computer but your files will stop syncing."
            ),
        )

        if should_unlink:
            self._refresh = False
            self.mdbx.unlink()
            await self.info_dialog(
                title="Successfully unlinked",
                message="Maestral will now quit.",
            )
            await self.app.exit_and_stop_daemon()

    async def on_update_interval_selected(self, widget: toga.Selection) -> None:
        interval = self._update_interval_mapping[str(widget.value)]
        self.app.updater.update_check_interval = interval

    async def on_autostart_clicked(self, widget: Switch) -> None:
        self.autostart.enabled = widget.state == ON

    async def on_notifications_clicked(self, widget):
        # 30 = SYNCISSUE, 15 = FILECHANGE
        self.mdbx.notification_level = 15 if widget.state == ON else 30

    async def on_cli_pressed(self, widget: Any) -> None:
        if self._macos_cli_install_path.is_symlink():
            # Uninstall CLI from /usr/local/bin.
            try:
                try:
                    self._macos_cli_install_path.unlink()
                except (FileNotFoundError, NotADirectoryError):
                    pass
                except PermissionError:
                    request_authorization_from_user_and_run(
                        f"/bin/rm -f {self._macos_cli_install_path}"
                    )
            except Exception as e:
                await self.error_dialog("Could not uninstall CLI", str(e))

        elif not self._macos_cli_install_path.exists():
            # Install CLI to /usr/local/bin.
            maestral_cli = Path(sys.executable).parent / "maestral-cli"
            destination_dir = self._macos_cli_install_path.parent

            try:
                try:
                    destination_dir.mkdir(exist_ok=True)
                    os.symlink(maestral_cli, self._macos_cli_install_path)
                except PermissionError:
                    request_authorization_from_user_and_run(
                        f"/bin/mkdir -p {destination_dir} && "
                        f"/bin/ln -s {maestral_cli} {self._macos_cli_install_path}"
                    )
            except Exception as e:
                await self.error_dialog("Could not install CLI", str(e))

        else:
            await self.error_dialog(
                "Could not install CLI",
                f"There already is a file at {self._macos_cli_install_path}",
            )

        self._update_cli_tool_button()

    def _update_cli_tool_button(self) -> None:
        if self._macos_cli_install_path.is_symlink():
            self.btn_cli_tool.enabled = True
            self.btn_cli_tool.text = "Uninstall"
            self.label_cli_tool_info.text = (
                "CLI installed. See 'maestral --help' for available commands."
            )
        elif self._macos_cli_install_path.exists():
            self.btn_cli_tool.enabled = False
            self.btn_cli_tool.text = "Install"
            self.label_cli_tool_info.text = "CLI already installed from Python package."
        else:
            self.btn_cli_tool.enabled = True
            self.btn_cli_tool.text = "Install"
            self.label_cli_tool_info.text = (
                "Install the 'maestral' command line tool to /usr/local/bin."
            )

    def set_profile_pic(self, path: bytes | str | os.PathLike | None) -> None:
        if not path or not osp.isfile(path):
            path = FACEHOLDER_PATH
        new_stat = os.stat(path)
        if new_stat != self._cached_pic_stat:
            try:
                self.profile_pic_view.image = toga.Image(path)
            except OSError:
                self.profile_pic_view.image = self.faceholder
            apply_round_clipping(self.profile_pic_view)
            self._cached_pic_stat = new_stat

    # ==== populate gui with data ======================================================

    def refresh_gui(self) -> None:
        # populate account info
        self.set_account_info_from_cache()

        # populate sync section
        self.combobox_dbx_location.current_selection = self.mdbx.dropbox_path

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

        if FROZEN:
            self._update_cli_tool_button()

    async def refresh_profile_pic(self, sender: Any = None) -> None:
        path = await call_async_maestral(self.mdbx.config_name, "get_profile_pic")
        self.set_profile_pic(path)

    async def periodic_refresh_gui(self, sender: Any = None) -> None:
        while self._refresh:
            self.refresh_gui()
            await asyncio.sleep(self._refresh_interval)

    async def periodic_refresh_profile_pic(self, sender: Any = None) -> None:
        while self._refresh:
            try:
                await self.refresh_profile_pic()
            except (ConnectionError, MaestralApiError, NotLinkedError):
                await asyncio.sleep(60 * 10)
            else:
                await asyncio.sleep(self._refresh_interval_profile_pic)

    def set_account_info_from_cache(self) -> None:
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

    def on_close_pressed(self, sender: Any = None) -> bool:
        self._refresh = False
        return True

    def show(self) -> None:
        self._refresh = True
        self.app.add_background_task(self.periodic_refresh_gui)
        self.app.add_background_task(self.periodic_refresh_profile_pic)
        super().show()
