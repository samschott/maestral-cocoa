# -*- coding: utf-8 -*-

# external imports
import toga
from toga.style.pack import Pack
from toga.constants import COLUMN, TOP, RIGHT, LEFT

# local imports
from .private.widgets import Label, RadioButton, Window, DialogButtons


class BandwidthGui(Window):
    COLUMN_WIDTH_LEFT = 100
    COLUMN_WIDTH_RIGHT = 250

    ELEMENT_PADDING = 10
    COLUMN_PADDING = 10

    def __init__(self, **kwargs) -> None:
        super().__init__(title="Bandwidth Settings", size=(400, 250), **kwargs)

        self._label_download_rate = Label(
            "Download rate:",
            style=Pack(text_align=RIGHT, width=BandwidthGui.COLUMN_WIDTH_LEFT),
        )

        self.radio_button_unlimited_down = RadioButton(
            "Don't limit", group=RadioButton.Group.A
        )
        self.radio_button_limited_down = RadioButton(
            "Limit to:", group=RadioButton.Group.A
        )
        self.number_input_limit_down = toga.NumberInput(
            value=1.0,
            min_value=0.005,
            style=Pack(padding_left=BandwidthGui.COLUMN_PADDING, width=70),
        )
        self._unit_label_down = toga.Label(
            "MB/s",
            style=Pack(padding_left=BandwidthGui.COLUMN_PADDING, width=50),
        )

        self._label_upload_rate = Label(
            "Upload rate:",
            style=Pack(text_align=RIGHT, width=BandwidthGui.COLUMN_WIDTH_LEFT),
        )

        self.radio_button_unlimited_up = RadioButton(
            "Don't limit", group=RadioButton.Group.B
        )
        self.radio_button_limited_up = RadioButton(
            "Limit to:", group=RadioButton.Group.B
        )
        self.number_input_limit_up = toga.NumberInput(
            value=1.0,
            min_value=0.005,
            style=Pack(padding_left=BandwidthGui.COLUMN_PADDING, width=70),
        )
        self._unit_label_up = toga.Label(
            "MB/s",
            style=Pack(padding_left=BandwidthGui.COLUMN_PADDING, width=50),
        )

        self.dialog_buttons = DialogButtons(
            labels=["Update", "Cancel"],
            style=Pack(padding=(20, 20, 20, 20), flex=1),
        )

        children = [
            toga.Box(
                children=[
                    self._label_download_rate,
                    toga.Box(
                        children=[
                            self.radio_button_unlimited_down,
                            toga.Box(
                                children=[
                                    self.radio_button_limited_down,
                                    self.number_input_limit_down,
                                    self._unit_label_down,
                                ],
                            ),
                        ],
                        style=Pack(
                            alignment=TOP,
                            direction=COLUMN,
                            padding_left=BandwidthGui.COLUMN_PADDING,
                        ),
                    ),
                ],
            ),
            toga.Box(
                children=[
                    self._label_upload_rate,
                    toga.Box(
                        children=[
                            self.radio_button_unlimited_up,
                            toga.Box(
                                children=[
                                    self.radio_button_limited_up,
                                    self.number_input_limit_up,
                                    self._unit_label_up,
                                ],
                            ),
                        ],
                        style=Pack(
                            alignment=TOP,
                            direction=COLUMN,
                            padding_left=BandwidthGui.COLUMN_PADDING,
                        ),
                    ),
                ],
                style=Pack(padding_top=BandwidthGui.ELEMENT_PADDING),
            ),
            self.dialog_buttons,
        ]

        main_box = toga.Box(
            children=children,
            style=Pack(
                direction=COLUMN,
                padding=30,
                width=BandwidthGui.COLUMN_WIDTH_LEFT + BandwidthGui.COLUMN_WIDTH_RIGHT,
                flex=1,
                alignment=LEFT,
            ),
        )

        self.content = main_box
