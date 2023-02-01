# -*- coding: utf-8 -*-

from __future__ import annotations

# system imports
import os.path as osp
import threading
import asyncio
from queue import Queue
from typing import Any, Callable

# external imports
import toga
from toga.sources import Source
from toga.style import Pack
from toga.constants import TRANSPARENT
from maestral.utils.path import is_child, is_equal_or_child
from maestral.exceptions import (
    NotAFolderError,
    NotFoundError,
    BusyError,
    NotLinkedError,
)
from maestral.core import FolderMetadata
from maestral.daemon import MaestralProxy

# local imports
from .selective_sync_gui import SelectiveSyncGui
from .utils import create_task, generate_async_maestral
from .private.constants import ON, OFF, MIXED
from .private.widgets import Icon, Switch


class Node:
    _children: list[Node | PlaceholderNode]

    def __init__(
        self,
        path_display: str,
        path_lower: str,
        parent: Node | None,
        mdbx: MaestralProxy,
        is_folder: bool,
    ) -> None:
        super().__init__()
        self._mdbx = mdbx
        self.path_display = path_display
        self.path_lower = path_lower
        self._is_folder = is_folder
        if is_folder:
            self._icon = Icon(for_path="/usr")
            self._children = [PlaceholderNode("Loading...", self)]
        else:
            # use icon for file extension
            self._icon = Icon(for_path=path_display)
            self._children = []
        self._parent = parent
        self._did_start_loading = False
        self._stop_loading = threading.Event()

        self._included = Switch(
            text="",
            on_change=self.on_selected_toggled,
            style=Pack(background_color=TRANSPARENT),
        )

        self._init_selected()

    # ---- Methods to track user selection ---------------------------------------------

    def _init_selected(self) -> None:
        excluded_items = getattr(self._mdbx, "excluded_items", [])

        # Get included state from current list.
        if self.path_lower in excluded_items:
            # Item is excluded.
            self._original_state = OFF
        elif self._parent is not None and self._parent._original_state == OFF:
            # Item's parent is excluded.
            self._original_state = OFF
        elif any(is_child(e, self.path_lower) for e in excluded_items):
            # Some of item's children are excluded.
            self._original_state = MIXED
        else:
            self._original_state = ON

        # Get included state from parent if it has been user modified.
        if (
            self.parent is not None
            and self.parent.is_selection_modified()
            and self.parent.included.state is not MIXED
        ):
            self.included.state = self.parent.included.state
        else:
            self.included.state = self._original_state

    def is_selection_modified(self) -> bool:
        own_selection_modified = self.included.state != self._original_state
        child_selection_modified = any(
            c.is_selection_modified() for c in self._children
        )
        return own_selection_modified or child_selection_modified

    def get_nodes_with_state(self, state: int) -> list[Node]:
        result = []
        queue: Queue[Node] = Queue()
        queue.put(self)

        while not queue.empty():
            node = queue.get()

            for child in node._children:
                if isinstance(child, Node):
                    if child.included.state == state:
                        result.append(child)

                    if child.included.state == MIXED:
                        # Children may have different state, traverse individually.
                        queue.put(child)

        return result

    # ---- Methods required for the data source interface ------------------------------

    def __len__(self) -> int:
        return len(self.children)

    def __getitem__(self, index: int) -> Node | PlaceholderNode:
        return self.children[index]

    def can_have_children(self) -> bool:
        return self._is_folder

    # ---- Properties for data access from GUI -----------------------------------------

    @property
    def name(self) -> tuple[Icon, str]:
        return self._icon, osp.basename(self.path_display)

    @property
    def included(self) -> Switch:
        return self._included

    @property
    def is_folder(self) -> bool:
        return self._is_folder

    # ---- Methods for dynamic loading of children -------------------------------------

    @property
    def parent(self) -> Node | None:
        return self._parent

    @property
    def children(self) -> list[Node | PlaceholderNode]:
        if self._is_folder and not self._did_start_loading:
            self._did_start_loading = True
            create_task(self._load_children_async())
        return self._children

    async def _load_children_async(self) -> None:
        try:
            did_clear_children = False

            async for res in generate_async_maestral(
                self._mdbx.config_name, "list_folder_iterator", self.path_lower
            ):
                # remove placeholder nodes
                if not did_clear_children:
                    self._children = []
                    self.notify("change_source", source=self)
                    did_clear_children = True

                res.sort(key=lambda e: e.name.lower())

                new_nodes = [
                    Node(
                        path_display=e.path_display,
                        path_lower=e.path_lower,
                        parent=self,
                        mdbx=self._mdbx,
                        is_folder=isinstance(e, FolderMetadata),
                    )
                    for e in res
                ]

                n_nodes = len(self._children)
                self._children.extend(new_nodes)

                for index, child in enumerate(new_nodes):
                    self.notify(
                        "insert", parent=self, index=index + n_nodes, item=child
                    )

                    # give UI time to process updates
                    if index > 20:
                        await asyncio.sleep(0.1)
                    elif index > 50:
                        await asyncio.sleep(0.2)

                if self._stop_loading.is_set():
                    return

        except (ConnectionError, NotLinkedError):
            self.on_loading_failed()
        except (NotFoundError, NotAFolderError):
            self._children = []
        else:
            self.on_loading_succeeded()

    def on_loading_failed(self) -> None:
        if self.parent:
            self.parent.on_loading_failed()

    def on_loading_succeeded(self) -> None:
        if self.parent:
            self.parent.on_loading_succeeded()

    def stop_loading(self) -> None:
        self._stop_loading.set()
        for child in self._children:
            child._stop_loading.set()

    def clear_stop_loading(self) -> None:
        self._stop_loading.clear()
        for child in self._children:
            child._stop_loading.clear()

    # ---- GUI callbacks ---------------------------------------------------------------

    def on_selected_toggled(self, widget: Any) -> None:
        self.propagate_selection_to_children(self.included.state)
        self.propagate_selection_to_parent(self.included.state)

    def propagate_selection_to_children(self, state: int) -> None:
        if state is not MIXED and len(self._children) > 0:
            for child in self._children:
                if isinstance(child, Node):
                    child.included.state = state
                    child.propagate_selection_to_children(state)

    def propagate_selection_to_parent(self, state: int) -> None:
        if self.parent:
            # get minimum of all other children's check state
            checkstate_other_children = min(
                c.included.state for c in self.parent.children if isinstance(c, Node)
            )
            # set parent's state to that minimum, if it is >= 1
            # (there always could be included files)
            new_parent_state = max([checkstate_other_children, MIXED])
            self.parent.included.state = new_parent_state
            # tell the parent to propagate its own state upwards
            self.parent.propagate_selection_to_parent(state)

    def notify(self, notification: str, **kwargs) -> None:
        # pass notifications to parent
        if self.parent:
            self.parent.notify(notification, **kwargs)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}({self.path_display})>"


