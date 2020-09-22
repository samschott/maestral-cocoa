# -*- coding: utf-8 -*-
import asyncio

# external imports
import click
import toga
from toga.handlers import wrapped_handler
from toga.widgets.base import Widget
from toga.style.pack import Pack
from toga.constants import ROW, RIGHT, TRANSPARENT
from toga.sources import ListSource, TreeSource
from toga.sources.accessors import to_accessor

# local imports
from .platform import get_platform_factory
from .constants import ON, MIXED, TRUNCATE_TAIL, VisualEffectMaterial, ImageTemplate
from .renderers import RendererText, RendererIconText


private_factory = get_platform_factory()


# ==== icons =============================================================================


class Icon(toga.Icon):
    """
    Reimplements toga.Icon to provide the icon for the file / folder type
    instead of loading an icon from the file content.

    :param path: File to path.
    """

    def __init__(self, path=None, for_path=None, template=None, system=False):
        super().__init__(path, system)
        self.for_path = for_path
        self.template = template

    def bind(self, factory):
        if self._impl is None:
            self._impl = private_factory.Icon(
                interface=self,
                path=self.path,
                for_path=self.for_path,
                template=self.template,
            )

        return self._impl


# ==== layout widgets ====================================================================


class Spacer(toga.Box):
    """A widget to take up space and push others to the side."""

    def __init__(self, direction=ROW, factory=None):
        style = Pack(flex=1, direction=direction, background_color=TRANSPARENT)
        super().__init__(style=style, factory=factory)


class VibrantBox(Widget):
    """A macOS style vibrant box, to be used as translucent window background."""

    def __init__(
        self,
        id=None,
        style=None,
        children=None,
        material=VisualEffectMaterial.UnderWindowBackground,
        factory=private_factory,
    ):
        super().__init__(id=id, style=style, factory=factory)
        self._children = []
        if children:
            for child in children:
                self.add(child)

        self._material = material
        self._impl = self.factory.VibrantBox(interface=self)

    @property
    def material(self):
        return self._material

    @material.setter
    def material(self, material):
        self._material = material
        self._impl.set_material(material)


# ==== buttons ===========================================================================


class DialogButtons(toga.Box):
    """
    A dialog button box. Buttons will be created from the given list of labels (defaults
    to ['Ok', 'Cancel']). If a callback ``on_press`` is provided, will be executed if any
    button is pressed, with the label of the respective button as an argument.

    :param labels: An iterable of label strings.
    :param str default: A default button to select. Value must match one of the labels
    :param on_press: Callback when any button is pressed. Takes the button
        label as argument.
    """

    MIN_BUTTON_WIDTH = 80

    def __init__(
        self,
        labels=("Ok", "Cancel"),
        default="Ok",
        on_press=None,
        id=None,
        style=None,
        factory=None,
    ):
        self._buttons = []
        super().__init__(id=id, style=style, factory=factory)

        # always display buttons in a row, to the right
        self.style.update(direction=ROW)
        self.add(Spacer())

        for label in labels[::-1]:
            style = Pack(padding_left=10, alignment=RIGHT, background_color=TRANSPARENT)
            btn = toga.Button(label=label, style=style)

            if label == default:
                # TODO: remove private API access
                btn._impl.native.keyEquivalent = "\r"

            self.add(btn)
            self._buttons.insert(0, btn)

            btn.style.width = max(self.MIN_BUTTON_WIDTH, btn.intrinsic.width.value)

        self.on_press = on_press

    @property
    def on_press(self):
        return self._on_press

    @on_press.setter
    def on_press(self, handler):

        if not handler:
            new_handler = None
        elif asyncio.iscoroutinefunction(handler):

            async def new_handler(widget):
                return await handler(widget.label)

        else:

            def new_handler(widget):
                return handler(widget.label)

        for btn in self._buttons:
            btn.on_press = new_handler

        self._on_press = new_handler

    def __getitem__(self, item):
        return next(btn for btn in self._buttons if btn.label == item)

    def __iter__(self):
        return iter(self._buttons)

    @property
    def enabled(self):
        return any(btn.enabled for btn in self)

    @enabled.setter
    def enabled(self, yes):
        for btn in self._buttons:
            btn.enabled = yes


