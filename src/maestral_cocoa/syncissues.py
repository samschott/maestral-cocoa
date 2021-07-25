# -*- coding: utf-8 -*-

# system imports
import os.path as osp
import asyncio
import urllib.parse
from typing import List, Any

# external imports
import toga
from toga.style.pack import Pack
from toga.constants import ROW, COLUMN
from maestral.daemon import MaestralProxy

# local imports
from .private.widgets import Label, FollowLinkButton, Icon, Window
from .private.constants import WORD_WRAP


PADDING = 10
ICON_SIZE = 48
WINDOW_SIZE = (370, 400)


class SyncIssueView(toga.Box):

    dbx_address = "https://www.dropbox.com/preview"

    def __init__(self, sync_err: dict) -> None:
        super().__init__(style=Pack(direction=COLUMN))

        self.sync_err = sync_err
        dbx_address = self.dbx_address + urllib.parse.quote(self.sync_err["dbx_path"])

        icon = Icon(for_path=self.sync_err["local_path"])
        # noinspection PyTypeChecker
        image_view = toga.ImageView(
            image=icon,
            style=Pack(
                width=ICON_SIZE,
                height=ICON_SIZE,
                padding=(0, 12, 0, 3),
            ),
        )

        path_label = Label(
            osp.basename(self.sync_err["local_path"]),
            style=Pack(
                padding_bottom=PADDING / 2,
            ),
        )
        error_label = Label(
            self.sync_err["title"] + ":\n" + self.sync_err["message"],
            linebreak_mode=WORD_WRAP,
            style=Pack(
                font_size=11,
                width=WINDOW_SIZE[0] - 4 * PADDING - 15 - ICON_SIZE,
                padding_bottom=PADDING / 2,
            ),
        )

        link_local = FollowLinkButton(
            "Show in Finder",
            url=self.sync_err["local_path"],
            enabled=osp.exists(self.sync_err["local_path"]),
            locate=True,
            style=Pack(
                padding_right=PADDING,
                font_size=11,
                height=12,
            ),
        )
        link_dbx = FollowLinkButton(
            "Show Online",
            url=dbx_address,
            style=Pack(font_size=11, height=12),
        )

        link_box = toga.Box(
            children=[link_local, link_dbx],
            style=Pack(direction=ROW),
        )
        info_box = toga.Box(
            children=[path_label, error_label, link_box],
            style=Pack(direction=COLUMN, flex=1),
        )
        content_box = toga.Box(
            children=[image_view, info_box],
            style=Pack(direction=ROW),
        )

        hline = toga.Divider(style=Pack(padding=(PADDING, 0, PADDING, 0)))

        self.add(content_box, hline)


class SyncIssuesWindow(Window):
    def __init__(self, mdbx: MaestralProxy, app: toga.App) -> None:
        super().__init__(title="Maestral Sync Issues", release_on_close=False, app=app)
        self.on_close = self.on_close_pressed

        self.mdbx = mdbx
        self._cached_errors: List[dict] = []

        self._refresh = False
        self._refresh_interval = 1

        self.size = WINDOW_SIZE

        placeholder_label = Label(
            "No sync issues 😊",
            style=Pack(padding_bottom=PADDING),
        )

        self.sync_errors_box = toga.Box(
            children=[placeholder_label],
            style=Pack(
                direction=COLUMN,
                padding=2 * PADDING,
            ),
        )
        self.scroll_container = toga.ScrollContainer(
            content=self.sync_errors_box,
            horizontal=False,
        )

        self.content = self.scroll_container
        self.center()

        self.refresh_gui()

    async def periodic_refresh_gui(self, sender: Any = None) -> None:

        while self._refresh:
            self.refresh_gui()
            await asyncio.sleep(self._refresh_interval)

    def refresh_gui(self) -> None:

        new_errors = self.mdbx.sync_errors

        if new_errors != self._cached_errors:

            # remove old errors
            for child in self.sync_errors_box.children.copy():
                self.sync_errors_box.remove(child)

            # add new errors
            if len(new_errors) == 0:
                placeholder_label = Label(
                    "No sync issues 😊",
                    style=Pack(padding_bottom=PADDING),
                )
                self.sync_errors_box.add(placeholder_label)
            else:
                for e in new_errors:
                    self.sync_errors_box.add(SyncIssueView(e))

            self._cached_errors = new_errors

    def on_close_pressed(self, sender: Any = None) -> bool:
        self._refresh = False
        return True

    def show(self) -> None:
        self._refresh = True
        self.app.add_background_task(self.periodic_refresh_gui)
        super().show()
