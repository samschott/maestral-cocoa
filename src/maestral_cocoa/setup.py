# -*- coding: utf-8 -*-

# system imports
import os.path as osp
from typing import Any

# external imports
import toga
from maestral.utils.path import delete
from maestral.utils.appdirs import get_home_dir
from maestral.daemon import MaestralProxy

# local imports
from .private.constants import OFF
from .utils import call_async_maestral, is_empty
from .setup_gui import SetupDialogGui
from .selective_sync import FileSystemSource


class SetupDialog(SetupDialogGui):

    ACCEPTED = 0
    REJECTED = 1

    def __init__(self, mdbx: MaestralProxy, app: toga.App) -> None:
        super().__init__(app=app)
        self.exit_status = self.REJECTED

        self.mdbx = mdbx
        self.config_name = self.mdbx.config_name

        # set up combobox
        dropbox_path = f"{get_home_dir()}/Dropbox ({self.config_name.capitalize()})"
        self.combobox_dbx_location.current_selection = dropbox_path

        # connect buttons to callbacks
        self.btn_start.on_press = self.on_start
        self.dialog_buttons_link_page.on_press = self.on_link_dialog
        self.dialog_buttons_location_page.on_press = self.on_dbx_location
        self.dialog_buttons_selective_sync_page.on_press = self.on_items_selected
        self.close_button.on_press = self.on_finish
        self.text_field_auth_token.on_change = self._token_field_validator

    # ==================================================================================
    # User interaction callbacks
    # ==================================================================================

    async def on_start(self, widget: Any) -> None:
        # start auth flow
        self.btn_auth_token.url = self.mdbx.get_auth_url()
        self.go_forward()

    async def on_link_dialog(self, btn_name: str) -> None:

        if btn_name == "Cancel":
            self.close()

        elif btn_name == "Link":

            token = self.text_field_auth_token.value

            self.spinner_link.start()
            self.dialog_buttons_link_page.enabled = False
            self.text_field_auth_token.enabled = False

            res = await call_async_maestral(self.config_name, "link", token)

            if res == 0:

                # initialize fs source
                self.fs_source = FileSystemSource(
                    mdbx=self.mdbx,
                    on_fs_loading_failed=self.on_loading_failed,
                )
                self.fs_source.included.style.padding_left = 10
                self.selective_sync_page.add(
                    self.fs_source.included, self.dialog_buttons_selective_sync_page
                )
                self.dropbox_tree.data = self.fs_source  # triggers loading

                # switch to next page
                self.go_forward()

            elif res == 1:
                await self.alert_sheet(
                    title="Authentication failed.",
                    message=(
                        "Please make sure that you entered the "
                        "correct authentication token."
                    ),
                )

            elif res == 2:
                await self.alert_sheet(
                    title="Connection failed.",
                    message=(
                        "Please make sure that you are connected "
                        "to the internet and try again."
                    ),
                )

            # reset contents of link page
            self.spinner_link.stop()
            self.text_field_auth_token.value = ""
            self.text_field_auth_token.enabled = True
            self.dialog_buttons_link_page.enabled = True

    async def on_dbx_location(self, btn_name: str) -> None:

        if btn_name == "Select":

            dropbox_path = self.combobox_dbx_location.current_selection

            # try to create the directory
            # continue to next page if success or alert user if failed
            try:

                # If a file / folder exists, ask for conflict resolution.
                if osp.exists(dropbox_path):

                    if is_empty(dropbox_path):
                        delete(dropbox_path, raise_error=True)
                    else:
                        choice = await self.alert_sheet(
                            title="Folder is not empty",
                            message=(
                                f'The folder "{osp.basename(dropbox_path)}" is not '
                                "empty. Would you like merge its content with "
                                "your Dropbox?"
                            ),
                            button_labels=("Cancel", "Merge"),
                        )

                        if choice == 0:  # cancel
                            return
                        elif choice == 1:  # merge
                            pass

                self.mdbx.create_dropbox_directory(dropbox_path)
            except OSError:
                await self.alert_sheet(
                    title="Could not set folder",
                    message=(
                        "Please make sure that you have permissions "
                        "to write to the selected location."
                    ),
                    button_labels=("Ok",),
                )
            else:
                self.go_forward()

        elif btn_name == "Cancel & Unlink":
            self.mdbx.unlink()
            self.close()

    async def on_items_selected(self, btn_name: str) -> None:

        self.fs_source.stop_loading()

        if btn_name == "Select":

            excluded_nodes = self.fs_source.get_nodes_with_state(OFF)
            excluded_paths = [node.path_lower for node in excluded_nodes]
            self.mdbx.excluded_items = excluded_paths

            # if any excluded folders are currently on the drive, delete them
            for path in excluded_paths:
                local_path = self.mdbx.to_local_path(path)
                delete(local_path)

            # switch to next page
            self.go_forward()

        elif btn_name == "Back":
            self.go_back()

    async def on_finish(self, widget: Any) -> None:
        self.exit_status = self.ACCEPTED
        self.close()

    def _token_field_validator(self, widget: toga.TextInput) -> None:
        self.dialog_buttons_link_page["Link"].enabled = len(widget.value) > 10

    def on_loading_failed(self) -> None:
        self.dialog_buttons_selective_sync_page["Select"].enabled = False
