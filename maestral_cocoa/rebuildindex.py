# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 31 16:23:13 2018

@author: samschott
"""
import toga
from toga.style.pack import Pack, HIDDEN, VISIBLE
from toga.constants import COLUMN
from toga.fonts import BOLD

from maestral.daemon import MaestralProxy

from .utils import async_call, run_maestral_async
from .private.widgets import Label, DialogButtons, Window
from .private.constants import WORD_WRAP


def _filter_status(text):
    f = list(filter(lambda x: x in '0123456789/', text))
    f = ''.join(f)
    s = f.split("/")

    if len(s) > 1:
        n = int(s[0])
        n_tot = int(s[1])
        return n, n_tot
    else:
        return None, None


class RebuildIndexDialog(Window):
    """A dialog to rebuild Maestral's sync index."""

    CONTENT_WIDTH = 600
    CONTENT_HEIGHT = 300

    REBUILD_BTN = 'Rebuild'
    CANCEL_BTN = 'Cancel'
    CLOSE_BTN = 'Done'

    def __init__(self, mdbx, app=None):
        super().__init__(title='Maestral Rebuild Index', closeable=False,
                         resizeable=False, minimizable=False, is_dialog=True, app=app)

        self.mdbx = mdbx
        self.config_name = self.mdbx.config_name

        style = Pack(width=self.CONTENT_WIDTH, padding_bottom=20)

        self.msg_title = Label(
            text='Rebuilt the Maestral index?',
            style=Pack(width=self.CONTENT_WIDTH, padding_bottom=15, font_weight=BOLD, font_size=13),
        )

        self.info = Label(
            text=(
                'If you encounter sync issues, please open "Show Sync Issues..." to check for '
                'incompatible file names, insufficient permissions or other issues which '
                'should be resolved manually. After resolving them, please pause and resume '
                'syncing. Only rebuild the index if you continue to have problems after '
                'taking those steps.\n\n'
                'Rebuilding the index may take several minutes, depending on the size of '
                'your Dropbox. Please do not modify any items in your local Dropbox folder '
                'during this process. Any changes to local files while rebuilding may be lost.'
            ),
            linebreak_mode=WORD_WRAP,
            style=Pack(width=self.CONTENT_WIDTH, padding_bottom=15, flex=1, font_size=12),
        )
        self.progress_bar = toga.ProgressBar(style=Pack(width=self.CONTENT_WIDTH, padding_bottom=7, visibility=HIDDEN))
        self.status_label = toga.Label('', style=Pack(width=self.CONTENT_WIDTH, padding_bottom=7))
        self.dialog_buttons = DialogButtons(
            labels=[self.REBUILD_BTN, self.CANCEL_BTN],
            default=self.CANCEL_BTN,
            style=style,
            on_press=self.on_dialog_press
        )

        outer_box = toga.Box(
            children=[
                self.msg_title,
                self.info,
                self.progress_bar,
                self.status_label,
                self.dialog_buttons,
            ],
            style=Pack(direction=COLUMN, width=self.CONTENT_WIDTH, padding=(20, 20, 0, 20))
        )

        self.content = outer_box

        self.rebuild_running = True

    def on_dialog_press(self, btn_name):
        if btn_name == self.REBUILD_BTN:
            self.start_rebuild()
        elif btn_name in (self.CANCEL_BTN, self.CLOSE_BTN):
            self.close()

    @async_call
    def update_status(self, interval=0.2):

        while self.rebuild_running:
            with MaestralProxy(self.config_name) as m:
                status = m.status
                self.status_label.text = m.status
                n, n_tot = _filter_status(status)
                self.progress_bar.value = n
                self.progress_bar.max = n_tot
                yield interval

    @async_call
    async def start_rebuild(self):
        self.rebuild_running = True
        self.progress_bar.style.visibility = VISIBLE
        self.update_status()

        self.dialog_buttons[self.REBUILD_BTN].enabled = False
        self.dialog_buttons[self.CANCEL_BTN].enabled = False

        self.progress_bar.value = None
        self.progress_bar.max = None
        self.progress_bar.start()

        await run_maestral_async(self.config_name, 'rebuild_index')

        self.rebuild_running = False
        self.progress_bar.stop()

        self.status_label.text = 'Rebuilding complete'
        self.dialog_buttons[self.REBUILD_BTN].enabled = True
        self.dialog_buttons[self.REBUILD_BTN].label = self.CLOSE_BTN
