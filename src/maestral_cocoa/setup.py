# -*- coding: utf-8 -*-

# system imports
import os.path as osp

# external imports
from maestral.utils.path import delete
from maestral.utils.appdirs import get_home_dir

# local imports
from .private.constants import OFF
from .utils import call_async_threaded_maestral
from .setup_gui import SetupDialogGui
from .selective_sync import FileSystemSource


class SetupDialog(SetupDialogGui):

    ACCEPTED = 0
    REJECTED = 1

    def __init__(self, app):
        super().__init__(app=app)
        self.exit_status = self.REJECTED

        self.mdbx = self.app.mdbx

        self._chosen_dropbox_folder = None
        self.excluded_items = []

        # set up combobox
        default_location = self.mdbx.get_conf("main", "path")
        default_parent = osp.dirname(default_location) or get_home_dir()
        self.combobox_dbx_location.current_selection = default_parent

        # connect buttons to callbacks
        self.btn_start.on_press = self.on_start
        self.dialog_buttons_link_page.on_press = self.on_link_dialog
        self.dialog_buttons_location_page.on_press = self.on_dbx_location
        self.dialog_buttons_selective_sync_page.on_press = self.on_items_selected
        self.close_button.on_press = self.on_finish
        self.text_field_auth_token.on_change = self._token_field_validator

        default_folder_name = self.mdbx.get_conf("main", "default_dir_name")
        location_label_text = self.dbx_location_label.text.format(default_folder_name)
        self.dbx_location_label.text = location_label_text

    # ====================================================================================
    # User interaction callbacks
    # ====================================================================================

    async def on_start(self, widget):
        # start auth flow
        self.btn_auth_token.url = self.mdbx.get_auth_url()
        self.go_forward()

    async def on_link_dialog(self, btn_name):

        if btn_name == "Cancel":
            self.close()

        elif btn_name == "Link":

            token = self.text_field_auth_token.value

            self.spinner_link.start()
            self.dialog_buttons_link_page.enabled = False
            self.text_field_auth_token.enabled = False

            res = await call_async_threaded_maestral(
                self.mdbx.config_name, "link", token
            )

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

    async def on_dbx_location(self, btn_name):

        if btn_name == "Select":

            default_name = self.mdbx.get_conf("main", "default_dir_name")
            self._chosen_dropbox_folder = osp.join(
                self.combobox_dbx_location.current_selection, default_name
            )

            # if a file / folder exists, ask for conflict resolution
            if osp.exists(self._chosen_dropbox_folder):
                if osp.isdir(self._chosen_dropbox_folder):
                    msg = (
                        'A folder "{}" already exists at this location. Would you like '
                        "to replace it or merge its contents with Dropbox?"
                    )
                    choice = await self.alert_sheet(
                        title="Folder already exists",
                        message=msg.format(default_name),
                        button_labels=("Replace", "Cancel", "Merge"),
                    )

                else:
                    msg = (
                        'A file named "{}" already exists at this location. '
                        "Would you like to replace it?"
                    )
                    choice = await self.alert_sheet(
                        title="File conflict",
                        message=msg.format(default_name),
                        button_labels=("Replace", "Cancel"),
                    )

                if choice == 0:  # replace
                    delete(self._chosen_dropbox_folder)
                elif choice == 1:  # cancel
                    return
                elif choice == 2:  # merge
                    pass

            # try to create the directory
            # continue to next page if success or alert user if failed
            try:
                self.mdbx.create_dropbox_directory(path=self._chosen_dropbox_folder)
            except OSError:
                await self.alert_sheet(
                    title="Could not create folder",
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

    async def on_items_selected(self, btn_name):

        if btn_name == "Select":

            self._get_selected_items(self.fs_source)
            self.mdbx.set_excluded_items(self.excluded_items)

            # if any excluded folders are currently on the drive, delete them
            for item in self.excluded_items:
                local_item = self.mdbx.to_local_path(item)
                delete(local_item)

            # switch to next page
            self.go_forward()

        elif btn_name == "Back":
            self.go_back()

    async def on_finish(self, widget):
        self.exit_status = self.ACCEPTED
        self.close()

    def _token_field_validator(self, widget):
        self.dialog_buttons_link_page["Link"].enabled = len(widget.value) > 10

    def on_loading_failed(self):
        self.dialog_buttons_selective_sync_page["Select"].enabled = False

    # ====================================================================================
    # Helper functions
    # ====================================================================================

    def _get_selected_items(self, parent):

        for child in parent._children:
            child_path_lower = child.path.lower()
            if child.included.state == OFF:
                self.excluded_items.append(child_path_lower)

            self._get_selected_items(child)
