# -*- coding: utf-8 -*-

from __future__ import annotations

# system imports
import os.path as osp
import asyncio
from datetime import datetime
from typing import Iterable, Any

# external imports
import click
import toga
from toga.sources import Source
from toga.style.pack import Pack
from maestral.models import SyncEvent, ItemType
from maestral.daemon import MaestralProxy
from maestral.utils import sanitize_string

# local imports
from .private.widgets import FreestandingIconButton, Icon, Window
from .private.constants import ImageTemplate


PADDING = 10
ICON_SIZE = 32
WINDOW_SIZE = (700, 600)


class SyncEventRow:
    _reveal_button: FreestandingIconButton | None

    def __init__(self, sync_event: SyncEvent) -> None:
        self.sync_event = sync_event

        dirname, basename = osp.split(self.sync_event.local_path)
        dt = datetime.fromtimestamp(self.sync_event.change_time_or_sync_time)

        # attributes for table column values
        self.location = osp.basename(dirname)
        self.type = self.sync_event.change_type.value.capitalize()
        self.time = dt.strftime("%d %b %Y %H:%M")
        self.username = self.sync_event.change_user_name

        self._basename = basename
        self._icon: Icon | None = None
        self._reveal_button = None

    @property
    def filename(self) -> tuple[Icon, str]:
        if not self._icon:
            if self.sync_event.item_type is ItemType.Folder:
                self._icon = Icon(for_path="/usr")
            else:
                self._icon = Icon(for_path=self.sync_event.local_path)

        return self._icon, sanitize_string(self._basename)

    @property
    def reveal(self) -> FreestandingIconButton:
        if not self._reveal_button:
            self._reveal_button = FreestandingIconButton(
                text="",
                icon=Icon(template=ImageTemplate.Reveal),
                on_press=self.on_reveal_pressed,
            )
            self._reveal_button.enabled = osp.exists(self.sync_event.local_path)

        return self._reveal_button

    def on_reveal_pressed(self, widget: Any) -> None:
        click.launch(self.sync_event.local_path, locate=True)

    def refresh(self) -> None:
        self.reveal.enabled = osp.exists(self.sync_event.local_path)


class SyncEventSource(Source):
    def __init__(self, sync_events: Iterable[SyncEvent] = tuple()) -> None:
        super().__init__()
        self._rows = [SyncEventRow(e) for e in sync_events]

    def __len__(self) -> int:
        return len(self._rows)

    def __getitem__(self, index: int) -> SyncEventRow:
        return self._rows[index]

    def add(self, sync_event: SyncEvent) -> None:
        row = SyncEventRow(sync_event)
        self._rows.append(row)
        self._notify("insert", index=len(self._rows) - 1, item=row)

    def insert(self, index: int, sync_event: SyncEvent) -> None:
        row = SyncEventRow(sync_event)
        self._rows.insert(index, row)
        self._notify("insert", index=index, item=row)

    def remove(self, index: int) -> None:
        row = self._rows[index]
        self._notify("pre_remove", item=row)
        del self._rows[index]
        self._notify("remove", item=row)

    def clear(self) -> None:
        self._rows.clear()
        self._notify("clear")


class ActivityWindow(Window):
    def __init__(self, mdbx: MaestralProxy, app: toga.App) -> None:
        super().__init__(title="Maestral Activity", release_on_close=False, app=app)
        self.size = WINDOW_SIZE

        self._refresh = False
        self._refresh_interval = 1
        self._ids: set[str] = set()

        self.on_close = self.on_close_pressed

        self.mdbx = mdbx

        self.table = toga.Table(
            headings=["File", "Location", "Change", "Time", " "],
            accessors=["filename", "location", "type", "time", "reveal"],
            missing_value="--",
            on_double_click=self.on_row_clicked,
            style=Pack(flex=1),
        )
        self.table._impl.columns[-1].maxWidth = 25  # TODO: don't use private API
        self.content = self.table

        self.center()
        self._initial_load = False

    def on_row_clicked(self, sender: Any, row: SyncEventRow) -> None:
        res = click.launch(row.sync_event.local_path)

        if res != 0:
            self.app.alert(
                title="Could not open item",
                message="The file or folder no longer exists.",
            )

    async def periodic_refresh_gui(self, sender: Any = None) -> None:
        while self._refresh:
            await self.refresh_gui()
            await asyncio.sleep(self._refresh_interval)

    async def refresh_gui(self) -> None:
        needs_refresh = False

        for event in self.mdbx.get_history():
            if event.id not in self._ids:
                self.table.data.insert(0, event)
                self._ids.add(event.id)
                await asyncio.sleep(0.002)
                needs_refresh = True

        if needs_refresh:
            for row in self.table.data:
                row.refresh()

    def on_close_pressed(self, sender: Any = None) -> bool:
        self._refresh = False
        return True

    def show(self) -> None:
        if not self._initial_load:
            sync_events = self.mdbx.get_history()
            data_source = SyncEventSource(reversed(sync_events))
            self._ids = set(event.id for event in sync_events)
            self.table.data = data_source
            self._initial_load = True

        self._refresh = True
        self.app.add_background_task(self.periodic_refresh_gui)
        super().show()
