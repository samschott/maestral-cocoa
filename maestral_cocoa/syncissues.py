# -*- coding: utf-8 -*-

# system imports
import os.path as osp
import asyncio
import urllib.parse

# external imports
import toga
from toga.style.pack import Pack
from toga.constants import ROW, COLUMN, TRANSPARENT, GREEN

# local imports
from .utils import create_task
from .private.widgets import Label, FollowLinkButton, Icon, Window, ScrollContainer
from .private.constants import WORD_WRAP


PADDING = 10
ICON_SIZE = 48
WINDOW_SIZE = (370, 400)


class SyncIssueView(toga.Box):

    dbx_address = 'https://www.dropbox.com/preview'

    def __init__(self, sync_err):
        style = Pack(flex=1, direction=COLUMN, background_color=TRANSPARENT)
        super().__init__(style=style)

        self.sync_err = sync_err
        dbx_address = self.dbx_address + urllib.parse.quote(self.sync_err['dbx_path'])

        icon = Icon(for_path=self.sync_err['local_path'])
        # noinspection PyTypeChecker
        image_view = toga.ImageView(
            image=icon,
            style=Pack(
                width=ICON_SIZE,
                height=ICON_SIZE,
                padding=(0, 12, 0, 3),
                background_color=TRANSPARENT,
            ),
        )

        path_label = Label(
            osp.basename(self.sync_err['local_path']),
            style=Pack(
                padding_bottom=PADDING / 2,
                flex=1,
                background_color=TRANSPARENT,
            )
        )
        error_label = Label(
            self.sync_err['title'] + ':\n' + self.sync_err['message'],
            linebreak_mode=WORD_WRAP,
            style=Pack(
                font_size=11,
                width=WINDOW_SIZE[0] - 4 * PADDING - 15 - ICON_SIZE,
                padding_bottom=PADDING / 2,
                background_color=GREEN,
            )
        )

        link_local = FollowLinkButton(
            'Show in Finder',
            url=self.sync_err['local_path'],
            enabled=osp.exists(self.sync_err['local_path']),
            locate=True,
            style=Pack(
                padding_right=PADDING,
                font_size=11,
                height=12,
                background_color=TRANSPARENT,
            ),
        )
        link_dbx = FollowLinkButton(
            'Show Online',
            url=dbx_address,
            style=Pack(font_size=11, height=12, background_color=TRANSPARENT)
        )

        link_box = toga.Box(
            children=[link_local, link_dbx],
            style=Pack(direction=ROW, flex=1, background_color=TRANSPARENT)
        )
        info_box = toga.Box(
            children=[path_label, error_label, link_box],
            style=Pack(direction=COLUMN, flex=1, background_color=TRANSPARENT)
        )
        content_box = toga.Box(
            children=[image_view, info_box],
            style=Pack(direction=ROW, flex=1, background_color=TRANSPARENT)
        )

        hline = toga.Divider(style=Pack(padding=(PADDING, 0, PADDING, 0)))

        self.add(content_box, hline)


class SyncIssuesWindow(Window):

    def __init__(self, mdbx, app=None):
        super().__init__(title='Maestral Sync Issues', release_on_close=False, app=app)

        self.mdbx = mdbx
        self._cached_errors = []

        self.size = WINDOW_SIZE

        self.placeholder_label = Label(
            'No sync issues 😊',
            style=Pack(
                padding_bottom=PADDING,
                flex=1,
                background_color=TRANSPARENT,
            )
        )

        self.sync_errors_box = toga.Box(
            children=[self.placeholder_label],
            style=Pack(
                direction=COLUMN, flex=1,
                padding=2 * PADDING,
                background_color=TRANSPARENT,
            )
        )
        self.scroll_container = ScrollContainer(
            content=self.sync_errors_box,
            horizontal=False,
            style=Pack(flex=1, background_color=TRANSPARENT)
        )

        self.content = self.scroll_container
        self.center()

        self.refresh_gui()
        self._periodic_refresh_task = None

    async def periodic_refresh_gui(self, interval=1):

        while True:
            self.refresh_gui()
            await asyncio.sleep(interval)

    def refresh_gui(self):

        new_errors = self.mdbx.sync_errors

        if new_errors != self._cached_errors:

            # remove old errors
            for child in self.sync_errors_box.children.copy():
                self.sync_errors_box.remove(child)

            # add new errors
            if len(new_errors) == 0:
                self.sync_errors_box.add(self.placeholder_label)
            else:
                for e in new_errors:
                    self.sync_errors_box.add(SyncIssueView(e))

            self._cached_errors = new_errors

    def on_close(self):
        if self._periodic_refresh_task:
            self._periodic_refresh_task.cancel()

    def show(self):
        self._periodic_refresh_task = create_task(self.periodic_refresh_gui())
        super().show()