class Switch(toga.Switch):
    """Reimplements toga.Switch to allow *programmatic* setting of
    an intermediate state."""

    def __init__(
        self,
        label,
        id=None,
        style=None,
        on_toggle=None,
        is_on=False,
        enabled=True,
        factory=private_factory,
    ):
        super().__init__(label, id, style, on_toggle, is_on, enabled, factory)

    @property
    def state(self):
        """Button state: 0 = off, 1 = mixed, 2 = on."""
        return self._impl.get_state()

    @state.setter
    def state(self, value):
        """Setter: Button state: 0 = off, 1 = mixed, 2 = on."""
        self._impl.set_state(value)

    @property
    def on_toggle(self):
        return self._on_toggle

    @on_toggle.setter
    def on_toggle(self, handler):

        if not handler:

            def new_handler(*args, **kwargs):
                if self.state == MIXED:
                    self.state = ON

        elif asyncio.iscoroutinefunction(handler):

            async def new_handler(*args, **kwargs):
                if self.state == MIXED:
                    self.state = ON
                return await handler(*args, **kwargs)

        else:

            def new_handler(*args, **kwargs):
                if self.state == MIXED:
                    self.state = ON
                return handler(*args, **kwargs)

        self._on_toggle = wrapped_handler(self, new_handler)
        self._impl.set_on_toggle(self._on_toggle)


class FreestandingIconButton(toga.Widget):
    """A freestanding button with an icon."""

    def __init__(
        self,
        label,
        icon=None,
        id=None,
        style=None,
        on_press=None,
        enabled=True,
        factory=private_factory,
    ):
        super().__init__(id=id, enabled=enabled, style=style, factory=factory)

        # Create a platform specific implementation of a Button
        self._impl = self.factory.FreestandingIconButton(interface=self)

        # Set all the properties
        self.label = label
        self.on_press = on_press
        self.enabled = enabled
        self.icon = icon

    @property
    def label(self):
        return self._label

    @label.setter
    def label(self, value):
        if value is None:
            self._label = ""
        else:
            self._label = str(value)
        self._impl.set_label(value)
        self._impl.rehint()

    @property
    def icon(self):
        return self._icon

    @icon.setter
    def icon(self, value):
        self._icon = value
        self._impl.set_icon(value)
        self._impl.rehint()

    @property
    def on_press(self):
        return self._on_press

    @on_press.setter
    def on_press(self, handler):
        self._on_press = wrapped_handler(self, handler)
        self._impl.set_on_press(self._on_press)


class FollowLinkButton(FreestandingIconButton):
    def __init__(
        self,
        label,
        url=None,
        locate=False,
        id=None,
        style=None,
        enabled=True,
        factory=private_factory,
    ):
        icon = Icon(template=ImageTemplate.FollowLink)
        self.url = url
        self.locate = locate
        super().__init__(
            label, icon=icon, id=id, enabled=enabled, style=style, factory=factory
        )

        def handler(widget):
            click.launch(widget.url, locate=widget.locate)

        self._on_press = wrapped_handler(self, handler)


class FileSelectionButton(toga.Widget):

    MIN_WIDTH = 100

    def __init__(
        self,
        initial=None,
        select_files=True,
        select_folders=False,
        on_select=None,
        dialog_title="",
        dialog_message="",
        id=None,
        enabled=True,
        style=None,
        factory=private_factory,
    ):
        super().__init__(id, enabled, style, factory)

        # Create a platform specific implementation
        self._impl = self.factory.FileSelectionButton(interface=self)

        # Set all the properties
        self.current_selection = str(initial)
        self.select_files = select_files
        self.select_folders = select_folders
        self.on_select = on_select
        self.dialog_title = dialog_title
        self.dialog_message = dialog_message

    @property
    def select_files(self):
        return self._select_files

    @select_files.setter
    def select_files(self, value):
        self._select_files = value
        self._impl.set_select_files(value)

    @property
    def select_folders(self):
        return self._select_folders

    @select_folders.setter
    def select_folders(self, value):
        self._select_folders = value
        self._impl.set_select_folders(value)

    @property
    def current_selection(self):
        return self._impl.get_current_selection()

    @current_selection.setter
    def current_selection(self, value):
        self._impl.set_current_selection(value)

    @property
    def dialog_title(self):
        return self._dialog_title

    @dialog_title.setter
    def dialog_title(self, value):
        self._dialog_title = value
        self._impl.set_dialog_title(self._dialog_title)

    @property
    def dialog_message(self):
        return self._dialog_message

    @dialog_message.setter
    def dialog_message(self, value):
        self._dialog_message = value
        self._impl.set_dialog_message(self._dialog_message)

    @property
    def on_select(self):
        return self._on_select

    @on_select.setter
    def on_select(self, handler):
        self._on_select = wrapped_handler(self, handler)
        self._impl.set_on_select(self._on_select)


