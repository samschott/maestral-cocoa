# -*- coding: utf-8 -*-

# system imports
import os.path as osp
import asyncio
from datetime import datetime

# external imports
import click
import toga
from toga.sources import Source
from toga.style.pack import Pack

# local imports
from .utils import create_task
from .private.widgets import FreestandingIconButton, Icon, Window
from .private.constants import ImageTemplate

PADDING = 10
ICON_SIZE = 32
WINDOW_SIZE = (700, 600)


class SyncEventRow:
    def __init__(self, sync_event):
        self.sync_event = sync_event

        dirname, basename = osp.split(self.sync_event["local_path"])
        dt = datetime.fromtimestamp(self.sync_event["change_time_or_sync_time"])

        # attributes for table column values
        self._basename = basename
        self._icon = None
        self.location = osp.basename(dirname)
        self.type = self.sync_event["change_type"].capitalize()
        self.time = dt.strftime("%d %b %Y %H:%M")
        self.username = self.sync_event["change_user_name"]
        self._reveal = None

    @property
    def filename(self):
        if not self._icon:
            if self.sync_event["item_type"] == "folder":
                self._icon = Icon(for_path="/usr")
            else:
                self._icon = Icon(for_path=self.sync_event["local_path"])

        return self._icon, self._basename

    @property
    def reveal(self):
        if not self._reveal:
            self._reveal = FreestandingIconButton(
                label="",
                icon=Icon(template=ImageTemplate.Reveal),
                on_press=self.on_reveal_pressed,
                enabled=osp.exists(self.sync_event["local_path"]),
            )

        return self._reveal

    def on_reveal_pressed(self, widget):
        click.launch(self.sync_event["local_path"], locate=True)

    def refresh(self):
        self.reveal.enabled = osp.exists(self.sync_event["local_path"])


class SyncEventSource(Source):
    def __init__(self, sync_events=tuple()):
        super().__init__()
        self._rows = [SyncEventRow(e) for e in sync_events]

    def __len__(self):
        return len(self._rows)

    def __getitem__(self, index):
        return self._rows[index]

    def add(self, sync_event):
        row = SyncEventRow(sync_event)
        self._rows.append(row)
        self._notify("insert", index=len(self._rows) - 1, item=row)

    def insert(self, index, sync_event):
        row = SyncEventRow(sync_event)
        self._rows.insert(index, row)
        self._notify("insert", index=index, item=row)

    def remove(self, index):
        row = self._rows[index]
        self._notify("pre_remove", item=row)
        del self._rows[index]
        self._notify("remove", item=row)

    def clear(self):
        self._rows.clear()
        self._notify("clear")


class ActivityWindow(Window):
    def __init__(self, mdbx, app=None):
        super().__init__(title="Maestral Activity", release_on_close=False, app=app)
        self.size = WINDOW_SIZE

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
        self._periodic_refresh_task = None
        self._initial_load = False

    def on_row_clicked(self, sender, row):
        res = click.launch(row.sync_event["local_path"])

        if res != 0:
            self.app.alert(
                title="Count not open item",
                message="The file or folder no longer exists.",
            )

    async def periodic_refresh_gui(self, interval=1):

        while True:
            await self.refresh_gui()
            await asyncio.sleep(interval)

    async def refresh_gui(self):

        needs_refresh = False

        for event in self.mdbx.get_history():
            if event["id"] not in self._ids:
                self.table.data.insert(0, event)
                self._ids.add(event["id"])
                await asyncio.sleep(0.002)
                needs_refresh = True

        if needs_refresh:
            for row in self.table.data:
                row.refresh()

    def on_close(self):
        if self._periodic_refresh_task:
            self._periodic_refresh_task.cancel()

    def show(self):
        if not self._initial_load:
            sync_events = self.mdbx.get_history()
            data_source = SyncEventSource(reversed(sync_events))
            self._ids = set(event["id"] for event in sync_events)
            self.table.data = data_source
            self._initial_load = True

        self._periodic_refresh_task = create_task(self.periodic_refresh_gui())
        super().show()