class PlaceholderNode:
    def __init__(self, message: str, parent: Node) -> None:
        self._parent = parent
        self._name = message
        self._included = ""
        self._stop_loading = threading.Event()

    # ---- Methods to track user selection ---------------------------------------------

    @staticmethod
    def is_selection_modified() -> bool:
        return False

    # ---- Methods required for the data source interface ------------------------------

    def __len__(self) -> int:
        return 0

    def __getitem__(self, index: int) -> Node:
        raise StopIteration()

    @staticmethod
    def can_have_children() -> bool:
        return False

    # ---- Properties for data access from GUI -----------------------------------------

    @property
    def name(self) -> str:
        return self._name

    @property
    def included(self) -> str:
        return self._included

    # ---- Methods for dynamic loading of children -------------------------------------

    @property
    def parent(self) -> Node:
        return self._parent

    @property
    def children(self) -> list[Node]:
        return []

    # ---- GUI callbacks ---------------------------------------------------------------

    def propagate_selection_to_children(self, state: int) -> None:
        pass

    def propagate_selection_to_parent(self, state: int) -> None:
        pass


class FileSystemSource(Node, Source):
    def __init__(
        self,
        mdbx: MaestralProxy,
        path_display: str = "/",
        path_lower: str = "/",
        on_fs_loading_succeeded: Callable | None = None,
        on_fs_loading_failed: Callable | None = None,
        on_fs_selection_changed: Callable | None = None,
    ):
        super().__init__(
            path_display, path_lower, parent=None, is_folder=True, mdbx=mdbx
        )
        self.on_fs_loading_succeeded = on_fs_loading_succeeded
        self.on_fs_loading_failed = on_fs_loading_failed
        self.on_fs_selection_changed = on_fs_selection_changed

        self._children = [PlaceholderNode("Loading...", self)]
        self.included.text = "Select all"
        self.included.enabled = False

    def reload(self):
        self._children = [PlaceholderNode("Loading...", self)]
        self.notify("change_source", source=self)
        create_task(self._load_children_async())

    def propagate_selection_to_parent(self, state: int) -> None:
        if self.on_fs_selection_changed:
            self.on_fs_selection_changed()

    def notify(self, notification: str, **kwargs) -> None:
        self._notify(notification, **kwargs)

    def on_loading_failed(self) -> None:
        self.included.enabled = False
        self._children = [PlaceholderNode("Could not connect to Dropbox 😕", self)]
        self.notify("change_source", source=self)

        if self.on_fs_loading_failed:
            self.on_fs_loading_failed()

    def on_loading_succeeded(self) -> None:
        self.included.enabled = True

        if self.on_fs_loading_succeeded:
            self.on_fs_loading_succeeded()

    def index(self, node: Node) -> int:
        if node.parent:
            return node.parent.children.index(node)
        else:
            return self.children.index(node)


