# -*- coding: utf-8 -*-

# local imports
from .private.constants import ON, OFF, MIXED
from .selective_sync_gui import SelectiveSyncGui


class SelectiveSyncDialog(SelectiveSyncGui):

    def __init__(self, mdbx, app=None):
        super().__init__(mdbx, app=app)

    # ==== callbacks to implement ========================================================

    def update_items(self):
        """
        Apply changes to local Dropbox folder.
        """

        assert self.fs_source.is_selection_modified()

        self.excluded_items = self.mdbx.excluded_items

        if not self.mdbx.connected:
            self.fs_source.on_fs_loading_failed()
            return

        self.get_changed_items(self.fs_source)

        self.mdbx.set_excluded_items(self.excluded_items)

    def get_changed_items(self, parent):

        for child in parent._children:
            if child.is_selection_modified():
                child_path_lower = child.path.lower()
                if child.included.state == OFF:
                    self.excluded_items.append(child_path_lower)
                elif child.included.state in (MIXED, ON):
                    while child_path_lower in self.excluded_items:
                        self.excluded_items.remove(child_path_lower)

            self.get_changed_items(child)