# ==== labels ============================================================================


class Label(toga.Label):
    """Reimplements toga.Label with text wrapping."""

    def __init__(
        self,
        text,
        linebreak_mode=TRUNCATE_TAIL,
        id=None,
        style=None,
        factory=private_factory,
    ):
        self._linebreak_mode = linebreak_mode
        super().__init__(text, id=id, style=style, factory=factory)
        self.linebreak_mode = linebreak_mode

    @property
    def linebreak_mode(self):
        return self._linebreak_mode

    @linebreak_mode.setter
    def linebreak_mode(self, value):
        self._linebreak_mode = value
        self._impl.set_linebreak_mode(value)


class RichMultilineTextInput(toga.MultilineTextInput):
    """A multiline text view with html support."""

    MIN_HEIGHT = 100
    MIN_WIDTH = 100

    def __init__(
        self,
        id=None,
        style=None,
        factory=private_factory,
        html="",
        readonly=False,
        placeholder=None,
    ):
        super().__init__(
            id=id,
            style=style,
            readonly=readonly,
            placeholder=placeholder,
            factory=factory,
        )

        # Create a platform specific implementation of a Label
        self._impl = self.factory.RichMultilineTextInput(interface=self)
        self.html = html
        self.readonly = readonly

    @property
    def html(self):
        return self._html

    @html.setter
    def html(self, value):
        self._html = value
        self._impl.set_html(value)


class RichLabel(Widget):
    """A label with html support."""

    def __init__(self, html, id=None, style=None, factory=private_factory):
        super().__init__(id=id, style=style, factory=factory)

        self._html = html

        # Create a platform specific implementation of a Label
        self._impl = self.factory.RichLabel(interface=self)
        self.html = html

    @property
    def html(self):
        return self._html

    @html.setter
    def html(self, value):
        self._html = value
        self._impl.set_html(value)


# ==== tree and table ====================================================================


class Column:
    def __init__(self, title, renderer, min_width=16, max_width=500):
        self.title = title
        self.renderer = renderer
        self.min_width = min_width
        self.max_width = max_width


