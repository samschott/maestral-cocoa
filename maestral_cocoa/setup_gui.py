import os.path as osp

import toga
from toga.style.pack import Pack, FONT_SIZE_CHOICES
from toga.constants import COLUMN, CENTER

from maestral.utils.appdirs import get_home_dir

from .private.widgets import Label, Spacer, DialogButtons, FollowLinkButton, Selection, Window, IconForPath
from .private.constants import WORD_WRAP, NSFullSizeContentViewWindowMask
from .utils import select_folder_sheet

# set default font size to 13 pt, as in macOS
Pack.validated_property('font_size', choices=FONT_SIZE_CHOICES, initial=13)


class SetupDialogGui(Window):

    WINDOW_WIDTH = 550
    WINDOW_HEIGHT = 400

    CONTENT_WIDTH = WINDOW_WIDTH - 40
    CONTENT_HEIGHT = WINDOW_HEIGHT - 15 - 25

    COMBOBOX_CHOOSE = 'Choose...'

    current_page = 0
    dbx_location_user_selected = 'DBX LOCATION'

    page_style = Pack(
        width=WINDOW_WIDTH, height=WINDOW_HEIGHT,
        direction=COLUMN,
        alignment=CENTER,
        flex=1,
        padding_top=20  # space for title bar
    )
    btn_box_style = Pack(width=CONTENT_WIDTH, padding_bottom=20)

    def __init__(self, config_name, app):
        # noinspection PyTypeChecker
        super().__init__(title='Maestral Setup', size=(self.WINDOW_WIDTH, self.WINDOW_HEIGHT), resizeable=False, minimizable=False, app=app)
        self._impl.native.titlebarAppearsTransparent = True
        self._impl.native.titleVisibility = 1
        self._impl.native.styleMask |= NSFullSizeContentViewWindowMask
        self._impl.native.movableByWindowBackground = True
        self._impl.native.level = 3

        self.config_name = config_name

        # ==== welcome page ==============================================================

        # noinspection PyTypeChecker
        image0 = toga.ImageView(
            self.app.icon,
            style=Pack(width=128, height=128, alignment=CENTER, padding=(40, 0, 40, 0))
        )
        label0 = Label(
            text='Welcome to Maestral, an open source Dropbox client for Linux and macOS.',
            style=Pack(width=self.WINDOW_WIDTH, padding_bottom=40, text_align=CENTER)
        )
        self.btn_start = toga.Button('Link Dropbox Account', style=Pack(width=180))

        self.welcome_page = toga.Box(
            children=[image0, label0, self.btn_start, Spacer(COLUMN)],
            style=self.page_style,
        )

        # ==== link page =================================================================

        # noinspection PyTypeChecker
        image1 = toga.ImageView(self.app.icon, style=Pack(width=64, height=64, padding=(40, 0, 40, 0)))
        label1 = Label(
            text=('To link Maestral to your Dropbox account, please retrieve an '
                  'authorization token from Dropbox and enter it below.'),
            linebreak_mode=WORD_WRAP,
            style=Pack(width=self.CONTENT_WIDTH, text_align=CENTER,  padding_bottom=10)
        )
        self.btn_auth_token = FollowLinkButton('Retrieve Token',  style=Pack(width=125, padding_bottom=35))
        self.text_field_auth_token = toga.TextInput(placeholder='Authorization Token', style=Pack(width=self.CONTENT_WIDTH))
        self.spinner_link = toga.ActivityIndicator(style=Pack(width=32, height=32))
        self.dialog_buttons_link_page = DialogButtons(labels=('Link', 'Cancel'), style=self.btn_box_style)

        self.link_page = toga.Box(
            children=[
                image1,
                label1,
                self.btn_auth_token,
                self.text_field_auth_token,
                Spacer(COLUMN),
                self.spinner_link,
                Spacer(COLUMN),
                self.dialog_buttons_link_page],
            style=self.page_style,
        )

        # ==== dbx location page =========================================================

        # noinspection PyTypeChecker
        image2 = toga.ImageView(self.app.icon, style=Pack(width=64, height=64, padding=(40, 0, 40, 0)))
        self.dbx_location_label = Label(
            text=('Maestral has been successfully linked with your Dropbox account.\n\n'
                  'Please select the location of your Dropbox folder below. Maestral will '
                  'create a new folder named "{}" in the selected location. In the next '
                  'step, you will be asked to choose which folders to sync.'),
            linebreak_mode=WORD_WRAP,
            style=Pack(width=self.CONTENT_WIDTH, height=80, padding_bottom=20, text_align=CENTER)
        )
        self.combobox_dbx_location = Selection(
            items=[self.dbx_location_user_selected, toga.SECTION_BREAK, self.COMBOBOX_CHOOSE],
            style=Pack(width=self.CONTENT_WIDTH, padding_bottom=20),
            on_select=self._on_button_location_pressed
        )

        self.dialog_buttons_location_page = DialogButtons(labels=('Select', 'Cancel & Unlink'), style=self.btn_box_style)

        self.dbx_location_page = toga.Box(
            children=[
                image2,
                self.dbx_location_label,
                self.combobox_dbx_location,
                Spacer(COLUMN),
                self.dialog_buttons_location_page
            ],
            style=self.page_style,
        )

        # ==== exclude folders page ======================================================

        label3 = Label(
            text=('Please select which folders to sync below. The initial download may '
                  'take a while, depending on the size of your Dropbox.'),
            linebreak_mode=WORD_WRAP,
            style=Pack(width=self.CONTENT_WIDTH, padding=(20, 0, 20, 0))
        )
        self.dropbox_folders_tree = toga.Tree(
            headings=['Folder', 'Included'],
            data=[],
            style=Pack(width=self.CONTENT_WIDTH, padding_bottom=20, flex=1),
            multiple_select=True,
        )
        self.dropbox_folders_tree._impl.columns[0].setMinWidth(150)

        self.dialog_buttons_folders_page = DialogButtons(
            labels=['Select', 'Back'],
            style=self.btn_box_style,
        )

        self.folders_page = toga.Box(
            children=[
                label3,
                self.dropbox_folders_tree,
            ],
            style=self.page_style,
        )

        # ==== done page =================================================================

        # noinspection PyTypeChecker
        image4 = toga.ImageView(self.app.icon, style=Pack(width=128, height=128, alignment=CENTER, padding=(40, 0, 40, 0)))
        label4 = Label(
            text=('You have successfully set up Maestral. Please allow some time for the '
                  'initial indexing and download of your Dropbox before Maestral will '
                  'commence syncing.'),
            linebreak_mode=WORD_WRAP,
            style=Pack(width=self.CONTENT_WIDTH, text_align=CENTER, padding_bottom=50)
        )
        self.close_button = toga.Button('Close', style=Pack(width=100), on_press=lambda s: self.close())

        self.done_page = toga.Box(
            children=[image4, label4, self.close_button, Spacer(COLUMN)],
            style=self.page_style,
        )

        self.pages = (self.welcome_page, self.link_page, self.dbx_location_page, self.folders_page, self.done_page)
        self.content = self.pages[0]

    def _on_button_location_pressed(self, widget):

        if widget.value == self.COMBOBOX_CHOOSE:
            select_folder_sheet(
                window=self,
                callback=self._on_dbx_location_selected,
            )

    def _on_dbx_location_selected(self, paths):
        if len(paths) > 0:
            path = paths[0]
            self._update_comboxbox_location(path)
        else:
            self.combobox_dbx_location.value = self.combobox_dbx_location.items[0]

    def _update_comboxbox_location(self, path):
        self.dbx_location_user_selected = path
        icon = IconForPath(path)
        short_path = self._relpath(path)
        self.combobox_dbx_location.items = [(icon, short_path), toga.SECTION_BREAK, self.COMBOBOX_CHOOSE]

    def on_loading_failed(self):
        self.dialog_buttons_folders_page['Select'].enabled = False

    @staticmethod
    def _relpath(path):
        usr = osp.abspath(osp.join(get_home_dir(), osp.pardir))
        if osp.commonprefix([path, usr]) == usr:
            return osp.relpath(path, usr)
        else:
            return path

    def go_forward(self):
        self.goto_page(self.current_page + 1)

    def go_back(self):
        self.goto_page(self.current_page - 1)

    def goto_page(self, i):
        self.current_page = i
        self.content = self.pages[self.current_page]
        self.show()

    def current_index(self):
        return self.current_page