class SelectiveSyncDialog(SelectiveSyncGui):
    def __init__(self, mdbx: MaestralProxy, app: toga.App):
        super().__init__(app=app, is_dialog=True)

        self.mdbx = mdbx

        self.dialog_buttons["Update"].enabled = False

        self.dialog_buttons.on_press = self.on_dialog_pressed
        self.on_close = self.on_close_pressed

        self.fs_source = FileSystemSource(
            mdbx=self.mdbx,
            on_fs_loading_failed=self.on_fs_loading_failed,
            on_fs_selection_changed=self.on_fs_selection_changed,
        )

        self.tree.data = self.fs_source

        self.fs_source.included.style = Pack(padding=(20, 20, 0, 24), flex=1)
        self.outer_box.insert(-1, self.fs_source.included)

    # ==== callbacks ===================================================================

    def update_items(self) -> None:
        """
        Apply changes to local Dropbox folder.
        """

        if not self.mdbx.connected:
            self.on_fs_loading_failed()
            return

        excluded_paths = set(self.mdbx.excluded_items)

        # update the state of nodes which are listed in the tree
        # preserve any exclusions which are not shown in the tree

        included_shown = self.fs_source.get_nodes_with_state(ON)
        excluded_shown = self.fs_source.get_nodes_with_state(OFF)
        mixed_shown = self.fs_source.get_nodes_with_state(MIXED)

        for node in included_shown:
            for path in excluded_paths.copy():
                if is_equal_or_child(path, node.path_lower):
                    excluded_paths.discard(path)

        for node in mixed_shown:
            excluded_paths.discard(node.path_lower)

        for node in excluded_shown:
            excluded_paths.add(node.path_lower)

        self.mdbx.excluded_items = list(excluded_paths)

    async def on_dialog_pressed(self, btn_name: str) -> None:
        if btn_name == "Update":
            try:
                self.update_items()
            except BusyError as err:
                await self.error_dialog(err.title, err.message)
            else:
                self.close()

        elif btn_name == "Cancel":
            self.close()

    def on_fs_loading_failed(self) -> None:
        self.dialog_buttons["Update"].enabled = False

    def on_fs_selection_changed(self) -> None:
        self.dialog_buttons["Update"].enabled = self.fs_source.is_selection_modified()

    def on_close_pressed(self, sender: Any = None) -> bool:
        self.fs_source.stop_loading()
        return True
