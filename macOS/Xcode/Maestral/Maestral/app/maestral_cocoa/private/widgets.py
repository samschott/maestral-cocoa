# -*- coding: utf-8 -*-
import asyncio

# external imports
import click
import toga
from toga.handlers import wrapped_handler
from toga.widgets.base import Widget
from toga.style.pack import Pack
from toga.constants import ROW, RIGHT, TRANSPARENT

# local imports
from .platform import get_platform_factory
from .constants import ON, MIXED, TRUNCATE_TAIL, ImageTemplate


private_factory = get_platform_factory()


# ==== layout widgets ==================================================================


class Spacer(toga.Box):
    """A widget to take up space and push others to the side."""

    def __init__(self, direction=ROW, factory=None):
        style = Pack(flex=1, direction=direction, background_color=TRANSPARENT)
        super().__init__(style=style, factory=factory)


# ==== buttons =========================================================================


class DialogButtons(toga.Box):
    """
    A dialog button box. Buttons will be created from the given list of labels (defaults
    to ['Ok', 'Cancel']). If a callback ``on_press`` is provided, will be executed if
    any button is pressed, with the label of the respective button as an argument.

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
        """
        Returns:
            The button label as a ``str``
        """
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
        """
        Returns:
            The button icon
        """
        return self._icon

    @icon.setter
    def icon(self, value):
        self._icon = value
        self._impl.set_icon(value)
        self._impl.rehint()

    @property
    def on_press(self):
        """The handler to invoke when the button is pressed.

        Returns:
            The function ``callable`` that is called on button press.
        """
        return self._on_press

    @on_press.setter
    def on_press(self, handler):
        """Set the handler to invoke when the button is pressed.

        Args:
            handler (:obj:`callable`): The handler to invoke when the button is pressed.
        """
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
        initial="",
        select_files=True,
        select_folders=False,
        on_select=None,
        dialog_title="",
        dialog_message="",
        show_full_path=False,
        id=None,
        enabled=True,
        style=None,
        factory=private_factory,
    ):
        super().__init__(id, enabled, style, factory)

        self._select_files = select_files
        self._select_folders = select_folders

        # Create a platform specific implementation
        self._impl = self.factory.FileSelectionButton(interface=self)

        # Set all the properties
        self.show_full_path = show_full_path
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
        self._impl.set_current_selection(str(value))

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
    def show_full_path(self):
        return self._show_full_path

    @show_full_path.setter
    def show_full_path(self, value):
        self._show_full_path = value
        self._impl.set_show_full_path(self._show_full_path)

    @property
    def on_select(self):
        return self._on_select

    @on_select.setter
    def on_select(self, handler):
        self._on_select = wrapped_handler(self, handler)
        self._impl.set_on_select(self._on_select)


# ==== labels ==========================================================================


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


# ==== input widgets ===================================================================


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


# ==== icons ===========================================================================


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


# ==== menus and menu items ============================================================


class MenuItem:
    """
    A menu item to be used in a Menu.

    Args:
        label: A label for the item.
        icon: (optional) a path to an icon resource to decorate the item.
        action: (optional) a function to invoke when the item is clicked.
        submenu: A Menu to use as a submenu. It will become visible when this item is
            clicked.
        factory: A python module that is capable to return a implementation of this
            class with the same name. (optional & normally not needed).
    """

    def __init__(
        self,
        label,
        icon=None,
        checkable=False,
        action=None,
        shortcut=None,
        submenu=None,
        factory=private_factory,
    ):
        self.factory = factory
        self._impl = self.factory.MenuItem(interface=self)

        self._checkable = checkable
        self.action = action
        self.label = label
        self.icon = icon
        self.shortcut = shortcut
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
    def shortcut(self):
        return self._shortcut

    @shortcut.setter
    def shortcut(self, value):
        self._shortcut = value
        if self._impl is not None:
            self._impl.set_shortcut(value)

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
                if action:
                    action(args)

        else:
            new_action = action

        self._action = wrapped_handler(self, new_action)
        self._impl.set_action(self._action)

        if self._action:
            self.enabled = True

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


# ==== StatusBarItem ===================================================================


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


# ==== Custom Window ===================================================================


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

    # sheet support

    def show_as_sheet(self, window):
        self._impl.show_as_sheet(window)

    @property
    def is_dialog(self):
        return self._is_dialog

    @is_dialog.setter
    def is_dialog(self, yes):
        self._is_dialog = yes
        self._impl.set_dialog(yes)

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


# ==== Application =====================================================================


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
            formal_name=formal_name,
            app_id=app_id,
            app_name=app_name,
            id=id,
            icon=icon,
            author=author,
            version=version,
            home_page=home_page,
            description=description,
            startup=startup,
            on_exit=on_exit,
            factory=factory,
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


# ==== helpers =========================================================================


def apply_round_clipping(image_view: toga.ImageView, factory=private_factory):
    """Clips an image in a given toga.ImageView to a circular mask."""
    return factory.apply_round_clipping(image_view._impl)
