# -*- coding: utf-8 -*-

from __future__ import annotations

# system imports
import os.path as osp
import asyncio
import urllib.parse
from typing import Any

# external imports
import toga
from toga.style.pack import Pack
from toga.constants import ROW, COLUMN
from maestral.daemon import MaestralProxy
from maestral.models import SyncErrorEntry
from maestral.utils import sanitize_string

# local imports
from .private.widgets import Label, FollowLinkButton, Icon, Window
from .private.constants import WORD_WRAP


PADDING = 10
ICON_SIZE = 48
WINDOW_SIZE = (370, 400)


class SyncIssueView(toga.Box):
    def __init__(self, sync_err: SyncErrorEntry) -> None:
        super().__init__(style=Pack(direction=COLUMN))

        self.sync_err = sync_err

        icon = Icon(for_path=self.sync_err.local_path)

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
            sanitize_string(osp.basename(self.sync_err.dbx_path)),
            style=Pack(
                padding_bottom=PADDING / 2,
            ),
        )
        error_label = Label(
            f"{self.sync_err.title}:\n{self.sync_err.message}",
            linebreak_mode=WORD_WRAP,
            style=Pack(
                font_size=11,
                width=WINDOW_SIZE[0] - 4 * PADDING - 15 - ICON_SIZE,
                padding_bottom=PADDING / 2,
            ),
        )

        link_local = FollowLinkButton(
            "Show in Finder",
            url=self.sync_err.local_path,
            locate=True,
            style=Pack(
                padding_right=PADDING,
                font_size=11,
                height=12,
            ),
        )
        link_local.enabled = osp.exists(self.sync_err.local_path)

        quoted_dbx_path = urllib.parse.quote(self.sync_err.dbx_path)
        dbx_address = f"https://www.dropbox.com/preview{quoted_dbx_path}"

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

        self._refresh = False
        self._refresh_interval = 1
        self._sync_issue_widgets: dict[str, SyncIssueView] = dict()

        self._placeholder = Label(
            "No sync issues 😊", style=Pack(padding_bottom=PADDING)
        )

        self.size = WINDOW_SIZE

        self.sync_errors_box = toga.Box(
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

    def _has_placeholder(self) -> bool:
        return self._placeholder in self.sync_errors_box.children

    def refresh_gui(self) -> None:
        new_errors = self.mdbx.sync_errors

        # remove placeholder if the error count > 0

        if len(new_errors) > 0 and self._has_placeholder():
            self.sync_errors_box.remove(self._placeholder)

        # add new errors

        new_err_paths: set[str] = set()

        for error in new_errors:
            new_err_paths.add(error.dbx_path)
            if error.dbx_path not in self._sync_issue_widgets:
                widget = SyncIssueView(error)
                self.sync_errors_box.add(widget)
                self._sync_issue_widgets[error.dbx_path] = widget

        # remove old errors

        for dbx_path in self._sync_issue_widgets.copy():
            if dbx_path not in new_err_paths:
                widget = self._sync_issue_widgets.pop(dbx_path)
                self.sync_errors_box.remove(widget)

        # add placeholder if we don't have any errors
        if len(new_errors) == 0 and not self._has_placeholder():
            self.sync_errors_box.add(self._placeholder)

    def on_close_pressed(self, sender: Any = None) -> bool:
        self._refresh = False
        return True

    def show(self) -> None:
        self._refresh = True
        self.app.add_background_task(self.periodic_refresh_gui)
        super().show()
