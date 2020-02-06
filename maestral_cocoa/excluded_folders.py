import logging

from .private.constants import ON, OFF, MIXED
from .excluded_folders_gui import ExcludedFoldersGui


logger = logging.getLogger(__name__)


class ExcludedFoldersDialog(ExcludedFoldersGui):

    def __init__(self, mdbx, app=None):
        super().__init__(mdbx, app=app)

    # ==== callbacks to implement ========================================================

    def update_folders(self):
        """
        Apply changes to local Dropbox folder.
        """

        assert self.fs_source.is_selection_modified()

        self.excluded_folders = self.mdbx.excluded_folders

        if not self.mdbx.connected:
            self.fs_source.on_fs_loading_failed()
            return

        self.get_changed_folders(self.fs_source)

        logger.debug(f'new excluded folders: {self.excluded_folders}')
        self.mdbx.set_excluded_folders(self.excluded_folders)

    def get_changed_folders(self, parent):

        for child in parent._children:
            if child.is_selection_modified():
                child_path_lower = child.path.lower()
                if child.included.state == OFF:
                    logger.debug(f'excluding: {child.path}')
                    self.excluded_folders.append(child_path_lower)
                elif child.included.state in (MIXED, ON):
                    logger.debug(f'including: {child.path}')
                    while child_path_lower in self.excluded_folders:
                        self.excluded_folders.remove(child_path_lower)

            self.get_changed_folders(child)