class Table(Widget):
    """A Table Widget allows the display of data in the form of columns and rows.

    :param columns: Can be a list of titles to generate columns, a list of tuples
        ``(title, accessor)`` where the accessor defines which column of the data source
        to access, or a list of :class:`Column` instances.
    :param id: An identifier for this widget.
    :param data: The data to display in the widget. Must be an instance of
        :class:`toga.sources.ListSource` or a class instance which implements the
        interface of :class:`toga.sources.ListSource`.
    :param style: An optional style object. If no style is provided` then a new one will
        be created for the widget.
    :param on_select: A function to be invoked on selecting a row of the table.
    :param on_double_click: A function to be invoked on double clicking a row of the table.
    :param factory: A python module that is capable to return a implementation of this
        class with the same name. (optional & normally not needed)

    Examples:

        Lets prepare a data source first.

        >>> data = [{'head_1': 'value 1', 'head_2': 'value 2', 'head_3': 'value3'}),
        >>>         {'head_1': 'value 1', 'head_2': 'value 2', 'head_3': 'value3'}]
        >>> table_source = ListSource(data)

        Columns can be provided in several forms.
        As a list of column titles which will be matched against accessors in the data:

        >>> columns = ['Head 1', 'Head 2', 'Head 3']

        A list of tuples with column titles and accessors:

        >>> columns = [('Head 1', 'head_1'), ('Head 2', 'head_2'), ('Head 3', 'head_3')]

        As ``Column`` instances with a renderer. The renderer determines how a column is
        displayed and how the data is mapped to column properties such as text and icon:

        >>> columns = [
        >>>     Column(title='Head 1', renderer=RendererIconText(text='head_1', icon='head_2')),
        >>>     Column(title='Head 2', renderer=RendererText(text='head_1')),
        >>> ]

        Now we can create our Table:

        >>> table = Table(columns=columns, data=table_source)
    """

    MIN_WIDTH = 100
    MIN_HEIGHT = 100

    def __init__(
        self,
        columns,
        id=None,
        style=None,
        data=None,
        multiple_select=False,
        on_select=None,
        on_double_click=None,
        factory=private_factory,
    ):
        super().__init__(id=id, style=style, factory=factory)

        self._columns = []
        for col_index, col in enumerate(columns):
            if isinstance(col, Column):
                self._columns.append(col)
            elif isinstance(col, tuple):
                title, accessor = col
                self._columns.append(Column(title, RendererText(text=accessor)))
            elif isinstance(col, str):
                title = col
                accessor = to_accessor(title)
                self._columns.append(Column(title, RendererText(text=accessor)))
            else:
                raise ValueError("Column must be tuple (title, accessor) or Column")

        self._multiple_select = multiple_select
        self._on_select = None
        self._on_double_click = None
        self._data = ListSource([], [])

        self._impl = self.factory.Table(interface=self)
        if data is not None:
            self.data = data
        self.on_select = on_select
        self.on_double_click = on_double_click

    @property
    def columns(self):
        return self._columns

    @property
    def data(self):
        """The data source of the widget. It accepts table data
        in the form of :obj:`ListSource`

        Returns:
            Returns a (:obj:`ListSource`).
        """
        return self._data

    @data.setter
    def data(self, data):
        self._data = data
        self._data.add_listener(self._impl)
        self._impl.change_source(source=self._data)

    @property
    def multiple_select(self):
        """Does the table allow multiple rows to be selected?"""
        return self._multiple_select

    @property
    def selection(self):
        """The current selection of the table.

        A value of None indicates no selection.
        If the tree allows multiple selection, returns a list of
        selected data nodes. Otherwise, returns a single data node.
        """
        return self._impl.get_selection()

    def scroll_to_top(self):
        """Scroll the view so that the top of the list (first row) is visible"""
        self.scroll_to_row(0)

    def scroll_to_row(self, row):
        """Scroll the view so that the specified row index is visible.

        Args:
            row: The index of the row to make visible. Negative values refer
                 to the nth last row (-1 is the last row, -2 second last,
                 and so on)
        """
        if row >= 0:
            self._impl.scroll_to_row(row)
        else:
            self._impl.scroll_to_row(len(self.data) + row)

    def scroll_to_bottom(self):
        """Scroll the view so that the bottom of the list (last row) is visible"""
        self.scroll_to_row(-1)

    @property
    def on_select(self):
        """The callback function that is invoked when a row of the table is selected.
        The provided callback function has to accept two arguments table (:obj:`Table`)
        and row (``Row`` or ``None``).

        Returns:
            (``callable``) The callback function.
        """
        return self._on_select

    @on_select.setter
    def on_select(self, handler):
        """
        Set the function to be executed on node selection

        :param handler: callback function
        :type handler: ``callable``
        """
        self._on_select = wrapped_handler(self, handler)
        self._impl.set_on_select(self._on_select)

    @property
    def on_double_click(self):
        """The callback function that is invoked when a row of the table is double clicked.
        The provided callback function has to accept two arguments table (:obj:`Table`)
        and row (``Row`` or ``None``).

        Returns:
            (``callable``) The callback function.
        """
        return self._on_double_click

    @on_double_click.setter
    def on_double_click(self, handler):
        """
        Set the function to be executed on node double click

        :param handler: callback function
        :type handler: ``callable``
        """
        self._on_double_click = wrapped_handler(self, handler)
        self._impl.set_on_double_click(self._on_double_click)

    def add_column(self, column, accessor=None):
        """
        Add a new column to the table

        :param column: title of the column or Column instance
        :param accessor: attribute name in data source
        """

        if isinstance(column, str):
            accessor = accessor or to_accessor(column)
            column = Column(title=column, renderer=RendererText(text=accessor))
        elif isinstance(column, Column):
            pass
        else:
            raise ValueError("Column must of type str or column")

        self._columns.append(column)
        self._impl.add_column(column)

        return column

    def remove_column(self, column):
        """
        Remove a table column.

        :param column: Column instance
        """

        try:
            # Remove column
            self._columns.remove(column)
            self._impl.remove_column(column)
        except KeyError:
            raise ValueError('Invalid column: "{}"'.format(column))


