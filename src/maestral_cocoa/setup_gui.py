# -*- coding: utf-8 -*-

# external imports
import toga
from click import style
from toga.style.pack import Pack
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
)
from .private.constants import WORD_WRAP
from .private.implementation.cocoa.constants import NSFullSizeContentViewWindowMask


class SetupDialogGui(Window):
    WINDOW_WIDTH = 550
    WINDOW_HEIGHT = 400

    CONTENT_WIDTH = WINDOW_WIDTH - 40
    CONTENT_HEIGHT = WINDOW_HEIGHT - 15 - 25

    page_style = Pack(
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        direction=COLUMN,
        align_items=CENTER,
        justify_content=CENTER,
        flex=1,
        margin_top=20,  # space for title bar
    )
    btn_box_style = Pack(width=CONTENT_WIDTH, margin_bottom=20)

    def __init__(self) -> None:
        # noinspection PyTypeChecker
        super().__init__(
            title="Maestral Setup",
            size=(self.WINDOW_WIDTH, self.WINDOW_HEIGHT),
            resizable=False,
            minimizable=False,
        )

        # FIXME: remove private API access
        self._impl.native.titlebarAppearsTransparent = True
        self._impl.native.titleVisibility = 1
        self._impl.native.styleMask |= NSFullSizeContentViewWindowMask
        self._impl.native.movableByWindowBackground = True

        self.current_page = 0

        # ==== welcome page ============================================================
        # noinspection PyTypeChecker
        self.image0 = toga.ImageView(
            self.app.icon.path,
            style=Pack(
                width=128, height=128, align_items=CENTER, margin=(40, 0, 40, 0)
            ),
        )
        self.label0 = Label(
            text="Welcome to Maestral, an open source Dropbox client.",
            style=Pack(width=325, margin_bottom=40, text_align=CENTER),
        )
        self.btn_start = toga.Button("Link Dropbox Account", style=Pack(width=180))

        self.welcome_page = toga.Box(
            children=[self.image0, self.label0, self.btn_start, Spacer(COLUMN)],
            style=self.page_style,
        )

        # ==== link page ===============================================================

        # noinspection PyTypeChecker
        self.image1 = toga.ImageView(
            self.app.icon.path, style=Pack(width=64, height=64, margin=(40, 0, 40, 0))
        )
        self.label1 = Label(
            text=(
                "To link Maestral to your Dropbox account, please retrieve an "
                "authorization token from Dropbox and enter it below."
            ),
            linebreak_mode=WORD_WRAP,
            style=Pack(
                width=int(self.CONTENT_WIDTH * 0.9), text_align=CENTER, margin_bottom=10
            ),
        )
        self.btn_auth_token = FollowLinkButton(
            "Retrieve Token", style=Pack(width=125, margin_bottom=35)
        )
        self.text_field_auth_token = toga.TextInput(
            placeholder="Authorization Token",
            style=Pack(
                width=int(self.CONTENT_WIDTH * 0.9),
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
            self.app.icon.path, style=Pack(width=64, height=64, margin=(40, 0, 40, 0))
        )
        self.dbx_location_label = Label(
            text=(
                "Maestral has been successfully linked with your Dropbox account.\n\n"
                "Please select a local folder for your Dropbox. If the folder is not "
                "empty, you will be given the option to merge its content with your "
                "remote Dropbox. Merging will not transfer or duplicate any identical "
                "files.\n\n"
                "In the next step, you will be asked to choose which folders to sync."
            ),
            linebreak_mode=WORD_WRAP,
            style=Pack(
                width=self.CONTENT_WIDTH,
                height=90,
                margin_bottom=20,
                text_align=CENTER,
            ),
        )
        self.combobox_dbx_location = FileSelectionButton(
            initial=get_home_dir(),
            select_files=False,
            select_folders=True,
            show_full_path=True,
            style=Pack(width=int(self.CONTENT_WIDTH * 0.9), margin_bottom=20),
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
            style=Pack(width=self.CONTENT_WIDTH, margin=(20, 0, 20, 0)),
        )
        self.dropbox_tree = toga.Tree(
            headings=["Name", "Included"],
            accessors=["name", "included"],
            data=[],
            style=Pack(width=self.CONTENT_WIDTH, margin_bottom=20, flex=1),
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
                self.dialog_buttons_selective_sync_page,
            ],
            style=self.page_style,
        )

        # ==== done page ===============================================================

        # noinspection PyTypeChecker
        self.image4 = toga.ImageView(
            self.app.icon.path,
            style=Pack(
                width=128, height=128, align_items=CENTER, margin=(40, 0, 40, 0)
            ),
        )
        self.label4 = Label(
            text=(
                "You have successfully set up Maestral. Please allow some time for the "
                "initial indexing and download of your Dropbox before Maestral will "
                "commence syncing."
            ),
            linebreak_mode=WORD_WRAP,
            style=Pack(width=self.CONTENT_WIDTH, text_align=CENTER, margin_bottom=50),
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

    def go_forward(self) -> None:
        self.goto_page(self.current_page + 1)

    def go_back(self) -> None:
        self.goto_page(self.current_page - 1)

    def goto_page(self, i: int) -> None:
        self.current_page = i
        self.content.remove(self.content.children[0])
        self.content.add(self.pages[self.current_page])
        self.show()
