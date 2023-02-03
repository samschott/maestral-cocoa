# -*- coding: utf-8 -*-

from __future__ import annotations

# system imports
import os.path as osp
from typing import Callable

# external imports
import toga
from toga.handlers import wrapped_handler
from toga.style.pack import Pack, FONT_SIZE_CHOICES
from maestral.utils.appdirs import get_home_dir
from maestral.utils.path import delete
from maestral.daemon import MaestralProxy

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

    def __init__(self, mdbx: MaestralProxy, app: toga.App) -> None:
        self.mdbx = mdbx
        self.config_name = self.mdbx.config_name

        self._on_success: Callable | None = None
        self._on_failure: Callable | None = None

        dropbox_path = self.mdbx.get_conf("sync", "path")

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

    @property
    def on_success(self):
        return self._on_success

    @on_success.setter
    def on_success(self, value):
        self._on_success = wrapped_handler(self, value)

    @property
    def on_failure(self):
        return self._on_failure

    @on_failure.setter
    def on_failure(self, value):
        self._on_failure = wrapped_handler(self, value)

    async def on_dialog_pressed(self, btn_name: str) -> None:
        self.dialog_buttons.enabled = False

        if btn_name == "Quit":
            if self.on_failure:
                self.on_failure(self)

            self.close()

        elif btn_name == "Unlink":
            self.spinner.start()

            await call_async_maestral(self.config_name, "unlink")

            if self.on_failure:
                self.on_failure(self)

            self.close()

        elif btn_name == "Select":
            # apply dropbox path
            dropbox_path = self.combobox_dbx_location.current_selection

            if osp.exists(dropbox_path):
                if is_empty(dropbox_path):
                    delete(dropbox_path, raise_error=True)
                else:
                    should_merge = await self.question_dialog(
                        title="Folder is not empty",
                        message=(
                            f'The folder "{osp.basename(dropbox_path)}" is not empty. '
                            "Would you like to merge its content with your Dropbox?"
                        ),
                    )

                    if not should_merge:  # cancel
                        self.dialog_buttons.enabled = True
                        return

            await call_async_maestral(
                self.config_name, "create_dropbox_directory", dropbox_path
            )
            self.mdbx.rebuild_index()

            if self.on_success:
                self.on_success(self)

            self.close()
