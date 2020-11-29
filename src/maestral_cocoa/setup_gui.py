# -*- coding: utf-8 -*-

# external imports
import toga
from toga.style.pack import Pack, FONT_SIZE_CHOICES
from toga.constants import COLUMN, CENTER
from maestral.utils.appdirs import get_home_dir

# local imports
from .private.widgets import (
    Label,
    Spacer,
    DialogButtons,
    FollowLinkButton,
    FileSelectionButton,
    Window,
    TextInput,
)
from .private.constants import WORD_WRAP
from .private.implementation.cocoa.constants import NSFullSizeContentViewWindowMask


# set default font size to 13 pt, as in macOS
Pack.validated_property("font_size", choices=FONT_SIZE_CHOICES, initial=13)


class SetupDialogGui(Window):

    WINDOW_WIDTH = 550
    WINDOW_HEIGHT = 400

    CONTENT_WIDTH = WINDOW_WIDTH - 40
    CONTENT_HEIGHT = WINDOW_HEIGHT - 15 - 25

    current_page = 0

    page_style = Pack(
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        direction=COLUMN,
        alignment=CENTER,
        flex=1,
        padding_top=20,  # space for title bar
    )
    btn_box_style = Pack(width=CONTENT_WIDTH, padding_bottom=20)

    def __init__(self, app):
        # noinspection PyTypeChecker
        super().__init__(
            title="Maestral Setup",
            size=(self.WINDOW_WIDTH, self.WINDOW_HEIGHT),
            resizeable=False,
            minimizable=False,
            app=app,
        )

        # FIXME: remove private API access
        self._impl.native.titlebarAppearsTransparent = True
        self._impl.native.titleVisibility = 1
        self._impl.native.styleMask |= NSFullSizeContentViewWindowMask
        self._impl.native.movableByWindowBackground = True
        self._impl.native.level = 3

        # ==== welcome page ============================================================
        # noinspection PyTypeChecker
        self.image0 = toga.ImageView(
            self.app.icon,
            style=Pack(width=128, height=128, alignment=CENTER, padding=(40, 0, 40, 0)),
        )
        self.label0 = Label(
            text="Welcome to Maestral, an open source Dropbox client.",
            style=Pack(width=self.WINDOW_WIDTH, padding_bottom=40, text_align=CENTER),
        )
        self.btn_start = toga.Button("Link Dropbox Account", style=Pack(width=180))

        self.welcome_page = toga.Box(
            children=[self.image0, self.label0, self.btn_start, Spacer(COLUMN)],
            style=self.page_style,
        )

        # ==== link page ===============================================================

        # noinspection PyTypeChecker
        self.image1 = toga.ImageView(
            self.app.icon, style=Pack(width=64, height=64, padding=(40, 0, 40, 0))
        )
        self.label1 = Label(
            text=(
                "To link Maestral to your Dropbox account, please retrieve an "
                "authorization token from Dropbox and enter it below."
            ),
            linebreak_mode=WORD_WRAP,
            style=Pack(
                width=self.CONTENT_WIDTH * 0.9, text_align=CENTER, padding_bottom=10
            ),
        )
        self.btn_auth_token = FollowLinkButton(
            "Retrieve Token", style=Pack(width=125, padding_bottom=35)
        )
        self.text_field_auth_token = TextInput(
            placeholder="Authorization Token",
            style=Pack(
                width=self.CONTENT_WIDTH * 0.9,
                text_align=CENTER,
            ),
        )
        self.spinner_link = toga.ActivityIndicator(style=Pack(width=32, height=32))
        self.dialog_buttons_link_page = DialogButtons(
            labels=("Link", "Cancel"), style=self.btn_box_style
        )
        self.dialog_buttons_link_page["Link"].enabled = False

        self.link_page = toga.Box(
            children=[
                self.image1,
                self.label1,
                self.btn_auth_token,
                self.text_field_auth_token,
                Spacer(COLUMN),
                self.spinner_link,
                Spacer(COLUMN),
                self.dialog_buttons_link_page,
            ],
            style=self.page_style,
        )

        # ==== dbx location page =======================================================

        # noinspection PyTypeChecker
        self.image2 = toga.ImageView(
            self.app.icon, style=Pack(width=64, height=64, padding=(40, 0, 40, 0))
        )
        self.dbx_location_label = Label(
            text=(
                "Maestral has been successfully linked with your Dropbox account.\n\n"
                "Please select the location of your Dropbox folder below. Maestral "
                'will create a new folder named "{}" in the selected location. In the '
                "next step, you will be asked to choose which folders to sync."
            ),
            linebreak_mode=WORD_WRAP,
            style=Pack(
                width=self.CONTENT_WIDTH,
                height=90,
                padding_bottom=20,
                text_align=CENTER,
            ),
        )
        self.combobox_dbx_location = FileSelectionButton(
            initial=get_home_dir(),
            select_files=False,
            select_folders=True,
            style=Pack(width=self.CONTENT_WIDTH * 0.9, padding_bottom=20),
        )

        self.dialog_buttons_location_page = DialogButtons(
            labels=("Select", "Cancel & Unlink"), style=self.btn_box_style
        )

        self.dbx_location_page = toga.Box(
            children=[
                self.image2,
                self.dbx_location_label,
                self.combobox_dbx_location,
                Spacer(COLUMN),
                self.dialog_buttons_location_page,
            ],
            style=self.page_style,
        )

        # ==== selective sync page =====================================================

        self.label3 = Label(
            text=(
                "Please select which files and folders to sync below. The initial "
                "download may take some time, depending on the size of your Dropbox."
            ),
            linebreak_mode=WORD_WRAP,
            style=Pack(width=self.CONTENT_WIDTH, padding=(20, 0, 20, 0)),
        )
        self.dropbox_tree = toga.Tree(
            headings=["Name", "Included"],
            accessors=["name", "included"],
            data=[],
            style=Pack(width=self.CONTENT_WIDTH, padding_bottom=20, flex=1),
            multiple_select=True,
        )

        self.dialog_buttons_selective_sync_page = DialogButtons(
            labels=["Select", "Back"],
            style=self.btn_box_style,
        )

        self.selective_sync_page = toga.Box(
            children=[
                self.label3,
                self.dropbox_tree,
            ],
            style=self.page_style,
        )

        # ==== done page ===============================================================

        # noinspection PyTypeChecker
        self.image4 = toga.ImageView(
            self.app.icon,
            style=Pack(width=128, height=128, alignment=CENTER, padding=(40, 0, 40, 0)),
        )
        self.label4 = Label(
            text=(
                "You have successfully set up Maestral. Please allow some time for the "
                "initial indexing and download of your Dropbox before Maestral will "
                "commence syncing."
            ),
            linebreak_mode=WORD_WRAP,
            style=Pack(width=self.CONTENT_WIDTH, text_align=CENTER, padding_bottom=50),
        )
        self.close_button = toga.Button(
            "Close", style=Pack(width=100), on_press=lambda s: self.close()
        )

        self.done_page = toga.Box(
            children=[self.image4, self.label4, self.close_button, Spacer(COLUMN)],
            style=self.page_style,
        )

        self.pages = (
            self.welcome_page,
            self.link_page,
            self.dbx_location_page,
            self.selective_sync_page,
            self.done_page,
        )
        self.content = toga.Box(children=[self.pages[0]])

    def go_forward(self):
        self.goto_page(self.current_page + 1)

    def go_back(self):
        self.goto_page(self.current_page - 1)

    def goto_page(self, i):
        self.current_page = i
        self.content.remove(self.content.children[0])
        self.content.add(self.pages[self.current_page])
        self.show()

    def current_index(self):
        return self.current_page
