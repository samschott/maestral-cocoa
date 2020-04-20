# -*- coding: utf-8 -*-

# system imports
import sys
import os
import os.path as osp
import time

# external imports
import toga
from toga.style.pack import Pack
from toga.constants import ROW, COLUMN, TOP, RIGHT, CENTER, GRAY
from maestral import __version__ as __daemon_version__

# local imports
from . import __url__, __author__
from . import __version__ as __gui_version__
from .utils import apply_round_clipping, select_folder_sheet
from .private.widgets import Label, RichLabel, Switch, Selection, IconForPath, Window
from .resources import FACEHOLDER_PATH

year = time.localtime().tm_year
_wiki_url = __url__ + '/wiki'


class SettingsGui(Window):

    COLUMN_WIDTH_LEFT = 210
    COLUMN_WIDTH_RIGHT = 350
    BUTTON_WIDTH = 180

    SECTION_PADDING = 15
    ELEMENT_PADDING = 10
    SUBELEMENT_PADDING = 3
    COLUMN_PADDING = 10

    COMBOBOX_CHOOSE = 'Choose...'

    faceholder = toga.Image(FACEHOLDER_PATH)
    _cached_pic_stat = os.stat(FACEHOLDER_PATH)
    _cached_dbx_location = None

    mdbx = None

    def __init__(self, **kwargs):
        super().__init__(title='Maestral Settings', resizeable=False, minimizable=False,
                         release_on_close=False, **kwargs)

        # ==== account info section ======================================================
        self.profile_pic_view = toga.ImageView(
            self.faceholder,
            style=Pack(width=self.COLUMN_WIDTH_LEFT, height=70)
        )
        self.profile_pic_view._impl.native.imageAlignment = 3
        apply_round_clipping(self.profile_pic_view)

        self.label_name = Label(
            'Account Name (Company Name)',
            style=Pack(
                font_size=17,
                padding_bottom=self.ELEMENT_PADDING - 4,
                width=self.COLUMN_WIDTH_RIGHT
            )
        )
        self.label_email = Label(
            'email@address.com, Business',
            style=Pack(
                padding_bottom=self.SUBELEMENT_PADDING,
                width=self.COLUMN_WIDTH_RIGHT,
                font_size=12
            )
        )
        self.label_usage = Label(
            '10.5 % from 1,005 TB used',
            style=Pack(
                padding_bottom=self.ELEMENT_PADDING,
                width=self.COLUMN_WIDTH_RIGHT,
                font_size=12
            )
        )
        self.btn_unlink = toga.Button(
            'Unlink this Dropbox...',
            on_press=self.on_unlink_pressed,
            style=Pack(width=self.BUTTON_WIDTH)
        )

        account_info_box = toga.Box(
            children=[
                self.profile_pic_view,
                toga.Box(
                    children=[self.label_name, self.label_email,
                              self.label_usage, self.btn_unlink],
                    style=Pack(direction=COLUMN, padding_left=self.COLUMN_PADDING)
                ),
            ],
            style=Pack(direction=ROW)
        )

        # ==== sync settings section =====================================================

        self._label_select_folders = Label(
            'Select folders to sync:',
            style=Pack(text_align=RIGHT, width=self.COLUMN_WIDTH_LEFT)
        )
        self.btn_select_folders = toga.Button(
            label='Choose folders to sync...',
            on_press=self.on_folder_selection_pressed,
            style=Pack(padding_left=self.COLUMN_PADDING, width=self.BUTTON_WIDTH)
        )

        self._label_dbx_location = Label(
            'Dropbox Folder location:',
            style=Pack(text_align=RIGHT, width=self.COLUMN_WIDTH_LEFT)
        )
        self.combobox_dbx_location = Selection(
            items=['DBX Location', toga.SECTION_BREAK, self.COMBOBOX_CHOOSE],
            on_select=self._on_button_location_pressed,
            style=Pack(padding_left=self.COLUMN_PADDING, width=self.BUTTON_WIDTH)
        )

        dropbox_settings_box = toga.Box(
            children=[
                toga.Box(
                    children=[self._label_select_folders, self.btn_select_folders],
                    style=Pack(alignment=CENTER, padding_bottom=self.ELEMENT_PADDING),
                ),
                toga.Box(
                    children=[self._label_dbx_location, self.combobox_dbx_location],
                    style=Pack(alignment=CENTER)
                ),
            ],
            style=Pack(direction=COLUMN)
        )

        # ==== system settings section ===================================================

        self._label_update_interval = Label(
            'Check for updates:',
            style=Pack(text_align=RIGHT, width=self.COLUMN_WIDTH_LEFT)
        )
        self.combobox_update_interval = Selection(
            items=['Daily', 'Weekly', 'Monthly', 'Never'],
            on_select=self.on_update_interval_selected,
            style=Pack(padding_left=self.COLUMN_PADDING, width=self.BUTTON_WIDTH)
        )

        self._label_system_settings = Label(
            'System Settings:',
            style=Pack(text_align=RIGHT, width=self.COLUMN_WIDTH_LEFT)
        )
        self.checkbox_autostart = Switch(
            label='Start Maestral on login',
            on_toggle=self.on_autostart_clicked,
            style=Pack(
                padding_bottom=self.SUBELEMENT_PADDING,
                width=self.COLUMN_WIDTH_RIGHT
            )
        )
        self.checkbox_notifications = Switch(
            label='Enable notifications',
            on_toggle=self.on_notifications_clicked,
            style=Pack(
                padding_bottom=self.SUBELEMENT_PADDING,
                width=self.COLUMN_WIDTH_RIGHT
            )
        )
        self.checkbox_analytics = Switch(
            label='Share crash reports',
            on_toggle=self.on_analytics_clicked,
            style=Pack(width=self.COLUMN_WIDTH_RIGHT)
        )

        self._label_cli_tool = Label(
            'Command line tool:',
            style=Pack(text_align=RIGHT, width=self.COLUMN_WIDTH_LEFT)
        )

        self.label_cli_tool_info = Label(
            "Install the 'maestral' command line tool to /usr/local/bin.",
            style=Pack(
                color=GRAY,
                width=self.COLUMN_WIDTH_RIGHT,
                padding_left=self.COLUMN_PADDING,
            )
        )

        self.btn_cli_tool = toga.Button(
            'Install',
            on_press=self.on_cli_pressed,
            style=Pack(
                width=self.BUTTON_WIDTH / 2,
                padding_bottom=self.SUBELEMENT_PADDING,
                padding_left=self.COLUMN_PADDING,
            )
        )

        children = [
            toga.Box(
                children=[self._label_update_interval,
                          self.combobox_update_interval],
                style=Pack(
                    alignment=CENTER, padding_bottom=self.ELEMENT_PADDING
                ),
            ),
            toga.Box(
                children=[
                    self._label_system_settings,
                    toga.Box(
                        children=[
                            self.checkbox_autostart,
                            self.checkbox_notifications,
                            self.checkbox_analytics
                        ],
                        style=Pack(
                            alignment=TOP, direction=COLUMN,
                            padding_left=self.COLUMN_PADDING,
                        ),
                    )
                ],
            )
        ]

        if getattr(sys, 'frozen', False):
            children.append(
                toga.Box(
                    children=[
                        self._label_cli_tool,
                        self.btn_cli_tool,
                    ],
                    style=Pack(alignment=CENTER, padding_top=self.ELEMENT_PADDING)
                )
            )
            children.append(
                toga.Box(
                    children=[
                        Label(' ', style=Pack(text_align=RIGHT, width=self.COLUMN_WIDTH_LEFT)),
                        self.label_cli_tool_info,
                    ],
                    style=Pack(alignment=CENTER, padding_top=self.SUBELEMENT_PADDING)
                )
            )

        maestral_settings_box = toga.Box(
            children=children,
            style=Pack(direction=COLUMN),
        )

        # ==== about section =============================================================

        about_box = toga.Box(
            children=[
                Label(
                    'About Maestral:',
                    style=Pack(text_align=RIGHT, width=self.COLUMN_WIDTH_LEFT)
                ),
                toga.Box(
                    children=[
                        Label(
                            f'v{__gui_version__} (daemon v{__daemon_version__})',
                            style=Pack(
                                padding_bottom=self.SUBELEMENT_PADDING,
                                width=self.COLUMN_WIDTH_RIGHT)
                        ),
                        RichLabel(
                            html=f'<a href="{_wiki_url}">{__url__}</a>',
                            style=Pack(
                                padding_bottom=self.SUBELEMENT_PADDING,
                                width=self.COLUMN_WIDTH_RIGHT)
                        ),
                        Label(
                            f'(c) 2018 - {year}, {__author__}.',
                            style=Pack(color=GRAY, width=self.COLUMN_WIDTH_RIGHT)
                        ),
                    ],
                    style=Pack(direction=COLUMN, padding_left=self.COLUMN_PADDING),
                )
            ],
            style=Pack(direction=ROW)
        )

        main_box = toga.Box(
            children=[
                account_info_box,
                toga.Divider(style=Pack(padding=self.SECTION_PADDING)),
                dropbox_settings_box,
                toga.Divider(style=Pack(padding=self.SECTION_PADDING)),
                maestral_settings_box,
                toga.Divider(style=Pack(padding=self.SECTION_PADDING)),
                about_box,
            ],
            style=Pack(
                direction=COLUMN, padding=30,
                width=self.COLUMN_WIDTH_LEFT + self.COLUMN_WIDTH_RIGHT
            )
        )

        self.content = main_box

    def _on_button_location_pressed(self, widget):

        if widget.value == self.COMBOBOX_CHOOSE:
            select_folder_sheet(
                window=self,
                message=('Choose a new place for your Dropbox folder. A folder named '
                         f'"Dropbox ({self.mdbx.config_name.title()})" will be '
                         'created in the selected location.'),
                callback=self._on_dbx_location_selected,
            )

    def _on_dbx_location_selected(self, paths):

        if len(paths) > 0:
            path = paths[0]

            self._update_combobox_location(path)
            self.on_dbx_location_selected(path)
        else:
            self.combobox_dbx_location.value = self.combobox_dbx_location.items[0]

    def _update_combobox_location(self, path):
        if path != self._cached_dbx_location:
            self._cached_dbx_location = path
            icon = IconForPath(path)
            short_path = osp.basename(path)
            self.combobox_dbx_location.items = [
                (icon, short_path), toga.SECTION_BREAK, self.COMBOBOX_CHOOSE
            ]

    def set_profile_pic(self, path):
        path = path if osp.isfile(path) else FACEHOLDER_PATH
        new_stat = os.stat(path)
        if new_stat != self._cached_pic_stat:
            try:
                self.profile_pic_view.image = toga.Image(path)
            except OSError:
                self.profile_pic_view.image = self.faceholder
            self.profile_pic_view._impl.native.imageAlignment = 3
            apply_round_clipping(self.profile_pic_view)

            self._cached_pic_stat = new_stat

    # ==== callbacks to implement ========================================================

    def on_dbx_location_selected(self, path):
        pass

    def on_folder_selection_pressed(self, widget):
        pass

    def on_unlink_pressed(self, yes):
        pass

    def on_update_interval_selected(self, widget):
        pass

    def on_autostart_clicked(self, widget):
        pass

    def on_notifications_clicked(self, widget):
        pass

    def on_analytics_clicked(self, widget):
        pass

    def on_cli_pressed(self, widget):
        pass
