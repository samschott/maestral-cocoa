# -*- coding: utf-8 -*-

from __future__ import annotations


# external imports
import toga
from maestral.daemon import MaestralProxy

# local imports
from .bandwidth_gui import BandwidthGui
from .private.widgets import Window


MB_2_BYTES = 10**6


class BandwidthDialog(BandwidthGui):
    def __init__(self, mdbx: MaestralProxy, app: toga.App):
        super().__init__(app=app, is_dialog=True)

        self.mdbx = mdbx
        self.dialog_buttons.on_press = self.on_dialog_pressed

        self.radio_button_unlimited_down.on_change = self.on_limit_downloads_toggled
        self.radio_button_limited_down.on_change = self.on_limit_downloads_toggled
        self.radio_button_unlimited_up.on_change = self.on_limit_uploads_toggled
        self.radio_button_limited_up.on_change = self.on_limit_uploads_toggled

    def refresh_gui(self) -> None:
        if self.mdbx.bandwidth_limit_down == 0:
            self.radio_button_unlimited_down.value = True
            self.number_input_limit_down.enabled = False
        else:
            self.radio_button_limited_down.value = True
            self.number_input_limit_down.value = (
                self.mdbx.bandwidth_limit_down / MB_2_BYTES
            )
            self.number_input_limit_down.enabled = True

        if self.mdbx.bandwidth_limit_up == 0:
            self.radio_button_unlimited_up.value = True
            self.number_input_limit_up.enabled = False
        else:
            self.radio_button_limited_up.value = True
            self.number_input_limit_up.value = self.mdbx.bandwidth_limit_up / MB_2_BYTES
            self.number_input_limit_up.enabled = True

    def update_settings(self):
        if self.radio_button_unlimited_down.value is True:
            self.mdbx.bandwidth_limit_down = 0.0
        else:
            self.mdbx.bandwidth_limit_down = (
                float(self.number_input_limit_down.value) * MB_2_BYTES
            )

        if self.radio_button_unlimited_up.value is True:
            self.mdbx.bandwidth_limit_up = 0.0
        else:
            self.mdbx.bandwidth_limit_up = (
                float(self.number_input_limit_up.value) * MB_2_BYTES
            )

    async def on_limit_downloads_toggled(self, widget: toga.Selection) -> None:
        if widget is self.radio_button_unlimited_down:
            self.number_input_limit_down.enabled = False
        elif widget is self.radio_button_limited_down:
            self.number_input_limit_down.enabled = True
        else:
            raise RuntimeError(f"Unexpected widget {widget}")

    async def on_limit_uploads_toggled(self, widget: toga.Selection) -> None:
        if widget is self.radio_button_unlimited_up:
            self.number_input_limit_up.enabled = False
        elif widget is self.radio_button_limited_up:
            self.number_input_limit_up.enabled = True
        else:
            raise RuntimeError(f"Unexpected widget {widget}")

    async def on_dialog_pressed(self, btn_name: str) -> None:
        try:
            if btn_name == "Update":
                self.update_settings()
        finally:
            self.close()

    def show_as_sheet(self, window: Window) -> None:
        self.refresh_gui()
        super().show_as_sheet(window)

    def show(self) -> None:
        self.refresh_gui()
        super().show()
