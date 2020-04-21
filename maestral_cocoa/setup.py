# -*- coding: utf-8 -*-

# system imports
import os.path as osp

# external imports
from maestral.utils.path import delete
from maestral.utils.appdirs import get_home_dir

# local imports
from .private.constants import OFF
from .utils import alert_sheet, run_maestral_async, async_call
from .setup_gui import SetupDialogGui
from .selective_sync_gui import FileSystemSource


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
        default_location = osp.dirname(self.mdbx.get_conf('main', 'path')) or get_home_dir()
        self._update_comboxbox_location(default_location)

        # connect buttons to callbacks
        self.btn_start.on_press = self.on_start
        self.dialog_buttons_link_page.on_press = self.on_link_dialog
        self.dialog_buttons_location_page.on_press = self.on_dbx_location
        self.dialog_buttons_selective_sync_page.on_press = self.on_items_selected
        self.close_button.on_press = self.on_finish

        default_folder_name = self.mdbx.get_conf('main', 'default_dir_name')
        location_label_text = self.dbx_location_label.text.format(default_folder_name)
        self.dbx_location_label.text = location_label_text

    # ====================================================================================
    # User interaction callbacks
    # ====================================================================================

    def on_start(self, widget):
        # start auth flow
        self.btn_auth_token.url = self.mdbx.get_auth_url()
        self.go_forward()

    @async_call
    async def on_link_dialog(self, btn_name):

        if btn_name == 'Cancel':
            self.close()

        token = self.text_field_auth_token.value
        if not token:
            alert_sheet(
                window=self,
                title='Authentication failed.',
                message='Please enter an authentication token.',
                icon=self.app.icon,
            )

        else:
            self.spinner_link.start()
            self.dialog_buttons_link_page.enabled = False
            self.text_field_auth_token.enabled = False

            res = await run_maestral_async(self.mdbx.config_name, 'link', token)

            if res == 0:

                # initialize fs source
                self.fs_source = FileSystemSource(gui_parent=self, mdbx=self.mdbx)
                self.fs_source.included.style.padding_left = 10
                self.selective_sync_page.add(self.fs_source.included,
                                             self.dialog_buttons_selective_sync_page)
                self.dropbox_tree.data = self.fs_source  # triggers loading

                # switch to next page
                self.go_forward()

            elif res == 1:
                alert_sheet(
                    window=self,
                    title='Authentication failed.',
                    message=('Please make sure that you entered the '
                             'correct authentication token.'),
                    icon=self.app.icon,
                )

            elif res == 2:
                alert_sheet(
                    window=self,
                    title='Connection failed.',
                    message=('Please make sure that you are connected '
                             'to the internet and try again.'),
                    icon=self.app.icon,
                )

            # reset contents of link page
            self.spinner_link.stop()
            self.text_field_auth_token.value = ''
            self.text_field_auth_token.enabled = True
            self.dialog_buttons_link_page.enabled = True

    def on_dbx_location(self, btn_name):

        if btn_name == 'Select':
            # apply dropbox path
            self._chosen_dropbox_folder = osp.join(
                self.dbx_location_user_selected,
                self.mdbx.get_conf('main', 'default_dir_name')
            )
            if osp.isdir(self._chosen_dropbox_folder):
                msg = ('The folder "{}" already exists. Would you like '
                       'to replace it or merge its contents with Dropbox?')
                alert_sheet(
                    window=self,
                    title='Folder already exists',
                    message=msg.format(self._chosen_dropbox_folder),
                    button_labels=('Replace', 'Cancel', 'Merge'),
                    icon=self.app.icon,
                    callback=self._on_exists,
                )

            elif osp.isfile(self._chosen_dropbox_folder):
                msg = ('There already is a file named "{}" at this location. '
                       'Would you like to replace it?')
                alert_sheet(
                    window=self,
                    title='File conflict',
                    message=msg.format(self.mdbx.get_conf('main', 'default_dir_name')),
                    button_labels=('Replace', 'Cancel'),
                    icon=self.app.icon,
                    callback=self._on_exists,
                )
            else:
                self._continue()

        elif btn_name == 'Cancel & Unlink':
            self.mdbx.unlink()
            self.close()

    def _on_exists(self, choice):

        if choice == 0:    # replace
            delete(self._chosen_dropbox_folder)
            self._continue()
        elif choice == 1:  # cancel
            return
        elif choice == 2:  # merge
            self._continue()

    def _continue(self):

        try:
            self.mdbx.create_dropbox_directory(path=self._chosen_dropbox_folder)
        except OSError:
            alert_sheet(
                window=self,
                title='Could not create folder',
                message=('Please make sure that you have permissions '
                         'to write to the selected location.'),
                button_labels=('Ok',),
                icon=self.app.icon,
            )
        else:
            # switch to next page
            self.go_forward()

    def on_items_selected(self, btn_name):

        if btn_name == 'Select':

            self.get_selected_items(self.fs_source)
            self.mdbx.set_excluded_items(self.excluded_items)

            # if any excluded folders are currently on the drive, delete them
            for item in self.excluded_items:
                local_item = self.mdbx.to_local_path(item)
                delete(local_item)

            # switch to next page
            self.go_forward()

        elif btn_name == 'Back':
            self.go_back()

    def on_finish(self, widget):
        self.exit_status = self.ACCEPTED
        self.close()

    # ====================================================================================
    # Helper functions
    # ====================================================================================

    def get_selected_items(self, parent):

        for child in parent._children:
            child_path_lower = child.path.lower()
            if child.included.state == OFF:
                self.excluded_items.append(child_path_lower)

            self.get_selected_items(child)
