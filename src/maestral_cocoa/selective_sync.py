# -*- coding: utf-8 -*-

# system imports
import os.path as osp
import threading
import asyncio

# external imports
from toga.sources import Source
from toga.style import Pack
from toga.constants import TRANSPARENT
from maestral.utils.path import is_child, is_equal_or_child
from maestral.errors import NotAFolderError, NotFoundError, BusyError

# local imports
from .selective_sync_gui import SelectiveSyncGui
from .utils import create_task, generate_async_maestral
from .private.constants import ON, OFF, MIXED
from .private.widgets import Icon, Switch


class Node:
    def __init__(self, path, parent, mdbx, is_folder):
        super().__init__()
        self._mdbx = mdbx
        self.path = path
        self._is_folder = is_folder
        if is_folder:
            self._icon = Icon(for_path="/usr")
        else:
            # use icon for file extension
            self._icon = Icon(for_path=path)
        self._parent = parent
        self._children = []
        self._did_start_loading = False
        self._stop_loading = threading.Event()

        self._included = Switch(
            label="",
            on_toggle=self.on_selected_toggled,
            style=Pack(background_color=TRANSPARENT),
        )

        self._init_selected()

    # ---- Methods to track user selection ---------------------------------------------

    def _init_selected(self):

        excluded_items = getattr(self._mdbx, "excluded_items", [])

        # get included state from current list
        if self.path.lower() in excluded_items:
            self._original_state = OFF  # item is excluded
        elif any(is_child(self.path.lower(), f) for f in excluded_items):
            self._original_state = OFF  # item's parent is excluded
        elif any(is_child(f, self.path.lower()) for f in excluded_items):
            self._original_state = MIXED  # some of item's children are excluded
        else:
            self._original_state = ON  # item is fully included

        # get included state from parent if it has been user modified
        if (
            self.parent
            and self.parent.is_selection_modified()
            and self.parent.included.state is not MIXED
        ):
            self.included.state = self.parent.included.state
        else:
            self.included.state = self._original_state

    def is_selection_modified(self):
        own_selection_modified = self.included.state != self._original_state
        child_selection_modified = any(
            c.is_selection_modified() for c in self._children
        )
        return own_selection_modified or child_selection_modified

    def get_nodes_with_state(self, state):

        nodes_with_state = []

        for child in self._children:
            if isinstance(child, Node):
                if child.included.state == state:
                    nodes_with_state.append(child)
                    if state in (ON, OFF):
                        # all children will have the same state
                        nodes_with_state.extend(child._children)

                if child.included.state == MIXED:
                    # children may have different state
                    nodes_with_state.extend(child.get_nodes_with_state(state))

        return nodes_with_state

    # ---- Methods required for the data source interface ------------------------------

    def __len__(self):
        return len(self.children)

    def __getitem__(self, index):
        return self.children[index]

    def can_have_children(self):
        if self._is_folder:
            # this will trigger loading of children, if not yet done
            return len(self.children) > 0
        else:
            return False

    # ---- Properties for data access from GUI -----------------------------------------

    @property
    def name(self):
        return self._icon, osp.basename(self.path)

    @property
    def included(self):
        return self._included

    @property
    def is_folder(self):
        return self._is_folder

    # ---- Methods for dynamic loading of children -------------------------------------

    @property
    def parent(self):
        return self._parent

    @property
    def children(self):
        if self._is_folder and not self._did_start_loading:
            self._did_start_loading = True
            create_task(self._load_children_async())
        return self._children

    async def _load_children_async(self):

        try:

            did_remove_placeholder = False

            async for res in generate_async_maestral(
                self._mdbx.config_name, "list_folder_iterator", self.path
            ):

                # remove placeholder nodes
                if not did_remove_placeholder:
                    for child in self._children.copy():
                        if isinstance(child, PlaceholderNode):
                            self._children.remove(child)
                            self.notify("remove", parent=self, index=0, item=child)

                    did_remove_placeholder = True

                res.sort(key=lambda e: e["name"].lower())

                new_nodes = [
                    Node(
                        path=e["path_display"],
                        parent=self,
                        mdbx=self._mdbx,
                        is_folder=e["type"] == "FolderMetadata",
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

        except ConnectionError:
            self.on_loading_failed()
        except (NotFoundError, NotAFolderError):
            self._children = []

    def on_loading_failed(self):
        self.parent.on_loading_failed()

    def stop_loading(self):
        self._stop_loading.set()
        for child in self._children:
            child._stop_loading.set()

    def clear_stop_loading(self):
        self._stop_loading.clear()
        for child in self._children:
            child._stop_loading.clear()

    # ---- GUI callbacks ---------------------------------------------------------------

    def on_selected_toggled(self, widget):
        self.propagate_selection_to_children(self.included.state)
        self.propagate_selection_to_parent(self.included.state)

    def propagate_selection_to_children(self, state):
        if state is not MIXED and len(self._children) > 0:
            for child in self._children:
                child.included.state = state
                child.propagate_selection_to_children(state)

    def propagate_selection_to_parent(self, state):
        if self.parent:
            # get minimum of all other children's check state
            checkstate_other_children = min(
                c.included.state for c in self.parent.children
            )
            # set parent's state to that minimum, if it is >= 1
            # (there always could be included files)
            new_parent_state = max([checkstate_other_children, MIXED])
            self.parent.included.state = new_parent_state
            # tell the parent to propagate its own state upwards
            self.parent.propagate_selection_to_parent(state)

    def notify(self, notification, **kwargs):
        # pass notifications to parent
        self.parent.notify(notification, **kwargs)

    def __repr__(self):
        return f"<{self.__class__.__name__}({self.path})>"


class PlaceholderNode:
    def __init__(self, message, parent):
        self._parent = parent
        self._name = message
        self._included = ""
        self._stop_loading = threading.Event()

    # ---- Methods to track user selection ---------------------------------------------

    @staticmethod
    def is_selection_modified():
        return False

    # ---- Methods required for the data source interface ------------------------------

    def __len__(self):
        return 0

    def __getitem__(self, index):
        raise StopIteration()

    @staticmethod
    def can_have_children():
        return False

    # ---- Properties for data access from GUI -----------------------------------------

    @property
    def name(self):
        return self._name

    @property
    def included(self):
        return self._included

    # ---- Methods for dynamic loading of children -------------------------------------

    @property
    def parent(self):
        return self._parent

    @property
    def children(self):
        return []

    # ---- GUI callbacks ---------------------------------------------------------------

    def propagate_selection_to_children(self, state):
        pass

    def propagate_selection_to_parent(self, state):
        pass


class FileSystemSource(Node, Source):
    def __init__(
        self,
        mdbx=None,
        path="/",
        on_fs_loading_failed=None,
        on_fs_selection_changed=None,
    ):
        super().__init__(path, parent=None, mdbx=mdbx, is_folder=True)
        self.on_fs_loading_failed = on_fs_loading_failed
        self.on_fs_selection_changed = on_fs_selection_changed
        self._children = [PlaceholderNode("Loading...", self)]
        self._included.label = "Select all"

    def propagate_selection_to_parent(self, state):
        if self.on_fs_selection_changed:
            self.on_fs_selection_changed()

    def notify(self, notification, **kwargs):
        self._notify(notification, **kwargs)

    def on_loading_failed(self):
        self.included.enabled = False
        self._children = [PlaceholderNode("Could not connect to Dropbox 😕", self)]
        self.notify("change_source", source=self)

        if self.on_fs_loading_failed:
            self.on_fs_loading_failed()

    def index(self, node):
        if node.parent:
            return node.parent.children.index(node)
        else:
            return self.children.index(node)


class SelectiveSyncDialog(SelectiveSyncGui):
    def __init__(self, mdbx, app=None):
        super().__init__(mdbx, app=app)

        self.dialog_buttons.on_press = self.on_dialog_pressed

        self.fs_source = FileSystemSource(
            mdbx=self.mdbx,
            on_fs_loading_failed=self.on_fs_loading_failed,
            on_fs_selection_changed=self.on_fs_selection_changed,
        )

        self.tree.data = self.fs_source

        self.fs_source.included.style = Pack(padding=(20, 20, 0, 24), flex=1)
        self.outer_box.insert(-1, self.fs_source.included)

    # ==== callbacks ===================================================================

    def update_items(self):
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
                if is_equal_or_child(path, node.path.lower()):
                    excluded_paths.remove(path)

        for node in mixed_shown:
            try:
                excluded_paths.remove(node.path.lower())
            except KeyError:
                pass

        for node in excluded_shown:
            excluded_paths.add(node.path.lower())

        self.mdbx.excluded_items = list(excluded_paths)

    async def on_dialog_pressed(self, btn_name):

        if btn_name == "Update":

            try:
                self.update_items()
            except BusyError as err:
                await self.alert_sheet(err.title, err.message, level="error")
            else:
                self.close()

        elif btn_name == "Cancel":
            self.close()

    def on_fs_loading_failed(self):
        self.dialog_buttons["Update"].enabled = False

    def on_fs_selection_changed(self):
        self.dialog_buttons["Update"].enabled = self.fs_source.is_selection_modified()

    def on_close(self):
        super().on_close()
        self.fs_source.stop_loading()