class Tree(Widget):
    """Tree Widget

    :param columns: Can be a list of titles to generate columns, a list of tuples
        ``(title, accessor)`` where the accessor defines which column of the data source
        to access, or a list of :class:`Column` instances.
    :param id:  An identifier for this widget.
    :param style: An optional style object. If no style is provided then a new
        one will be created for the widget.
    :param data: The data to display in the widget. Can be an instance of
        :class:`toga.sources.TreeSource`, a list, or tuple with data to
        display in the tree widget, or a class instance which implements the
        interface of :class:`toga.sources.TreeSource`.
    :param multiple_select: Boolean; if ``True``, allows for the selection of
        multiple rows. Defaults to ``False``.
    :param on_select: A handler to be invoked when the user selects one or
        multiple rows.
    :param on_double_click: A handler to be invoked when the user double clicks a row.
    :param factory:: A python module that is capable to return a implementation
        of this class with the same name. (optional; used only for testing)

    Examples:

        Lets prepare a data source first.

        >>> data = {
        >>>    ('father', 38): [('child 1', 17), ('child 1', 15)],
        >>>    ('mother', 42): [('child 1', 17)],
        >>> }
        >>> accessors = ['name', 'age']
        >>> tree_source = TreeSource(data, accessors)

        Columns can be provided in several forms.
        As a list of column titles which will be matched against accessors in the data:

        >>> columns = ['Name', 'Age']

        A list of tuples with column titles and accessors:

        >>> columns = [('Name', 'name'), ('Age', 'age')]

        As ``Column`` instances with a renderer. The renderer determines how a column is
        displayed and how the data is mapped to column properties such as text and icon:

        >>> columns = [
        >>>     Column(title='Name', renderer=RendererText(text='name')),
        >>>     Column(title='Age', renderer=RendererText(text='age')),
        >>> ]

        Now we can create our Table:

        >>> table = Tree(columns=columns, data=tree_source)
    """

    MIN_WIDTH = 100
    MIN_HEIGHT = 100

    def __init__(
        self,
        columns,
        id=None,
        style=None,
        data=None,
        multiple_select=False,
        on_select=None,
        on_double_click=None,
        factory=private_factory,
    ):
        super().__init__(id=id, style=style, factory=factory)

        self._columns = []
        for col_index, col in enumerate(columns):
            if isinstance(col, Column):
                self._columns.append(col)
            elif isinstance(col, tuple):
                title, accessor = col
                self._columns.append(Column(title, RendererText(text=accessor)))
            elif isinstance(col, str):
                title = col
                accessor = to_accessor(title)
                self._columns.append(Column(title, RendererText(text=accessor)))
            else:
                raise ValueError("Column must be tuple (title, accessor) or Column")

        self._multiple_select = multiple_select
        self._data = TreeSource([], [])
        self._on_select = None
        self._on_double_click = None

        self._impl = self.factory.Tree(interface=self)
        if data is not None:
            self.data = data
        self.on_select = on_select
        self.on_double_click = on_double_click

    @property
    def columns(self):
        return self._columns

    @property
    def data(self):
        """
        :returns: The data source of the tree
        :rtype: :class:`toga.sources.TreeSource`
        """
        return self._data

    @data.setter
    def data(self, data):
        """
        Set the data source of the data

        :param data: Data source
        :type data: :class:`toga.sources.TreeSource`
        """
        self._data = data
        self._data.add_listener(self._impl)
        self._impl.change_source(source=self._data)

    @property
    def multiple_select(self):
        """Does the table allow multiple rows to be selected?"""
        return self._multiple_select

    @property
    def selection(self):
        """The current selection of the table.

        A value of None indicates no selection.
        If the tree allows multiple selection, returns a list of
        selected data nodes. Otherwise, returns a single data node.
        """
        return self._impl.get_selection()

    @property
    def on_select(self):
        """
        The callable function for when a node on the Tree is selected. The provided
        callback function has to accept two arguments tree (:obj:`Tree`) and node
        (``Node`` or ``None``).

        :rtype: ``callable``
        """
        return self._on_select

    @on_select.setter
    def on_select(self, handler):
        """
        Set the function to be executed on node select

        :param handler:     callback function
        :type handler:      ``callable``
        """
        self._on_select = wrapped_handler(self, handler)
        self._impl.set_on_select(self._on_select)

    @property
    def on_double_click(self):
        """
        The callable function for when a node on the Tree is selected. The provided
        callback function has to accept two arguments tree (:obj:`Tree`) and node
        (``Node`` or ``None``).

        :rtype: ``callable``
        """
        return self._on_double_click

    @on_double_click.setter
    def on_double_click(self, handler):
        """
        Set the function to be executed on node double click

        :param handler:     callback function
        :type handler:      ``callable``
        """
        self._on_double_click = wrapped_handler(self, handler)
        self._impl.set_on_double_click(self._on_double_click)


