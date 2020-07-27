# -*- coding: utf-8 -*-

# external imports
import toga
from toga.style import Pack
from toga.constants import RIGHT, COLUMN

# local imports
from .private.widgets import Window, DialogButtons


class SelectiveSyncGui(Window):

    def __init__(self, mdbx, **kwargs):
        super().__init__(title='Folder Selection', **kwargs)
        self.mdbx = mdbx

        self.tree = toga.Tree(
            headings=['Name', 'Included'],
            accessors=['name', 'included'],
            style=Pack(flex=1),
            multiple_select=True,
        )

        self.tree._impl.columns[0].setMinWidth(200)

        self.dialog_button = DialogButtons(
            labels=['Update', 'Cancel'],
            style=Pack(padding=(0, 20, 20, 20)),
        )
        self.dialog_button['Update'].enabled = False

        # Outermost box
        self.outer_box = toga.Box(
            children=[
                toga.Label(
                    'Please select which files and folders to sync.',
                    style=Pack(padding=20)
                ),
                self.tree,
                self.dialog_button,
            ],
            style=Pack(direction=COLUMN, flex=1, alignment=RIGHT)
        )

        # Add the content on the main window
        self.content = self.outer_box
