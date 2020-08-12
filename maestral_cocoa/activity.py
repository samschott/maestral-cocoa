# -*- coding: utf-8 -*-

# system imports
import os.path as osp
import asyncio
import urllib.parse
from datetime import datetime

# external imports
import toga
from toga.style.pack import Pack
from toga.constants import ROW, COLUMN, TRANSPARENT, GRAY

# local imports
from .utils import create_task
from .private.widgets import Label, FollowLinkButton, IconForPath, Window, ScrollContainer

PADDING = 10
ICON_SIZE = 32
WINDOW_SIZE = (400, 600)


class SyncEventView(toga.Box):

    dbx_address = 'https://www.dropbox.com/preview'

    def __init__(self, sync_event):
        style = Pack(flex=1, direction=COLUMN, background_color=TRANSPARENT)
        super().__init__(style=style)

        self.sync_event = sync_event

        dbx_address = self.dbx_address + urllib.parse.quote(self.sync_event['dbx_path'])
        dirname, filename = osp.split(self.sync_event['local_path'])
        parent_dir = osp.basename(dirname)
        change_type = self.sync_event['change_type'].capitalize()

        dt = datetime.fromtimestamp(self.sync_event['change_time'] or self.sync_event['sync_time'])
        change_time = dt.strftime('%d %b %Y %H:%M')
        exists = osp.exists(self.sync_event['local_path'])

        if self.sync_event['item_type'] == 'folder' and not exists:
            icon = IconForPath('/usr')
        else:
            icon = IconForPath(self.sync_event['local_path'])

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

        filename_label = Label(
            filename,
            style=Pack(
                padding_bottom=PADDING / 2,
                flex=1,
                background_color=TRANSPARENT,
                font_size=11,
            )
        )
        details_label = Label(
            f'{change_type} {change_time} • {parent_dir}',
            style=Pack(
                font_size=11,
                color=GRAY,
                flex=1,
                padding_bottom=PADDING / 2,
                background_color=TRANSPARENT,
            )
        )

        link_local = FollowLinkButton(
            'Show in Finder',
            url=self.sync_event['local_path'],
            enabled=exists,
            locate=True,
            style=Pack(
                padding_right=PADDING,
                font_size=11,
                background_color=TRANSPARENT,
                height=12
            ),
        )
        link_dbx = FollowLinkButton(
            'Show Online',
            url=dbx_address,
            enabled=exists,
            style=Pack(font_size=11, background_color=TRANSPARENT, height=12)
        )

        link_box = toga.Box(
            children=[link_local, link_dbx],
            style=Pack(direction=ROW, flex=1, background_color=TRANSPARENT, height=12)
        )
        info_box = toga.Box(
            children=[filename_label, details_label],
            style=Pack(direction=COLUMN, flex=1, background_color=TRANSPARENT)
        )
        content_box = toga.Box(
            children=[image_view, info_box],
            style=Pack(direction=ROW, flex=1, background_color=TRANSPARENT)
        )

        if exists:
            info_box.add(link_box)

        hline = toga.Divider(style=Pack(padding=(PADDING, 0, PADDING, 0)))

        self.add(content_box, hline)


class ActivityWindow(Window):

    def __init__(self, mdbx, app=None):
        super().__init__(title='Maestral Activity', release_on_close=False, app=app)

        self.mdbx = mdbx
        self._ids = set()

        self.size = WINDOW_SIZE

        self.sync_event_box = toga.Box(
            style=Pack(
                direction=COLUMN, flex=1,
                padding=2 * PADDING,
                background_color=TRANSPARENT,
            )
        )
        self.scroll_container = ScrollContainer(
            content=self.sync_event_box,
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

        for event in self.mdbx.get_history():
            if event['id'] not in self._ids:
                self.sync_event_box.insert(0, SyncEventView(event))
                self._ids.add(event['id'])

    def on_close(self):
        if self._periodic_refresh_task:
            self._periodic_refresh_task.cancel()

    def show(self):
        self._periodic_refresh_task = create_task(self.periodic_refresh_gui())
        super().show()
