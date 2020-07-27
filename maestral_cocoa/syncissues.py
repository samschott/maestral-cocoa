# -*- coding: utf-8 -*-

# system imports
import os.path as osp
import asyncio
import urllib.parse

# external imports
import toga
from toga.style.pack import Pack
from toga.constants import ROW, COLUMN, TRANSPARENT

# local imports
from .private.widgets import Label, FollowLinkButton, VibrantBox, IconForPath, Window
from .private.constants import TRUNCATE_HEAD, WORD_WRAP, VisualEffectMaterial


CONTENT_WIDTH = 330
PADDING = 10
ICON_SIZE = 48
WINDOW_SIZE = (CONTENT_WIDTH + 4 * PADDING, 400)


class SyncIssueView(toga.Box):

    dbx_address = 'https://www.dropbox.com/preview'

    def __init__(self, sync_err):
        style = Pack(width=CONTENT_WIDTH, direction=COLUMN, background_color=TRANSPARENT)
        super().__init__(style=style)

        text_width = CONTENT_WIDTH - 15 - ICON_SIZE

        self.sync_err = sync_err
        dbx_address = self.dbx_address + urllib.parse.quote(self.sync_err['dbx_path'])

        icon = IconForPath(self.sync_err['local_path'])
        image_view = toga.ImageView(
            image=icon,
            style=Pack(
                width=ICON_SIZE,
                height=ICON_SIZE,
                padding=(0, 12, 0, 3),
                flex=1,
                background_color=TRANSPARENT,
            ),
        )

        # FIXME: avoid private API
        image_view._impl.native.imageAlignment = 3

        path_label = Label(
            osp.basename(self.sync_err['local_path']),
            linebreak_mode=TRUNCATE_HEAD,
            style=Pack(
                padding_bottom=PADDING / 2,
                width=text_width,
                background_color=TRANSPARENT,
            )
        )
        error_label = Label(
            self.sync_err['title'] + ':\n' + self.sync_err['message'],
            linebreak_mode=WORD_WRAP,
            style=Pack(
                font_size=11,
                width=text_width,
                padding_bottom=PADDING / 2,
                background_color=TRANSPARENT,
            )
        )

        link_local = FollowLinkButton(
            'Show in Finder',
            url=self.sync_err['local_path'],
            enabled=osp.exists(self.sync_err['local_path']),
            locate=True,
            style=Pack(
                padding_right=PADDING,
                font_size=12,
                background_color=TRANSPARENT,
            ),
        )
        link_dbx = FollowLinkButton(
            'Show Online',
            url=dbx_address,
            style=Pack(font_size=12, background_color=TRANSPARENT)
        )

        link_box = toga.Box(
            children=[link_local, link_dbx],
            style=Pack(direction=ROW, background_color=TRANSPARENT)
        )
        info_box = toga.Box(
            children=[path_label, error_label, link_box],
            style=Pack(direction=COLUMN, background_color=TRANSPARENT)
        )
        content_box = toga.Box(
            children=[image_view, info_box],
            style=Pack(direction=ROW, width=CONTENT_WIDTH, background_color=TRANSPARENT)
        )

        hline = toga.Divider(style=Pack(padding=(PADDING, 0, PADDING, 0)))

        self.add(content_box, hline)


class SyncIssuesWindow(Window):

    box_style = Pack(
        direction=COLUMN, width=CONTENT_WIDTH,
        padding=2 * PADDING,
        background_color=TRANSPARENT,
    )

    def __init__(self, mdbx, app=None):
        super().__init__(title='Maestral Sync Issues', release_on_close=False, app=app)

        self.mdbx = mdbx
        self._cached_errors = []

        self.size = WINDOW_SIZE
        # FIXME: avoid private API
        self._impl.native.titlebarAppearsTransparent = True

        self.placeholder_label = Label(
            'No sync issues 😊',
            style=Pack(
                padding_bottom=PADDING,
                width=CONTENT_WIDTH,
                background_color=TRANSPARENT,
            )
        )

        self.sync_errors_box = toga.Box(
            children=[self.placeholder_label],
            style=self.box_style
        )
        self.scroll_container = toga.ScrollContainer(
            content=self.sync_errors_box,
            style=Pack(flex=1, background_color=TRANSPARENT)
        )

        self.content = VibrantBox(
            children=[self.scroll_container],
            material=VisualEffectMaterial.Popover
        )

        self.center()

        self.refresh_gui()
        self._periodic_refresh_task = asyncio.Task(self.periodic_refresh_gui())

    async def periodic_refresh_gui(self, interval=1):

        while True:
            self.refresh_gui()
            await asyncio.sleep(interval)

    def refresh_gui(self):

        new_errors = self.mdbx.sync_errors

        if new_errors != self._cached_errors:

            print(self.sync_errors_box.children)

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
        self._periodic_refresh_task.cancel()

    def show(self):
        asyncio.ensure_future(self._periodic_refresh_task)
        super().show()
