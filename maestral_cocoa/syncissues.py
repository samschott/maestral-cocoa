# -*- coding: utf-8 -*-

# system imports
import os.path as osp
import asyncio
import urllib.parse

# external imports
import toga
from toga.style.pack import Pack
from toga.constants import ROW, COLUMN

# local imports
from .utils import async_call, clear_background
from .private.widgets import Label, FollowLinkButton, VibrantBox, IconForPath, Window
from .private.constants import TRUNCATE_HEAD, WORD_WRAP, VisualEffectMaterial


CONTENT_WIDTH = 330
PADDING = 10
ICON_SIZE = 48
WINDOW_SIZE = (CONTENT_WIDTH + 4 * PADDING, 400)


# TODO: use toga.DetailedList to display sync errors (once it is view-based)

class SyncIssueBox(toga.Box):

    dbx_address = "https://www.dropbox.com/preview"

    def __init__(self, sync_err):
        style = Pack(width=CONTENT_WIDTH, direction=COLUMN)
        super().__init__(style=style)

        text_width = CONTENT_WIDTH - 15 - ICON_SIZE

        self.sync_err = sync_err
        dbx_address = self.dbx_address + urllib.parse.quote(self.sync_err["dbx_path"])

        icon = IconForPath(self.sync_err['local_path'])
        image_view = toga.ImageView(
            image=icon,
            style=Pack(width=ICON_SIZE, height=ICON_SIZE, padding=(0, 12, 0, 3), flex=1),
        )
        image_view._impl.native.imageAlignment = 3

        path_label = Label(
            osp.basename(self.sync_err['local_path']),
            linebreak_mode=TRUNCATE_HEAD,
            style=Pack(padding_bottom=PADDING / 2, width=text_width)
        )
        error_label = Label(
            self.sync_err["title"] + ":\n" + self.sync_err["message"],
            linebreak_mode=WORD_WRAP,
            style=Pack(font_size=11, width=text_width, padding_bottom=PADDING / 2)
        )

        link_local = FollowLinkButton(
            'Show in Finder',
            url=self.sync_err["local_path"],
            enabled=osp.exists(self.sync_err["local_path"]),
            locate=True,
            style=Pack(padding_right=PADDING, font_size=12),
        )
        link_dbx = FollowLinkButton(
            'Show Online',
            url=dbx_address,
            style=Pack(font_size=12)
        )

        link_box = toga.Box(children=[link_local, link_dbx], style=Pack(direction=ROW))
        info_box = toga.Box(
            children=[path_label, error_label, link_box],
            style=Pack(direction=COLUMN)
        )
        content_box = toga.Box(
            children=[image_view, info_box],
            style=Pack(direction=ROW, width=CONTENT_WIDTH)
        )

        hline = toga.Divider(style=Pack(padding=(PADDING, 0, PADDING, 0)))

        self.add(content_box, hline)


class SyncIssuesWindow(Window):

    placeholder_label = Label(
        'No sync issues 😊',
        style=Pack(padding_bottom=PADDING, width=CONTENT_WIDTH)
    )

    box_style = Pack(direction=COLUMN, width=CONTENT_WIDTH, padding=2 * PADDING)

    def __init__(self, mdbx, app=None):
        super().__init__(title='Maestral Sync Issues', release_on_close=False, app=app)

        self.mdbx = mdbx
        self.refresh = True
        self._cached_errors = []

        self.size = WINDOW_SIZE
        self._impl.native.titlebarAppearsTransparent = True

        sync_errors_box = toga.Box(
            children=[self.placeholder_label],
            style=self.box_style
        )
        self.scroll_container = toga.ScrollContainer(
            content=sync_errors_box,
            style=Pack(flex=1)
        )

        clear_background(self.scroll_container)

        self.periodic_refresh_gui()
        self.content = VibrantBox(
            children=[self.scroll_container],
            material=VisualEffectMaterial.Popover
        )

        self.center()

    @async_call
    async def periodic_refresh_gui(self, interval=1):

        while self.refresh:
            if self.visible:
                self.refresh_gui()

            await asyncio.sleep(interval)

    def refresh_gui(self):

        new_errors = self.mdbx.sync_errors

        if new_errors != self._cached_errors:
            if len(new_errors) == 0:
                sync_errors_box = toga.Box(
                    children=[self.placeholder_label],
                    style=self.box_style
                )
            else:
                sync_errors_box = toga.Box(
                    children=list(SyncIssueBox(e) for e in new_errors),
                    style=self.box_style
                )

            clear_background(sync_errors_box)
            self.scroll_container.content = sync_errors_box

            self._cached_errors = new_errors

    def on_close(self):
        self.refresh = False
