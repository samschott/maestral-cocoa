# -*- coding: utf-8 -*-

# system imports
import time

# external imports
import toga
from toga.style.pack import Pack
from toga.constants import ROW, COLUMN, TOP, RIGHT, CENTER, GRAY, TRANSPARENT
from maestral import __version__ as __daemon_version__
from maestral.utils.appdirs import get_home_dir

# local imports
from . import __url__, __author__, __version__
from .private.widgets import (
    Label,
    RichLabel,
    Switch,
    FileSelectionButton,
    Window,
    apply_round_clipping,
)
from .resources import FACEHOLDER_PATH
from .constants import FROZEN


year = time.localtime().tm_year
_wiki_url = __url__ + "/wiki"


class SettingsGui(Window):

    COLUMN_WIDTH_LEFT = 210
    COLUMN_WIDTH_RIGHT = 350
    BUTTON_WIDTH = 180
    IMAGE_WIDTH = 70

    SECTION_PADDING = 15
    ELEMENT_PADDING = 10
    SUBELEMENT_PADDING = 3
    COLUMN_PADDING = 10

    faceholder = toga.Image(FACEHOLDER_PATH)

    def __init__(self, **kwargs):
        super().__init__(
            title="Maestral Settings",
            resizeable=False,
            minimizable=False,
            release_on_close=False,
            **kwargs,
        )

        # ==== account info section ====================================================

        self.profile_pic_view = toga.ImageView(
            self.faceholder,
            style=Pack(
                width=SettingsGui.IMAGE_WIDTH,
                height=SettingsGui.IMAGE_WIDTH,
                background_color=TRANSPARENT,
            ),
        )
        apply_round_clipping(self.profile_pic_view)

        self.profile_pic_view_spacer = toga.Box(
            style=Pack(
                width=SettingsGui.COLUMN_WIDTH_LEFT - SettingsGui.IMAGE_WIDTH,
                direction=ROW,
                background_color=TRANSPARENT,
            )
        )

        self.label_name = Label(
            "Account Name (Company Name)",
            style=Pack(
                font_size=17,
                padding_bottom=SettingsGui.ELEMENT_PADDING - 4,
                width=SettingsGui.COLUMN_WIDTH_RIGHT,
            ),
        )
        self.label_email = Label(
            "email@address.com, Business",
            style=Pack(
                padding_bottom=SettingsGui.SUBELEMENT_PADDING,
                width=SettingsGui.COLUMN_WIDTH_RIGHT,
                font_size=12,
            ),
        )
        self.label_usage = Label(
            "10.5 % from 1,005 TB used",
            style=Pack(
                padding_bottom=SettingsGui.ELEMENT_PADDING,
                width=SettingsGui.COLUMN_WIDTH_RIGHT,
                font_size=12,
            ),
        )
        self.btn_unlink = toga.Button(
            "Unlink this Dropbox...", style=Pack(width=SettingsGui.BUTTON_WIDTH)
        )

        account_info_box = toga.Box(
            children=[
                self.profile_pic_view_spacer,
                self.profile_pic_view,
                toga.Box(
                    children=[
                        self.label_name,
                        self.label_email,
                        self.label_usage,
                        self.btn_unlink,
                    ],
                    style=Pack(
                        direction=COLUMN, padding_left=SettingsGui.COLUMN_PADDING
                    ),
                ),
            ],
            style=Pack(direction=ROW),
        )

        # ==== sync settings section ===================================================

        self._label_select_folders = Label(
            "Selective sync:",
            style=Pack(text_align=RIGHT, width=SettingsGui.COLUMN_WIDTH_LEFT),
        )
        self.btn_select_folders = toga.Button(
            label="Select files and folders...",
            style=Pack(
                padding_left=SettingsGui.COLUMN_PADDING, width=SettingsGui.BUTTON_WIDTH
            ),
        )

        self._label_dbx_location = Label(
            "Dropbox Folder location:",
            style=Pack(text_align=RIGHT, width=SettingsGui.COLUMN_WIDTH_LEFT),
        )
        self.combobox_dbx_location = FileSelectionButton(
            initial=get_home_dir(),
            select_files=False,
            select_folders=True,
            style=Pack(
                padding_left=SettingsGui.COLUMN_PADDING, width=SettingsGui.BUTTON_WIDTH
            ),
        )

        dropbox_settings_box = toga.Box(
            children=[
                toga.Box(
                    children=[self._label_select_folders, self.btn_select_folders],
                    style=Pack(
                        alignment=CENTER, padding_bottom=SettingsGui.ELEMENT_PADDING
                    ),
                ),
                toga.Box(
                    children=[self._label_dbx_location, self.combobox_dbx_location],
                    style=Pack(alignment=CENTER),
                ),
            ],
            style=Pack(direction=COLUMN),
        )

        # ==== system settings section =================================================

        self._label_update_interval = Label(
            "Check for updates:",
            style=Pack(text_align=RIGHT, width=SettingsGui.COLUMN_WIDTH_LEFT),
        )
        self.combobox_update_interval = toga.Selection(
            items=["Daily", "Weekly", "Monthly", "Never"],
            style=Pack(
                padding_left=SettingsGui.COLUMN_PADDING, width=SettingsGui.BUTTON_WIDTH
            ),
        )

        self._label_system_settings = Label(
            "System Settings:",
            style=Pack(text_align=RIGHT, width=SettingsGui.COLUMN_WIDTH_LEFT),
        )
        self.checkbox_autostart = Switch(
            label="Start Maestral on login",
            style=Pack(
                padding_bottom=SettingsGui.SUBELEMENT_PADDING,
                width=SettingsGui.COLUMN_WIDTH_RIGHT,
            ),
        )
        self.checkbox_notifications = Switch(
            label="Enable notifications",
            style=Pack(
                padding_bottom=SettingsGui.SUBELEMENT_PADDING,
                width=SettingsGui.COLUMN_WIDTH_RIGHT,
            ),
        )

        self._label_cli_tool = Label(
            "Command line tool:",
            style=Pack(text_align=RIGHT, width=SettingsGui.COLUMN_WIDTH_LEFT),
        )

        self.label_cli_tool_info = Label(
            "Install the 'maestral' command line tool to /usr/local/bin.",
            style=Pack(
                color=GRAY,
                font_size=12,
                width=SettingsGui.COLUMN_WIDTH_RIGHT,
                padding_left=SettingsGui.COLUMN_PADDING,
            ),
        )

        self.btn_cli_tool = toga.Button(
            "Install",
            style=Pack(
                width=SettingsGui.BUTTON_WIDTH / 2,
                padding_bottom=SettingsGui.SUBELEMENT_PADDING,
                padding_left=SettingsGui.COLUMN_PADDING,
            ),
        )

        children = [
            toga.Box(
                children=[self._label_update_interval, self.combobox_update_interval],
                style=Pack(
                    alignment=CENTER, padding_bottom=SettingsGui.ELEMENT_PADDING
                ),
            ),
            toga.Box(
                children=[
                    self._label_system_settings,
                    toga.Box(
                        children=[
                            self.checkbox_autostart,
                            self.checkbox_notifications,
                        ],
                        style=Pack(
                            alignment=TOP,
                            direction=COLUMN,
                            padding_left=SettingsGui.COLUMN_PADDING,
                        ),
                    ),
                ],
            ),
        ]

        if FROZEN:
            # add UI to install command line interface
            children.append(
                toga.Box(
                    children=[
                        self._label_cli_tool,
                        self.btn_cli_tool,
                    ],
                    style=Pack(
                        alignment=CENTER, padding_top=SettingsGui.ELEMENT_PADDING
                    ),
                )
            )
            children.append(
                toga.Box(
                    children=[
                        Label(
                            " ",
                            style=Pack(
                                text_align=RIGHT, width=SettingsGui.COLUMN_WIDTH_LEFT
                            ),
                        ),
                        self.label_cli_tool_info,
                    ],
                    style=Pack(
                        alignment=CENTER, padding_top=SettingsGui.SUBELEMENT_PADDING
                    ),
                )
            )

        maestral_settings_box = toga.Box(
            children=children,
            style=Pack(direction=COLUMN),
        )

        # ==== about section ===========================================================

        about_box = toga.Box(
            children=[
                Label(
                    "About Maestral:",
                    style=Pack(text_align=RIGHT, width=SettingsGui.COLUMN_WIDTH_LEFT),
                ),
                toga.Box(
                    children=[
                        Label(
                            f"GUI v{__version__}, daemon v{__daemon_version__}",
                            style=Pack(
                                padding_bottom=SettingsGui.SUBELEMENT_PADDING,
                                width=SettingsGui.COLUMN_WIDTH_RIGHT,
                            ),
                        ),
                        RichLabel(
                            html=f'<a href="{_wiki_url}">{__url__}</a>',
                            style=Pack(
                                padding_bottom=SettingsGui.SUBELEMENT_PADDING,
                                width=SettingsGui.COLUMN_WIDTH_RIGHT,
                            ),
                        ),
                        Label(
                            f"(c) 2018 - {year}, {__author__}.",
                            style=Pack(
                                color=GRAY, width=SettingsGui.COLUMN_WIDTH_RIGHT
                            ),
                        ),
                    ],
                    style=Pack(
                        direction=COLUMN, padding_left=SettingsGui.COLUMN_PADDING
                    ),
                ),
            ],
            style=Pack(direction=ROW),
        )

        main_box = toga.Box(
            children=[
                account_info_box,
                toga.Divider(style=Pack(padding=SettingsGui.SECTION_PADDING)),
                dropbox_settings_box,
                toga.Divider(style=Pack(padding=SettingsGui.SECTION_PADDING)),
                maestral_settings_box,
                toga.Divider(style=Pack(padding=SettingsGui.SECTION_PADDING)),
                about_box,
            ],
            style=Pack(
                direction=COLUMN,
                padding=30,
                width=SettingsGui.COLUMN_WIDTH_LEFT + SettingsGui.COLUMN_WIDTH_RIGHT,
            ),
        )

        self.content = main_box