# ==== menus and menu items ==============================================================


class MenuItem:
    """
    A menu item to be used in a Menu.

    Args:
        label: A label for the item.
        icon: (optional) a path to an icon resource to decorate the item.
        action: (optional) a function to invoke when the item is clicked.
        submenu: A Menu to use as a submenu. It will become visible when this item is
            clicked.
        factory: A python module that is capable to return a implementation of this class
            with the same name. (optional & normally not needed).
    """

    def __init__(
        self,
        label,
        icon=None,
        checkable=False,
        action=None,
        submenu=None,
        factory=private_factory,
    ):
        self.factory = factory
        self._impl = self.factory.MenuItem(interface=self)

        self._checkable = checkable
        self.action = action
        self.label = label
        self.icon = icon
        self.enabled = self.action is not None
        self.submenu = submenu

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._enabled = value
        if self._impl is not None:
            self._impl.set_enabled(value)

    @property
    def icon(self):
        return self._icon

    @icon.setter
    def icon(self, icon_or_name):
        if isinstance(icon_or_name, Icon) or icon_or_name is None:
            self._icon = icon_or_name
        else:
            self._icon = Icon(icon_or_name)

        self._impl.set_icon(self._icon)

    @property
    def label(self):
        return self._label

    @label.setter
    def label(self, label):
        self._label = label
        self._impl.set_label(label)

    @property
    def submenu(self):
        return self._submenu

    @submenu.setter
    def submenu(self, submenu):
        self._submenu = submenu
        if submenu:
            self._impl.set_submenu(submenu._impl)
        else:
            self._impl.set_submenu(None)

    @property
    def action(self):
        return self._action

    @action.setter
    def action(self, action):

        if self._checkable:

            def new_action(*args):
                self.checked = not self.checked
                action(args)

        else:
            new_action = action

        self._action = wrapped_handler(self, new_action)
        self._impl.set_action(self._action)

    @property
    def checked(self):
        return self._checked

    @checked.setter
    def checked(self, yes):
        if self._checkable:
            self._checked = yes
            self._impl.set_checked(yes)


class MenuItemSeparator:
    """A horizontal separator between menu items."""

    def __init__(self, factory=private_factory):
        self.factory = factory
        self._impl = self.factory.MenuItemSeparator(self)


class Menu:
    """
    A menu, to be used as context menu, status bar menu or in the menu bar.

    Args:
        items: A list of MenuItem.
    """

    def __init__(
        self, items=None, on_open=None, on_close=None, factory=private_factory
    ):
        self.factory = factory
        self._items = []
        self.on_open = on_open
        self.on_close = on_close

        self._impl = self.factory.Menu(self)

        if items:
            self.add(*items)

    def add(self, *items):
        """Add items to the menu."""
        self._items += items
        for item in items:
            self._impl.add_item(item._impl)

    def insert(self, index, item):
        """Insert item at a given index."""
        if item not in self._items:
            self._items.insert(index, item)
            self._impl.insert_item(index, item._impl)

    def remove(self, *items):
        """Remove items from the menu."""
        for item in items:
            try:
                self._items.remove(item)
            except ValueError:
                pass
            else:
                self._impl.remove_item(item._impl)

    def clear(self):
        """Clear the menu (removes all items)"""
        for item in self.items:
            self._impl.remove_item(item._impl)
        self._items.clear()

    @property
    def items(self):
        """All MenuItems in the menu."""
        return self._items

    @property
    def visible(self):
        """True if the menu is currently visible."""
        return self._impl.visible

    @property
    def on_open(self):
        return self._on_open

    @on_open.setter
    def on_open(self, callback):
        self._on_open = wrapped_handler(self, callback)

    @property
    def on_close(self):
        return self._on_close

    @on_close.setter
    def on_close(self, callback):
        self._on_close = wrapped_handler(self, callback)


# ==== StatusBarItem =====================================================================


class StatusBarItem:
    """A status bar item which can have an icon and a menu."""

    def __init__(self, icon, menu=None, factory=private_factory):
        self.factory = factory
        self._impl = self.factory.StatusBarItem(self)

        self.icon = icon
        self.menu = menu

    @property
    def menu(self):
        return self._menu

    @menu.setter
    def menu(self, menu):
        self._menu = menu
        if menu:
            self._impl.set_menu(menu._impl)

    @property
    def icon(self):
        return self._icon

    @icon.setter
    def icon(self, icon_or_name):
        if isinstance(icon_or_name, Icon) or icon_or_name is None:
            self._icon = icon_or_name
        else:
            self._icon = Icon(icon_or_name)

        self._impl.set_icon(self._icon)


