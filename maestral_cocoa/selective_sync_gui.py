# -*- coding: utf-8 -*-

# system imports
import os.path as osp

# external imports
import toga
from toga.style import Pack
from toga.constants import RIGHT, COLUMN
from toga.sources import Source
from maestral.utils.path import is_child
from maestral.errors import NotAFolderError, NotFoundError

# local imports
from .utils import async_call, run_maestral_async
from .private.widgets import Window, IconForPath, DialogButtons, Switch
from .private.constants import ON, OFF, MIXED


class Node:

    def __init__(self, path, parent, mdbx, is_folder):
        super().__init__()
        self.mdbx = mdbx
        self.path = path
        self.is_folder = is_folder
        if is_folder:
            self._icon = IconForPath('/usr')
        else:
            # use a non-existing file to get generic icon
            self._icon = IconForPath('/test.file')
        self.parent = parent
        self._children = []
        self._did_start_loading = False

        self.included = Switch(
            label='',
            on_toggle=self._on_selected_pressed,
        )
        self._init_selected()

    # Methods required for the data source interface
    def __len__(self):
        return len(self.children)

    def __getitem__(self, index):
        return self.children[index]

    def can_have_children(self):
        if self.is_folder:
            # this will trigger loading of children, if not yet done
            return len(self.children) > 0
        else:
            return False

    def is_selection_modified(self):
        own_selection_modified = self.included.state != self._original_state
        child_selection_modified = any(c.is_selection_modified() for c in self._children)
        return own_selection_modified or child_selection_modified

    # Property that returns the first column (icon, label)
    @property
    def name(self):
        return self._icon, osp.basename(self.path)

    # Dynamic loading
    @property
    def children(self):
        if self.is_folder and not self._did_start_loading:
            self._did_start_loading = True
            self._load_children_async()
        return self._children

    def _init_selected(self):

        excluded_items = getattr(self.mdbx, 'excluded_items', [])

        # get included state from current list
        if self.path.lower() in excluded_items:
            self._original_state = OFF   # item is excluded
        elif any(is_child(self.path.lower(), f) for f in excluded_items):
            self._original_state = OFF  # item's parent is excluded
        elif any(is_child(f, self.path.lower()) for f in excluded_items):
            self._original_state = MIXED  # some of item's children are excluded
        else:
            self._original_state = ON  # item is fully included

        # get included state from parent if it has been user modified
        if self.parent and self.parent.is_selection_modified() and self.parent.included.state is not MIXED:
            self.included.state = self.parent.included.state
        else:
            self.included.state = self._original_state

    def _on_selected_pressed(self, widget):
        self._propagate_selection_to_children(self.included.state)
        self._propagate_selection_to_parent(self.included.state)

    def _propagate_selection_to_children(self, state):
        if state is not MIXED and len(self._children) > 0:
            for child in self._children:
                child.included.state = state
                child._propagate_selection_to_children(state)

    def _propagate_selection_to_parent(self, state):
        # propagate to parent if checked or unchecked
        if self.parent:
            # get minimum of all other children's check state
            checkstate_other_children = min(c.included.state for c in self.parent.children)
            # set parent's state to that minimum, if it is >= 1
            # (there always could be included files)
            new_parent_state = max([checkstate_other_children, MIXED])
            self.parent.included.state = new_parent_state
            # tell the parent to propagate its own state upwards
            self.parent._propagate_selection_to_parent(state)

    @async_call
    async def _load_children_async(self):

        try:
            entries = await run_maestral_async(self.mdbx.config_name,
                                               'list_folder', self.path)
        except (NotAFolderError, NotFoundError):
            entries = []
        except ConnectionError:
            entries = False

        # remove all placeholders
        for c in self._children:
            if isinstance(c, PlaceholderNode):
                self.notify('remove', item=c)

        # populate with new entries
        if entries is False:
            self.loading_failed()
        else:
            entries.sort(key=lambda e: e['name'].lower())
            self._children = [
                Node(
                    path=e['path_display'],
                    parent=self,
                    mdbx=self.mdbx,
                    is_folder=e['type'] == 'FolderMetadata',
                ) for e in entries
            ]

            for i, child in enumerate(self._children):
                self.notify('insert', parent=self, index=i, item=child)

    def notify(self, notification, **kwargs):
        # pass notifications to parent
        self.parent.notify(notification, **kwargs)

    def loading_failed(self):
        self.parent.loading_failed()

    def __repr__(self):
        return f'<{self.__class__.__name__}({self.path})>'


class PlaceholderNode:

    def __init__(self, message, parent):
        self.parent = parent
        self.name = message
        self.included = ''

    @property
    def children(self):
        return []

    def can_have_children(self):
        return False

    def is_selection_modified(self):
        return False

    def sort(self, *args, **kwargs):
        pass

    def _propagate_selection_to_parent(self, state):
        pass


class FileSystemSource(Node, Source):

    def __init__(self, gui_parent, mdbx=None, path='/'):
        super().__init__(path, parent=self, mdbx=mdbx, is_folder=True)
        self.path = path
        self.parent = None
        self._children = [PlaceholderNode('Loading...', self)]
        self.gui_parent = gui_parent
        self.included.label = 'Select all'

    def _propagate_selection_to_parent(self, state):
        if hasattr(self.gui_parent, 'on_fs_selection_changed'):
            self.gui_parent.on_fs_selection_changed()

    def notify(self, notification, **kwargs):
        self._notify(notification, **kwargs)

    def loading_failed(self):
        self._children = [PlaceholderNode('Could not connect to Dropbox 😕', self)]
        self.included.enabled = False
        self.notify('change_source', source=self)

        if hasattr(self.gui_parent, 'on_fs_loading_failed'):
            self.gui_parent.on_fs_loading_failed()


class SelectiveSyncGui(Window):

    def __init__(self, mdbx, **kwargs):
        super().__init__(title='Folder Selection', **kwargs)
        self.mdbx = mdbx

        self.fs_source = FileSystemSource(gui_parent=self, mdbx=self.mdbx)
        self.fs_source.included.style = Pack(padding=(20, 20, 0, 24), flex=1)

        self.tree = toga.Tree(
            headings=['  Name', '  Included'],
            accessors=['name', 'included'],
            data=self.fs_source,
            style=Pack(flex=1),
            multiple_select=True,
        )

        self.tree._impl.columns[0].setMinWidth(200)

        self.dialog_button = DialogButtons(
            labels=['Update', 'Cancel'],
            style=Pack(padding=(0, 20, 20, 20)),
            on_press=self.on_dialog_pressed,
        )
        self.dialog_button['Update'].enabled = False

        # Outermost box
        outer_box = toga.Box(
            children=[
                toga.Label('Please select which files and folders to sync.', style=Pack(padding=20)),
                self.tree,
                self.fs_source.included,
                self.dialog_button,
            ],
            style=Pack(direction=COLUMN, flex=1, alignment=RIGHT)
        )

        # Add the content on the main window
        self.content = outer_box

    def on_dialog_pressed(self, btn_name):
        if btn_name == 'Update':
            self.update_items()

        self.close()

    def on_fs_loading_failed(self):
        self.dialog_button['Update'].enabled = False

    def on_fs_selection_changed(self):
        self.dialog_button['Update'].enabled = self.fs_source.is_selection_modified()

    # ==== callbacks to implement ========================================================

    def update_items(self):
        pass
