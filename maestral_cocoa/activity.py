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
from .private.widgets import Label, FollowLinkButton, VibrantBox, IconForPath, Window
from .private.constants import TRUNCATE_HEAD, VisualEffectMaterial


CONTENT_WIDTH = 400
PADDING = 10
ICON_SIZE = 32
WINDOW_SIZE = (CONTENT_WIDTH + 4 * PADDING, 600)


class SyncEventView(toga.Box):

    dbx_address = 'https://www.dropbox.com/preview'

    def __init__(self, sync_event):
        style = Pack(width=CONTENT_WIDTH, direction=COLUMN, background_color=TRANSPARENT)
        super().__init__(style=style)

        text_width = CONTENT_WIDTH - 15 - ICON_SIZE

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
            linebreak_mode=TRUNCATE_HEAD,
            style=Pack(
                padding_bottom=PADDING / 2,
                width=text_width,
                background_color=TRANSPARENT,
                font_size=11,
            )
        )
        details_label = Label(
            f'{change_type} • {change_time} • {parent_dir}',
            style=Pack(
                font_size=11,
                color=GRAY,
                width=text_width,
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
                font_size=12,
                background_color=TRANSPARENT,
            ),
        )
        link_dbx = FollowLinkButton(
            'Show Online',
            url=dbx_address,
            enabled=exists,
            style=Pack(font_size=12, background_color=TRANSPARENT)
        )

        link_box = toga.Box(
            children=[link_local, link_dbx],
            style=Pack(direction=ROW, background_color=TRANSPARENT)
        )
        info_box = toga.Box(
            children=[filename_label, details_label],
            style=Pack(direction=COLUMN, background_color=TRANSPARENT)
        )
        content_box = toga.Box(
            children=[image_view, info_box],
            style=Pack(direction=ROW, width=CONTENT_WIDTH, background_color=TRANSPARENT)
        )

        if exists:
            info_box.add(link_box)

        hline = toga.Divider(style=Pack(padding=(PADDING, 0, PADDING, 0)))

        self.add(content_box, hline)


class ActivityWindow(Window):

    box_style = Pack(
        direction=COLUMN, width=CONTENT_WIDTH,
        padding=2 * PADDING,
        background_color=TRANSPARENT,
    )

    def __init__(self, mdbx, app=None):
        super().__init__(title='Maestral Activity', release_on_close=False, app=app)

        self.mdbx = mdbx
        self._cached_events = []

        self.size = WINDOW_SIZE

        self.sync_event_box = toga.Box(
            style=self.box_style
        )
        self.scroll_container = toga.ScrollContainer(
            content=self.sync_event_box,
            style=Pack(flex=1, background_color=TRANSPARENT)
        )

        self.content = VibrantBox(
            children=[self.scroll_container],
            material=VisualEffectMaterial.Popover
        )

        self.center()

        self.refresh_gui()
        self._periodic_refresh_task = None

    async def periodic_refresh_gui(self, interval=1):

        while True:
            self.refresh_gui()
            await asyncio.sleep(interval)

    def refresh_gui(self):

        history = self.mdbx.get_history()
        history.sort(key=lambda x: x['sync_time'], reverse=True)

        if history != self._cached_events:

            # remove old events
            for child in self.sync_event_box.children.copy():
                self.sync_event_box.remove(child)

            # add new events
            for event in history:
                self.sync_event_box.add(SyncEventView(event))

            self._cached_events = history

    def on_close(self):
        if self._periodic_refresh_task:
            self._periodic_refresh_task.cancel()

    def show(self):
        self._periodic_refresh_task = create_task(self.periodic_refresh_gui())
        super().show()
