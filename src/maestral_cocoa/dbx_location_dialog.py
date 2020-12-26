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
from .utils import call_async_maestral


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

        self._old_path = self.mdbx.get_conf("main", "path")
        self.default_dirname = f"Dropbox ({self.mdbx.config_name.capitalize()})"

        message = (
            "Your Dropbox folder has been moved or deleted from its original location. "
            "Maestral will not work properly until you move it back. It used to be "
            'located at:\n\n{0}\n\nTo move it back, click "Quit" below, move the '
            "Dropbox folder back to its original location, and launch Maestral again. "
            "To re-download your Dropbox, please select a location for your Dropbox "
            'folder below. Maestral will create a new folder named "{1}" in the '
            "selected location.\n\nTo unlink your Dropbox account from Maestral, "
            'click "Unlink" below.'
        ).format(self._old_path, self.default_dirname)

        self.combobox_dbx_location = FileSelectionButton(
            initial=get_home_dir(),
            select_files=False,
            select_folders=True,
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
        self.msg_content.style.height = 170

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
            chosen_dropbox_folder = osp.join(
                self.combobox_dbx_location.current_selection,
                self.default_dirname,
            )

            if osp.exists(chosen_dropbox_folder):

                if osp.isdir(chosen_dropbox_folder):
                    choice = self.alert_sheet(
                        title="Folder already exists",
                        message=(
                            f'The folder "{chosen_dropbox_folder}" already '
                            "exists. Would you like to replace it or merge its "
                            "contents with Dropbox?"
                        ),
                        button_labels=("Replace", "Cancel", "Merge"),
                    )

                else:
                    choice = self.alert_sheet(
                        title="File conflict",
                        message=(
                            f'There already is a file named "{self.default_dirname}" '
                            f"at this location. Would you like to replace it?"
                        ),
                        button_labels=("Replace", "Cancel"),
                    )

                if choice == 0:  # replace
                    delete(chosen_dropbox_folder)
                elif choice == 1:  # cancel
                    self.dialog_buttons.enabled = True
                    return
                elif choice == 2:  # merge
                    pass

            await call_async_maestral(
                self.mdbx.config_name, "create_dropbox_directory", chosen_dropbox_folder
            )
            self.mdbx.rebuild_index()
            self.exit_status = self.ACCEPTED
            self.close()
