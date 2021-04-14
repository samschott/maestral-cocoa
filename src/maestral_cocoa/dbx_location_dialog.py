# -*- coding: utf-8 -*-

# system imports
import os.path as osp

# external imports
from toga.style.pack import Pack, FONT_SIZE_CHOICES
from maestral.utils.appdirs import get_home_dir
from maestral.utils.path import delete

# local imports
from .private.widgets import FileSelectionButton
from .dialogs import Dialog
from .utils import call_async_maestral, is_empty


# set default font size to 13 pt, as in macOS
Pack.validated_property("font_size", choices=FONT_SIZE_CHOICES, initial=13)


class DbxLocationDialog(Dialog):

    WINDOW_WIDTH = 600
    CONTENT_WIDTH = (
        WINDOW_WIDTH
        - Dialog.PADDING_LEFT
        - Dialog.PADDING_RIGHT
        - Dialog.ICON_PADDING_RIGHT
        - Dialog.ICON_SIZE[0]
    )

    COMBOBOX_CHOOSE = "Choose..."

    ACCEPTED = 0
    REJECTED = 1

    def __init__(self, app):

        self.mdbx = app.mdbx
        self.config_name = self.mdbx.config_name
        self.exit_status = self.REJECTED

        dropbox_path = self.mdbx.get_conf("main", "path")

        if dropbox_path == "":
            dropbox_path = f"{get_home_dir()}/Dropbox ({self.config_name.capitalize()})"

        message = (
            "Your Dropbox folder has been moved or deleted from its original location. "
            "Syncing will not work until you move it back.\n\n"
            'To move it back, click "Quit" below, move the Dropbox folder back to its '
            "original location, and launch Maestral again. "
            "To re-download your Dropbox, please select a new folder below.\n\n"
            'Select "Unlink" to unlink your Dropbox account from Maestral.'
        )

        self.combobox_dbx_location = FileSelectionButton(
            initial=dropbox_path,
            select_files=False,
            select_folders=True,
            show_full_path=True,
            style=Pack(width=self.CONTENT_WIDTH, padding=(10, 0, 30, 0)),
        )

        # noinspection PyTypeChecker
        super().__init__(
            title="Cannot find Dropbox folder",
            message=message,
            button_labels=("Select", "Quit", "Unlink"),
            default="Select",
            accessory_view=self.combobox_dbx_location,
            callback=self.on_dialog_pressed,
            app=app,
        )

        self.msg_content.style.font_size = 12
        self.msg_content.style.width = 450
        self.msg_content.style.height = 130

    async def on_dialog_pressed(self, btn_name):

        self.dialog_buttons.enabled = False

        if btn_name == "Quit":
            self.exit_status = self.REJECTED
            self.close()

        elif btn_name == "Unlink":
            self.spinner.start()
            self.mdbx.unlink()
            self.exit_status = self.REJECTED
            self.close()

        elif btn_name == "Select":
            # apply dropbox path
            dropbox_path = self.combobox_dbx_location.current_selection

            if osp.exists(dropbox_path):

                if is_empty(dropbox_path):
                    delete(dropbox_path, raise_error=True)
                else:
                    choice = await self.alert_sheet(
                        title="Folder is not empty",
                        message=(
                            f'The folder "{osp.basename(dropbox_path)}" is not empty. '
                            "Would you like to delete its content or merge it with "
                            "your Dropbox?"
                        ),
                        button_labels=("Delete", "Cancel", "Merge"),
                    )

                    if choice == 0:  # replace
                        delete(dropbox_path, raise_error=True)
                    elif choice == 1:  # cancel
                        self.dialog_buttons.enabled = True
                        return
                    elif choice == 2:  # merge
                        pass

            await call_async_maestral(
                self.config_name, "create_dropbox_directory", dropbox_path
            )
            self.mdbx.rebuild_index()
            self.exit_status = self.ACCEPTED
            self.close()