# ==== Custom window =====================================================================


class Window(toga.Window):
    def __init__(
        self,
        id=None,
        title=None,
        position=None,
        size=(640, 480),
        toolbar=None,
        resizeable=True,
        closeable=True,
        minimizable=True,
        release_on_close=True,
        is_dialog=False,
        app=None,
        factory=private_factory,
    ):
        initial_position = position or (100, 100)
        super().__init__(
            id,
            title,
            initial_position,
            size,
            toolbar,
            resizeable,
            closeable,
            minimizable,
            factory,
        )
        if app:
            self.app = app

        self.release_on_close = release_on_close
        self.is_dialog = is_dialog

        if not position:
            self.center()

    # visibility and positioning

    @property
    def visible(self):
        return self._impl.is_visible()

    def center(self):
        self._impl.center()

    def raise_(self):
        self.show()
        self._impl.force_to_front()

    def hide(self):
        self._impl.hide()

    # sheet support

    def show_as_sheet(self, window):
        self._impl.show_as_sheet(window)

    @property
    def is_dialog(self):
        return self._is_dialog

    @is_dialog.setter
    def is_dialog(self, yes):
        self._is_dialog = yes
        self._impl.set_dialog(True)

    # memory management

    @property
    def release_on_close(self):
        return self._release_on_close

    @release_on_close.setter
    def release_on_close(self, value):
        self._release_on_close = value
        self._impl.set_release_on_close(value)

    # dialogs

    async def save_file_sheet(
        self, title="", message="", suggested_filename="untitled", file_types=None
    ):
        return await self._impl.save_file_sheet(
            title, message, suggested_filename, file_types
        )

    async def open_file_sheet(
        self,
        title="",
        message="",
        initial_directory=None,
        file_types=None,
        multiselect=False,
    ):
        return await self._impl.open_file_sheet(
            title, message, initial_directory, file_types, multiselect
        )

    async def select_folder_sheet(
        self, title="", message="", initial_directory=None, multiselect=False
    ):
        return await self._impl.select_folder_sheet(
            title, message, initial_directory, multiselect
        )

    async def alert_sheet(
        self,
        title="",
        message="",
        details=None,
        details_title="Traceback",
        button_labels=("Ok",),
        checkbox_text=None,
        level="info",
        icon=None,
    ):

        if not icon and self.app:
            icon = self.app.icon

        return await self._impl.alert_sheet(
            title,
            message,
            details,
            details_title,
            button_labels,
            checkbox_text,
            level,
            icon,
        )


# ==== Application =======================================================================


class SystemTrayApp(toga.App):
    def __init__(
        self,
        formal_name=None,
        app_id=None,
        app_name=None,
        id=None,
        icon=None,
        author=None,
        version=None,
        home_page=None,
        description=None,
        startup=None,
        on_exit=None,
        factory=private_factory,
    ):
        super().__init__(
            formal_name,
            app_id,
            app_name,
            id,
            icon,
            author,
            version,
            home_page,
            description,
            startup,
            on_exit,
            factory,
        )

    def _create_impl(self):
        return self.factory.SystemTrayApp(interface=self)

    def alert(
        self,
        title,
        message,
        details=None,
        details_title="Traceback",
        button_labels=("Ok",),
        checkbox_text=None,
        level="info",
        icon=None,
    ):

        icon = icon or self.icon

        return self._impl.alert(
            title,
            message,
            details,
            details_title,
            button_labels,
            checkbox_text,
            level,
            icon,
        )

    async def alert_async(
        self,
        title,
        message,
        details=None,
        details_title="Traceback",
        button_labels=("Ok",),
        checkbox_text=None,
        level="info",
        icon=None,
    ):

        icon = icon or self.icon

        return await self._impl.alert_async(
            title,
            message,
            details,
            details_title,
            button_labels,
            checkbox_text,
            level,
            icon,
        )


# ==== helpers ===========================================================================


def apply_round_clipping(image_view: toga.ImageView, factory=private_factory):
    """Clips an image in a given toga.ImageView to a circular mask."""
    return factory.apply_round_clipping(image_view._impl)
